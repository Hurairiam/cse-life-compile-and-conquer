"""
tools/level_editor.py
CSE Life: Compile & Conquer — Level editor
─────────────────────────────────────────────────────────────
Standalone level editor.

    python -m tools.level_editor [levels/<file>.json]

pygame IS allowed here: the editor is asset tooling, the same
class as assemble_sprite_sheet.py (Spec §1). What is NOT allowed
is game state — this app imports `content/` (the registries and
the level document model) and its own `tools/` chrome, and
nothing else. It reads and writes `levels/*.json`; the game only
ever reads them.

Layout (Spec §3.1):

    ┌─────────────────────────────────────┬──────────────┐
    │ TOP BAR  44 px                      │              │
    ├─────────────────────────────────────┤  SIDE PANEL  │
    │            CANVAS                   │    280 px    │
    └─────────────────────────────────────┴──────────────┘

Hotkeys (Spec §8): 1-4 tabs · LMB paint · RMB entity settings ·
X+LMB erase · MMB/arrows pan · +/- zoom · Ctrl+S/O/N ·
Ctrl+Z/Y undo/redo · G grid · B badges · F11 fullscreen ·
ESC close popup / clear selection.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Callable, List, Optional, Tuple

import pygame

if __package__ in (None, ""):        # allow `python tools/level_editor.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))

from content.level_registry import (
    AMBIENT_PRESETS,
    DEFAULT_GROUND_TILE,
    EMPTY_TILE,
    GRID_MAX,
    GRID_MIN,
    LAYER_GROUND,
    LAYER_OVERLAY,
    NPC_REGISTRY,
    PROP_REGISTRY,
    TILE_REGISTRY,
    get_npc_type_ids,
    get_prop_type_ids,
    get_tile_def,
    get_tile_indices,
    get_tile_layer,
)
from content.level_schema import (
    LEVELS_DIR,
    SCHEMA_VERSION,
    GateData,
    LevelData,
    LevelSchemaError,
    level_path,
    list_level_files,
    read_level,
    write_level,
)
from tools import editor_theme as th
from tools.editor_assets import AssetCache
from tools.editor_popups import (
    CANCEL,
    ConfirmPopup,
    FilePickerPopup,
    GatePopup,
    MessagePopup,
    NewLevelPopup,
    NewZonePopup,
    NpcDialogPopup,
    PropSettingsPopup,
    ValidationPopup,
    slugify,
)
from tools.editor_widgets import ChipRow, PaletteGrid, PaletteItem, Stepper, TextInput

# ─────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────

WINDOW_SIZE = (th.SCREEN_W, th.SCREEN_H)
WINDOWED_FLAGS = pygame.SCALED
FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

TOP_BAR = pygame.Rect(0, 0, th.SCREEN_W, th.TOP_BAR_H)
CANVAS = pygame.Rect(0, th.TOP_BAR_H, th.SCREEN_W - th.SIDE_PANEL_W,
                     th.SCREEN_H - th.TOP_BAR_H)
SIDE_PANEL = pygame.Rect(CANVAS.right, th.TOP_BAR_H, th.SIDE_PANEL_W,
                         th.SCREEN_H - th.TOP_BAR_H)

BAR_BTN_Y = 6
BAR_BTN_H = 32
BAR_ICON = 20

# ZONES is the F6 addition (Feature 6). SETTINGS moved from index 3
# to 4, so every branch on the tab index now goes through these names
# rather than a bare number.
TAB_TILES = 0
TAB_PROPS = 1
TAB_NPCS = 2
TAB_ZONES = 3
TAB_SETTINGS = 4
TAB_NAMES = ("TILES", "PROPS", "NPCS", "ZONES", "SETTINGS")
TAB_H = 36
TAB_Y = SIDE_PANEL.y + 10
TAB_COLUMNS = 3          # 3 tabs on the first row, the rest on the second
TAB_ROWS = (len(TAB_NAMES) + TAB_COLUMNS - 1) // TAB_COLUMNS
PANEL_PAD = 10
SECTION_Y = TAB_Y + TAB_ROWS * (TAB_H + 4) + 12
FOOTER_H = 76

# Pixel size of one cell on screen. Every step is an integer multiple
# of the 16 px source art, so the pixels stay crisp (Spec §3.3); 48 is
# the game-true size and the default.
ZOOM_STEPS = (32, 48, 96)
DEFAULT_ZOOM = 1

UNDO_LIMIT = 60          # Spec §3.3 asks for >= 50

TOOL_NONE = ""
TOOL_ERASER = "eraser"
ERASER_KEY = "__eraser__"


# ─────────────────────────────────────────────────────────────
# UNDO
# ─────────────────────────────────────────────────────────────


class UndoStack:
    """
    Whole-document snapshots (Spec §3.3, >= 50 steps).

    A 40x24 level is a few hundred kilobytes of plain lists, so
    snapshotting is far cheaper than a command log and cannot drift
    out of sync with the document — every paint, erase, placement and
    settings edit is covered by construction.
    """

    def __init__(self, limit: int = UNDO_LIMIT) -> None:
        self.__undo: List[LevelData] = []
        self.__redo: List[LevelData] = []
        self.__limit: int = limit

    def record(self, level: LevelData) -> None:
        """Snapshot the state BEFORE a change; clears the redo branch."""
        self.__undo.append(level.clone())
        if len(self.__undo) > self.__limit:
            self.__undo.pop(0)
        self.__redo.clear()

    def undo(self, current: LevelData) -> Optional[LevelData]:
        """Step back one change, or None when there is nothing to undo."""
        if not self.__undo:
            return None
        self.__redo.append(current.clone())
        return self.__undo.pop()

    def redo(self, current: LevelData) -> Optional[LevelData]:
        """Step forward again, or None."""
        if not self.__redo:
            return None
        self.__undo.append(current.clone())
        return self.__redo.pop()

    def clear(self) -> None:
        """Drop all history — used when a different file is opened."""
        self.__undo.clear()
        self.__redo.clear()

    def get_depth(self) -> Tuple[int, int]:
        """(undo steps, redo steps) for the status readout."""
        return (len(self.__undo), len(self.__redo))


# ─────────────────────────────────────────────────────────────
# THE APP
# ─────────────────────────────────────────────────────────────


class LevelEditorApp:
    """
    The editor application: document, view, tools and input routing.

    OOP: Encapsulation — the document, the camera and the tool state
    are all private. Drawing is split into one method per region so
    each stays readable, and every popup is a self-contained object
    that hands back a value for this class to apply.
    """

    def __init__(self, open_path: str = "",
                 levels_dir: str = LEVELS_DIR) -> None:
        self.__levels_dir: str = levels_dir
        pygame.init()
        pygame.display.set_caption("CSE Life — Level Editor")
        self.__window: pygame.Surface = pygame.display.set_mode(
            WINDOW_SIZE, WINDOWED_FLAGS)
        self.__clock: pygame.time.Clock = pygame.time.Clock()
        self.__fullscreen: bool = False
        self.__running: bool = True

        self.__assets: AssetCache = AssetCache()
        self.__undo: UndoStack = UndoStack()
        self.__level: LevelData = LevelData("New Level", "new_level", 40, 24)
        self.__dirty: bool = False
        self.__status: str = ""
        self.__status_timer: float = 0.0

        # view
        self.__zoom: int = DEFAULT_ZOOM
        self.__cam_x: int = 0
        self.__cam_y: int = 0
        self.__panning: bool = False
        self.__show_grid: bool = True
        self.__show_badges: bool = True
        self.__grid_layer: pygame.Surface = pygame.Surface(CANVAS.size,
                                                           pygame.SRCALPHA)

        # tools
        self.__tab: int = TAB_TILES
        self.__selection_kind: str = TOOL_NONE
        self.__selection_key: str = ""
        self.__painting: bool = False
        self.__spawn_arm: bool = False
        self.__hover_cell: Optional[Tuple[int, int]] = None
        self.__editing_uid: str = ""

        # zone tool (F6): the in-progress drag, and which zone the
        # gate popup is currently editing
        self.__zone_anchor: Optional[Tuple[int, int]] = None
        self.__zone_drag: Optional[Tuple[int, int]] = None
        self.__zone_selected: str = ""
        self.__pending_zone: Optional[dict] = None
        self.__gate_target: Tuple[str, str] = ("", "")

        self.__palette: PaletteGrid = PaletteGrid(self.__palette_rect())
        self.__rebuild_palette()
        self.__build_settings_widgets()

        # modal state
        self.__modal: Optional[Any] = None
        self.__pending: Optional[Callable[[], None]] = None

        if open_path:
            self.__open_file(open_path)
        self.__center_camera()

    # ─────────────────────────────────────────────────────────
    # DOCUMENT
    # ─────────────────────────────────────────────────────────

    def __set_dirty(self, dirty: bool = True) -> None:
        """Flip the unsaved-changes marker shown next to the level name."""
        self.__dirty = dirty

    def __set_status(self, text: str) -> None:
        """Show a transient line in the top bar for a few seconds."""
        self.__status = text
        self.__status_timer = 4.0

    def __record(self) -> None:
        """Snapshot before a mutation and mark the document dirty."""
        self.__undo.record(self.__level)
        self.__set_dirty(True)

    def __open_file(self, path: str) -> None:
        """Read a level from disk, replacing the document and history."""
        try:
            self.__level = read_level(path)
        except LevelSchemaError as error:
            self.__modal = MessagePopup("CANNOT OPEN", [str(error)[:60]])
            return
        self.__undo.clear()
        self.__set_dirty(False)
        self.__clear_selection()
        self.__center_camera()
        self.__sync_settings()
        self.__set_status(f"Opened {os.path.basename(path)}")

    def __save(self) -> None:
        """
        Validate, then write `levels/<level_id>.json`. Blockers abort
        the write and open the report; warnings are saved and listed.
        """
        path = level_path(self.__level.get_level_id(), self.__levels_dir)
        report = write_level(self.__level, path)
        if not report.is_saveable():
            self.__modal = ValidationPopup(report, "CANNOT SAVE")
            return
        self.__set_dirty(False)
        self.__sync_settings()
        self.__set_status(f"Saved {os.path.basename(path)}")
        if report.get_warnings():
            self.__modal = ValidationPopup(report, "SAVED WITH WARNINGS")

    def __guard_unsaved(self, action: Callable[[], None]) -> None:
        """Run `action`, asking first if there are unsaved changes."""
        if not self.__dirty:
            action()
            return
        self.__pending = action
        self.__modal = ConfirmPopup(
            "UNSAVED CHANGES",
            ["This level has unsaved edits.", "Discard them and continue?"],
            th.BAR_OVER, "DISCARD")

    # ─────────────────────────────────────────────────────────
    # VIEW
    # ─────────────────────────────────────────────────────────

    def __cell_px(self) -> int:
        """Screen size of one cell at the current zoom."""
        return ZOOM_STEPS[self.__zoom]

    def __world_size(self) -> Tuple[int, int]:
        """The whole level in screen pixels."""
        cell = self.__cell_px()
        return (self.__level.get_grid_width() * cell,
                self.__level.get_grid_height() * cell)

    def __clamp_camera(self) -> None:
        """
        Keep the level roughly on screen. A quarter-canvas of slack on
        each side lets you work comfortably at the map's edges.
        """
        world_w, world_h = self.__world_size()
        slack_x, slack_y = CANVAS.w // 4, CANVAS.h // 4
        self.__cam_x = max(-slack_x, min(world_w - CANVAS.w + slack_x,
                                         self.__cam_x))
        self.__cam_y = max(-slack_y, min(world_h - CANVAS.h + slack_y,
                                         self.__cam_y))

    def __center_camera(self) -> None:
        """Centre the view on the level."""
        world_w, world_h = self.__world_size()
        self.__cam_x = (world_w - CANVAS.w) // 2
        self.__cam_y = (world_h - CANVAS.h) // 2
        self.__clamp_camera()

    def focus_cell(self, cell: Tuple[int, int]) -> None:
        """
        Centre the view on one cell. Public because it is how the
        validation report jumps to an offending cell, and how any
        outside driver (the screenshot harness, the tests) brings a
        cell on screen before clicking it.
        """
        cell_px = self.__cell_px()
        self.__cam_x = cell[0] * cell_px - CANVAS.w // 2
        self.__cam_y = cell[1] * cell_px - CANVAS.h // 2
        self.__clamp_camera()

    def __set_zoom(self, index: int) -> None:
        """Zoom about the centre of the canvas so the view stays put."""
        index = max(0, min(len(ZOOM_STEPS) - 1, index))
        if index == self.__zoom:
            return
        before = self.__cell_px()
        centre = ((self.__cam_x + CANVAS.w // 2) / before,
                  (self.__cam_y + CANVAS.h // 2) / before)
        self.__zoom = index
        after = self.__cell_px()
        self.__cam_x = int(centre[0] * after) - CANVAS.w // 2
        self.__cam_y = int(centre[1] * after) - CANVAS.h // 2
        self.__clamp_camera()

    def __cell_at(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Grid cell under a screen position, or None outside the level."""
        if not CANVAS.collidepoint(pos):
            return None
        cell = self.__cell_px()
        x = (pos[0] - CANVAS.x + self.__cam_x) // cell
        y = (pos[1] - CANVAS.y + self.__cam_y) // cell
        if self.__level.is_inside(x, y):
            return (int(x), int(y))
        return None

    def __cell_screen_rect(self, x: int, y: int) -> pygame.Rect:
        """Screen rect of a grid cell."""
        cell = self.__cell_px()
        return pygame.Rect(CANVAS.x + x * cell - self.__cam_x,
                           CANVAS.y + y * cell - self.__cam_y, cell, cell)

    # ─────────────────────────────────────────────────────────
    # PALETTE + SELECTION
    # ─────────────────────────────────────────────────────────

    def __palette_rect(self) -> pygame.Rect:
        """Where the palette grid lives inside the side panel."""
        return pygame.Rect(SIDE_PANEL.x + PANEL_PAD, SECTION_Y,
                           SIDE_PANEL.w - PANEL_PAD * 2,
                           SIDE_PANEL.bottom - SECTION_Y - FOOTER_H)

    def __rebuild_palette(self) -> None:
        """Fill the palette with the active tab's registry entries."""
        items: List[PaletteItem] = []
        if self.__tab in (TAB_TILES, TAB_PROPS, TAB_NPCS):
            items.append(PaletteItem(ERASER_KEY, "erase", TOOL_ERASER))
        if self.__tab == TAB_TILES:
            for index in get_tile_indices():
                items.append(PaletteItem(str(index),
                                         TILE_REGISTRY[index]["name"], "tile"))
        elif self.__tab == TAB_PROPS:
            for type_id in get_prop_type_ids():
                items.append(PaletteItem(
                    type_id, PROP_REGISTRY[type_id].get("name", type_id),
                    "prop"))
        elif self.__tab == TAB_NPCS:
            for type_id in get_npc_type_ids():
                items.append(PaletteItem(
                    type_id, NPC_REGISTRY[type_id].get("name", type_id),
                    "npc"))
        self.__palette.set_items(items)

    def __palette_sprite(self, item: PaletteItem,
                         size: int) -> Optional[pygame.Surface]:
        """
        Preview art for one palette cell. NPCs show their `level_editor`
        frame here — the `idle` sheet is what stands in the map.
        """
        kind = item.get_kind()
        if kind == "tile":
            return self.__assets.get_tile(int(item.get_key()), size)
        if kind == "prop":
            return self.__assets.get_prop(item.get_key(), size)
        if kind == "npc":
            return self.__assets.get_npc_editor(item.get_key(), size)
        return None

    # ─────────────────────────────────────────────────────────
    # SETTINGS SECTION  (Spec §4.4)
    # ─────────────────────────────────────────────────────────

    def __build_settings_widgets(self) -> None:
        """
        Create the SETTINGS form once and reposition nothing afterwards
        (fixed pixel layout, Style Guide §4.1). `__sync_settings` pushes
        the document into these widgets whenever the document changes.
        """
        x = SIDE_PANEL.x + PANEL_PAD
        width = SIDE_PANEL.w - PANEL_PAD * 2
        y = SECTION_Y
        self.__field_name: TextInput = TextInput(
            pygame.Rect(x, y + 14, width, 28), "", 40)
        self.__field_id: TextInput = TextInput(
            pygame.Rect(x, y + 62, width, 28), "", 40,
            lambda c: c in "abcdefghijklmnopqrstuvwxyz0123456789_")
        self.__step_w: Stepper = Stepper(
            pygame.Rect(x, y + 122, 120, 28), 40, GRID_MIN, GRID_MAX, 1)
        self.__step_h: Stepper = Stepper(
            pygame.Rect(x + 130, y + 122, 120, 28), 24, GRID_MIN, GRID_MAX, 1)
        self.__btn_resize: pygame.Rect = pygame.Rect(x, y + 156, width, 26)
        self.__chips_ambient: ChipRow = ChipRow(
            pygame.Rect(x, y + 202, width, 24), list(AMBIENT_PRESETS), "day",
            4)
        self.__field_music: TextInput = TextInput(
            pygame.Rect(x, y + 246, width, 28), "", 60)
        self.__btn_spawn: pygame.Rect = pygame.Rect(x, y + 288, width, 28)
        self.__btn_validate: pygame.Rect = pygame.Rect(x, y + 324, width, 28)
        self.__saved_id: str = ""
        self.__sync_settings()

    def __sync_settings(self) -> None:
        """Reload the form from the document (after open / new / undo)."""
        self.__field_name.set_text(self.__level.get_level_name())
        self.__field_id.set_text(self.__level.get_level_id())
        self.__step_w.set_value(self.__level.get_grid_width())
        self.__step_h.set_value(self.__level.get_grid_height())
        self.__chips_ambient.set_value(self.__level.get_ambient())
        self.__field_music.set_text(self.__level.get_music())
        source = self.__level.get_source_path()
        self.__saved_id = os.path.splitext(os.path.basename(source))[0] \
            if source else ""

    def __handle_settings_event(self, event: pygame.event.Event) -> bool:
        """Route an event to the SETTINGS form. True when consumed."""
        if self.__field_name.handle_event(event):
            if self.__field_name.take_changed() and \
                    self.__level.set_level_name(self.__field_name.get_text()):
                self.__set_dirty(True)
            return True
        if self.__field_id.handle_event(event):
            if self.__field_id.take_changed():
                if self.__level.set_level_id(
                        slugify(self.__field_id.get_text())):
                    self.__set_dirty(True)
            return True
        if self.__field_music.handle_event(event):
            if self.__field_music.take_changed():
                self.__level.set_music(self.__field_music.get_text())
                self.__set_dirty(True)
            return True
        if self.__chips_ambient.handle_event(event):
            if self.__level.set_ambient(self.__chips_ambient.get_value()):
                self.__set_dirty(True)
            return True
        if self.__step_w.handle_event(event) or \
                self.__step_h.handle_event(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.__btn_resize.collidepoint(event.pos):
                self.__request_resize()
                return True
            if self.__btn_spawn.collidepoint(event.pos):
                self.__clear_selection()
                self.__spawn_arm = True
                self.__set_status("Click a cell to place the spawn")
                return True
            if self.__btn_validate.collidepoint(event.pos):
                self.__modal = ValidationPopup(self.__level.validate())
                return True
        return False

    def __request_resize(self) -> None:
        """Resize the grid, warning first when content would be deleted."""
        width = int(self.__step_w.get_value())
        height = int(self.__step_h.get_value())
        if (width, height) == (self.__level.get_grid_width(),
                               self.__level.get_grid_height()):
            return
        lost = self.__level.count_out_of_range(width, height)
        if lost > 0:
            self.__pending = lambda: self.__apply_resize(width, height)
            self.__modal = ConfirmPopup(
                "SHRINKING THE GRID",
                [f"{lost} prop(s)/NPC(s) fall outside",
                 f"{width} x {height} and will be deleted.",
                 "Continue?"], th.BAR_OVER, "RESIZE")
            return
        self.__apply_resize(width, height)

    def __apply_resize(self, width: int, height: int) -> None:
        """Commit a grid resize as one undo step."""
        self.__record()
        if self.__level.resize(width, height, DEFAULT_GROUND_TILE):
            self.__set_status(f"Grid is now {width} x {height}")
            self.__clamp_camera()
        self.__sync_settings()

    def __clear_selection(self) -> None:
        """Drop the active tool."""
        self.__selection_kind = TOOL_NONE
        self.__selection_key = ""
        self.__spawn_arm = False

    def __select(self, item: PaletteItem) -> None:
        """
        Owner-specified selection model (Spec §4): clicking the selected
        item unselects it, clicking another moves the selection, and only
        ONE item is selected across all sections at a time.
        """
        if self.__selection_key == item.get_key():
            self.__clear_selection()
            return
        self.__selection_kind = item.get_kind()
        self.__selection_key = item.get_key()
        self.__spawn_arm = False

    def __tool_readout(self) -> str:
        """The `TILE: path` line at the right end of the top bar."""
        if self.__spawn_arm:
            return "SET SPAWN"
        if self.__selection_kind == TOOL_ERASER:
            return "ERASER"
        if self.__selection_kind == "tile":
            entry = get_tile_def(int(self.__selection_key))
            return f"TILE: {entry['name']}" if entry else "TILE: ?"
        if self.__selection_kind in ("prop", "npc"):
            return f"{self.__selection_kind.upper()}: {self.__selection_key}"
        return "NO TOOL"

    # ─────────────────────────────────────────────────────────
    # EDITING
    # ─────────────────────────────────────────────────────────

    def __apply_tool(self, cell: Tuple[int, int]) -> None:
        """Apply the active tool to one cell. Undo is recorded by caller."""
        x, y = cell
        if self.__spawn_arm:
            if self.__level.set_spawn(x, y):
                self.__set_status(f"Spawn moved to ({x},{y})")
            self.__spawn_arm = False
            return
        if self.__selection_kind == TOOL_ERASER:
            self.__erase(cell)
            return
        if self.__selection_kind == "tile":
            index = int(self.__selection_key)
            self.__level.set_tile(get_tile_layer(index), x, y, index)
        elif self.__selection_kind == "prop":
            self.__level.add_prop(self.__selection_key, x, y)
        elif self.__selection_kind == "npc":
            self.__level.add_npc(self.__selection_key, x, y)

    def __erase(self, cell: Tuple[int, int]) -> None:
        """
        Top-down erase (Spec §3.3): the topmost thing on the cell goes
        first — NPC, then prop, then the overlay tile, and finally the
        ground resets to the default fill (ground can never be empty).
        """
        x, y = cell
        if self.__level.remove_npc_at(x, y):
            return
        if self.__level.remove_prop_at(x, y):
            return
        if self.__level.get_tile(LAYER_OVERLAY, x, y) != EMPTY_TILE:
            self.__level.set_tile(LAYER_OVERLAY, x, y, EMPTY_TILE)
            return
        self.__level.set_tile(LAYER_GROUND, x, y, DEFAULT_GROUND_TILE)

    def __is_erasing(self) -> bool:
        """True while the eraser tool or the X-key shortcut is active."""
        return (self.__selection_kind == TOOL_ERASER
                or pygame.key.get_pressed()[pygame.K_x])

    # ── zone tool (Feature 6, phase F6) ───────────────────────

    def __zone_drag_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """
        The (x, y, w, h) the current drag covers, or None.

        Normalised, so dragging up-left works exactly like down-right --
        an author should not have to think about which corner they
        started from.
        """
        if self.__zone_anchor is None or self.__zone_drag is None:
            return None
        ax, ay = self.__zone_anchor
        bx, by = self.__zone_drag
        x, y = min(ax, bx), min(ay, by)
        return (x, y, abs(bx - ax) + 1, abs(by - ay) + 1)

    def __begin_zone_drag(self, cell: Tuple[int, int]) -> None:
        """
        Start dragging a new zone, or select an existing one.

        Clicking inside a zone selects it rather than starting a new
        overlapping one -- otherwise editing a zone would mean drawing
        a second one on top of it every time.
        """
        existing = self.__level.get_zone_at(*cell)
        if existing is not None and self.__zone_selected != existing.get_uid():
            self.__zone_selected = existing.get_uid()
            self.__set_status(f"Selected zone {existing.get_zone_id()}")
            return
        self.__zone_anchor = cell
        self.__zone_drag = cell

    def __finish_zone_drag(self) -> None:
        """Release: hand the rectangle to NewZonePopup, then GatePopup."""
        rect = self.__zone_drag_rect()
        self.__zone_anchor = None
        self.__zone_drag = None
        if rect is None:
            return
        self.__modal = NewZonePopup(
            rect, f"zone_{self.__level.get_zone_count() + 1}")

    def __create_zone(self, rect: Tuple[int, int, int, int],
                      names: dict) -> None:
        """Commit a named zone, then chain straight into its gate form."""
        x, y, w, h = rect
        self.__record()
        zone = self.__level.add_zone(x, y, w, h)
        if zone is None:
            self.__set_status("Zone rectangle is outside the grid")
            return
        zone.set_zone_id(names.get("zone_id", "zone"))
        zone.set_display_name(names.get("display_name", ""))
        self.__zone_selected = zone.get_uid()
        self.__set_dirty(True)
        self.__gate_target = ("zone", zone.get_uid())
        self.__modal = GatePopup(zone.get_gate(),
                                 zone.get_display_name()
                                 or zone.get_zone_id())

    def __open_gate_popup(self, kind: str, uid: str) -> None:
        """
        Open the gate form for a prop, an NPC or a zone.

        An NPC with no gate yet is seeded from the roster
        (PHASELOG_F5 §4.6) so gating Prof. Hoque's conversation starts
        at the semester Ayesha already said he appears in.
        """
        seed = 0
        label = uid
        if kind == "prop":
            entity = self.__find_prop(uid)
        elif kind == "npc":
            entity = self.__find_npc(uid)
            if entity is not None:
                seed = entity.make_default_gate().get_min_semester()
        else:
            entity = self.__level.get_zone(uid)
            if entity is not None:
                label = entity.get_display_name() or entity.get_zone_id()
        if entity is None:
            return
        self.__gate_target = (kind, uid)
        self.__modal = GatePopup(entity.get_gate(), label, seed)

    def __find_prop(self, uid: str):
        """The prop with this uid, or None."""
        return next((p for p in self.__level.get_props()
                     if p.get_uid() == uid), None)

    def __find_npc(self, uid: str):
        """The NPC with this uid, or None."""
        return next((n for n in self.__level.get_npcs()
                     if n.get_uid() == uid), None)

    def __apply_gate(self, data: dict) -> None:
        """Fold a finished gate form back onto whatever opened it."""
        kind, uid = self.__gate_target
        self.__gate_target = ("", "")
        if not kind or not uid:
            return
        gate = GateData.from_dict(data)
        self.__record()
        if kind == "zone":
            target = self.__level.get_zone(uid)
        elif kind == "prop":
            target = self.__find_prop(uid)
        else:
            target = self.__find_npc(uid)
        if target is None:
            return
        target.set_gate(gate)
        self.__set_dirty(True)
        self.__set_status("Gate updated" if gate.has_requirements()
                          else "Gate cleared")

    def __open_gate_at(self, cell: Tuple[int, int]) -> None:
        """
        Right-click on the ZONES tab: gate whatever is under the cursor.

        Prop first, then NPC, then zone -- the same precedence
        LevelData.get_gate_at() uses at runtime, so what the author
        edits is what the player will meet.
        """
        prop = self.__level.get_prop_at(*cell)
        if prop is not None:
            self.__open_gate_popup("prop", prop.get_uid())
            return
        npc = self.__level.get_npc_at(*cell)
        if npc is not None:
            self.__open_gate_popup("npc", npc.get_uid())
            return
        zone = self.__level.get_zone_at(*cell)
        if zone is not None:
            self.__zone_selected = zone.get_uid()
            self.__open_gate_popup("zone", zone.get_uid())
            return
        self.__set_status("Nothing to gate on this cell")

    def __delete_selected_zone(self) -> None:
        """Remove the selected zone, if there is one."""
        if not self.__zone_selected:
            return
        self.__record()
        if self.__level.remove_zone(self.__zone_selected):
            self.__zone_selected = ""
            self.__set_dirty(True)
            self.__set_status("Zone deleted")

    def __begin_stroke(self, cell: Tuple[int, int]) -> None:
        """Start a paint/erase drag: one undo step for the whole stroke."""
        if self.__tab == TAB_ZONES:
            self.__begin_zone_drag(cell)
            return
        if self.__is_erasing():
            self.__record()
            self.__painting = True
            self.__erase(cell)
            return
        if self.__spawn_arm or self.__selection_kind != TOOL_NONE:
            self.__record()
            self.__painting = self.__selection_kind == "tile"
            self.__apply_tool(cell)

    def __continue_stroke(self, cell: Tuple[int, int]) -> None:
        """Keep painting while the button is held."""
        if not self.__painting:
            return
        if self.__is_erasing():
            self.__erase(cell)
        else:
            self.__apply_tool(cell)

    def __undo_step(self) -> None:
        """Ctrl+Z."""
        restored = self.__undo.undo(self.__level)
        if restored is None:
            self.__set_status("Nothing to undo")
            return
        self.__level = restored
        self.__set_dirty(True)
        self.__sync_settings()

    def __redo_step(self) -> None:
        """Ctrl+Y."""
        restored = self.__undo.redo(self.__level)
        if restored is None:
            self.__set_status("Nothing to redo")
            return
        self.__level = restored
        self.__set_dirty(True)
        self.__sync_settings()

    # ─────────────────────────────────────────────────────────
    # TOP BAR ACTIONS
    # ─────────────────────────────────────────────────────────

    def __bar_button_rects(self) -> List[pygame.Rect]:
        """NEW / SAVE / LOAD hit boxes, left-packed with 22 px gaps."""
        rects: List[pygame.Rect] = []
        x = 10
        for width in (96, 100, 100):
            rects.append(pygame.Rect(x, BAR_BTN_Y, width, BAR_BTN_H))
            x += width + 22
        return rects

    def __action_new(self) -> None:
        """Open the NEW dialog (after the unsaved-changes guard)."""
        self.__modal = NewLevelPopup()

    def __action_load(self) -> None:
        """Open the LOAD picker (after the unsaved-changes guard)."""
        self.__modal = FilePickerPopup(list_level_files(self.__levels_dir))

    def __create_level(self, settings: dict) -> None:
        """Replace the document with a fresh level from the NEW dialog."""
        self.__level = LevelData(settings["name"], settings["level_id"],
                                 settings["width"], settings["height"],
                                 DEFAULT_GROUND_TILE)
        self.__undo.clear()
        self.__set_dirty(True)
        self.__clear_selection()
        self.__center_camera()
        self.__sync_settings()
        self.__set_status(f"New level '{settings['level_id']}'")

    # ─────────────────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route one event: modal first, then chrome, then the canvas."""
        if event.type == pygame.QUIT:
            self.__guard_unsaved(self.__quit)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.__toggle_fullscreen()
            return

        if self.__modal is not None:
            self.__modal.handle_event(event)
            return

        # The SETTINGS form owns the keyboard whenever one of its fields
        # has focus, so typing a level name never fires a hotkey.
        if self.__tab == TAB_SETTINGS and self.__handle_settings_event(event):
            return

        if event.type == pygame.KEYDOWN:
            self.__handle_key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.__handle_mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in (1, 2):
                if event.button == 1 and self.__zone_anchor is not None:
                    self.__finish_zone_drag()
                self.__painting = False
                self.__panning = False
        elif event.type == pygame.MOUSEMOTION:
            self.__handle_motion(event)
        elif event.type == pygame.MOUSEWHEEL:
            self.__palette.handle_event(event)

    def __handle_key(self, event: pygame.event.Event) -> None:
        """Hotkeys (Spec §8)."""
        ctrl = event.mod & pygame.KMOD_CTRL
        if ctrl and event.key == pygame.K_s:
            self.__save()
        elif ctrl and event.key == pygame.K_o:
            self.__guard_unsaved(self.__action_load)
        elif ctrl and event.key == pygame.K_n:
            self.__guard_unsaved(self.__action_new)
        elif ctrl and event.key == pygame.K_z:
            self.__undo_step()
        elif ctrl and event.key == pygame.K_y:
            self.__redo_step()
        elif event.key == pygame.K_ESCAPE:
            self.__clear_selection()
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                           pygame.K_5):
            self.__set_tab(event.key - pygame.K_1)
        elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.__set_zoom(self.__zoom + 1)
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.__set_zoom(self.__zoom - 1)
        elif event.key == pygame.K_g:
            self.__show_grid = not self.__show_grid
        elif event.key == pygame.K_b:
            self.__show_badges = not self.__show_badges

    def __handle_mouse_down(self, event: pygame.event.Event) -> None:
        """Clicks on the top bar, the side panel or the canvas."""
        pos = event.pos
        if event.button == 2:
            self.__panning = True
            return

        if TOP_BAR.collidepoint(pos) and event.button == 1:
            index = th.hit(self.__bar_button_rects(), pos)
            if index == 0:
                self.__guard_unsaved(self.__action_new)
            elif index == 1:
                self.__save()
            elif index == 2:
                self.__guard_unsaved(self.__action_load)
            elif self.__name_label_rect().collidepoint(pos):
                self.__set_tab(TAB_SETTINGS)
            return

        if SIDE_PANEL.collidepoint(pos) and event.button == 1:
            self.__handle_side_panel_click(pos)
            return

        cell = self.__cell_at(pos)
        if cell is None:
            return
        if event.button == 1:
            self.__begin_stroke(cell)
        elif event.button == 3:
            if self.__tab == TAB_ZONES:
                self.__open_gate_at(cell)
            else:
                self.__open_entity_settings(cell)

    def __handle_side_panel_click(self, pos: Tuple[int, int]) -> None:
        """Tab bar first, then the active section."""
        index = th.hit(self.__tab_rects(), pos)
        if index >= 0:
            self.__set_tab(index)
            return
        if self.__tab == TAB_ZONES:
            self.__handle_zone_panel_click(pos)
            return
        item = self.__palette.item_at(pos)
        if item is not None:
            self.__select(item)

    def __handle_zone_panel_click(self, pos: Tuple[int, int]) -> None:
        """Select a zone from the list, or delete the selected one."""
        if self.__zone_selected and \
                self.__zone_delete_rect().collidepoint(pos):
            self.__delete_selected_zone()
            return
        row = th.hit(self.__zone_row_rects(), pos)
        if row >= 0:
            zone = self.__level.get_zones()[row]
            self.__zone_selected = zone.get_uid()
            x, y, _, _ = zone.get_rect()
            self.focus_cell((x, y))

    def __handle_motion(self, event: pygame.event.Event) -> None:
        """Hover tracking, drag-painting and middle-drag panning."""
        self.__hover_cell = self.__cell_at(event.pos)
        if self.__panning:
            self.__cam_x -= event.rel[0]
            self.__cam_y -= event.rel[1]
            self.__clamp_camera()
            return
        if self.__zone_anchor is not None and self.__hover_cell is not None:
            self.__zone_drag = self.__hover_cell
            return
        if self.__painting and self.__hover_cell is not None:
            self.__continue_stroke(self.__hover_cell)

    def __set_tab(self, index: int) -> None:
        """Switch side-panel section (hotkeys 1-4)."""
        if not 0 <= index < len(TAB_NAMES):
            return
        self.__tab = index
        self.__rebuild_palette()

    def __open_entity_settings(self, cell: Tuple[int, int]) -> None:
        """
        Right-click on a placed entity opens its settings popup. Tiles
        have no per-instance settings (Spec §4.1), so right-clicking
        bare ground does nothing. NPCs sit above props on a shared cell.
        """
        npc = self.__level.get_npc_at(*cell)
        if npc is not None:
            self.__editing_uid = npc.get_uid()
            self.__modal = NpcDialogPopup(npc, self.__assets)
            return
        prop = self.__level.get_prop_at(*cell)
        if prop is not None:
            self.__editing_uid = prop.get_uid()
            self.__modal = PropSettingsPopup(prop)

    def __toggle_fullscreen(self) -> None:
        """F11 — the same toggle every screen in the game uses."""
        self.__fullscreen = not self.__fullscreen
        self.__window = pygame.display.set_mode(
            WINDOW_SIZE,
            FULLSCREEN_FLAGS if self.__fullscreen else WINDOWED_FLAGS)

    def __quit(self) -> None:
        """Leave the main loop."""
        self.__running = False

    def __consume_modal(self) -> None:
        """Apply a finished popup's result, then close it."""
        modal = self.__modal
        if modal is None or modal.is_open():
            return
        result = modal.get_result()
        self.__modal = None

        if isinstance(modal, ConfirmPopup):
            pending, self.__pending = self.__pending, None
            if result is True and pending is not None:
                pending()
        elif isinstance(modal, NewLevelPopup) and result != CANCEL:
            self.__create_level(result)
        elif isinstance(modal, FilePickerPopup) and result != CANCEL:
            self.__open_file(result)
        elif isinstance(modal, ValidationPopup):
            cell = modal.take_focus_cell()
            if cell is not None:
                self.focus_cell(cell)
        elif isinstance(modal, PropSettingsPopup) and result != CANCEL:
            self.__record()
            self.__level.replace_prop(self.__editing_uid, result)
        elif isinstance(modal, NpcDialogPopup) and result != CANCEL:
            self.__record()
            self.__level.replace_npc(self.__editing_uid, result)
        elif isinstance(modal, NewZonePopup):
            # NewZonePopup chains straight into GatePopup, so the zone is
            # named and gated in one gesture (Feature 6).
            if result != CANCEL:
                self.__create_zone(modal.get_rect_cells(), result)
        elif isinstance(modal, GatePopup) and result != CANCEL:
            self.__apply_gate(result)

    # ─────────────────────────────────────────────────────────
    # RENDERING
    # ─────────────────────────────────────────────────────────

    def render(self) -> None:
        """Draw one frame, bottom-up."""
        self.__window.fill(th.PANEL_TAN)
        self.__render_canvas()
        self.__render_top_bar()
        self.__render_side_panel()
        if self.__modal is not None:
            self.__modal.render(self.__window)
        pygame.display.flip()

    # ── canvas ────────────────────────────────────────────────

    def __render_canvas(self) -> None:
        """Layers bottom-up: ground, overlay, props, NPCs, chrome."""
        surface = self.__window
        previous_clip = surface.get_clip()
        surface.set_clip(CANVAS)
        surface.fill(th.HEADER_TAN, CANVAS)

        cell_px = self.__cell_px()
        first_x = max(0, self.__cam_x // cell_px)
        first_y = max(0, self.__cam_y // cell_px)
        last_x = min(self.__level.get_grid_width(),
                     (self.__cam_x + CANVAS.w) // cell_px + 1)
        last_y = min(self.__level.get_grid_height(),
                     (self.__cam_y + CANVAS.h) // cell_px + 1)

        for layer in (LAYER_GROUND, LAYER_OVERLAY):
            rows = self.__level.get_layer_rows(layer)
            for y in range(first_y, last_y):
                for x in range(first_x, last_x):
                    index = rows[y][x]
                    if index == EMPTY_TILE:
                        continue
                    rect = self.__cell_screen_rect(x, y)
                    sprite = self.__assets.get_tile(index, cell_px)
                    if sprite is not None:
                        surface.blit(sprite, rect.topleft)
                    else:
                        th.draw_placeholder(surface, rect)

        self.__render_entities(first_x, first_y, last_x, last_y, cell_px)
        self.__render_zones(cell_px)
        if self.__show_grid:
            self.__render_grid(first_x, first_y, last_x, last_y, cell_px)
        self.__render_spawn_marker(cell_px)
        self.__render_hover(cell_px)
        surface.set_clip(previous_clip)

    def __render_zones(self, cell_px: int) -> None:
        """
        Zone outlines and the in-progress drag (Feature 6).

        Drawn ABOVE the entities so a zone covering a busy area is still
        readable, but as an outline only, so it never hides the art it
        encloses. Blue = open, red = gated, amber = selected.
        """
        surface = self.__window
        font = th.load_font(th.SIZE_LABEL)
        for zone in self.__level.get_zones():
            x, y, w, h = zone.get_rect()
            top_left = self.__cell_screen_rect(x, y)
            rect = pygame.Rect(top_left.x, top_left.y, w * cell_px,
                               h * cell_px)
            if not rect.colliderect(CANVAS):
                continue
            if zone.get_uid() == self.__zone_selected:
                colour = th.BAR_AMBER
            elif zone.is_gated():
                colour = th.BAR_RED
            else:
                colour = th.ROW_BLUE
            pygame.draw.rect(surface, colour, rect, th.BORDER_ROW)
            label = zone.get_display_name() or zone.get_zone_id()
            th.draw_text(surface, font,
                         th.truncate(font, label.upper(), rect.w - 6),
                         (rect.x + 4, rect.y + 3), colour)
            if zone.is_gated():
                self.__render_lock_badge(rect)

        drag = self.__zone_drag_rect()
        if drag is not None:
            x, y, w, h = drag
            top_left = self.__cell_screen_rect(x, y)
            pygame.draw.rect(
                surface, th.BAR_AMBER,
                pygame.Rect(top_left.x, top_left.y, w * cell_px,
                            h * cell_px), th.BORDER_CARD)

    def __render_lock_badge(self, rect: pygame.Rect) -> None:
        """
        The gated marker: a small amber chip in the top-right corner.

        [ICON PLACEHOLDER: assets/ui/icon_lock.png -- 24x24 firewall /
         locked action. Until it exists this draws the Style Guide §5.2
         placeholder square with a shackle stroke over it, so a gated
         entity is still obvious at a glance.]
        """
        surface = self.__window
        badge = pygame.Rect(rect.right - 14, rect.y + 2, 12, 12)
        sprite = self.__assets.get_icon("assets/ui/icon_lock.png", 12)
        if sprite is not None:
            surface.blit(sprite, badge.topleft)
            return
        pygame.draw.rect(surface, th.BAR_AMBER, badge)
        pygame.draw.rect(surface, th.TEXT_COFFEE, badge, 1)
        pygame.draw.rect(surface, th.TEXT_COFFEE,
                         pygame.Rect(badge.x + 4, badge.y + 2, 4, 4), 1)

    def __render_entities(self, first_x: int, first_y: int, last_x: int,
                          last_y: int, cell_px: int) -> None:
        """
        Props then NPCs. NPCs use their `level_editor` art here — the
        `idle` sheet is what stands in the actual map (owner ruling).
        """
        surface = self.__window
        for prop in self.__level.get_props():
            x, y = prop.get_position()
            if not (first_x <= x < last_x and first_y <= y < last_y):
                continue
            rect = self.__cell_screen_rect(x, y)
            sprite = self.__assets.get_prop(prop.get_type_id(), cell_px)
            if sprite is not None:
                surface.blit(sprite, rect.topleft)
            else:
                th.draw_placeholder(surface, rect, prop.get_type_id())
            if self.__show_badges:
                self.__render_prop_badges(prop, rect)

        for npc in self.__level.get_npcs():
            x, y = npc.get_position()
            if not (first_x <= x < last_x and first_y <= y < last_y):
                continue
            rect = self.__cell_screen_rect(x, y)
            sprite = self.__assets.get_npc_editor(npc.get_type_id(), cell_px)
            if sprite is not None:
                surface.blit(sprite, rect.topleft)
            else:
                th.draw_placeholder(surface, rect, npc.get_type_id())
            if self.__show_badges:
                self.__render_npc_badges(npc, rect)

    def __render_prop_badges(self, prop, rect: pygame.Rect) -> None:
        """
        Editor-only corner badges (Spec §4.2) — never drawn in game.
        Red dot = blocking, green dot = interactable, » / « = speed up
        or down.
        """
        surface = self.__window
        if not prop.get_passthrough():
            pygame.draw.rect(surface, th.BAR_RED,
                             pygame.Rect(rect.x + 2, rect.y + 2, 6, 6))
        if prop.get_interactable():
            pygame.draw.rect(surface, th.ROW_GREEN,
                             pygame.Rect(rect.right - 8, rect.y + 2, 6, 6))
        modifier = prop.get_speed_modifier()
        if modifier != 1.0:
            glyph = ">>" if modifier > 1.0 else "<<"
            th.draw_text(surface, th.load_font(th.SIZE_LABEL), glyph,
                         (rect.x + 3, rect.bottom - 13), th.TITLE_SLATE)
        if prop.is_gated():
            self.__render_lock_badge(rect)

    def __render_npc_badges(self, npc, rect: pygame.Rect) -> None:
        """Green dot when the NPC can be talked to, amber when mute."""
        colour = th.ROW_GREEN if npc.get_interactable() else th.BAR_AMBER
        pygame.draw.rect(self.__window, colour,
                         pygame.Rect(rect.right - 8, rect.y + 2, 6, 6))
        if npc.is_gated():
            self.__render_lock_badge(
                pygame.Rect(rect.x, rect.bottom - 16, rect.w, 16))

    def __render_grid(self, first_x: int, first_y: int, last_x: int,
                      last_y: int, cell_px: int) -> None:
        """1 px grid lines at 40% alpha (Spec §3.3)."""
        self.__grid_layer.fill((0, 0, 0, 0))
        colour = (*th.BORDER_BROWN, 102)          # 40% of 255
        for x in range(first_x, last_x + 1):
            screen_x = CANVAS.x + x * cell_px - self.__cam_x - CANVAS.x
            pygame.draw.line(self.__grid_layer, colour, (screen_x, 0),
                             (screen_x, CANVAS.h), 1)
        for y in range(first_y, last_y + 1):
            screen_y = CANVAS.y + y * cell_px - self.__cam_y - CANVAS.y
            pygame.draw.line(self.__grid_layer, colour, (0, screen_y),
                             (CANVAS.w, screen_y), 1)
        self.__window.blit(self.__grid_layer, CANVAS.topleft)

    def __render_spawn_marker(self, cell_px: int) -> None:
        """
        Where the player appears.
        [ICON PLACEHOLDER: assets/ui/icon_spawn.png — spawn flag]
        """
        rect = self.__cell_screen_rect(*self.__level.get_spawn())
        if not CANVAS.colliderect(rect):
            return
        icon = self.__assets.get_icon("assets/ui/icon_spawn.png", cell_px)
        if icon is not None:
            self.__window.blit(icon, rect.topleft)
        else:
            inset = rect.inflate(-cell_px // 4, -cell_px // 4)
            pygame.draw.polygon(self.__window, th.BAR_AMBER,
                                [(inset.centerx, inset.bottom),
                                 (inset.left, inset.top),
                                 (inset.right, inset.top)])
        pygame.draw.rect(self.__window, th.BAR_AMBER, rect, 3)

    def __render_hover(self, cell_px: int) -> None:
        """Hover outline plus the 50%-alpha ghost of the selected item."""
        if self.__hover_cell is None:
            return
        rect = self.__cell_screen_rect(*self.__hover_cell)
        if self.__selection_kind not in (TOOL_NONE, TOOL_ERASER):
            ghost = self.__ghost_sprite(cell_px)
            if ghost is None:
                # art missing — preview the PLACEHOLDER square instead, so
                # the tool still shows where it will land (Style Guide §5.2)
                ghost = pygame.Surface((cell_px, cell_px))
                th.draw_placeholder(ghost, pygame.Rect(0, 0, cell_px,
                                                       cell_px))
            else:
                ghost = ghost.copy()
            ghost.set_alpha(128)
            self.__window.blit(ghost, rect.topleft)
        outline = th.BAR_OVER if self.__is_erasing() else th.ROW_BLUE
        pygame.draw.rect(self.__window, outline, rect, 2)

    def __ghost_sprite(self, cell_px: int) -> Optional[pygame.Surface]:
        """The preview sprite for whatever tool is selected."""
        if self.__selection_kind == "tile":
            return self.__assets.get_tile(int(self.__selection_key), cell_px)
        if self.__selection_kind == "prop":
            return self.__assets.get_prop(self.__selection_key, cell_px)
        if self.__selection_kind == "npc":
            return self.__assets.get_npc_editor(self.__selection_key, cell_px)
        return None

    # ── top bar ───────────────────────────────────────────────

    def __name_label_rect(self) -> pygame.Rect:
        """Clickable level-name label — jumps to SETTINGS (Spec §3.2)."""
        return pygame.Rect(372, BAR_BTN_Y, 460, BAR_BTN_H)

    def __render_top_bar(self) -> None:
        """PANEL_TAN strip, 4 px bottom edge, buttons, name, readout."""
        surface = self.__window
        pygame.draw.rect(surface, th.PANEL_TAN, TOP_BAR)
        pygame.draw.rect(surface, th.BORDER_BROWN,
                         pygame.Rect(0, TOP_BAR.bottom - th.BORDER_HUD,
                                     TOP_BAR.w, th.BORDER_HUD))

        rects = self.__bar_button_rects()
        icons = ("assets/ui/icon_new.png", "assets/ui/icon_save.png",
                 "assets/ui/icon_load.png")
        # [ICON PLACEHOLDER: assets/ui/icon_new.png  — blank page]
        # [ICON PLACEHOLDER: assets/ui/icon_save.png — floppy disk]
        # [ICON PLACEHOLDER: assets/ui/icon_load.png — open folder]
        fills = (th.HEADER_TAN, th.BTN_CONFIRM, th.HEADER_TAN)
        font = th.load_font(th.SIZE_LABEL)
        for rect, label, path, fill in zip(rects, ("NEW", "SAVE", "LOAD"),
                                           icons, fills):
            th.draw_panel(surface, rect, fill, th.BORDER_CARD)
            icon_rect = pygame.Rect(rect.x + 8, rect.centery - BAR_ICON // 2,
                                    BAR_ICON, BAR_ICON)
            icon = self.__assets.get_icon(path, BAR_ICON)
            if icon is not None:
                surface.blit(icon, icon_rect.topleft)
            else:
                th.draw_placeholder(surface, icon_rect)
            th.draw_text_vcenter(surface, font, label,
                                 icon_rect.right + 6, rect, th.TEXT_COFFEE)

        name = self.__level.get_level_name()
        label_rect = self.__name_label_rect()
        body = th.load_font(th.SIZE_BODY)
        th.draw_text_vcenter(surface, body,
                             th.truncate(body, name, label_rect.w - 20),
                             label_rect.x, label_rect, th.TEXT_COFFEE)
        if self.__dirty:
            width = body.size(th.truncate(body, name, label_rect.w - 20))[0]
            th.draw_text_vcenter(surface, body, "*", label_rect.x + width + 6,
                                 label_rect, th.BAR_AMBER)

        readout = self.__status if self.__status_timer > 0 \
            else self.__tool_readout()
        colour = th.CREDIT_HL if self.__status_timer > 0 else th.STAT_BROWN
        rendered = font.render(th.truncate(font, readout, 420), True, colour)
        surface.blit(rendered, (TOP_BAR.right - rendered.get_width() - 12,
                                TOP_BAR.centery - rendered.get_height() // 2))

    # ── side panel ────────────────────────────────────────────

    def __tab_rects(self) -> List[pygame.Rect]:
        """
        The tab buttons, laid out over TAB_ROWS rows.

        Derived from len(TAB_NAMES) rather than a hard-coded count --
        the ported version assumed four, so adding ZONES left SETTINGS
        with no button at all even though its hotkey still worked.

        Two rows, because five tabs across a 280 px panel gives 48 px
        each and "SETTINGS" needs 64 px at the smallest font the theme
        offers. Three-then-two keeps every label whole.
        """
        gap = 4
        rects: List[pygame.Rect] = []
        for index in range(len(TAB_NAMES)):
            row, column = divmod(index, TAB_COLUMNS)
            in_row = min(TAB_COLUMNS, len(TAB_NAMES) - row * TAB_COLUMNS)
            width = (SIDE_PANEL.w - PANEL_PAD * 2 - gap * (in_row - 1)) \
                // in_row
            rects.append(pygame.Rect(
                SIDE_PANEL.x + PANEL_PAD + column * (width + gap),
                TAB_Y + row * (TAB_H + gap), width, TAB_H))
        return rects

    def __render_side_panel(self) -> None:
        """CARD_TAN panel, 3 px left edge, tab row, then the section."""
        surface = self.__window
        pygame.draw.rect(surface, th.CARD_TAN, SIDE_PANEL)
        pygame.draw.rect(surface, th.BORDER_BROWN,
                         pygame.Rect(SIDE_PANEL.x, SIDE_PANEL.y,
                                     th.BORDER_CARD, SIDE_PANEL.h))

        tabs = self.__tab_rects()
        font = th.fit_font(max(TAB_NAMES, key=len), tabs[0].w - 8)
        for index, (rect, name) in enumerate(zip(tabs, TAB_NAMES)):
            active = index == self.__tab
            th.draw_panel(surface, rect,
                          th.BAR_AMBER if active else th.HEADER_TAN,
                          th.BORDER_ROW)
            th.draw_text_centered(surface, font, name, rect, th.TEXT_COFFEE)

        if self.__tab == TAB_SETTINGS:
            self.__render_settings_section()
        elif self.__tab == TAB_ZONES:
            self.__render_zone_section()
        else:
            self.__render_palette_section()
        self.__render_panel_footer()

    def __zone_row_rects(self) -> List[pygame.Rect]:
        """One row per zone in the side-panel list."""
        area = self.__palette_rect()
        return [pygame.Rect(area.x, area.y + 46 + index * 34, area.w, 30)
                for index in range(self.__level.get_zone_count())]

    def __zone_delete_rect(self) -> pygame.Rect:
        """The DELETE ZONE button at the bottom of the zone list."""
        area = self.__palette_rect()
        return pygame.Rect(area.x, area.bottom - 38, area.w, 32)

    def __render_zone_section(self) -> None:
        """
        The ZONES tab: how to draw one, then the list of what exists.

        There is no sprite palette here -- a zone is a rectangle, not a
        placeable thing -- so the panel explains the gesture instead.
        """
        surface = self.__window
        area = self.__palette_rect()
        label = th.load_font(th.SIZE_LABEL)
        sub = th.load_font(th.SIZE_SUB)

        th.draw_text(surface, label, "DRAG ON THE MAP TO ADD",
                     (area.x, area.y), th.CREDIT_HL)
        th.draw_text(surface, label, "RIGHT-CLICK TO GATE",
                     (area.x, area.y + 18), th.STAT_BROWN)

        zones = self.__level.get_zones()
        if not zones:
            th.draw_text(surface, sub, "No zones yet.",
                         (area.x, area.y + 52), th.STAT_BROWN)
            return

        for rect, zone in zip(self.__zone_row_rects(), zones):
            selected = zone.get_uid() == self.__zone_selected
            th.draw_panel(surface, rect,
                          th.ROW_BLUE if selected else th.ROW_WHITE,
                          th.BORDER_ROW)
            name = zone.get_display_name() or zone.get_zone_id()
            th.draw_text_vcenter(
                surface, sub, th.truncate(sub, name.upper(), rect.w - 34),
                rect.x + 8, rect, th.ROW_WHITE if selected else
                th.TEXT_COFFEE)
            if zone.is_gated():
                self.__render_lock_badge(rect)

        if self.__zone_selected:
            th.draw_button(surface, self.__zone_delete_rect(), "DELETE ZONE",
                           th.BTN_CANCEL, th.load_font(th.SIZE_LABEL))

    def __render_palette_section(self) -> None:
        """The palette grid plus the selected item's property footer."""
        self.__palette.render(self.__window, self.__selection_key or None,
                              self.__palette_sprite)

        footer_y = SIDE_PANEL.bottom - FOOTER_H + 4
        x = SIDE_PANEL.x + PANEL_PAD
        font = th.load_font(th.SIZE_LABEL)
        if self.__selection_kind == TOOL_ERASER:
            th.draw_text(self.__window, font, "ERASES TOP-DOWN:",
                         (x, footer_y), th.CREDIT_HL)
            th.draw_text(self.__window, font, "NPC > PROP > OVERLAY > GROUND",
                         (x, footer_y + 14), th.STAT_BROWN)
        elif self.__selection_kind == "tile":
            entry = get_tile_def(int(self.__selection_key))
            walkable = "yes" if entry and entry["walkable"] else "no"
            layer = entry["layer"] if entry else "-"
            th.draw_text(self.__window, font, f"WALKABLE: {walkable}",
                         (x, footer_y), th.CREDIT_HL)
            th.draw_text(self.__window, font, f"PAINTS INTO: {layer}",
                         (x, footer_y + 14), th.STAT_BROWN)
        elif self.__selection_kind in ("prop", "npc"):
            th.draw_text(self.__window, font, "RIGHT-CLICK A PLACED",
                         (x, footer_y), th.CREDIT_HL)
            th.draw_text(self.__window, font,
                         f"{self.__selection_kind.upper()} TO EDIT IT",
                         (x, footer_y + 14), th.STAT_BROWN)

    def __render_settings_section(self) -> None:
        """The level settings form (Spec §4.4)."""
        surface = self.__window
        x = SIDE_PANEL.x + PANEL_PAD
        y = SECTION_Y
        label = th.load_font(th.SIZE_LABEL)

        th.draw_text(surface, label, "LEVEL NAME", (x, y), th.CREDIT_HL)
        self.__field_name.render(surface, "Campus Main")

        th.draw_text(surface, label, "LEVEL ID", (x, y + 48), th.CREDIT_HL)
        self.__field_id.render(surface, "campus_main")
        if self.__saved_id and self.__saved_id != self.__level.get_level_id():
            th.draw_text(surface, label,
                         f"SAVES AS A NEW FILE ({self.__saved_id} STAYS)",
                         (x, y + 94), th.BAR_AMBER)

        th.draw_text(surface, label, "GRID W x H", (x, y + 108), th.CREDIT_HL)
        self.__step_w.render(surface)
        self.__step_h.render(surface)
        th.draw_button(surface, self.__btn_resize, "APPLY GRID SIZE",
                       th.HEADER_TAN,
                       th.fit_font("APPLY GRID SIZE",
                                   self.__btn_resize.w - 8))

        th.draw_text(surface, label, "AMBIENT PRESET", (x, y + 188),
                     th.CREDIT_HL)
        self.__chips_ambient.render(surface, th.BAR_AMBER)

        th.draw_text(surface, label, "MUSIC TRACK", (x, y + 232),
                     th.CREDIT_HL)
        # [ICON PLACEHOLDER: assets/audio/<track>.ogg — level BGM]
        self.__field_music.render(surface, "assets/audio/quad.ogg")

        spawn = self.__level.get_spawn()
        th.draw_button(surface, self.__btn_spawn,
                       f"SET SPAWN ({spawn[0]},{spawn[1]})",
                       th.BAR_AMBER if self.__spawn_arm else th.HEADER_TAN,
                       th.fit_font("SET SPAWN (00,00)",
                                   self.__btn_spawn.w - 8))
        th.draw_button(surface, self.__btn_validate, "VALIDATE NOW",
                       th.HEADER_TAN,
                       th.fit_font("VALIDATE NOW", self.__btn_validate.w - 8))

        source = self.__level.get_source_path()
        stamp = "never saved"
        if source and os.path.isfile(source):
            stamp = time.strftime("%Y-%m-%d %H:%M",
                                  time.localtime(os.path.getmtime(source)))
        info = (
            f"FILE: {os.path.basename(source) if source else '-'}",
            f"SCHEMA: v{SCHEMA_VERSION}",
            f"PROPS: {len(self.__level.get_props())}   "
            f"NPCS: {len(self.__level.get_npcs())}",
            f"SAVED: {stamp}",
        )
        for index, line in enumerate(info):
            th.draw_text(surface, label,
                         th.truncate(label, line,
                                     SIDE_PANEL.w - PANEL_PAD * 2),
                         (x, y + 366 + index * 14), th.STAT_BROWN)

    def __render_panel_footer(self) -> None:
        """Zoom, grid state and undo depth — the panel's status line."""
        font = th.load_font(th.SIZE_LABEL)
        undo_depth, redo_depth = self.__undo.get_depth()
        lines = (
            f"ZOOM {self.__cell_px()}PX   "
            f"GRID {'ON' if self.__show_grid else 'OFF'}",
            f"UNDO {undo_depth}   REDO {redo_depth}",
        )
        y = SIDE_PANEL.bottom - 34
        for index, line in enumerate(lines):
            th.draw_text(self.__window, font, line,
                         (SIDE_PANEL.x + PANEL_PAD, y + index * 14),
                         th.STAT_BROWN)

    # ─────────────────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────────────────

    # ── public app surface ────────────────────────────────────
    # The main loop, the headless screenshot harness and the tests all
    # drive the editor through these three methods plus the getters, so
    # nothing outside this class reaches into its private state.

    def get_level(self) -> LevelData:
        """The document currently being edited."""
        return self.__level

    def is_dirty(self) -> bool:
        """True when there are unsaved changes."""
        return self.__dirty

    def get_active_modal(self) -> Optional[Any]:
        """The open popup, or None."""
        return self.__modal

    def get_undo_depth(self) -> Tuple[int, int]:
        """(undo steps, redo steps)."""
        return self.__undo.get_depth()

    def get_selection(self) -> Tuple[str, str]:
        """(tool kind, key) for the active palette selection."""
        return (self.__selection_kind, self.__selection_key)

    def get_missing_assets(self) -> List[str]:
        """Every asset path that failed to load — the artist's work queue."""
        return self.__assets.get_missing_paths()

    def get_levels_dir(self) -> str:
        """The folder SAVE writes to and LOAD lists."""
        return self.__levels_dir

    def is_running(self) -> bool:
        """False once the app has been asked to close."""
        return self.__running

    def update(self, dt: float) -> None:
        """Per-frame state: modal result, timers, carets, held keys."""
        if self.__modal is not None:
            self.__modal.update(dt)
            self.__consume_modal()
        if self.__status_timer > 0:
            self.__status_timer = max(0.0, self.__status_timer - dt)
        for field in (self.__field_name, self.__field_id,
                      self.__field_music):
            field.update(dt)
        self.__pan_with_keys()

    def run(self) -> None:
        """60 FPS loop: events, update, draw."""
        while self.__running:
            dt = self.__clock.tick(60) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.render()
        self.__report_missing_assets()
        pygame.quit()

    def __pan_with_keys(self) -> None:
        """Arrow-key panning, applied every frame while held (Spec §8)."""
        if self.__modal is not None:
            return
        keys = pygame.key.get_pressed()
        speed = 12
        moved = False
        if keys[pygame.K_LEFT]:
            self.__cam_x -= speed
            moved = True
        if keys[pygame.K_RIGHT]:
            self.__cam_x += speed
            moved = True
        if keys[pygame.K_UP]:
            self.__cam_y -= speed
            moved = True
        if keys[pygame.K_DOWN]:
            self.__cam_y += speed
            moved = True
        if moved:
            self.__clamp_camera()

    def __report_missing_assets(self) -> None:
        """
        Print the placeholder work queue on exit (Style Guide §5.2
        step 4) so the artist gets a concrete list.
        """
        missing = self.__assets.get_missing_paths()
        if not missing:
            return
        print("\n[PLACEHOLDER ART QUEUE] these files are still missing:")
        for path in missing:
            print(f"  - {path}")


def resolve_level_argument(argument: str) -> str:
    """
    Turn a command-line argument into a level file path.

    Accepts a path relative to wherever the user ran the command, an
    absolute path, or a bare level id ("campus_main"). Returns "" when
    nothing matches.
    """
    if not argument:
        return ""
    if os.path.isfile(argument):
        return os.path.abspath(argument)
    level_id = os.path.splitext(os.path.basename(argument))[0]
    guess = level_path(level_id)
    return guess if os.path.isfile(guess) else ""


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point. An optional argument opens a level file on start."""
    argv = sys.argv[1:] if argv is None else argv
    open_path = resolve_level_argument(argv[0]) if argv else ""
    if argv and not open_path:
        print(f"[level editor] no such level: {argv[0]}")
    if not open_path:
        open_path = resolve_level_argument("campus_main")

    # Say out loud where content is coming from. The failure mode this
    # replaces was silent: launched from the wrong folder, the editor
    # used to open an empty level full of placeholder squares and give
    # no hint why.
    print(f"[level editor] levels : {LEVELS_DIR}")
    print(f"[level editor] opening: {open_path or '(new empty level)'}")
    LevelEditorApp(open_path).run()


if __name__ == "__main__":
    main()

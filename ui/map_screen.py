"""
CSE Life: Compile & Conquer
ui/map_screen.py

The campus itself: the tile grid the player walks around in, the
props standing on it, the NPCs waiting to be talked to, and the
player sprite in the middle of it all.

A level is 48 px cells. The source art is 16 px pixel-art tiles
and 48 px character frames, scaled up with pygame.transform.scale
-- never smoothscale, because a blurred pixel tile stops being
pixel art.

This file has NO game logic. render() is handed the Level to draw,
where the camera is, where the player is, which frame of the walk
cycle they are on and which gates are currently locked. It decides
none of that. It does not move the player, does not test
collision, does not trigger a prop and does not know what a
semester is -- walking lives in the runner (play_sandbox.py today,
Abu Huraira's state manager later), collision lives on the Level,
and whether a gate opens is engine/gate_evaluator.py's ruling.

What it DOES own is pure screen geometry: where the camera sits so
it never scrolls past the level edge, which cells are actually
visible, and the rectangle any given cell occupies on screen so a
caller can float a prompt over it.

Style: Nangiba Tasnim's tan pixel look. Missing art never blocks --
every sprite that fails to load draws the Style Guide PLACEHOLDER
square instead (§5.2), which is why campus_main's walls, pond and
portal are visible and collide correctly with no art at all.

Abu Huraira removes the stub test block when he plugs in the real game.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import pygame

from content.level_registry import (
    EMPTY_TILE,
    FACINGS,
    TILE_SIZE_PX,
    get_npc_def,
    get_prop_def,
    get_tile_def,
    resolve_asset,
)

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. Every new UI file
# declares its own block (Build Plan §0.5) -- screens never import
# colours from each other, so this file runs with no other screen present.
PANEL_TAN = (231, 214, 189)     # the void outside the level edge
BORDER_BROWN = (169, 130, 94)   # level edge frame, badge outlines
PLACEHOLDER = (196, 178, 150)   # square drawn where a PNG is missing
HEADER_TAN = (214, 196, 168)    # lock badge fill
BAR_RED = (199, 123, 107)       # a gate the player cannot pass
BAR_GREEN = (167, 185, 133)     # a gate whose requirements are met
STAT_BROWN = (140, 110, 85)     # muted hint text (stub test only)

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
# The cell size is NOT redeclared here: content/level_registry.py owns
# the grid contract that the schema, the loader and the editor all read,
# and a renderer that disagreed with it would draw a different map than
# the one the collision grid describes.
CELL = TILE_SIZE_PX             # 48 px on screen per cell

VIEWPORT_TOP = 44               # the HUD strip owns the top 44 px (§4.3)

EDGE_BORDER_W = 3               # frame drawn around the level's outer edge
GATE_OUTLINE_W = 2              # §4.4 border weight on a gated cell

BADGE_SIZE = 16                 # the little lock chip on a gated cell
BADGE_INSET = 4                 # gap from the cell corner to the badge
BADGE_BORDER_W = 2

PLAYER_FRAMES = 4               # frames in one walk cycle
NPC_FRAMES_DEFAULT = 4          # frames in a 192x48 idle strip
NPC_ANIM_FPS = 4.0              # idle strips loop slowly (~4 fps)

# Compass folder -> the animation direction it plays (§1.6 ruling).
# The newer per-file player art is stored under compass names; the
# rest of the codebase speaks in FACINGS, so the map is made here once.
DIR_TO_COMPASS: Dict[str, str] = {
    "down": "south", "left": "west", "right": "east", "up": "north",
}

PLAYER_DIR_ROOT = "assets/npcs/main_character"
PLAYER_FRAME_PATTERN = "frame_00{index}.png"
# The older 4x4 sheet, kept as the fallback (§1.6). Rows run in FACINGS
# order: down, left, right, up.
PLAYER_SHEET_PATH = "assets/sprites/player_walk.png"
PLAYER_SHEET_CELL = 48

# [ICON PLACEHOLDER: assets/ui/icon_lock.png -- firewall / locked action,
#  drawn at 16x16 on a gated cell. Missing today, so every gate badge
#  falls back to the PLACEHOLDER square (Style Guide §5.2/§5.3).]
LOCK_ICON_PATH = "assets/ui/icon_lock.png"


class MapScreen:
    """
    Draws one level.

    It never fetches its own data -- render() is handed the Level, the
    camera, the player's pixel position and animation frame, and the
    gate verdicts, so the visuals stay fully separate from movement and
    from the gate rules (separation of concerns).

    Sprites are loaded once and cached by (path, cell, size); a load
    that fails is cached as None so a missing file costs one failed
    open per session rather than one per frame.
    """

    def __init__(self) -> None:
        """Prepare the sprite caches. Nothing is loaded until it is drawn."""
        self.__sheets: Dict[str, Optional[pygame.Surface]] = {}
        self.__cells: Dict[Tuple[Any, ...], Optional[pygame.Surface]] = {}
        self.__missing: set = set()
        self.__tints: Dict[Tuple[int, int, int, int, int, int],
                           pygame.Surface] = {}
        # Advanced by dt and used ONLY when a caller does not track NPC
        # frames itself, so `render(..., npc_frames=None)` still animates.
        self.__anim_clock: float = 0.0

    # -- loading helpers --------------------------------------
    def __load_sheet(self, path: str) -> Optional[pygame.Surface]:
        """
        Load a source image once. Returns None -- remembered, so it is
        not retried every frame -- when the file is missing, and records
        the path for get_missing_paths().

        Registry paths are repo-relative, so they resolve against the
        project root rather than the working directory: the game must
        find the same art whether it was started from the repo, from an
        IDE, or from a shortcut.
        """
        if path in self.__sheets:
            return self.__sheets[path]
        image: Optional[pygame.Surface]
        try:
            image = pygame.image.load(resolve_asset(path))
            image = image.convert_alpha() if pygame.display.get_init() \
                else image
        except (FileNotFoundError, OSError, pygame.error):
            image = None
            self.__missing.add(path)
        self.__sheets[path] = image
        return image

    def __load_cell(self, path: str, col: int, row: int, cell_px: int,
                    size: int) -> Optional[pygame.Surface]:
        """
        Slice one cell out of a sheet and scale it to `size`.

        A single-image asset is simply a 1x1 sheet at (0, 0), which is
        how the 16x16 tiles and props are registered. Scaling uses
        pygame.transform.scale -- nearest neighbour, no smoothing -- so
        16 px art stays hard-edged at 3x.
        """
        key = (path, col, row, cell_px, size)
        if key in self.__cells:
            return self.__cells[key]

        sheet = self.__load_sheet(path)
        surface: Optional[pygame.Surface] = None
        if sheet is not None:
            area = pygame.Rect(col * cell_px, row * cell_px, cell_px, cell_px)
            if sheet.get_rect().contains(area):
                surface = pygame.transform.scale(sheet.subsurface(area),
                                                 (size, size))
            else:
                # The file exists but is the wrong shape. Treat it as
                # missing art rather than crashing mid-frame.
                self.__missing.add(path)
        self.__cells[key] = surface
        return surface

    def __load_scaled(self, path: str,
                      size: int) -> Optional[pygame.Surface]:
        """A whole image scaled to a square, or None when it is missing."""
        sheet = self.__load_sheet(path)
        if sheet is None:
            return None
        key = ("whole", path, size)
        if key not in self.__cells:
            self.__cells[key] = pygame.transform.scale(sheet, (size, size))
        return self.__cells[key]

    def __tile_sprite(self, tile_index: int) -> Optional[pygame.Surface]:
        """The 48 px sprite for a tile index, or None when unregistered."""
        entry = get_tile_def(tile_index)
        if entry is None:
            return None
        return self.__load_cell(str(entry.get("sheet", "")),
                                int(entry.get("col", 0)),
                                int(entry.get("row", 0)),
                                int(entry.get("cell_px", 16)), CELL)

    def __prop_sprite(self, type_id: str) -> Optional[pygame.Surface]:
        """The 48 px sprite for a prop type, or None when its art is gone."""
        entry = get_prop_def(type_id)
        if entry is None:
            return None
        return self.__load_cell(str(entry.get("sheet", "")),
                                int(entry.get("col", 0)),
                                int(entry.get("row", 0)),
                                int(entry.get("cell_px", 16)), CELL)

    def __npc_sprite(self, type_id: str,
                     frame: int) -> Optional[pygame.Surface]:
        """
        One frame of an NPC's idle strip (owner ruling: the "idle" art is
        what stands in the map). Frames wrap, so an ever-increasing
        animation counter can be handed straight in.
        """
        entry = get_npc_def(type_id)
        if entry is None:
            return None
        frames = max(1, int(entry.get("frames", NPC_FRAMES_DEFAULT)))
        return self.__load_cell(str(entry.get("idle_sheet", "")),
                                frame % frames, 0,
                                int(entry.get("cell_px", 48)), CELL)

    def __player_sprite(self, direction: str,
                        frame: int) -> Optional[pygame.Surface]:
        """
        The player's walk frame, preferring the newer per-file art.

        Three steps, in the order §1.6 rules:
          1. assets/npcs/main_character/<compass>/frame_00N.png
          2. the older 4x4 assets/sprites/player_walk.png sheet
          3. None -- the caller draws a PLACEHOLDER square
        """
        facing = direction if direction in FACINGS else FACINGS[0]
        index = frame % PLAYER_FRAMES

        compass = DIR_TO_COMPASS.get(facing, "south")
        relative = os.path.join(
            PLAYER_DIR_ROOT, compass,
            PLAYER_FRAME_PATTERN.format(index=index)).replace("\\", "/")
        sprite = self.__load_cell(relative, 0, 0, PLAYER_SHEET_CELL, CELL)
        if sprite is not None:
            return sprite

        # [IMAGE PLACEHOLDER: assets/sprites/player_walk.png -- 192x192
        #  4x4 walk sheet, rows down/left/right/up. Only reached when the
        #  per-direction folder art is absent; if this is missing too the
        #  player draws as a PLACEHOLDER square (Style Guide §5.2).]
        return self.__load_cell(PLAYER_SHEET_PATH, index,
                                FACINGS.index(facing), PLAYER_SHEET_CELL, CELL)

    # -- geometry (the only decisions this file makes) ---------
    def get_viewport_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """
        The part of the window the level is drawn into.

        The top 44 px belong to the HUD strip (§4.3), so the map starts
        below it and the camera centres on what is actually visible
        rather than on the whole window.
        """
        return pygame.Rect(0, VIEWPORT_TOP, screen.get_width(),
                           max(0, screen.get_height() - VIEWPORT_TOP))

    def compute_camera(self, level: Any, player_px: Sequence[float],
                       screen: pygame.Surface) -> Tuple[int, int]:
        """
        Where the camera should sit, in world pixels, for this player
        position: centred on the player, then clamped so it never
        scrolls past the level edge.

        A level smaller than the viewport cannot be clamped that way --
        there is no edge to push against -- so it is centred instead,
        which puts the tan void evenly on both sides rather than
        stranding the whole map in one corner.
        """
        viewport = self.get_viewport_rect(screen)
        grid_w, grid_h = level.get_grid_size()
        return (self.__axis_camera(float(player_px[0]), grid_w * CELL,
                                   viewport.w),
                self.__axis_camera(float(player_px[1]), grid_h * CELL,
                                   viewport.h))

    @staticmethod
    def __axis_camera(centre_px: float, level_px: int,
                      viewport_px: int) -> int:
        """One axis of the camera rule -- centre, then clamp or centre."""
        if level_px <= viewport_px:
            return (level_px - viewport_px) // 2
        return int(max(0, min(level_px - viewport_px,
                              centre_px - viewport_px / 2.0)))

    def get_screen_rect_for_cell(self, x: int, y: int,
                                 camera: Sequence[int]) -> pygame.Rect:
        """
        Where cell (x, y) lands on screen for this camera.

        Callers use it to float an interaction prompt over the cell they
        are about to interact with, so the prompt and the tile can never
        drift apart.
        """
        return pygame.Rect(x * CELL - int(camera[0]),
                           y * CELL - int(camera[1]) + VIEWPORT_TOP,
                           CELL, CELL)

    def get_cell_for_screen_point(self, point: Sequence[int],
                                  camera: Sequence[int]) -> Tuple[int, int]:
        """
        The cell under a screen point -- the inverse of the above, used
        by the sandbox's debug overlay to report what is under the mouse.
        May return coordinates outside the grid; callers test with
        `level.is_inside()`.
        """
        return ((int(point[0]) + int(camera[0])) // CELL,
                (int(point[1]) - VIEWPORT_TOP + int(camera[1])) // CELL)

    def get_visible_cell_range(self, level: Any, camera: Sequence[int],
                               screen: pygame.Surface
                               ) -> Tuple[int, int, int, int]:
        """
        (first_col, first_row, last_col, last_row) actually on screen,
        clamped to the grid.

        Everything drawn iterates this instead of the whole grid: a
        200x200 level is 40,000 cells and only about 600 of them can be
        seen, so culling is the difference between 60 fps and a slideshow.
        """
        viewport = self.get_viewport_rect(screen)
        grid_w, grid_h = level.get_grid_size()
        first_col = max(0, int(camera[0]) // CELL)
        first_row = max(0, int(camera[1]) // CELL)
        last_col = min(grid_w - 1, (int(camera[0]) + viewport.w) // CELL)
        last_row = min(grid_h - 1, (int(camera[1]) + viewport.h) // CELL)
        return (first_col, first_row, last_col, last_row)

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, level: Any,
               camera: Sequence[int], player_px: Sequence[float],
               player_dir: str = "down", player_frame: int = 0,
               npc_frames: Optional[Mapping[str, int]] = None,
               gate_states: Optional[Mapping[Tuple[int, int], bool]] = None,
               dt: float = 0.0) -> None:
        """
        Draw the level from the state handed in.

        level        : the read-only engine.level_loader.Level to draw
        camera       : (x, y) world-pixel offset, from compute_camera()
        player_px    : the player's CENTRE in world pixels
        player_dir   : one of FACINGS -- down / left / right / up
        player_frame : index into the 4-frame walk cycle, 0 when idle
        npc_frames   : {npc uid: frame index}; None animates them here
        gate_states  : {(x, y): is_locked} for gated cells; a cell that
                       is gated but absent from the map is drawn locked,
                       which is the safe default before F8's evaluator
                       has had a chance to speak
        dt           : seconds since the last frame, used only to drive
                       the fallback NPC animation when npc_frames is None

        Draw order is ground, overlay, props (y-sorted), NPCs, player,
        ambient tint, gate markers. Y-sorting the props is what lets the
        player walk behind a rock that is further down the screen.
        """
        self.__anim_clock += max(0.0, float(dt))
        viewport = self.get_viewport_rect(screen)
        bounds = self.get_visible_cell_range(level, camera, screen)

        previous_clip = screen.get_clip()
        screen.set_clip(viewport)
        try:
            screen.fill(PANEL_TAN, viewport)
            self.__draw_layer(screen, level.get_ground_rows(), camera, bounds)
            self.__draw_layer(screen, level.get_overlay_rows(), camera, bounds)
            self.__draw_props(screen, level, camera, bounds)
            self.__draw_npcs(screen, level, camera, bounds, npc_frames)
            self.__draw_player(screen, camera, player_px, player_dir,
                               player_frame)
            self.__draw_edge(screen, level, camera)
            self.__draw_ambient(screen, level, viewport)
            self.__draw_gates(screen, level, camera, bounds, gate_states)
        finally:
            screen.set_clip(previous_clip)

    # -- piece-by-piece drawing -------------------------------
    def __draw_layer(self, screen: pygame.Surface, rows: List[List[int]],
                     camera: Sequence[int],
                     bounds: Tuple[int, int, int, int]) -> None:
        """
        Blit one tile layer over the visible rectangle.

        EMPTY_TILE means "nothing here", which is normal on the overlay
        layer and is how a level says a cell has no wall on it.
        """
        first_col, first_row, last_col, last_row = bounds
        for y in range(first_row, last_row + 1):
            if y >= len(rows):
                break
            row = rows[y]
            for x in range(first_col, min(last_col + 1, len(row))):
                index = row[x]
                if index == EMPTY_TILE:
                    continue
                rect = self.get_screen_rect_for_cell(x, y, camera)
                sprite = self.__tile_sprite(index)
                if sprite is not None:
                    screen.blit(sprite, rect.topleft)
                else:
                    # [TILE PLACEHOLDER: assets/tiles/{wall_0,water_0}.png --
                    #  16x16 wall and pond tiles. Missing art draws the
                    #  PLACEHOLDER square; collision is unaffected because
                    #  it comes from the registry, not the PNG (§5.2).]
                    pygame.draw.rect(screen, PLACEHOLDER, rect)

    def __draw_props(self, screen: pygame.Surface, level: Any,
                     camera: Sequence[int],
                     bounds: Tuple[int, int, int, int]) -> None:
        """
        Draw the visible props, sorted by row so a prop lower on the
        screen overlaps one above it.
        """
        first_col, first_row, last_col, last_row = bounds
        visible = [p for p in level.get_props()
                   if first_col <= p.get_position()[0] <= last_col
                   and first_row <= p.get_position()[1] <= last_row]
        for prop in sorted(visible, key=lambda p: p.get_position()[1]):
            x, y = prop.get_position()
            rect = self.get_screen_rect_for_cell(x, y, camera)
            sprite = self.__prop_sprite(prop.get_type_id())
            if sprite is not None:
                screen.blit(sprite, rect.topleft)
            else:
                # [PROP PLACEHOLDER: assets/props/portal_0.png -- 16x16
                #  doorway / arch marker. The portal still works: the
                #  target level is level data, not art (§5.2).]
                pygame.draw.rect(screen, PLACEHOLDER, rect)

    def __draw_npcs(self, screen: pygame.Surface, level: Any,
                    camera: Sequence[int],
                    bounds: Tuple[int, int, int, int],
                    npc_frames: Optional[Mapping[str, int]]) -> None:
        """
        Draw the visible NPCs on their idle frame.

        With no frame map handed in they animate off this class's own
        clock, so a caller that does not care about NPC timing still
        gets a living campus.
        """
        first_col, first_row, last_col, last_row = bounds
        fallback = int(self.__anim_clock * NPC_ANIM_FPS)
        for npc in level.get_npcs():
            x, y = npc.get_position()
            if not (first_col <= x <= last_col and first_row <= y <= last_row):
                continue
            frame = fallback if npc_frames is None \
                else int(npc_frames.get(npc.get_uid(), 0))
            rect = self.get_screen_rect_for_cell(x, y, camera)
            sprite = self.__npc_sprite(npc.get_type_id(), frame)
            if sprite is not None:
                screen.blit(sprite, rect.topleft)
            else:
                # [NPC PLACEHOLDER: assets/npcs/npc_<name>_idle.png --
                #  192x48 idle strip, 4 frames of 48 px. Only hoque and
                #  roya exist today (§5.2).]
                pygame.draw.rect(screen, PLACEHOLDER, rect)

    def __draw_player(self, screen: pygame.Surface, camera: Sequence[int],
                      player_px: Sequence[float], player_dir: str,
                      player_frame: int) -> None:
        """
        Draw the player sprite centred on their world position.

        The position is a float and the cell size is 48, so the sprite
        rides between cells -- movement is smooth pixels, not grid steps.
        """
        rect = pygame.Rect(0, 0, CELL, CELL)
        rect.center = (int(player_px[0]) - int(camera[0]),
                       int(player_px[1]) - int(camera[1]) + VIEWPORT_TOP)
        sprite = self.__player_sprite(player_dir, player_frame)
        if sprite is not None:
            screen.blit(sprite, rect.topleft)
        else:
            # [IMAGE PLACEHOLDER: assets/npcs/main_character/<compass>/
            #  frame_00N.png -- 48x48 walk frames. Both this and the older
            #  sheet absent means the player is a PLACEHOLDER square, which
            #  is still playable (Style Guide §5.2).]
            pygame.draw.rect(screen, PLACEHOLDER, rect)

    def __draw_edge(self, screen: pygame.Surface, level: Any,
                    camera: Sequence[int]) -> None:
        """
        Frame the level's outer edge so the tan void reads as "outside
        the map" rather than as an unpainted mistake.
        """
        grid_w, grid_h = level.get_grid_size()
        edge = pygame.Rect(-int(camera[0]),
                           -int(camera[1]) + VIEWPORT_TOP,
                           grid_w * CELL, grid_h * CELL)
        pygame.draw.rect(screen, BORDER_BROWN, edge, EDGE_BORDER_W)

    def __draw_ambient(self, screen: pygame.Surface, level: Any,
                       viewport: pygame.Rect) -> None:
        """
        Blit the level's ambient tint over the finished frame.

        A static cosmetic wash, never a clock (owner ruling): "day" is
        fully transparent and costs nothing, so the common case skips
        the blit entirely.
        """
        tint = tuple(level.get_ambient_tint())
        if len(tint) < 4 or tint[3] <= 0:
            return
        key = (viewport.w, viewport.h, int(tint[0]), int(tint[1]),
               int(tint[2]), int(tint[3]))
        surface = self.__tints.get(key)
        if surface is None:
            surface = pygame.Surface((viewport.w, viewport.h), pygame.SRCALPHA)
            surface.fill((int(tint[0]), int(tint[1]), int(tint[2]),
                          int(tint[3])))
            self.__tints[key] = surface
        screen.blit(surface, viewport.topleft)

    def __draw_gates(self, screen: pygame.Surface, level: Any,
                     camera: Sequence[int],
                     bounds: Tuple[int, int, int, int],
                     gate_states: Optional[Mapping[Tuple[int, int], bool]]
                     ) -> None:
        """
        Outline every visible gated cell, and badge the ones worth
        badging.

        The outline goes on every cell so the shape of a gated zone
        reads at a glance; the lock badge goes only on a gated PROP (a
        door -- the thing you actually interact with) and on a zone's
        top-left cell, because sixteen lock chips on a 4x4 zone is
        noise, not information.
        """
        first_col, first_row, last_col, last_row = bounds
        anchors = {zone.get_rect()[:2] for zone in level.get_zones()}
        for y in range(first_row, last_row + 1):
            for x in range(first_col, last_col + 1):
                gate = level.get_gate_at(x, y)
                if gate is None:
                    continue
                locked = True if gate_states is None \
                    else bool(gate_states.get((x, y), True))
                colour = BAR_RED if locked else BAR_GREEN
                rect = self.get_screen_rect_for_cell(x, y, camera)
                pygame.draw.rect(screen, colour, rect, GATE_OUTLINE_W)
                prop = level.get_prop_at(x, y)
                if (prop is not None and prop.is_gated()) or (x, y) in anchors:
                    self.__draw_lock_badge(screen, rect, colour)

    def __draw_lock_badge(self, screen: pygame.Surface, cell: pygame.Rect,
                          colour: Tuple[int, int, int]) -> None:
        """
        The little lock chip in a gated cell's top-right corner: flat
        fill, 2 px border in the gate's status colour, icon on top.
        """
        badge = pygame.Rect(cell.right - BADGE_SIZE - BADGE_INSET,
                            cell.top + BADGE_INSET, BADGE_SIZE, BADGE_SIZE)
        pygame.draw.rect(screen, HEADER_TAN, badge)
        # [ICON PLACEHOLDER: assets/ui/icon_lock.png -- firewall / locked
        #  action, drawn at 16x16. Missing today, so the chip shows the
        #  PLACEHOLDER square inside its border (Style Guide §5.2).]
        icon = self.__load_scaled(LOCK_ICON_PATH, BADGE_SIZE)
        if icon is not None:
            screen.blit(icon, badge.topleft)
        else:
            pygame.draw.rect(screen, PLACEHOLDER, badge.inflate(-4, -4))
        pygame.draw.rect(screen, colour, badge, BADGE_BORDER_W)

    # -- reporting --------------------------------------------
    def get_missing_paths(self) -> List[str]:
        """
        Every asset path that failed to load this session, sorted.

        The sandbox prints this on exit so the artist gets a work queue
        rather than a bug report (Style Guide §5.2 step 4).
        """
        return sorted(self.__missing)


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to fly over a real level.
# Abu Huraira removes this block when he plugs in the real game.
#   Arrows / WASD -> pan the camera (this stub does NOT walk -- the
#                    player sprite sits at the spawn cell; walking is
#                    play_sandbox.py's job, because moving a player is
#                    a game decision and this file makes none)
#   TAB           -> cycle the player's facing
#   SPACE         -> step the walk frame
#   G             -> cycle the ambient tint preset (morning/day/evening/night)
#   L             -> toggle the demo gate markers locked / open
#   F11           -> toggle windowed / fullscreen
#   ESC           -> quit
#
# The level is the real levels/campus_main.json, loaded through
# engine/level_loader.py. Its walls, pond and portal have no art yet
# and draw as PLACEHOLDER squares -- which is the point: collision
# comes from the registry, so the level is fully playable anyway.
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    # Imported HERE, inside the runner, not at module scope: the class
    # above never imports engine/, so ui/ keeps its one-way dependency.
    from content.level_registry import AMBIENT_PRESETS
    from engine.level_loader import Level, load_level_document

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Map screen test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    # The DOCUMENT is kept around so the ambient key can retint the level:
    # a Level is read-only by design, so the honest way to change its tint
    # is to edit the document and build a new view, which is exactly what
    # the game does when it walks through a portal.
    demo_document = load_level_document("campus_main")
    demo_level = Level(demo_document)
    demo_map = MapScreen()

    spawn_cell = demo_level.get_spawn()
    focus = [spawn_cell[0] * CELL + CELL / 2.0,
             spawn_cell[1] * CELL + CELL / 2.0]
    facing_index = 0
    walk_frame = 0
    ambient_index = list(AMBIENT_PRESETS).index(demo_level.get_ambient())
    gates_locked = True
    PAN_SPEED = 400.0

    # A stand-in for F8's verdicts so the marker colours can be seen
    # before engine/gate_evaluator.py exists.
    demo_gate_cells = {(x, y)
                       for y in range(demo_level.get_grid_size()[1])
                       for x in range(demo_level.get_grid_size()[0])
                       if demo_level.get_gate_at(x, y) is not None}

    running = True
    while running:
        frame_dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    window = pygame.display.set_mode(
                        SIZE, FULLSCREEN_FLAGS if is_fullscreen
                        else WINDOWED_FLAGS)
                elif event.key == pygame.K_TAB:
                    facing_index = (facing_index + 1) % len(FACINGS)
                elif event.key == pygame.K_SPACE:
                    walk_frame = (walk_frame + 1) % PLAYER_FRAMES
                elif event.key == pygame.K_g:
                    ambient_index = (ambient_index + 1) % len(AMBIENT_PRESETS)
                    demo_document.set_ambient(AMBIENT_PRESETS[ambient_index])
                    demo_level = Level(demo_document)
                elif event.key == pygame.K_l:
                    gates_locked = not gates_locked

        held = pygame.key.get_pressed()
        if held[pygame.K_LEFT] or held[pygame.K_a]:
            focus[0] -= PAN_SPEED * frame_dt
        if held[pygame.K_RIGHT] or held[pygame.K_d]:
            focus[0] += PAN_SPEED * frame_dt
        if held[pygame.K_UP] or held[pygame.K_w]:
            focus[1] -= PAN_SPEED * frame_dt
        if held[pygame.K_DOWN] or held[pygame.K_s]:
            focus[1] += PAN_SPEED * frame_dt

        demo_camera = demo_map.compute_camera(demo_level, focus, window)
        demo_map.render(window, demo_level, demo_camera, focus,
                        FACINGS[facing_index], walk_frame,
                        gate_states={cell: gates_locked
                                     for cell in demo_gate_cells},
                        dt=frame_dt)

        # Dev text sits on a flat HEADER_TAN plate: muted brown straight
        # onto grass is the same value as the grass. A boxed footer fill
        # (§2.1) is what the style guide already uses for this.
        def plate(text: str, topleft: tuple) -> None:
            """Draw one line of stub-test text on a bordered tan plate."""
            surface = hint_font.render(text, True, STAT_BROWN)
            box = pygame.Rect(topleft[0], topleft[1],
                              surface.get_width() + 16,
                              surface.get_height() + 12)
            pygame.draw.rect(window, HEADER_TAN, box)
            pygame.draw.rect(window, BORDER_BROWN, box, 2)
            window.blit(surface, (box.x + 8, box.y + 6))

        cursor_cell = demo_map.get_cell_for_screen_point(
            pygame.mouse.get_pos(), demo_camera)
        plate(f"{demo_level.get_level_name()}  |  camera {demo_camera}  |  "
              f"cell {cursor_cell}  |  ambient {demo_level.get_ambient()}  |  "
              f"facing {FACINGS[facing_index]}  |  "
              f"gates {'locked' if gates_locked else 'open'}", (10, 8))

        hint_text = ("WASD/arrows pan  |  TAB facing  |  SPACE frame  |  "
                     "G ambient  |  L gates  |  F11 fullscreen  |  ESC quit")
        hint_w = hint_font.size(hint_text)[0] + 16
        hint_h = hint_font.get_height() + 12
        plate(hint_text, (window.get_width() - hint_w - 10,
                          window.get_height() - hint_h - 8))

        pygame.display.flip()

    if demo_map.get_missing_paths():
        print("missing art (Style Guide §5.2 queue):")
        for path in demo_map.get_missing_paths():
            print(f"  {path}")

    pygame.quit()

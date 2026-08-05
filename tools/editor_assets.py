"""
tools/editor_assets.py
CSE Life: Compile & Conquer — Level editor, phase E2
─────────────────────────────────────────────────────────────
Sprite loading for the editor, with the Style Guide §5.2
placeholder protocol built in: EVERY loader returns None on
failure and the caller draws a PLACEHOLDER square. Missing art
must never crash the editor or shift its layout.

Registry entries name a sheet plus a cell (col, row, cell_px).
Single-image assets are simply a 1x1 sheet. Source art is 16x16
for tiles/props and 48x48 for characters; everything is scaled
with `pygame.transform.scale`, which does no smoothing, so the
pixels stay hard-edged at any integer multiple.

Which art goes where (owner ruling 2026-07-29):
    map      -> the NPC's `idle` sheet
    editor   -> the NPC's `level_editor` frame
    dialog   -> the NPC's emotion portraits
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import pygame

from content.level_registry import (
    get_npc_def,
    get_npc_portrait_path,
    get_prop_def,
    get_prop_footprint,
    get_tile_def,
    resolve_asset,
)


class AssetCache:
    """
    Loads and scales sprites once, then hands out the same surface.

    OOP: Encapsulation — both caches are private; callers only ever
    ask for a finished surface at a size.
    """

    def __init__(self) -> None:
        self.__sheets: Dict[str, Optional[pygame.Surface]] = {}
        self.__cells: Dict[Tuple, Optional[pygame.Surface]] = {}
        self.__missing: set = set()

    # ── low level ─────────────────────────────────────────────

    def __sheet(self, path: str) -> Optional[pygame.Surface]:
        """
        Load a sheet once. None (remembered) when the file is absent.
        Registry paths are repo-relative, so they are resolved against
        the project root — never against the working directory.
        """
        if path in self.__sheets:
            return self.__sheets[path]
        try:
            image = pygame.image.load(resolve_asset(path))
            image = image.convert_alpha() if pygame.display.get_init() \
                else image
        except (FileNotFoundError, OSError, pygame.error):
            image = None
            self.__missing.add(path)
        self.__sheets[path] = image
        return image

    def __cell(self, path: str, col: int, row: int, cell_px: int,
               size: int) -> Optional[pygame.Surface]:
        """Slice one cell out of a sheet and scale it to `size`."""
        key = (path, col, row, cell_px, size)
        if key in self.__cells:
            return self.__cells[key]

        sheet = self.__sheet(path)
        surface: Optional[pygame.Surface] = None
        if sheet is not None:
            area = pygame.Rect(col * cell_px, row * cell_px, cell_px, cell_px)
            if sheet.get_rect().contains(area):
                surface = pygame.transform.scale(sheet.subsurface(area),
                                                 (size, size))
            else:
                # sheet exists but is the wrong shape — treat as missing
                # art rather than crashing mid-frame
                self.__missing.add(path)
        self.__cells[key] = surface
        return surface

    def __from_registry(self, entry: Optional[dict], sheet_key: str,
                        size: int) -> Optional[pygame.Surface]:
        """Shared path for the registry-shaped entries."""
        if entry is None:
            return None
        return self.__cell(entry.get(sheet_key, ""), int(entry.get("col", 0)),
                           int(entry.get("row", 0)),
                           int(entry.get("cell_px", 16)), size)

    # ── public loaders ────────────────────────────────────────

    def get_tile(self, tile_index: int, size: int) -> Optional[pygame.Surface]:
        """Tile sprite at `size`, or None when its art is missing."""
        return self.__from_registry(get_tile_def(tile_index), "sheet", size)

    def get_prop(self, type_id: str, size: int) -> Optional[pygame.Surface]:
        """Prop sprite at `size`, or None when its art is missing."""
        return self.__from_registry(get_prop_def(type_id), "sheet", size)

    def get_prop_footprint_sprite(self, type_id: str,
                                  cell_px: int) -> Optional[pygame.Surface]:
        """
        Prop sprite at its FULL footprint, for canvas drawing.

        A 1x1 prop is one cell, as always. A multi-cell prop (a tree)
        comes back at cells_w x cells_h cells, because its art is not
        square and slicing a square cell out of it would show only the
        bottom-left corner. The palette still uses get_prop(), which
        squeezes the whole thing into one square swatch.
        """
        cells_w, cells_h = get_prop_footprint(type_id)
        if (cells_w, cells_h) == (1, 1):
            return self.get_prop(type_id, cell_px)
        entry = get_prop_def(type_id)
        if entry is None:
            return None
        path = str(entry.get("sheet", ""))
        key = ("footprint", path, cells_w, cells_h, cell_px)
        if key not in self.__cells:
            sheet = self.__sheet(path)
            self.__cells[key] = None if sheet is None else \
                pygame.transform.scale(
                    sheet, (cells_w * cell_px, cells_h * cell_px))
        return self.__cells[key]

    def get_npc_editor(self, type_id: str,
                       size: int) -> Optional[pygame.Surface]:
        """
        The NPC's `level_editor` art — palette cell and canvas preview.
        This is editor chrome; the game never shows it.

        Falls back to the first frame of the idle sheet when the
        dedicated icon is absent. Only two of the seven NPCs ever got a
        `_level_editor.png`, so without this the other five drew as
        blank placeholder squares and were impossible to tell apart in
        the palette — an NPC with a map sprite should always be
        recognisable, even before its icon is drawn.

        The missing path is still recorded, so `get_missing_paths()`
        keeps listing it as art worth making.
        """
        entry = get_npc_def(type_id)
        if entry is None:
            return None
        cell_px = int(entry.get("cell_px", 48))
        icon = str(entry.get("editor_icon", ""))
        surface = self.__cell(icon, 0, 0, cell_px, size) if icon else None
        if surface is None:
            surface = self.__cell(str(entry.get("idle_sheet", "")), 0, 0,
                                  cell_px, size)
        return surface

    def get_npc_idle(self, type_id: str, size: int,
                     frame: int = 0) -> Optional[pygame.Surface]:
        """
        One frame of the NPC's idle sheet — what actually stands in the
        map. Frames wrap, so an animation index can be passed straight in.
        """
        entry = get_npc_def(type_id)
        if entry is None:
            return None
        frames = max(1, int(entry.get("frames", 1)))
        return self.__cell(entry.get("idle_sheet", ""), frame % frames, 0,
                           int(entry.get("cell_px", 48)), size)

    def get_npc_portrait(self, type_id: str, emotion: str,
                         size: int) -> Optional[pygame.Surface]:
        """
        The emotion face for the dialog box. Unknown emotions fall back
        to the NPC's default portrait (registry rule).
        """
        path = get_npc_portrait_path(type_id, emotion)
        if not path:
            return None
        sheet = self.__sheet(path)
        if sheet is None:
            return None
        key = ("portrait", path, size)
        if key not in self.__cells:
            self.__cells[key] = pygame.transform.scale(sheet, (size, size))
        return self.__cells[key]

    def get_icon(self, path: str, size: int) -> Optional[pygame.Surface]:
        """A UI icon scaled to `size`, or None when the PNG is missing."""
        sheet = self.__sheet(path)
        if sheet is None:
            return None
        key = ("icon", path, size)
        if key not in self.__cells:
            self.__cells[key] = pygame.transform.scale(sheet, (size, size))
        return self.__cells[key]

    # ── reporting ─────────────────────────────────────────────

    def get_missing_paths(self) -> list:
        """
        Every asset path that failed to load this session, sorted.
        The editor prints this on exit so the artist gets a work queue
        (Style Guide §5.2 step 4).
        """
        return sorted(self.__missing)

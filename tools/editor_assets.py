"""
tools/editor_assets.py
CSE Life: Compile & Conquer — Level editor, phase E2
─────────────────────────────────────────────────────────────
Sprite loading for the editor, with the Style Guide §5.2
placeholder protocol built in: EVERY loader returns None on
failure and the caller draws a PLACEHOLDER square. Missing art
must never crash the editor or shift its layout.

Registry entries name a sheet plus a cell (col, row, cell_px).
Single-image assets are simply a 1x1 sheet. Characters are 48x48;
everything is scaled with `pygame.transform.scale`, which does no
smoothing, so the pixels stay hard-edged at any integer multiple.

TILES are one cell by definition. PROPS are not: a prop is drawn
at whatever size its PNG actually is, measured against the 16 px
cell unit (content/level_registry.get_prop_draw_size), so art of
any dimensions lands on the map uncropped and unstretched.

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
    TILE_SOURCE_PX,
    get_npc_def,
    get_npc_portrait_path,
    get_prop_def,
    get_prop_pixel_size,
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
            elif (col, row) == (0, 0):
                # A single-image asset whose PNG is not the shape the
                # registry expected. Scaling the WHOLE file into the
                # cell shows all of it; slicing a square out showed one
                # corner and refusing showed the missing-art square. A
                # TILE is one cell by definition, so this is the only
                # honest option — art meant to span several cells
                # belongs in assets/props, which draws at true size.
                surface = pygame.transform.scale(sheet, (size, size))
            else:
                # A real sheet whose grid does not add up: that IS
                # broken art, so it goes on the artist's queue.
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

    def __prop_source(self, type_id: str) -> Tuple[Optional[pygame.Surface],
                                                   Optional[pygame.Rect]]:
        """
        (sheet, source rect) for a prop's art, or (None, None).

        The rect is the region the registry claims — px_w by px_h at
        (col, row) — EXCEPT when the file disagrees with the registry,
        in which case the file wins and the whole image is used. Art
        gets replaced mid-project; cropping it to a stale measurement
        would silently lose pixels, and scaling the real thing never
        does.
        """
        entry = get_prop_def(type_id)
        if entry is None:
            return (None, None)
        sheet = self.__sheet(str(entry.get("sheet", "")))
        if sheet is None:
            return (None, None)
        px_w, px_h = get_prop_pixel_size(type_id)
        area = pygame.Rect(int(entry.get("col", 0)) * px_w,
                           int(entry.get("row", 0)) * px_h, px_w, px_h)
        if not sheet.get_rect().contains(area):
            area = sheet.get_rect()
        return (sheet, area)

    def get_prop(self, type_id: str,
                 cell_px: int) -> Optional[pygame.Surface]:
        """
        Prop sprite at its TRUE proportions for this cell size.

        The art is scaled against the 16 px cell unit and nothing else:
        a 16x16 rock fills one cell, a 16x48 tree is one cell by three,
        a 24x40 signboard is one and a half by two and a half. Nothing
        is cropped to a square and nothing is stretched to a whole
        number of cells.

        This used to slice a square `cell_px` region out of the sheet,
        which is why every prop that was not square lost everything
        below and right of its first cell.
        """
        sheet, area = self.__prop_source(type_id)
        if sheet is None or area is None:
            return None
        key = ("prop", type_id, area.x, area.y, area.w, area.h, cell_px)
        if key not in self.__cells:
            scale = max(1, int(cell_px)) / TILE_SOURCE_PX
            self.__cells[key] = pygame.transform.scale(
                sheet.subsurface(area),
                (max(1, int(round(area.w * scale))),
                 max(1, int(round(area.h * scale)))))
        return self.__cells[key]

    def get_prop_swatch(self, type_id: str,
                        box_px: int) -> Optional[pygame.Surface]:
        """
        Prop sprite scaled to FIT a square palette cell, aspect kept.

        The palette used to squeeze every prop into a square swatch, so
        a tree and a fence post looked the same shape in the grid. This
        fits the longer side to the box instead, which makes the
        palette a preview of what will actually land on the map.
        """
        sheet, area = self.__prop_source(type_id)
        if sheet is None or area is None:
            return None
        key = ("swatch", type_id, area.x, area.y, area.w, area.h, box_px)
        if key not in self.__cells:
            scale = box_px / max(area.w, area.h)
            self.__cells[key] = pygame.transform.scale(
                sheet.subsurface(area),
                (max(1, int(round(area.w * scale))),
                 max(1, int(round(area.h * scale)))))
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

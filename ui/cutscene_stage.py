"""
ui/cutscene_stage.py
The intro's drawing half: black stage, standing sprite, fade veil.

Phase 18 §6. Pure drawing — no game logic, no `ctx` — the same rule
ui/monologue_screen.py and ui/dialog_box.py follow.

WHY THIS EXISTS AT ALL
──────────────────────
So that ui/map_screen.py is never touched. The sprite loader the intro
needs is `MapScreen.__npc_sprite`, which is name-mangled and private;
re-implementing twenty lines here is far cheaper than widening a shared
file's API for one caller.

ROYA IS DRAWN OVER THE MAP, NOT PLACED IN THE LEVEL. Three reasons, all
load-bearing (§6):

  1. `Level` is read-only by design — engine/level_loader.py says so and
     get_npcs() hands back a copy. Injecting one means rebuilding the
     Level through LevelData.
  2. The semester filter would delete her. Roya's semester_available_from
     is 4, and load_level(..., semester=1) drops every NPC who has not
     appeared yet — so a genuinely placed Roya would be invisible in the
     only semester this cutscene ever runs in.
  3. A placed NPC is talkable, solid and persistent. She would block a
     cell, need removing after the fade, and E would open her ordinary
     career-office dialogue mid-tutorial.

An overlay has none of those problems and needs no cleanup: stop drawing
her and she is gone.
"""
from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

import pygame

from content.level_registry import (TILE_SIZE_PX, get_npc_def,
                                    npc_blit_offset, npc_sprite_px)

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BLACK: Tuple[int, int, int] = (0, 0, 0)
# 48 x 6. Roya reads as a figure on the black stage, not a map token.
STAGE_NPC_PX: int = 288
# Top edge. The dialogue card occupies Rect(46, 524, 1188, 168), so a
# 288px figure topped at 150 ends at 438 — 86px of clearance. If she is
# resized, keep that gap.
STAGE_NPC_Y: int = 150
FRAME_PERIOD: float = 0.22          # seconds per idle frame

# Style Guide §5.2 placeholder, for art that is not on disk.
PLACEHOLDER: Tuple[int, int, int] = (196, 178, 150)
PLACEHOLDER_EDGE: Tuple[int, int, int] = (169, 130, 94)

# (type_id, frame, size_px) -> Surface | None. Loading and scaling a PNG
# every frame will show; None is cached too, so missing art is not
# re-probed sixty times a second.
_FRAME_CACHE: Dict[Tuple[str, int, int], Optional[pygame.Surface]] = {}
_VEIL: Optional[pygame.Surface] = None
_VEIL_KEY: Optional[Tuple[int, int, int]] = None


def frame_for(elapsed: float, frames: int = 4) -> int:
    """Which idle frame `elapsed` seconds into the beat."""
    if frames <= 0:
        return 0
    try:
        return int(max(0.0, float(elapsed)) / FRAME_PERIOD) % frames
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


def load_npc_frame(type_id: str, frame: int,
                   size_px: int) -> Optional[pygame.Surface]:
    """
    One column of row 0 of an NPC's idle sheet, scaled to `size_px`.

    Missing art returns None and the caller draws the placeholder square
    rather than crashing. Roya's art does exist
    (assets/npcs/npc_roya_idle.png), so that path is insurance.
    """
    key = (str(type_id), int(frame), int(size_px))
    if key in _FRAME_CACHE:
        return _FRAME_CACHE[key]

    surface: Optional[pygame.Surface] = None
    entry = get_npc_def(str(type_id))
    if entry is not None:
        relative = entry.get("idle_sheet") or ""
        frames = max(1, int(entry.get("frames", 4) or 4))
        cell = max(1, int(entry.get("cell_px", 48) or 48))
        path = os.path.join(PROJECT_ROOT, relative) if relative else ""
        if path and os.path.isfile(path):
            try:
                sheet = pygame.image.load(path).convert_alpha()
                column = int(frame) % frames
                clip = pygame.Rect(column * cell, 0, cell, cell)
                if sheet.get_width() >= clip.right \
                        and sheet.get_height() >= clip.bottom:
                    surface = pygame.transform.scale(
                        sheet.subsurface(clip), (int(size_px), int(size_px)))
            except (pygame.error, ValueError):
                surface = None

    _FRAME_CACHE[key] = surface
    return surface


def draw_black_stage(screen: pygame.Surface, type_id: str,
                     frame: int) -> None:
    """Fill black and stand the NPC centred at STAGE_NPC_Y."""
    screen.fill(BLACK)
    sprite = load_npc_frame(type_id, frame, STAGE_NPC_PX)
    x = screen.get_width() // 2 - STAGE_NPC_PX // 2
    if sprite is None:
        __placeholder(screen, pygame.Rect(x, STAGE_NPC_Y,
                                          STAGE_NPC_PX, STAGE_NPC_PX))
        return
    screen.blit(sprite, (x, STAGE_NPC_Y))


def draw_standing_npc(screen: pygame.Surface, map_screen, cell,
                      camera, type_id: str, frame: int) -> None:
    """
    Draw the NPC standing on one map cell, over the already-drawn map.

    Uses npc_sprite_px / npc_blit_offset from the registry rather than
    its own numbers, which is what makes the cutscene NPC sit at exactly
    the same scale and footing as a real placed one. She is NOT centred
    in the cell — that would make her hover; the offset is the
    feet-on-the-floor anchor.
    """
    if cell is None or camera is None:
        return
    try:
        rect = map_screen.get_screen_rect_for_cell(int(cell[0]), int(cell[1]),
                                                   camera)
    except (AttributeError, TypeError, ValueError, IndexError):
        return
    size = npc_sprite_px(TILE_SIZE_PX)
    dx, dy = npc_blit_offset(TILE_SIZE_PX)
    sprite = load_npc_frame(type_id, frame, size)
    if sprite is None:
        __placeholder(screen, pygame.Rect(rect.x + dx, rect.y + dy,
                                          size, size))
        return
    screen.blit(sprite, (rect.x + dx, rect.y + dy))


def draw_fade(screen: pygame.Surface, alpha: int) -> None:
    """
    Black veil over everything, at `alpha` (0-255).

    One cached SRCALPHA surface, rebuilt only when the alpha or the
    screen size changes.
    """
    global _VEIL, _VEIL_KEY
    level = max(0, min(255, int(alpha)))
    if level <= 0:
        return
    key = (screen.get_width(), screen.get_height(), level)
    if _VEIL is None or _VEIL_KEY != key:
        _VEIL = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        _VEIL.fill((0, 0, 0, level))
        _VEIL_KEY = key
    screen.blit(_VEIL, (0, 0))


def __placeholder(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """The Style Guide §5.2 block, for art that is not there."""
    pygame.draw.rect(screen, PLACEHOLDER, rect)
    pygame.draw.rect(screen, PLACEHOLDER_EDGE, rect, 3)

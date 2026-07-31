"""
tools/editor_theme.py
CSE Life: Compile & Conquer — Level editor, phase E2
─────────────────────────────────────────────────────────────
The UI Style Guide, as code.

Every colour, every font size and every drawing primitive the
editor is allowed to use lives here, so no screen re-invents a
border width or picks a hue that is not in the palette. The
values are copied verbatim from docs/UI_STYLE_GUIDE.md §2-§4.

pygame IS allowed in tools/ — the editor is asset tooling, the
same class as assemble_sprite_sheet.py (Spec §1).

Nothing here holds state or game logic: these are pure drawing
functions over surfaces and rects.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import pygame

from content.level_registry import resolve_asset

# ─────────────────────────────────────────────────────────────
# PALETTE  (Style Guide §2 — exact RGB, no new hues)
# ─────────────────────────────────────────────────────────────

PANEL_TAN = (231, 214, 189)
CARD_TAN = (240, 228, 208)
HEADER_TAN = (214, 196, 168)
BORDER_BROWN = (169, 130, 94)
TEXT_COFFEE = (74, 53, 39)
TITLE_SLATE = (45, 58, 71)
CREDIT_HL = (155, 110, 70)
STAT_BROWN = (140, 110, 85)
BAR_TRACK = (214, 196, 168)

BAR_GREEN = (167, 185, 133)
BAR_AMBER = (217, 169, 106)
BAR_RED = (199, 123, 107)
BAR_OVER = (186, 74, 62)

ROW_WHITE = (247, 243, 236)
ROW_BLUE = (120, 150, 190)
ROW_GREEN = (150, 180, 125)

BTN_CONFIRM = (150, 180, 125)
BTN_CANCEL = (199, 123, 107)

PLACEHOLDER = (196, 178, 150)
PORTRAIT_BG = (255, 255, 255)
PORTRAIT_FILL = (190, 165, 135)
PORTRAIT_LABEL = (120, 95, 75)

OVERLAY_DIM = (25, 18, 12, 160)
HINT_BROWN = (150, 125, 100)

# ─────────────────────────────────────────────────────────────
# TYPOGRAPHY  (Style Guide §3)
# ─────────────────────────────────────────────────────────────

FONT_PATH = "assets/ui/PressStart2P.ttf"

SIZE_TITLE = 26
SIZE_TOTAL = 16
SIZE_POPUP_TITLE = 16
SIZE_BODY = 12
SIZE_SUB = 11
SIZE_LABEL = 10

# ─────────────────────────────────────────────────────────────
# LAYOUT  (Style Guide §4)
# ─────────────────────────────────────────────────────────────

SCREEN_W = 1280
SCREEN_H = 720

TOP_BAR_H = 44
SIDE_PANEL_W = 280

CARD_PAD = 14
CORNER_LEN = 22
BORDER_CARD = 3
BORDER_ROW = 2
BORDER_HUD = 4

BTN_H = 44
ROW_H = 38
ROW_PITCH = 44
HEADER_H = 34

_FONT_CACHE: dict = {}


def load_font(size: int) -> pygame.font.Font:
    """
    The pixel font at `size`, cached. Falls back to a system font so
    a missing TTF can never crash the editor (Style Guide §3).
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(resolve_asset(FONT_PATH),
                                                 size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


# ─────────────────────────────────────────────────────────────
# TEXT
# ─────────────────────────────────────────────────────────────


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str,
              pos: Tuple[int, int], colour: tuple) -> pygame.Rect:
    """Draw text at a top-left position; returns the rect it filled."""
    rendered = font.render(text, True, colour)
    surface.blit(rendered, pos)
    return rendered.get_rect(topleft=pos)


def draw_text_centered(surface: pygame.Surface, font: pygame.font.Font,
                       text: str, rect: pygame.Rect, colour: tuple) -> None:
    """Draw text centred inside a rect."""
    rendered = font.render(text, True, colour)
    surface.blit(rendered, (rect.x + (rect.w - rendered.get_width()) // 2,
                            rect.y + (rect.h - rendered.get_height()) // 2))


def draw_text_vcenter(surface: pygame.Surface, font: pygame.font.Font,
                      text: str, x: int, rect: pygame.Rect,
                      colour: tuple) -> None:
    """Draw text at `x`, vertically centred in a row."""
    rendered = font.render(text, True, colour)
    surface.blit(rendered, (x, rect.y + (rect.h - rendered.get_height()) // 2))


def fit_font(text: str, max_w: int,
             sizes: Sequence[int] = (SIZE_BODY, SIZE_SUB, SIZE_LABEL,
                                     9, 8)) -> pygame.font.Font:
    """
    The largest font from `sizes` that renders `text` inside `max_w`.

    Press Start 2P is a fixed-advance pixel face, so a label like
    "SETTINGS" simply will not fit a quarter of a 280 px panel at the
    body size. Stepping down the scale keeps the label whole and
    readable instead of truncating it to "SETTIN...".
    """
    chosen = sizes[-1]
    for size in sizes:
        if load_font(size).size(text)[0] <= max_w:
            chosen = size
            break
    return load_font(chosen)


def truncate(font: pygame.font.Font, text: str, max_w: int) -> str:
    """
    Shorten text with a trailing ellipsis until it fits. The Style
    Guide forbids wrapping logic, so long strings are clipped, never
    reflowed (§3).
    """
    if font.size(text)[0] <= max_w:
        return text
    while text and font.size(text + "...")[0] > max_w:
        text = text[:-1]
    return text + "..."


# ─────────────────────────────────────────────────────────────
# SURFACES
# ─────────────────────────────────────────────────────────────


def draw_panel(surface: pygame.Surface, rect: pygame.Rect, fill: tuple,
               border: int = BORDER_ROW,
               border_colour: tuple = BORDER_BROWN) -> None:
    """Flat filled rect with a square border — the base of everything."""
    pygame.draw.rect(surface, fill, rect)
    if border > 0:
        pygame.draw.rect(surface, border_colour, rect, border)


def draw_corner_marks(surface: pygame.Surface, rect: pygame.Rect,
                      colour: tuple = BORDER_BROWN,
                      length: int = CORNER_LEN) -> None:
    """
    The franchise signature: two 3 px arms at each corner of a frame
    (Style Guide §4.2). Never omit these on a card.
    """
    corners = (
        ((rect.left, rect.top), (length, 0), (0, length)),
        ((rect.right, rect.top), (-length, 0), (0, length)),
        ((rect.left, rect.bottom), (length, 0), (0, -length)),
        ((rect.right, rect.bottom), (-length, 0), (0, -length)),
    )
    for (px, py), (dx1, dy1), (dx2, dy2) in corners:
        pygame.draw.line(surface, colour, (px, py), (px + dx1, py + dy1), 3)
        pygame.draw.line(surface, colour, (px, py), (px + dx2, py + dy2), 3)


def draw_card(surface: pygame.Surface, rect: pygame.Rect,
              fill: tuple = CARD_TAN, accent: tuple = BORDER_BROWN,
              border: int = BORDER_CARD) -> None:
    """The signature framed card: fill, outline, inner rule, corners."""
    pygame.draw.rect(surface, fill, rect)
    pygame.draw.rect(surface, accent, rect, border)
    inner = rect.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
    pygame.draw.rect(surface, accent, inner, 1)
    draw_corner_marks(surface, inner, accent)


def draw_button(surface: pygame.Surface, rect: pygame.Rect, label: str,
                fill: tuple, font: Optional[pygame.font.Font] = None,
                enabled: bool = True) -> None:
    """
    Flat button, 3 px border, ALL-CAPS centred label (§4.6). Disabled
    buttons desaturate toward the panel tan instead of changing shape.
    """
    font = font or load_font(SIZE_BODY)
    body = fill if enabled else _blend(fill, PANEL_TAN, 0.6)
    pygame.draw.rect(surface, body, rect)
    pygame.draw.rect(surface, BORDER_BROWN, rect, BORDER_CARD)
    draw_text_centered(surface, font, label.upper(), rect,
                       TEXT_COFFEE if enabled else STAT_BROWN)


def draw_chip(surface: pygame.Surface, rect: pygame.Rect, label: str,
              active: bool, font: Optional[pygame.font.Font] = None,
              active_fill: tuple = ROW_BLUE) -> None:
    """
    A two-state toggle chip. Active chips take the accent fill, the
    rest sit on HEADER_TAN (Spec §5.3 / §6.3).
    """
    text = label.upper()
    font = font or fit_font(text, rect.w - 6, (SIZE_LABEL, 9, 8))
    draw_panel(surface, rect, active_fill if active else HEADER_TAN,
               BORDER_ROW)
    draw_text_centered(surface, font, text, rect,
                       ROW_WHITE if active else TEXT_COFFEE)


def draw_progress(surface: pygame.Surface, rect: pygame.Rect, ratio: float,
                  fill: tuple = ROW_BLUE,
                  track: tuple = BAR_TRACK) -> None:
    """Track, left-anchored fill, 2 px outline (§4.5)."""
    pygame.draw.rect(surface, track, rect)
    filled = int(rect.w * max(0.0, min(1.0, ratio)))
    if filled > 0:
        pygame.draw.rect(surface, fill,
                         pygame.Rect(rect.x, rect.y, filled, rect.h))
    pygame.draw.rect(surface, BORDER_BROWN, rect, BORDER_ROW)


def draw_placeholder(surface: pygame.Surface, rect: pygame.Rect,
                     label: str = "") -> None:
    """
    The mandatory missing-art square (Style Guide §5.2). Drawn wherever
    a sprite or icon failed to load — the editor must stay usable long
    before the art does.
    """
    pygame.draw.rect(surface, PLACEHOLDER, rect)
    pygame.draw.rect(surface, BORDER_BROWN, rect, 1)
    if label and rect.w >= 40:
        draw_text_centered(surface, load_font(SIZE_LABEL),
                           truncate(load_font(SIZE_LABEL), label,
                                    rect.w - 6),
                           rect, PORTRAIT_LABEL)


def draw_dim_overlay(surface: pygame.Surface) -> None:
    """Dim the whole screen behind a modal (§2.6)."""
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill(OVERLAY_DIM)
    surface.blit(shade, (0, 0))


def draw_rule(surface: pygame.Surface, y: int, x1: int, x2: int,
              colour: tuple = BORDER_BROWN) -> None:
    """
    Ceremonial horizontal rule: two segments with a diamond in the gap
    (§4.8). Used on popup headers.
    """
    mid = (x1 + x2) // 2
    pygame.draw.line(surface, colour, (x1, y), (mid - 14, y), 2)
    pygame.draw.line(surface, colour, (mid + 14, y), (x2, y), 2)
    pygame.draw.polygon(surface, colour, [(mid, y - 5), (mid + 7, y),
                                          (mid, y + 5), (mid - 7, y)])


def _blend(a: tuple, b: tuple, t: float) -> tuple:
    """Mix two palette colours — only used to mute disabled controls."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def darken(colour: tuple, amount: float = 0.1) -> tuple:
    """
    Darken a fill by ~10% for a hover/pressed state — the only visual
    change the Style Guide permits on buttons (§4.6).
    """
    return tuple(max(0, int(channel * (1.0 - amount))) for channel in colour)


def status_colour(value: float, limit: float) -> tuple:
    """
    The franchise traffic light: blue under the limit, amber exactly
    at it, red over it (§2.2). Reused by every gauge in the editor.
    """
    if value > limit:
        return BAR_OVER
    if value == limit:
        return BAR_AMBER
    return ROW_BLUE


def hit(rects: Sequence[pygame.Rect], pos: Tuple[int, int]) -> int:
    """Index of the first rect containing `pos`, or -1."""
    for index, rect in enumerate(rects):
        if rect.collidepoint(pos):
            return index
    return -1

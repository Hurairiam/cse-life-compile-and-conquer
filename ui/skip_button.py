"""
ui/skip_button.py
The SKIP control both lecture screens carry (Task 1).

WHY THIS IS ITS OWN FILE
────────────────────────
Two screens need the same button in the same place —
engine/states/side_quest_lecture.py and engine/states/lecture.py — and
Task 1 says "present on every lecture". One module means one geometry:
move the button here and it moves on both, and neither screen can drift
into drawing it somewhere slightly different.

It is also the rule the rest of this engine already follows
(engine/menu_prop.py, engine/day_drain.py, engine/final_exam.py): new
logic in a new file, and the shared modules take the smallest possible
call site.

WHERE IT SITS, AND WHY THAT IS NOT A GUESS
──────────────────────────────────────────
Top right, BELOW the HUD. Neither lecture state is in
`engine/state_router.py::HUD_HIDDEN`, so the 44px HUD strip is drawn
over both of them every frame — a button at y=0 would sit underneath the
day/wallet/semester readouts. `TOP_GAP` is measured from
`ui.hud.STRIP_HEIGHT` rather than from a copied 44, so if the strip ever
changes height this follows it instead of quietly overlapping again.

NO GAME LOGIC HERE. This draws a rectangle and hands it back for
hit-testing, the way ui/pause_menu.py and ui/skill_tree_screen.py do.
What a press MEANS is the calling state's decision (§6.2).
"""
from __future__ import annotations

import os

import pygame

from ui.hud import STRIP_HEIGHT

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")

# -- palette (UI_STYLE_GUIDE §2, same values the other screens copy) --
HEADER_TAN   = (214, 196, 168)   # the button fill
BORDER_BROWN = (169, 130, 94)    # its outline
TEXT_COFFEE  = (74, 53, 39)      # its label
HOVER_TAN    = (231, 214, 189)   # a shade up, under the cursor

# -- layout ----------------------------------------------------
BTN_W       = 132
BTN_H       = 38
BORDER_BTN  = 3
RIGHT_GAP   = 24                 # from the right edge of the screen
TOP_GAP     = 12                 # clear of the HUD strip, not over it
SIZE_LABEL  = 10

LABEL = "SKIP"

_FONT_CACHE: dict = {}


def load_font(size: int) -> pygame.font.Font:
    """The pixel font at `size`, cached, with the mandatory fallback."""
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


def get_rect(screen_w: int) -> pygame.Rect:
    """
    Where the button is, for drawing and for hit-testing.

    Both callers ask this rather than keeping their own copy, so a click
    can never be tested against a rectangle different from the one the
    player saw.
    """
    return pygame.Rect(int(screen_w) - RIGHT_GAP - BTN_W,
                       STRIP_HEIGHT + TOP_GAP, BTN_W, BTN_H)


def hit(screen_w: int, pos) -> bool:
    """True when `pos` is inside the button."""
    try:
        return get_rect(screen_w).collidepoint(pos)
    except (TypeError, ValueError):
        return False


def render(screen: pygame.Surface, screen_w: int,
           label: str = LABEL) -> pygame.Rect:
    """
    Draw the button and return its rectangle.

    Lights up under the cursor so it reads as pressable on a screen
    whose every other pixel is text.
    """
    rect = get_rect(screen_w)
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(screen, HOVER_TAN if hovered else HEADER_TAN, rect)
    pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_BTN)
    rendered = load_font(SIZE_LABEL).render(str(label).upper(), True,
                                            TEXT_COFFEE)
    screen.blit(rendered, (rect.centerx - rendered.get_width() // 2,
                           rect.centery - rendered.get_height() // 2))
    return rect

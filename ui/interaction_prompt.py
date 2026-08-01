"""
CSE Life: Compile & Conquer
ui/interaction_prompt.py

The small chip that floats above whatever the player is standing
in front of: [E] TALK over an NPC, [E] ENTER over a portal,
[E] EXAMINE over an interactable prop, [E] LOCKED over a gate they
cannot pass yet.

It is deliberately tiny and deliberately dumb. It bobs a couple of
pixels so the eye finds it against a busy tile map, and that is the
only motion in it -- flat fill, 2 px border, ALL-CAPS label, no
fade, no scale, no shadow (§7).

This file has NO game logic. render() is handed the label to draw
and the screen rectangle of the cell to sit above; it does not
decide whether anything is interactable, does not read the level,
and does not know what the E key is bound to. The runner works out
which cell the player faces (ui/map_screen.py turns that cell into
a rectangle) and picks the verb.

Abu Huraira removes the stub test block when he plugs in the real game.
"""
from __future__ import annotations

import math
import os
from typing import Dict, Optional, Tuple

import pygame

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. Every new UI file declares
# its own block (Build Plan §0.5); nothing here is imported from another
# screen, so this file runs on its own.
HEADER_TAN = (214, 196, 168)    # the chip fill (§2.1 boxed footer fill)
BORDER_BROWN = (169, 130, 94)   # the chip outline
TEXT_COFFEE = (74, 53, 39)      # the label
BAR_RED = (199, 123, 107)       # a locked target's outline (§2.2)
STAT_BROWN = (140, 110, 85)     # muted hint text (stub test only)
PANEL_TAN = (231, 214, 189)     # stub-test backdrop

# Anchored to the project, not to the working directory, so the font
# loads the same whether the game was started from the project root,
# from an IDE, or from a shortcut.
FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "ui", "PressStart2P.ttf")

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
LABEL_SIZE = 10         # §3 label/hint size
PAD_X = 10              # horizontal padding inside the chip
PAD_Y = 6               # vertical padding inside the chip
BORDER_W = 2            # §4.4 border weight
CELL_GAP = 8            # gap between the chip and the top of the cell

BOB_PX = 3              # how far the chip rides up and down
BOB_PERIOD = 0.9        # seconds per bob, matching the dialog arrow

# The four verbs the sandbox and the state manager use. Kept here so
# nobody spells "[E] EXAMINE" three different ways.
LABEL_TALK = "[E] TALK"
LABEL_ENTER = "[E] ENTER"
LABEL_EXAMINE = "[E] EXAMINE"
LABEL_LOCKED = "[E] LOCKED"

_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def load_font(size: int) -> pygame.font.Font:
    """
    The pixel font at `size`, cached, with the mandatory fallback.

    §3: every font load falls back to SysFont("Courier", size + 3,
    bold=True) so a missing TTF degrades instead of crashing.
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


class InteractionPrompt:
    """
    Draws one floating prompt chip.

    It never fetches its own data -- render() is handed the verb, the
    cell rectangle and the pulse clock, so the visuals stay separate
    from whatever decided there was something to interact with
    (separation of concerns).

    The chip rect is exposed through a getter so a caller can keep it
    clear of the dialog box or test it for a click.
    """

    def __init__(self) -> None:
        """Load the label font once, up front."""
        self.__font: pygame.font.Font = load_font(LABEL_SIZE)
        self.__rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    # -- rectangle getters (for layout decisions outside this file) ---
    def get_rect(self) -> pygame.Rect:
        """Where the chip was last drawn. Empty until the first render."""
        return self.__rect

    def measure(self, label: str, cell_rect: pygame.Rect,
                pulse: float = 0.0) -> pygame.Rect:
        """
        Where the chip WOULD be drawn for this label and cell.

        Centred horizontally on the cell and floated above it, plus the
        bob offset, so a caller can reserve the space before drawing --
        or clamp it back on screen when the target sits at the top edge.
        """
        text = label.upper()
        width = self.__font.size(text)[0] + PAD_X * 2
        height = self.__font.get_height() + PAD_Y * 2
        bob = int(BOB_PX * math.sin(pulse * 2 * math.pi / BOB_PERIOD))
        return pygame.Rect(cell_rect.centerx - width // 2,
                           cell_rect.top - height - CELL_GAP + bob,
                           width, height)

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, label: str,
               cell_rect: pygame.Rect, pulse: float = 0.0,
               is_locked: bool = False,
               clamp_to: Optional[pygame.Rect] = None) -> None:
        """
        Draw the chip above a cell.

        label     : the verb, drawn ALL CAPS (LABEL_TALK and friends)
        cell_rect : the target cell on screen, from
                    MapScreen.get_screen_rect_for_cell()
        pulse     : a seconds counter driving the bob
        is_locked : outline the chip in BAR_RED instead of BORDER_BROWN,
                    reusing the §2.2 danger colour rather than inventing
                    a "locked" hue
        clamp_to  : optional rectangle to keep the chip inside, so a
                    target against the top of the viewport still shows
                    its prompt
        """
        if not label:
            return
        text = label.upper()
        rect = self.measure(text, cell_rect, pulse)
        if clamp_to is not None:
            rect = self.__clamp(rect, clamp_to, cell_rect, pulse)
        self.__rect = rect

        pygame.draw.rect(screen, HEADER_TAN, rect)
        pygame.draw.rect(screen, BAR_RED if is_locked else BORDER_BROWN,
                         rect, BORDER_W)
        surface = self.__font.render(text, True, TEXT_COFFEE)
        screen.blit(surface, (rect.centerx - surface.get_width() // 2,
                              rect.centery - surface.get_height() // 2))

    # -- piece-by-piece drawing -------------------------------
    def __clamp(self, rect: pygame.Rect, bounds: pygame.Rect,
                cell_rect: pygame.Rect, pulse: float) -> pygame.Rect:
        """
        Keep the chip inside `bounds`.

        A target near the top of the viewport has no room above it, so
        the chip flips to below the cell rather than being drawn half
        off screen; left and right are simply pushed back in.
        """
        placed = rect.copy()
        if placed.top < bounds.top:
            bob = int(BOB_PX * math.sin(pulse * 2 * math.pi / BOB_PERIOD))
            placed.top = cell_rect.bottom + CELL_GAP + bob
        placed.left = max(bounds.left, min(bounds.right - placed.w,
                                           placed.left))
        placed.top = max(bounds.top, min(bounds.bottom - placed.h,
                                         placed.top))
        return placed


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see the prompt chip.
# Abu Huraira removes this block when he plugs in the real game.
#   SPACE  -> cycle the verb: TALK / ENTER / EXAMINE / LOCKED
#   Arrows -> move the fake target cell around
#   C      -> toggle clamping (drag the cell to the top edge to see it)
#   F11    -> toggle windowed / fullscreen
#   ESC    -> quit
#
# The grey square is a stand-in for a map cell -- in the real game the
# rectangle comes from MapScreen.get_screen_rect_for_cell(), which is
# why this file needs no level and no camera to be exercised.
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Interaction prompt test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    prompt = InteractionPrompt()
    LABELS: Tuple[str, ...] = (LABEL_TALK, LABEL_ENTER, LABEL_EXAMINE,
                               LABEL_LOCKED)
    label_index = 0
    cell = pygame.Rect(620, 340, 48, 48)
    clamping = True
    pulse = 0.0
    CELL_FILL = (196, 178, 150)
    VIEWPORT = pygame.Rect(0, 44, SIZE[0], SIZE[1] - 44)

    running = True
    while running:
        pulse += clock.tick(60) / 1000.0

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
                elif event.key == pygame.K_SPACE:
                    label_index = (label_index + 1) % len(LABELS)
                elif event.key == pygame.K_c:
                    clamping = not clamping

        held = pygame.key.get_pressed()
        step = int(300 * clock.get_time() / 1000.0) or 1
        if held[pygame.K_LEFT]:
            cell.x -= step
        if held[pygame.K_RIGHT]:
            cell.x += step
        if held[pygame.K_UP]:
            cell.y -= step
        if held[pygame.K_DOWN]:
            cell.y += step

        window.fill(PANEL_TAN)
        pygame.draw.rect(window, BORDER_BROWN,
                         pygame.Rect(0, VIEWPORT.top - 4, SIZE[0], 4))
        pygame.draw.rect(window, CELL_FILL, cell)
        pygame.draw.rect(window, BORDER_BROWN, cell, 2)

        current = LABELS[label_index]
        prompt.render(window, current, cell, pulse,
                      is_locked=current == LABEL_LOCKED,
                      clamp_to=VIEWPORT if clamping else None)

        header = hint_font.render(
            f"label {current}  |  cell {tuple(cell.topleft)}  |  "
            f"chip {tuple(prompt.get_rect().topleft)}  |  "
            f"clamp {'on' if clamping else 'off'}", True, STAT_BROWN)
        window.blit(header, (10, 14))

        hint = hint_font.render(
            "SPACE verb  |  arrows move target  |  C clamp"
            "  |  F11 fullscreen  |  ESC quit", True, STAT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 12,
                           window.get_height() - hint.get_height() - 8))

        pygame.display.flip()

    pygame.quit()

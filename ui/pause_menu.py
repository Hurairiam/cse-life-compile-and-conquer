"""
ui/pause_menu.py
CSE Life: Compile & Conquer — phase F10  (Feature 7, the pause overlay)
─────────────────────────────────────────────────────────────
The in-game pause menu: a dim overlay and a small centred card of
seven buttons.

An OVERLAY, not a screen — the world stays visible and dimmed
underneath, and while it is open it eats every event
(consumes_input()), so a click can never fall through to the map
below (§4.7).

This file has NO game logic. It records which button is focused
and hands back rectangles; whether the game actually saves, quits
or opens the skill tree is the caller's decision (§6.1/§6.2).

Self-contained by owner ruling (Build Plan §0.5): the palette and
layout constants below are copied verbatim from UI_STYLE_GUIDE.md
§2-§4 rather than imported from another screen.

Layout + test by Nangiba Tasnim (Dev 3).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import pygame

# -------------------------------------------------------------
# PATHS
# -------------------------------------------------------------
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues (§0.5).
PANEL_TAN     = (231, 214, 189)   # stub-test background only
CARD_TAN      = (240, 228, 208)   # the card fill
HEADER_TAN    = (214, 196, 168)   # the four neutral buttons
BORDER_BROWN  = (169, 130, 94)    # every outline and corner mark
TEXT_COFFEE   = (74, 53, 39)      # button labels
STAT_BROWN    = (140, 110, 85)    # stub-test secondary text
BAR_AMBER     = (217, 169, 106)   # the keyboard focus bracket
BTN_CONFIRM   = (150, 180, 125)   # RESUME
BTN_CANCEL    = (199, 123, 107)   # QUIT TO MENU
HINT_BROWN    = (150, 125, 100)   # stub-test hint line only

OVERLAY_RGBA  = (25, 18, 12, 160)  # the dim behind the card (§2.6)

# -------------------------------------------------------------
# LAYOUT  (UI_STYLE_GUIDE §4 — fixed pixel constants)
# -------------------------------------------------------------
SCREEN_W       = 1280
SCREEN_H       = 720

CARD_W         = 420
# TASK 8: 360 fitted exactly six buttons (5*60 + 44 = 344, leaving 8px
# top and bottom). LOAD GAME makes seven — 6*60 + 44 = 404 — so the card
# grows by the one pitch that costs, and the same 8px margin comes back.
CARD_H         = 420
BORDER_CARD    = 3
CORNER_LEN     = 22         # corner bracket arm length

BTN_W          = 320
BTN_H          = 44         # every button is 44 px tall (§4.6)
BTN_PITCH      = 60
BORDER_BTN     = 3

MARKER_GAP     = 12         # the focus bracket sits 12 px left of a button
MARKER_W       = 6          # bracket arm length
MARKER_H       = 18         # bracket height

SIZE_BODY      = 11         # button labels

# The seven actions, in draw order. A caller matches the index it gets
# from get_button_rects() against this tuple rather than a label string,
# so relabelling a button never breaks the wiring.
#
# TASK 8: LOAD GAME is placed immediately after SAVE GAME — the brief
# asks for it "next to Save game", and the pair reads as one idea there.
# Inserting rather than appending is safe precisely because of the rule
# above: nothing stores an index across frames (ctx.pause_focus is
# re-read every frame from get_focused_index()), and every caller
# resolves an index to an action through ACTIONS before acting on it.
ACTION_RESUME: str = "resume"
ACTION_SKILL_TREE: str = "skill_tree"
ACTION_STATS: str = "stats"
ACTION_SETTINGS: str = "settings"
ACTION_SAVE_GAME: str = "save_game"
ACTION_LOAD_GAME: str = "load_game"
ACTION_QUIT_TO_MENU: str = "quit_to_menu"

ACTIONS: Tuple[str, ...] = (
    ACTION_RESUME, ACTION_SKILL_TREE, ACTION_STATS,
    ACTION_SETTINGS, ACTION_SAVE_GAME, ACTION_LOAD_GAME,
    ACTION_QUIT_TO_MENU)

LABELS: Tuple[str, ...] = (
    "RESUME", "SKILL TREE", "STATS", "SETTINGS", "SAVE GAME", "LOAD GAME",
    "QUIT TO MENU")

# RESUME reads as the constructive action and QUIT TO MENU as the
# destructive one; the five in between are neutral (§4.6). LOAD GAME is
# neutral rather than destructive: it discards the run in progress, but
# so does QUIT TO MENU, and the slot picker it opens is the place that
# asks — same as reaching it from the title screen.
FILLS: Tuple[Tuple[int, int, int], ...] = (
    BTN_CONFIRM, HEADER_TAN, HEADER_TAN, HEADER_TAN, HEADER_TAN,
    HEADER_TAN, BTN_CANCEL)

_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def load_font(size: int) -> pygame.font.Font:
    """
    Return the pixel font at `size`, cached across the module.

    Falls back to the mandatory Courier substitute so a missing TTF can
    never crash the overlay (UI_STYLE_GUIDE §3).
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


class PauseMenu:
    """
    The pause overlay: six buttons on a small card over a dimmed world.

    Owns only its open flag and which button has keyboard focus. The
    caller reads get_button_rects() (or take_action()) and decides what
    any of it means.
    """

    def __init__(self, screen_w: int = SCREEN_W,
                 screen_h: int = SCREEN_H) -> None:
        """Centre the card inside the given screen and lay out its buttons."""
        self.__card: pygame.Rect = pygame.Rect(
            (int(screen_w) - CARD_W) // 2, (int(screen_h) - CARD_H) // 2,
            CARD_W, CARD_H)

        # Seven buttons at a 60 px pitch occupy 6*60 + 44 = 404 px, which
        # leaves exactly 8 px above and below inside a 420 px card. That
        # is why this overlay carries no title -- there is no room for
        # one, and the labels already say what everything does.
        # Derived from len(ACTIONS), so an eighth entry would need CARD_H
        # raised but never this arithmetic touched.
        span = BTN_PITCH * (len(ACTIONS) - 1) + BTN_H
        top = self.__card.y + (CARD_H - span) // 2
        left = self.__card.x + (CARD_W - BTN_W) // 2
        self.__buttons: List[pygame.Rect] = [
            pygame.Rect(left, top + index * BTN_PITCH, BTN_W, BTN_H)
            for index in range(len(ACTIONS))]

        self.__open: bool = False
        self.__focused: int = 0
        self.__result: Optional[str] = None

    # -- opening and closing ----------------------------------
    def open(self) -> None:
        """Show the overlay with RESUME focused and no result recorded."""
        self.__open = True
        self.__focused = 0
        self.__result = None

    def close(self) -> None:
        """Hide the overlay, keeping the last result readable."""
        self.__open = False

    def is_open(self) -> bool:
        """True while the overlay is showing."""
        return self.__open

    def consumes_input(self) -> bool:
        """
        True while the overlay must swallow every event (§4.7).

        Callers check this before running their own input handling, so a
        click can never reach the world underneath.
        """
        return self.__open

    # -- focus and result -------------------------------------
    def get_focused_index(self) -> int:
        """Which button currently has keyboard focus."""
        return self.__focused

    def set_focused_index(self, index: int) -> bool:
        """
        Move focus. Returns False for an out-of-range index, leaving
        focus untouched — a bad value never corrupts state (§0.8).
        """
        if not 0 <= int(index) < len(ACTIONS):
            return False
        self.__focused = int(index)
        return True

    def get_result(self) -> Optional[str]:
        """The action chosen, or None while undecided."""
        return self.__result

    def take_result(self) -> Optional[str]:
        """Read the result once and clear it, so it fires exactly once."""
        result, self.__result = self.__result, None
        return result

    def get_action_at(self, index: int) -> Optional[str]:
        """The action id for a button index, or None if out of range."""
        if 0 <= int(index) < len(ACTIONS):
            return ACTIONS[int(index)]
        return None

    # -- geometry ---------------------------------------------
    def get_card_rect(self) -> pygame.Rect:
        """The overlay card rectangle."""
        return self.__card

    def get_button_rects(self) -> List[pygame.Rect]:
        """Every button rectangle, in ACTIONS order."""
        return list(self.__buttons)

    # -- input ------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Route one event. Returns True whenever the overlay consumed it.

        Up/down move focus, ENTER activates, ESC resumes (the key that
        opened the menu closes it), the mouse both focuses and activates.
        A closed overlay consumes nothing.
        """
        if not self.__open:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.__focused = (self.__focused + 1) % len(ACTIONS)
            elif event.key == pygame.K_UP:
                self.__focused = (self.__focused - 1) % len(ACTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                               pygame.K_SPACE):
                self.__choose(self.__focused)
            elif event.key == pygame.K_ESCAPE:
                self.__choose(0)                 # ESC always resumes
        elif event.type == pygame.MOUSEMOTION:
            for index, rect in enumerate(self.__buttons):
                if rect.collidepoint(event.pos):
                    self.__focused = index
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.__buttons):
                if rect.collidepoint(event.pos):
                    self.__choose(index)
        return True

    def __choose(self, index: int) -> None:
        """Record an action and close the overlay."""
        self.__result = ACTIONS[index]
        self.__open = False

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface,
               focused_index: Optional[int] = None) -> None:
        """
        Draw the overlay: dim, card, corner marks, buttons, focus bracket.

        `focused_index` overrides the stored focus when a caller drives
        it externally; omitted, the overlay draws its own (§6.1).
        """
        if not self.__open:
            return
        focus = self.__focused if focused_index is None else int(focused_index)

        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill(OVERLAY_RGBA)
        screen.blit(shade, (0, 0))

        pygame.draw.rect(screen, CARD_TAN, self.__card)
        pygame.draw.rect(screen, BORDER_BROWN, self.__card, BORDER_CARD)
        self.__draw_corners(screen)

        font = load_font(SIZE_BODY)
        for index, rect in enumerate(self.__buttons):
            pygame.draw.rect(screen, FILLS[index], rect)
            pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_BTN)
            rendered = font.render(LABELS[index], True, TEXT_COFFEE)
            screen.blit(rendered,
                        (rect.centerx - rendered.get_width() // 2,
                         rect.centery - rendered.get_height() // 2))
            if index == focus:
                self.__draw_marker(screen, rect)

    def __draw_corners(self, screen: pygame.Surface) -> None:
        """Two 3 px arms per corner — the franchise signature (§4.2)."""
        n = CORNER_LEN
        rect = self.__card
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((rect.left, rect.top), (n, 0), (0, n)),
                ((rect.right, rect.top), (-n, 0), (0, n)),
                ((rect.left, rect.bottom), (n, 0), (0, -n)),
                ((rect.right, rect.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_marker(self, screen: pygame.Surface,
                      rect: pygame.Rect) -> None:
        """The amber focus bracket, 12 px left of the focused button."""
        x = rect.left - MARKER_GAP - MARKER_W
        top = rect.centery - MARKER_H // 2
        pygame.draw.line(screen, BAR_AMBER, (x, top),
                         (x + MARKER_W, top), 3)
        pygame.draw.line(screen, BAR_AMBER, (x, top),
                         (x, top + MARKER_H), 3)
        pygame.draw.line(screen, BAR_AMBER, (x, top + MARKER_H),
                         (x + MARKER_W, top + MARKER_H), 3)


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   ESC / P -> open the pause menu (ESC again resumes)
#   up/down -> move focus       ENTER / click -> choose
#   F11     -> toggle windowed / fullscreen
#   Q       -> quit the stub
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (SCREEN_W, SCREEN_H)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Pause menu test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    menu = PauseMenu()
    menu.open()
    last_action = "-"

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                window = pygame.display.set_mode(
                    SIZE,
                    FULLSCREEN_FLAGS if is_fullscreen else WINDOWED_FLAGS)
                continue
            # The overlay gets first refusal on every event while open.
            if menu.consumes_input():
                menu.handle_event(event)
                action = menu.take_result()
                if action is not None:
                    last_action = action
                    print(f"chose: {action}")
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key in (pygame.K_ESCAPE, pygame.K_p):
                    menu.open()

        # A stand-in "world" so the dim overlay has something to dim.
        window.fill(PANEL_TAN)
        body = load_font(SIZE_BODY)
        window.blit(body.render("THE GAME WORLD SITS HERE", True,
                                TEXT_COFFEE), (60, 60))
        window.blit(body.render(f"LAST ACTION: {last_action}", True,
                                STAT_BROWN), (60, 100))
        if not menu.is_open():
            window.blit(body.render("PRESS ESC OR P TO PAUSE", True,
                                    STAT_BROWN), (60, 140))

        menu.render(window)

        hint = hint_font.render(
            "ESC/P pause  |  up/down focus  |  ENTER choose  |  F11  |  Q quit",
            True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

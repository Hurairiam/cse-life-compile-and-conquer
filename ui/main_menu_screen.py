"""
CSE Life: Compile & Conquer
ui/main_menu_screen.py

The title screen. A ceremonial card holding the wordmark, a
horizontal rule, and the four things the player can do: start,
load, change settings, or leave.

This file has NO game logic. render() only DRAWS what it is handed:
which button has focus, and the version string. It does not know
whether a save exists, does not start a game, and does not quit --
it exposes get_button_rects() and the state manager decides
(Style Guide §6.1, §6.2).

Style: Nangiba Tasnim's ceremonial card, ported from the quarry's
main_menu_system/main_menu_screen.py.
Abu Huraira removes the stub test block when he plugs in the real game.
"""
from __future__ import annotations

import os
from typing import List, Optional

import pygame

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues, and no
# colours imported from another screen (Build Plan §0.5).
PANEL_TAN = (231, 214, 189)     # screen background behind the card
CARD_TAN = (240, 228, 208)      # the ceremonial card
HEADER_TAN = (214, 196, 168)    # the two neutral buttons
BORDER_BROWN = (169, 130, 94)   # frame, corner marks, button outlines
TEXT_COFFEE = (74, 53, 39)      # button labels
TITLE_SLATE = (45, 58, 71)      # the wordmark
CREDIT_HL = (155, 110, 70)      # the subtitle
STAT_BROWN = (140, 110, 85)     # the version string
BAR_AMBER = (217, 169, 106)     # the keyboard focus bracket
BTN_CONFIRM = (150, 180, 125)   # START GAME
BTN_CANCEL = (199, 123, 107)    # EXIT
PLACEHOLDER = (196, 178, 150)   # square drawn where art is missing
HINT_BROWN = (150, 125, 100)    # stub-test hint line only

# Anchored to the project, not to the working directory, so the art
# loads the same whether the game was started from the project root,
# from an IDE, or from a shortcut.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(_PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")
# [IMAGE PLACEHOLDER: assets/ui/logo_title.png -- "CSE LIFE" wordmark,
#  ~640x96, pixel lettering in TITLE_SLATE on transparency. Missing art
#  falls back to the text masthead below, not to a blank screen.]
LOGO_PATH = os.path.join(_PROJECT_ROOT, "assets", "ui", "logo_title.png")
# [IMAGE PLACEHOLDER: assets/ui/menu_backdrop.png -- muted campus scene,
#  1280x720, drawn at BACKDROP_ALPHA behind the card. Missing art leaves
#  the plain PANEL_TAN fill.]
BACKDROP_PATH = os.path.join(_PROJECT_ROOT, "assets", "ui",
                             "menu_backdrop.png")

# -------------------------------------------------------------
# MENU ENTRIES
# -------------------------------------------------------------
START_GAME = 0
LOAD_GAME = 1
SETTINGS = 2
EXIT = 3

MENU_LABELS: tuple = ("START GAME", "LOAD GAME", "SETTINGS", "EXIT")
MENU_FILLS: tuple = (BTN_CONFIRM, HEADER_TAN, HEADER_TAN, BTN_CANCEL)

TITLE_TEXT = "CSE LIFE"
SUBTITLE_TEXT = "COMPILE & CONQUER"

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
CARD_MARGIN = 46        # ceremonial inset (§4.2)
CARD_PAD = 18
CORNER_LEN = 26

BACKDROP_ALPHA = 90     # how strongly the campus scene shows through

LOGO_W = 640
LOGO_H = 96
LOGO_Y = 96

TITLE_Y = 110
SUBTITLE_Y = 168
RULE_Y = 200
RULE_HALF = 300
RULE_GAP = 14           # §4.8 rule: 14 px gap holding the diamond
RULE_DIAMOND = 7        # §4.8 rule: 7 px half-width diamond

FIRST_BTN_Y = 260
BTN_W = 320
BTN_H = 44
BTN_PITCH = 60

MARKER_GAP = 12         # gap between the focus bracket and the button
MARKER_W = 10           # bracket arm length
MARKER_H = 22           # bracket height
MARKER_THICK = 3        # bracket stroke, matching the corner marks

CHROME_PAD = 14         # inset of the version string from the frame

TITLE_SIZE = 28
SUB_SIZE = 11
BODY_SIZE = 12
LABEL_SIZE = 10


class MainMenuScreen:
    """
    Draws the title screen.

    The screen returns no decisions. It reports where its buttons are
    through get_button_rects(); the caller does the hit-testing and
    acts. Keyboard focus is passed in per frame rather than owned here,
    so the caller stays the single source of truth for what is selected.
    """

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        """Load fonts and art, and fix the four button rects."""
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h

        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_sub: pygame.font.Font = self.__load_font(SUB_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)

        self.__logo: Optional[pygame.Surface] = self.__load_logo()
        self.__backdrop: Optional[pygame.Surface] = self.__load_backdrop()

        centre_x = screen_w // 2
        self.__button_rects: List[pygame.Rect] = [
            pygame.Rect(centre_x - BTN_W // 2, FIRST_BTN_Y + i * BTN_PITCH,
                        BTN_W, BTN_H)
            for i in range(len(MENU_LABELS))
        ]

        self.__audio = audio
        self.__last_focus: int = -1

    # -- loading helpers --------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    def __load_logo(self) -> Optional[pygame.Surface]:
        """
        Load the wordmark, or None so the text masthead is drawn instead.

        A missing logo is not a placeholder square here -- the screen has
        a perfectly good typographic fallback, which reads better than a
        640x96 grey block (§5.2 allows the graceful path).
        """
        try:
            image = pygame.image.load(LOGO_PATH).convert_alpha()
            return pygame.transform.scale(image, (LOGO_W, LOGO_H))
        except (FileNotFoundError, OSError, pygame.error):
            return None

    def __load_backdrop(self) -> Optional[pygame.Surface]:
        """Load the campus backdrop at BACKDROP_ALPHA, or None."""
        try:
            image = pygame.image.load(BACKDROP_PATH).convert()
            scaled = pygame.transform.scale(
                image, (self.__screen_w, self.__screen_h))
            scaled.set_alpha(BACKDROP_ALPHA)
            return scaled
        except (FileNotFoundError, OSError, pygame.error):
            return None

    def has_logo(self) -> bool:
        """True when the wordmark art loaded; False means text fallback."""
        return self.__logo is not None

    def has_backdrop(self) -> bool:
        """True when the campus backdrop art loaded."""
        return self.__backdrop is not None

    # -- rectangle getters (for click detection outside this file) ---
    def get_button_rects(self) -> List[pygame.Rect]:
        """One rectangle per menu entry, in MENU_LABELS order."""
        return list(self.__button_rects)

    def get_button_index_at(self, pos: tuple) -> int:
        """Index of the button under a screen position, or -1."""
        for index, rect in enumerate(self.__button_rects):
            if rect.collidepoint(pos):
                return index
        return -1

    # -- audio hooks (optional, F1 convention) ----------------
    def notify_activated(self) -> None:
        """Play the click cue. The caller decides what was activated."""
        if self.__audio:
            self.__audio.play_sfx("click")

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, focused_index: int,
               version: str) -> None:
        """
        Draw the title screen from the state handed in.

        focused_index : which entry has keyboard focus, or -1 for none
        version       : the build string, drawn bottom-right in the frame
        """
        # The select cue fires from the focus actually being drawn, so a
        # caller never has to remember to announce it. Still no decision
        # made here -- the caller owns focused_index.
        if self.__audio and focused_index != self.__last_focus \
                and self.__last_focus != -1:
            self.__audio.play_sfx("select")
        self.__last_focus = focused_index

        screen.fill(PANEL_TAN)
        if self.__backdrop is not None:
            screen.blit(self.__backdrop, (0, 0))

        inner = self.__draw_card(screen)
        self.__draw_masthead(screen)
        self.__draw_rule(screen, screen.get_width() // 2, RULE_Y)

        for index, rect in enumerate(self.__button_rects):
            self.__draw_button(screen, rect, MENU_LABELS[index],
                               MENU_FILLS[index], index == focused_index)

        self.__draw_version(screen, inner, version)

    # -- piece-by-piece drawing -------------------------------
    def __draw_card(self, screen: pygame.Surface) -> pygame.Rect:
        """Draw the framed card and return its inner border rect."""
        card = pygame.Rect(CARD_MARGIN, CARD_MARGIN,
                           screen.get_width() - CARD_MARGIN * 2,
                           screen.get_height() - CARD_MARGIN * 2)
        pygame.draw.rect(screen, CARD_TAN, card)
        pygame.draw.rect(screen, BORDER_BROWN, card, 3)

        inner = card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
        pygame.draw.rect(screen, BORDER_BROWN, inner, 1)
        self.__draw_corners(screen, inner)
        return inner

    def __draw_corners(self, screen: pygame.Surface,
                       rect: pygame.Rect) -> None:
        """Draw short bracket marks at each corner of the inner border."""
        n = CORNER_LEN
        corners = [
            ((rect.left, rect.top), (n, 0), (0, n)),
            ((rect.right, rect.top), (-n, 0), (0, n)),
            ((rect.left, rect.bottom), (n, 0), (0, -n)),
            ((rect.right, rect.bottom), (-n, 0), (0, -n)),
        ]
        for (px, py), (dx1, dy1), (dx2, dy2) in corners:
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_masthead(self, screen: pygame.Surface) -> None:
        """Draw the wordmark art, or the typographic fallback."""
        centre_x = screen.get_width() // 2
        if self.__logo is not None:
            screen.blit(self.__logo, (centre_x - LOGO_W // 2, LOGO_Y))
            return
        self.__blit_centred(screen, self.__font_title, TITLE_TEXT,
                            TITLE_SLATE, centre_x, TITLE_Y)
        self.__blit_centred(screen, self.__font_sub, SUBTITLE_TEXT,
                            CREDIT_HL, centre_x, SUBTITLE_Y)

    def __draw_rule(self, screen: pygame.Surface, cx: int, y: int) -> None:
        """
        The ceremonial horizontal rule (§4.8): two 2 px segments with a
        14 px gap in the middle holding a 7 px half-width diamond.
        """
        pygame.draw.line(screen, BORDER_BROWN,
                         (cx - RULE_HALF, y), (cx - RULE_GAP, y), 2)
        pygame.draw.line(screen, BORDER_BROWN,
                         (cx + RULE_GAP, y), (cx + RULE_HALF, y), 2)
        pygame.draw.polygon(screen, BORDER_BROWN,
                            [(cx, y - 6), (cx + RULE_DIAMOND, y),
                             (cx, y + 6), (cx - RULE_DIAMOND, y)])

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, fill: tuple, focused: bool) -> None:
        """
        Draw one menu button, plus the focus bracket when it is selected.

        The fill never changes with focus: START GAME stays confirm-green
        and EXIT stays cancel-red, because those colours carry meaning
        (§2.2) and swapping them on focus would throw that away. Focus is
        shown by the amber bracket outside the button instead, which also
        keeps §4.6's "no hover effects" rule intact.
        """
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, 3)
        text = self.__font_body.render(label, True, TEXT_COFFEE)
        screen.blit(text, (rect.centerx - text.get_width() // 2,
                           rect.centery - text.get_height() // 2))
        if focused:
            self.__draw_focus_bracket(screen, rect)

    def __draw_focus_bracket(self, screen: pygame.Surface,
                             rect: pygame.Rect) -> None:
        """
        The amber bracket marking keyboard focus, MARKER_GAP px to the
        left of the button. Drawn as a "[" -- the same square-cornered
        vocabulary as the card's corner marks, at button scale.
        """
        right = rect.left - MARKER_GAP
        left = right - MARKER_W
        top = rect.centery - MARKER_H // 2
        bottom = top + MARKER_H
        pygame.draw.line(screen, BAR_AMBER, (left, top), (left, bottom),
                         MARKER_THICK)
        pygame.draw.line(screen, BAR_AMBER, (left, top), (right, top),
                         MARKER_THICK)
        pygame.draw.line(screen, BAR_AMBER, (left, bottom), (right, bottom),
                         MARKER_THICK)

    def __draw_version(self, screen: pygame.Surface, inner: pygame.Rect,
                       version: str) -> None:
        """Draw the build string inside the bottom-right of the frame."""
        surface = self.__font_label.render(version, True, STAT_BROWN)
        screen.blit(surface,
                    (inner.right - CHROME_PAD - surface.get_width(),
                     inner.bottom - CHROME_PAD - surface.get_height()))

    def __blit_centred(self, screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: tuple, centre_x: int,
                       y: int) -> None:
        """Draw text horizontally centred on `centre_x` at `y`."""
        surface = font.render(text, True, colour)
        screen.blit(surface, (centre_x - surface.get_width() // 2, y))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   UP / DOWN     -> move focus (wraps); hovering also sets focus
#   ENTER / SPACE -> activate the focused entry, prints it
#   click         -> activate whatever was clicked, prints it
#   F11           -> toggle windowed / fullscreen
#   ESC           -> jump to EXIT, then quit
#
# The hit-testing and every decision live HERE, not in the class --
# in the real game the state manager owns them.
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Main menu test")
    menu = MainMenuScreen(*SIZE)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    VERSION = "v0.2 — short scope"
    focused = START_GAME
    last_action = "-"

    def activate(index: int) -> bool:
        """Report the chosen entry; returns False when the game should end."""
        global last_action
        last_action = MENU_LABELS[index]
        print(f"activated: {last_action}")
        menu.notify_activated()
        return index != EXIT

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if focused == EXIT:
                        running = False
                    else:
                        focused = EXIT
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    window = pygame.display.set_mode(
                        SIZE, FULLSCREEN_FLAGS if is_fullscreen
                        else WINDOWED_FLAGS)
                elif event.key == pygame.K_UP:
                    focused = (focused - 1) % len(MENU_LABELS)
                elif event.key == pygame.K_DOWN:
                    focused = (focused + 1) % len(MENU_LABELS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    running = activate(focused)

            elif event.type == pygame.MOUSEMOTION:
                index = menu.get_button_index_at(event.pos)
                if index >= 0:
                    focused = index

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                index = menu.get_button_index_at(event.pos)
                if index >= 0:
                    focused = index
                    running = activate(index)

        menu.render(window, focused, VERSION)

        window.blit(hint_font.render(
            f"logo art: {'yes' if menu.has_logo() else 'placeholder fallback'}"
            f"   |   backdrop art: "
            f"{'yes' if menu.has_backdrop() else 'none'}"
            f"   |   last action: {last_action}",
            True, STAT_BROWN), (CARD_MARGIN + CARD_PAD + 10,
                                CARD_MARGIN + 26))

        hint = hint_font.render(
            "arrows / hover = focus  |  ENTER or click activates"
            "  |  F11 fullscreen  |  ESC quit", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

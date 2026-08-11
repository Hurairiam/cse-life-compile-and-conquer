"""
CSE Life: Compile & Conquer
ui/name_entry_screen.py

The name prompt. A ceremonial card holding one question, one text
field, and the two things the player can do: confirm, or go back to
the title.

This file has NO game logic. render() only DRAWS what it is handed:
the name typed so far, and whether the caret is in its visible half of
the blink. It does not own the text, does not read a key, does not
decide whether a name is acceptable and does not know what happens
next -- it exposes get_field_rect() / get_confirm_rect() /
get_back_rect() and the state manager decides (Style Guide §6.1, §6.2).

The two rules the field enforces live here as MAX_NAME_LENGTH and
is_allowed_char() rather than in the state, for the same reason
VOLUME_MIN/MAX/STEP and value_from_x() live in ui/settings_screen.py:
they are properties of the control the player is looking at, and the
length cap is what keeps the text inside FIELD_W.

Styled to sit directly after ui/main_menu_screen.py -- same ceremonial
card, same backdrop art, same rule -- because it is the very next thing
the player sees after pressing START GAME.
Abu Huraira removes the stub test block when he plugs in the real game.
"""
from __future__ import annotations

import os
from typing import Optional

import pygame

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues, and no
# colours imported from another screen (Build Plan §0.5).
PANEL_TAN = (231, 214, 189)     # screen background behind the card
CARD_TAN = (240, 228, 208)      # the ceremonial card
BORDER_BROWN = (169, 130, 94)   # frame, corner marks, button outlines
TEXT_COFFEE = (74, 53, 39)      # the typed name, button labels
TITLE_SLATE = (45, 58, 71)      # the question
CREDIT_HL = (155, 110, 70)      # the subtitle
STAT_BROWN = (140, 110, 85)     # hints, counter, placeholder text
ROW_WHITE = (247, 243, 236)     # the field fill
ROW_BLUE = (120, 150, 190)      # the field border, which always has focus
BTN_CONFIRM = (150, 180, 125)   # CONFIRM
BTN_CANCEL = (199, 123, 107)    # BACK
HINT_BROWN = (150, 125, 100)    # stub-test hint line only

# Anchored to the project, not to the working directory, so the art
# loads the same whether the game was started from the project root,
# from an IDE, or from a shortcut.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(_PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")
# The title screen's backdrop, reused deliberately: this card is the
# same card one keypress later, and a different background would read
# as a different place. Missing art leaves the plain PANEL_TAN fill.
BACKDROP_PATH = os.path.join(_PROJECT_ROOT, "assets", "ui",
                             "menu_backdrop.png")

# -------------------------------------------------------------
# THE FIELD'S TWO RULES
# -------------------------------------------------------------
# 16 characters is what fits FIELD_W at FIELD_SIZE with room for the
# caret. Raising it means widening the field, not just this number.
MAX_NAME_LENGTH = 16

# Letters and spaces only (owner ruling). str.isalpha() is deliberate
# rather than an A-Z test: a player typing an accented or non-Latin
# name gets to keep it, and the font falls back to a box glyph rather
# than swallowing the keystroke.
ALLOWED_PUNCTUATION = " "

TITLE_TEXT = "WHAT SHOULD WE CALL YOU?"
SUBTITLE_TEXT = "THIS NAME FOLLOWS YOU THROUGH THE DEGREE"
# Shown greyed in an empty field. It is the name the player keeps by
# submitting nothing, so the fallback is visible instead of a surprise.
PLACEHOLDER_TEXT = "CSE Student"
HINT_LINE_1 = "LETTERS AND SPACES ONLY  |  16 CHARACTERS MAX"
HINT_LINE_2 = "LEAVE IT BLANK TO STAY CSE STUDENT"

CONFIRM_LABEL = "CONFIRM"
BACK_LABEL = "BACK"

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
CARD_MARGIN = 46        # ceremonial inset (§4.2), matching the title
CARD_PAD = 18
CORNER_LEN = 26

BACKDROP_ALPHA = 90     # how strongly the campus scene shows through

TITLE_Y = 170
SUBTITLE_Y = 220
RULE_Y = 256
RULE_HALF = 300
RULE_GAP = 14           # §4.8 rule: 14 px gap holding the diamond
RULE_DIAMOND = 7        # §4.8 rule: 7 px half-width diamond

BTN_W = 180
BTN_H = 44
BTN_GAP = 22
BTN_Y = 470

# Declared above the field so the field can be measured from it. The
# two are exactly the same width, so the box and the CONFIRM + BACK run
# beneath it share both edges. A 16-character name is 256 px at
# FIELD_SIZE, which leaves the box looking fillable rather than empty.
FIELD_W = BTN_W * 2 + BTN_GAP
FIELD_H = 54
FIELD_Y = 320
FIELD_PAD = 14          # gap from the field's left edge to the text
CARET_W = 2
CARET_INSET = 8         # how far the caret stops short of each edge
# The placeholder starts this far right of where real text does, so an
# empty field does not draw the caret through its first glyph. Typed
# text needs no such nudge: the caret trails it.
PLACEHOLDER_INDENT = 8

# Above the field rather than beside the hints: hint line 1 is wider
# than the field, so a counter right-aligned to the field's edge would
# be drawn straight through the end of it.
COUNTER_Y = 298
HINT_1_Y = 392
HINT_2_Y = 414

TITLE_SIZE = 28
FIELD_SIZE = 16         # the typed name, the biggest thing after the title
SUB_SIZE = 11
BODY_SIZE = 12
LABEL_SIZE = 10


def is_allowed_char(char: str) -> bool:
    """
    True if `char` may be typed into the name field.

    One character at a time, because that is how a KEYDOWN arrives.
    Control keys report an unprintable unicode (or none at all) and are
    refused here rather than in the state module.
    """
    if not char or len(char) != 1:
        return False
    return char.isalpha() or char in ALLOWED_PUNCTUATION


class NameEntryScreen:
    """
    Draws the name prompt.

    The screen returns no decisions. It reports where its field and
    buttons are through getters; the caller does the hit-testing, owns
    the typed text, and acts. The caret's blink phase is passed in per
    frame rather than timed here, so the caller stays the single source
    of truth for the field's state.
    """

    def __init__(self, screen_w: int, screen_h: int) -> None:
        """Load fonts and art, and fix the field and button rects."""
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h

        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_field: pygame.font.Font = self.__load_font(FIELD_SIZE)
        self.__font_sub: pygame.font.Font = self.__load_font(SUB_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)

        self.__backdrop: Optional[pygame.Surface] = self.__load_backdrop()

        centre_x = screen_w // 2
        self.__field_rect: pygame.Rect = pygame.Rect(
            centre_x - FIELD_W // 2, FIELD_Y, FIELD_W, FIELD_H)
        # CONFIRM sits left of centre and BACK right of it, the same
        # order APPLY / BACK use on the settings screen.
        pair_w = BTN_W * 2 + BTN_GAP
        self.__confirm_rect: pygame.Rect = pygame.Rect(
            centre_x - pair_w // 2, BTN_Y, BTN_W, BTN_H)
        self.__back_rect: pygame.Rect = pygame.Rect(
            self.__confirm_rect.right + BTN_GAP, BTN_Y, BTN_W, BTN_H)

    # -- loading helpers --------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

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

    def has_backdrop(self) -> bool:
        """True when the campus backdrop art loaded."""
        return self.__backdrop is not None

    # -- rectangle getters (for click detection outside this file) ---
    def get_field_rect(self) -> pygame.Rect:
        """The text field's rectangle."""
        return self.__field_rect

    def get_confirm_rect(self) -> pygame.Rect:
        """The CONFIRM button's rectangle."""
        return self.__confirm_rect

    def get_back_rect(self) -> pygame.Rect:
        """The BACK button's rectangle."""
        return self.__back_rect

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, name: str,
               caret_visible: bool) -> None:
        """
        Draw the name prompt from the state handed in.

        name          : the text typed so far, drawn as-is; empty shows
                        the greyed placeholder instead
        caret_visible : True during the lit half of the blink cycle
        """
        screen.fill(PANEL_TAN)
        if self.__backdrop is not None:
            screen.blit(self.__backdrop, (0, 0))

        self.__draw_card(screen)
        centre_x = screen.get_width() // 2
        self.__blit_centred(screen, self.__font_title, TITLE_TEXT,
                            TITLE_SLATE, centre_x, TITLE_Y)
        self.__blit_centred(screen, self.__font_sub, SUBTITLE_TEXT,
                            CREDIT_HL, centre_x, SUBTITLE_Y)
        self.__draw_rule(screen, centre_x, RULE_Y)

        self.__draw_field(screen, name, caret_visible)
        self.__draw_hints(screen, centre_x, name)

        self.__draw_button(screen, self.__confirm_rect, CONFIRM_LABEL,
                           BTN_CONFIRM)
        self.__draw_button(screen, self.__back_rect, BACK_LABEL, BTN_CANCEL)

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

    def __draw_field(self, screen: pygame.Surface, name: str,
                     caret_visible: bool) -> None:
        """
        Draw the field, its text and the caret.

        The border is the focused blue every frame: this screen has one
        control and it never gives up the keyboard, so a focus state
        that could be off would only ever be a lie.
        """
        rect = self.__field_rect
        pygame.draw.rect(screen, ROW_WHITE, rect)
        pygame.draw.rect(screen, ROW_BLUE, rect, 3)

        shown = name or PLACEHOLDER_TEXT
        colour = TEXT_COFFEE if name else STAT_BROWN
        text = self.__font_field.render(shown, True, colour)
        text_x = rect.x + FIELD_PAD
        shown_x = text_x if name else text_x + PLACEHOLDER_INDENT
        screen.blit(text, (shown_x, rect.centery - text.get_height() // 2))

        if not caret_visible:
            return
        # Trails the real text, never the placeholder -- the placeholder
        # is not there to be edited.
        typed_w = self.__font_field.size(name)[0] if name else 0
        caret_x = min(text_x + typed_w + 2, rect.right - CARET_INSET)
        pygame.draw.rect(screen, TEXT_COFFEE,
                         pygame.Rect(caret_x, rect.y + CARET_INSET, CARET_W,
                                     rect.h - CARET_INSET * 2))

    def __draw_hints(self, screen: pygame.Surface, centre_x: int,
                     name: str) -> None:
        """Draw the two rule lines and the character counter."""
        self.__blit_centred(screen, self.__font_label, HINT_LINE_1,
                            STAT_BROWN, centre_x, HINT_1_Y)
        self.__blit_centred(screen, self.__font_label, HINT_LINE_2,
                            STAT_BROWN, centre_x, HINT_2_Y)
        counter = self.__font_label.render(
            f"{len(name)}/{MAX_NAME_LENGTH}", True, STAT_BROWN)
        screen.blit(counter, (self.__field_rect.right - counter.get_width(),
                              COUNTER_Y))

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, fill: tuple) -> None:
        """
        Draw one button.

        No focus bracket and no hover effect: the keyboard belongs to
        the field, so ENTER confirms and ESC goes back without either
        button ever being "selected" (§4.6 forbids hover states anyway).
        """
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, 3)
        text = self.__font_body.render(label, True, TEXT_COFFEE)
        screen.blit(text, (rect.centerx - text.get_width() // 2,
                           rect.centery - text.get_height() // 2))

    def __blit_centred(self, screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: tuple, centre_x: int,
                       y: int) -> None:
        """Draw text horizontally centred on `centre_x` at `y`."""
        surface = font.render(text, True, colour)
        screen.blit(surface, (centre_x - surface.get_width() // 2, y))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   type          -> letters and spaces are accepted, nothing else
#   BACKSPACE     -> delete the last character
#   ENTER / click CONFIRM -> print the name that would be committed
#   ESC / click BACK      -> quit
#   F11           -> toggle windowed / fullscreen
#
# The hit-testing, the caret clock and every decision live HERE, not in
# the class -- in the real game engine/states/name_entry.py owns them.
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Name entry test")
    prompt = NameEntryScreen(*SIZE)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    typed = ""
    committed = "-"
    caret = 0.0

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        caret = (caret + dt) % 1.0

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
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    committed = typed.strip() or "(blank -> CSE Student)"
                    print(f"committed: {committed}")
                elif event.key == pygame.K_BACKSPACE:
                    typed = typed[:-1]
                    caret = 0.0
                elif (is_allowed_char(event.unicode)
                        and len(typed) < MAX_NAME_LENGTH
                        and not (event.unicode == " " and not typed)):
                    typed += event.unicode
                    caret = 0.0

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if prompt.get_confirm_rect().collidepoint(event.pos):
                    committed = typed.strip() or "(blank -> CSE Student)"
                    print(f"committed: {committed}")
                elif prompt.get_back_rect().collidepoint(event.pos):
                    running = False

        prompt.render(window, typed, caret < 0.5)

        window.blit(hint_font.render(
            f"backdrop art: {'yes' if prompt.has_backdrop() else 'none'}"
            f"   |   last committed: {committed}",
            True, STAT_BROWN), (CARD_MARGIN + CARD_PAD + 10,
                                CARD_MARGIN + 26))

        hint = hint_font.render(
            "type a name  |  ENTER commits  |  F11 fullscreen  |  ESC quit",
            True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        pygame.display.flip()

    pygame.quit()

"""
CSE Life: Compile & Conquer
ui/choice_box.py

The reply list that docks above the dialog box when a conversation
branches. One row per option, on the same 38/44 px table pitch the
registration screen uses: white when unselected, blue when selected,
2 px brown borders throughout.

This file has NO game logic. render() only DRAWS what it is handed:
the option strings and which one is highlighted. It does not know
what an option means, whether the player can afford it, or what
happens when it is picked -- the state manager decides all of that
and calls the engine.

The box sizes itself to the number of options and anchors above
ui/dialog_box.py's card, so the two read as one panel.

Style: Nangiba Tasnim's tan card pattern, corner brackets and all.
Abu Huraira removes the stub test block when he plugs in the real game.
"""
from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

import pygame

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues, and no
# colours imported from another screen (Build Plan §0.5).
CARD_TAN = (240, 228, 208)      # the box itself
HEADER_TAN = (214, 196, 168)    # the prompt strip above the options
BORDER_BROWN = (169, 130, 94)   # frame, corner marks, row borders
TEXT_COFFEE = (74, 53, 39)      # option text
CREDIT_HL = (155, 110, 70)      # the prompt label
STAT_BROWN = (140, 110, 85)     # the hint line
ROW_WHITE = (247, 243, 236)     # an option not selected
ROW_BLUE = (120, 150, 190)      # the selected option
BAR_AMBER = (217, 169, 106)     # the selection bracket marker
HINT_BROWN = (150, 125, 100)    # stub-test hint line only

# Anchored to the project, not to the working directory, so the font
# loads the same whether the game was started from the project root,
# from an IDE, or from a shortcut.
FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "ui", "PressStart2P.ttf")

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
SIDE_MARGIN = 46        # matches ui/dialog_box.py so the two line up
DIALOG_BOX_H = 168      # ui/dialog_box.py's card height
DIALOG_BOTTOM = 28      # ui/dialog_box.py's bottom margin
DOCK_GAP = 12           # gap between this box and the dialog card

BOX_W = 560             # narrower than the dialog card, right-aligned
CARD_PAD = 12           # gap between the card and its inner border
CORNER_LEN = 14         # shorter arms than a full screen's 22 px
BORDER_W = 3
BORDER_ROW = 2

PROMPT_H = 30           # the "CHOOSE A REPLY" strip
ROW_H = 38              # option row height (§4.4)
ROW_PITCH = 44          # row height + the 6 px gap below it
ROW_INSET = 20          # gap from the card edge to a row
TEXT_INSET = 12         # gap from the row edge to its text
MARKER_W = 6            # the amber bracket on the selected row

MAX_OPTIONS = 4         # more than four replies does not fit the dock

BODY_SIZE = 12
LABEL_SIZE = 10


class ChoiceBox:
    """
    Draws a branching-dialogue reply list.

    Like the F0 widgets, the box owns only its OWN interaction state --
    which row the keyboard is on -- and nothing else. render() still
    takes the options and the highlighted index as parameters, so a
    caller that would rather drive the selection itself can ignore
    handle_event() entirely and pass its own index (§6.1).
    """

    def __init__(self, screen_w: int, screen_h: int) -> None:
        """Store the screen size, load the fonts, fix the dock anchor."""
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)
        self.__selected: int = 0
        self.__confirmed: bool = False

    # -- loading helpers --------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    # -- geometry ---------------------------------------------
    def get_box_rect(self, count: int) -> pygame.Rect:
        """
        The card rectangle for `count` options.

        Sized to its contents and docked directly above the dialog
        card's top edge, so the two never overlap whatever the option
        count is.
        """
        rows = max(1, min(int(count), MAX_OPTIONS))
        height = (CARD_PAD * 2 + PROMPT_H + 8
                  + rows * ROW_PITCH - (ROW_PITCH - ROW_H))
        dialog_top = self.__screen_h - DIALOG_BOTTOM - DIALOG_BOX_H
        return pygame.Rect(self.__screen_w - SIDE_MARGIN - BOX_W,
                           dialog_top - DOCK_GAP - height, BOX_W, height)

    def get_option_rects(self, count: int) -> List[pygame.Rect]:
        """One rectangle per option row, so clicks can be matched."""
        box = self.get_box_rect(count)
        first_y = box.y + CARD_PAD + PROMPT_H + 8
        rows = max(0, min(int(count), MAX_OPTIONS))
        return [pygame.Rect(box.x + ROW_INSET, first_y + i * ROW_PITCH,
                            box.w - ROW_INSET * 2, ROW_H)
                for i in range(rows)]

    # -- interaction state ------------------------------------
    def get_selected(self) -> int:
        """The row the keyboard is currently on."""
        return self.__selected

    def set_selected(self, index: int, count: int) -> bool:
        """Move the highlight, clamped to the option count."""
        rows = max(0, min(int(count), MAX_OPTIONS))
        if rows == 0:
            return False
        new = max(0, min(rows - 1, int(index)))
        changed = new != self.__selected
        self.__selected = new
        return changed

    def take_confirmed(self) -> bool:
        """True once after an option was picked -- clears the flag."""
        was, self.__confirmed = self.__confirmed, False
        return was

    def reset(self) -> None:
        """Put the highlight back on the first row for a new branch."""
        self.__selected = 0
        self.__confirmed = False

    def handle_event(self, event: pygame.event.Event,
                     count: int) -> bool:
        """
        Route one event. Returns True when it was consumed.

        Up/down move the highlight and wrap at both ends; Enter picks
        the highlighted row; a click both moves the highlight and picks,
        which is what a mouse user expects from a one-click list.
        """
        rows = max(0, min(int(count), MAX_OPTIONS))
        if rows == 0:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.__selected = (self.__selected - 1) % rows
                return True
            if event.key == pygame.K_DOWN:
                self.__selected = (self.__selected + 1) % rows
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.__confirmed = True
                return True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.get_option_rects(rows)):
                if rect.collidepoint(event.pos):
                    self.__selected = index
                    self.__confirmed = True
                    return True
        elif event.type == pygame.MOUSEMOTION:
            for index, rect in enumerate(self.get_option_rects(rows)):
                if rect.collidepoint(event.pos):
                    self.__selected = index
                    return True
        return False

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, options: Sequence[str],
               selected_index: int, prompt: str = "YOUR DECISION") -> None:
        """
        Draw the reply list from the state handed in.

        options        : the reply strings, at most MAX_OPTIONS drawn
        selected_index : which row is highlighted
        prompt         : the ALL-CAPS label on the header strip
        """
        shown = list(options)[:MAX_OPTIONS]
        if not shown:
            return
        box = self.get_box_rect(len(shown))
        self.__draw_card(screen, box)

        strip = pygame.Rect(box.x + ROW_INSET, box.y + CARD_PAD,
                            box.w - ROW_INSET * 2, PROMPT_H)
        pygame.draw.rect(screen, HEADER_TAN, strip)
        pygame.draw.rect(screen, BORDER_BROWN, strip, BORDER_ROW)
        label = self.__font_label.render(prompt.upper(), True, CREDIT_HL)
        screen.blit(label, (strip.x + TEXT_INSET,
                            strip.centery - label.get_height() // 2))

        for index, (rect, text) in enumerate(
                zip(self.get_option_rects(len(shown)), shown)):
            selected = index == selected_index
            pygame.draw.rect(screen, ROW_BLUE if selected else ROW_WHITE, rect)
            pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_ROW)
            if selected:
                # A solid amber bracket on the left edge, so the choice
                # is still obvious to anyone who cannot separate the
                # blue from the white fill.
                pygame.draw.rect(screen, BAR_AMBER,
                                 pygame.Rect(rect.x, rect.y, MARKER_W,
                                             rect.h))
            rendered = self.__font_body.render(
                self.__truncate(text, rect.w - TEXT_INSET * 2 - MARKER_W),
                True, ROW_WHITE if selected else TEXT_COFFEE)
            screen.blit(rendered, (rect.x + TEXT_INSET + MARKER_W,
                                   rect.centery - rendered.get_height() // 2))

    def __truncate(self, text: str, max_px: int) -> str:
        """
        Clip an over-long reply with an ellipsis.

        The style guide forbids reflow inside a row (§3), and a reply
        that does not fit one row is a content problem, not a layout one.
        """
        if max_px <= 0:
            return ""
        if self.__font_body.size(text)[0] <= max_px:
            return text
        while text and self.__font_body.size(text + "...")[0] > max_px:
            text = text[:-1]
        return text + "..."

    def __draw_card(self, screen: pygame.Surface, box: pygame.Rect) -> None:
        """Draw the framed card, inner border, and corner marks."""
        pygame.draw.rect(screen, CARD_TAN, box)
        pygame.draw.rect(screen, BORDER_BROWN, box, BORDER_W)
        inner = box.inflate(-CARD_PAD, -CARD_PAD)
        pygame.draw.rect(screen, BORDER_BROWN, inner, 1)
        n = CORNER_LEN
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((inner.left, inner.top), (n, 0), (0, n)),
                ((inner.right, inner.top), (-n, 0), (0, n)),
                ((inner.left, inner.bottom), (n, 0), (0, -n)),
                ((inner.right, inner.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 3)


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   UP / DOWN     -> move the highlight (wraps)
#   ENTER / click -> pick the highlighted reply, prints it
#   TAB           -> cycle 2 / 3 / 4 option branches
#   F11           -> toggle windowed / fullscreen
#   ESC           -> quit
#
# The dialog box underneath is drawn from the real ui/dialog_box.py
# with a real line from content/dialogues.py, so the dock alignment
# is validated against the thing it actually docks to.
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    from content.dialogues import NPC_DIALOGUES
    from content.npc_roster import NPC_ROSTER
    from ui.dialog_box import DialogBox

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Choice box test")
    choices = ChoiceBox(*SIZE)
    dialog = DialogBox(*SIZE)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    # Reply sets are UI affordances, not narrative prose -- the spoken
    # line under them is real content from content/dialogues.py.
    BRANCHES = [
        ["Yes.", "Not right now."],
        ["Tell me more.", "Maybe later.", "I have to go."],
        ["Yes, I am in.", "How many days will it take?",
         "Ask me next semester.", "No."],
    ]
    branch_index = 1
    picked = "-"

    SPEAKER = "warm_classmate_purnno"
    LINE = NPC_DIALOGUES[SPEAKER]["offer"][0]
    pulse = 0.0

    running = True
    while running:
        pulse += clock.tick(60) / 1000.0
        options = BRANCHES[branch_index]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                window = pygame.display.set_mode(
                    SIZE, FULLSCREEN_FLAGS if is_fullscreen
                    else WINDOWED_FLAGS)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                branch_index = (branch_index + 1) % len(BRANCHES)
                choices.reset()
            else:
                choices.handle_event(event, len(options))

        if choices.take_confirmed():
            picked = options[choices.get_selected()]
            print(f"picked: {picked}")

        window.fill((231, 214, 189))
        dialog.render(window, NPC_ROSTER[SPEAKER]["display_name"], LINE,
                      None, True, pulse)
        choices.render(window, options, choices.get_selected())

        window.blit(hint_font.render(f"last pick: {picked}", True,
                                     STAT_BROWN), (SIDE_MARGIN, 40))
        hint = hint_font.render(
            "UP / DOWN move  |  ENTER or click picks  |  TAB branch size"
            "  |  F11 fullscreen  |  ESC quit", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 8))

        pygame.display.flip()

    pygame.quit()

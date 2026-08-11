"""
CSE Life: Compile & Conquer
ui/teleport_screen.py

The destination picker a teleport prop opens: "WHERE TO GO?" over a
scrollable list of the areas the player can be sent to.

Drawn as a CARD OVER THE MAP, not a full-screen takeover, for the same
reason ui/activity_choice_screen.py is — the player is answering the
thing they are standing next to, so the campus stays visible behind a
dimming veil.

The list itself is ui/ui_widgets.py::RowTable, the shared game-side
scroll control: 38 px rows on a 44 px pitch, wheel and up/down, and an
8 px scrollbar that only appears once the content overflows. It is the
project's list widget and it is used here rather than reimplemented,
because a fifth hand-rolled scroll offset is exactly the thing that
library exists to prevent. The palette and card geometry below are
still this file's own (Build Plan §0.5) — a widget is imported, a
screen's colours never are.

NO game logic. render() is handed the rows, which one is highlighted
and whether GO is live; it decides none of it. Which areas exist is
content/map_directory.py's answer and where the player lands is
engine/states/teleport.py's.

Style: Nangiba Tasnim's tan pixel look (UI_STYLE_GUIDE §2/§4.2).
Missing art never blocks -- this screen uses no art at all.
"""
from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

import pygame

from ui.ui_widgets import RowTable

# -- palette (§2, declared per file -- Build Plan §0.5) -------
CARD_TAN = (240, 228, 208)
HEADER_TAN = (214, 196, 168)
BORDER_BROWN = (169, 130, 94)
TEXT_COFFEE = (74, 53, 39)
STAT_BROWN = (140, 110, 85)
ROW_WHITE = (247, 243, 236)
ROW_GREEN = (150, 180, 125)     # the area the player is already in
BTN_CONFIRM = (150, 180, 125)   # GO
PANEL_TAN = (231, 214, 189)     # what a disabled button fades toward
VEIL = (24, 18, 14, 150)        # dim over the map behind the card

# -- layout ---------------------------------------------------
CARD_W = 520
CARD_H = 400
BORDER_CARD = 3
CARD_PAD = 10
CORNER_LEN = 14

TITLE_Y = 24
SUB_Y = 52

TABLE_X = 30                    # inset from the card's left edge
TABLE_Y = 76
TABLE_W = CARD_W - TABLE_X * 2
# Five rows at the shared 44 px pitch. Deliberately shorter than the
# nine areas the maps currently connect, so the scrollbar is a live
# part of the design rather than something that only shows up if
# somebody adds enough levels.
TABLE_ROWS_VISIBLE = 5
TABLE_H = TABLE_ROWS_VISIBLE * 44

BTN_W = 150
BTN_H = 44
BTN_Y = TABLE_Y + TABLE_H + 18

FONT_PATH = "assets/ui/PressStart2P.ttf"
SIZE_TITLE = 16
SIZE_BODY = 11
SIZE_LABEL = 9

TITLE_TEXT = "WHERE TO GO?"
HERE_SUFFIX = " · YOU ARE HERE"
HINT_TEXT = "ARROWS + ENTER  |  CLICK  |  ESC CANCELS"


def format_destination(name: str, is_here: bool = False) -> List[str]:
    """
    Turn one area into the row the table draws.

    Module-level and outside the class, the way
    ui/load_game_screen.py::format_slot_row() is: the screen must not
    reach into a domain object (§6.1). The caller maps its destinations
    through this and hands the result to set_rows().
    """
    return [str(name) + (HERE_SUFFIX if is_here else "")]


class TeleportScreen:
    """
    Draws the destination card.

    Owns geometry and the table's own interaction state (which row is
    selected, how far it is scrolled) — that is a widget's business,
    not the game's. It never fetches a destination and never moves
    anybody.
    """

    def __init__(self) -> None:
        """Build the table once; its rect follows the card each frame."""
        self.__fonts: dict = {}
        self.__veil: Optional[pygame.Surface] = None
        # One column, no header bar: the title above already says what
        # the list is, and a column title over a list of place names
        # would only repeat it.
        self.__table: RowTable = RowTable(
            pygame.Rect(0, 0, TABLE_W, TABLE_H), (), (14,))

    # -- fonts ------------------------------------------------
    def __font(self, size: int) -> pygame.font.Font:
        """Load the pixel font once per size, falling back to default."""
        if size not in self.__fonts:
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                FONT_PATH)
            try:
                self.__fonts[size] = pygame.font.Font(path, size)
            except (FileNotFoundError, OSError, pygame.error):
                self.__fonts[size] = pygame.font.Font(None, size + 6)
        return self.__fonts[size]

    # -- the rows (handed in, never fetched) ------------------
    def set_rows(self, rows: Sequence[Sequence[str]],
                 colours: Optional[Sequence[Optional[
                     Tuple[int, int, int]]]] = None) -> None:
        """Replace the destination list, already formatted."""
        self.__table.set_rows(rows, colours)

    def get_row_count(self) -> int:
        """How many destinations are listed."""
        return self.__table.get_row_count()

    def get_selected(self) -> int:
        """The highlighted row, or -1 when the list is empty."""
        return self.__table.get_selected()

    def set_selected(self, index: int) -> bool:
        """Highlight a row and scroll it into view. True if it moved."""
        return self.__table.set_selected(index)

    # -- geometry (the only thing this class knows) -----------
    def get_card_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """The card, centred on the screen it will be drawn onto."""
        card = pygame.Rect(0, 0, CARD_W, CARD_H)
        card.center = (screen.get_width() // 2, screen.get_height() // 2)
        return card

    def get_table_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """Where the list sits, in screen coordinates."""
        card = self.get_card_rect(screen)
        return pygame.Rect(card.x + TABLE_X, card.y + TABLE_Y,
                           TABLE_W, TABLE_H)

    def get_go_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """The GO button."""
        card = self.get_card_rect(screen)
        return pygame.Rect(card.x + TABLE_X, card.y + BTN_Y, BTN_W, BTN_H)

    def get_back_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """The BACK button."""
        card = self.get_card_rect(screen)
        return pygame.Rect(card.right - TABLE_X - BTN_W, card.y + BTN_Y,
                           BTN_W, BTN_H)

    def __sync(self, screen: pygame.Surface) -> None:
        """
        Park the table under the card before anything touches it.

        The card is centred on whatever surface it is drawn onto, so its
        rect is not known until then — and a hit test run against last
        frame's rect after a resize would select the wrong row.
        """
        rect = self.get_table_rect(screen)
        if self.__table.get_rect() != rect:
            self.__table.set_rect(rect)

    # -- input ------------------------------------------------
    def handle_event(self, screen: pygame.Surface,
                     event: pygame.event.Event) -> bool:
        """
        Let the table answer first. True when it consumed the event.

        Click selects a row, the wheel scrolls, up/down step — the
        widget's own contract. Committing a choice is the caller's, so
        ENTER and the buttons deliberately fall through.
        """
        self.__sync(screen)
        return self.__table.handle_event(event)

    def get_row_at(self, screen: pygame.Surface,
                   pos: Sequence[int]) -> int:
        """Index of the row under a screen position, or -1."""
        self.__sync(screen)
        return self.__table.row_at(tuple(pos))

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface, subtitle: str = "",
               can_go: bool = True) -> None:
        """
        Draw the card over whatever is already on `screen`.

        subtitle : one line under the title, e.g. where the player is
        can_go   : draws GO muted when the highlighted row is not
                   somewhere the player can actually be sent
        """
        self.__sync(screen)
        self.__draw_veil(screen)
        card = self.get_card_rect(screen)
        self.__draw_card(screen, card)

        title = self.__font(SIZE_TITLE).render(TITLE_TEXT, True, TEXT_COFFEE)
        screen.blit(title, (card.centerx - title.get_width() // 2,
                            card.y + TITLE_Y))
        if subtitle:
            sub = self.__font(SIZE_LABEL).render(subtitle.upper(), True,
                                                 STAT_BROWN)
            screen.blit(sub, (card.centerx - sub.get_width() // 2,
                              card.y + SUB_Y))

        self.__table.render(screen)

        self.__draw_button(screen, self.get_go_rect(screen), "GO",
                           BTN_CONFIRM, can_go)
        self.__draw_button(screen, self.get_back_rect(screen), "BACK",
                           HEADER_TAN, True)

        hint = self.__font(SIZE_LABEL).render(HINT_TEXT, True, STAT_BROWN)
        screen.blit(hint, (card.centerx - hint.get_width() // 2,
                           card.bottom - 26))

    def __draw_veil(self, screen: pygame.Surface) -> None:
        """Dim the map so the card reads as the thing being answered."""
        size = screen.get_size()
        if self.__veil is None or self.__veil.get_size() != size:
            self.__veil = pygame.Surface(size, pygame.SRCALPHA)
            self.__veil.fill(VEIL)
        screen.blit(self.__veil, (0, 0))

    def __draw_card(self, screen: pygame.Surface,
                    card: pygame.Rect) -> None:
        """Framed card with an inner border and corner brackets (§4.2)."""
        pygame.draw.rect(screen, CARD_TAN, card)
        pygame.draw.rect(screen, BORDER_BROWN, card, BORDER_CARD)
        inner = card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
        pygame.draw.rect(screen, BORDER_BROWN, inner, 1)
        n = CORNER_LEN
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((inner.left, inner.top), (n, 0), (0, n)),
                ((inner.right, inner.top), (-n, 0), (0, n)),
                ((inner.left, inner.bottom), (n, 0), (0, -n)),
                ((inner.right, inner.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 2)
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 2)

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, colour: tuple, enabled: bool) -> None:
        """
        Draw a labelled button. A disabled one desaturates toward the
        panel tan instead of changing shape (§4.6).
        """
        if enabled:
            fill = colour
            ink = TEXT_COFFEE
        else:
            fill = tuple(int(c + (PANEL_TAN[i] - c) * 0.6)
                         for i, c in enumerate(colour))
            ink = STAT_BROWN
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, 2)
        text = self.__font(SIZE_BODY).render(label, True, ink)
        screen.blit(text, (rect.centerx - text.get_width() // 2,
                           rect.centery - text.get_height() // 2))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   UP / DOWN or click -> select a destination
#   WHEEL              -> scroll the list past five rows
#   GO / ENTER         -> prints where it would send you
#   BACK / ESC         -> quit
#   F11                -> toggle windowed / fullscreen
#
# The destinations are the REAL ones content/map_directory.py derives
# from levels/, so this also shows what the menu will actually list.
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    from content.map_directory import walk_reachable

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Teleport screen test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    destinations = walk_reachable()
    HERE = "campus_main"        # pretend the player is standing here
    card_ui = TeleportScreen()
    card_ui.set_rows(
        [format_destination(name, level_id == HERE)
         for level_id, name in destinations],
        [ROW_GREEN if level_id == HERE else None
         for level_id, _ in destinations])
    card_ui.set_selected(0)
    last_action = "-"

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if card_ui.handle_event(window, event):
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    window = pygame.display.set_mode(
                        SIZE, FULLSCREEN_FLAGS if is_fullscreen
                        else WINDOWED_FLAGS)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    index = card_ui.get_selected()
                    last_action = ("GO %s" % destinations[index][0]
                                   if index >= 0 else "GO (nothing)")
                    print(last_action)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if card_ui.get_go_rect(window).collidepoint(event.pos):
                    index = card_ui.get_selected()
                    last_action = ("GO %s" % destinations[index][0]
                                   if index >= 0 else "GO (nothing)")
                    print(last_action)
                elif card_ui.get_back_rect(window).collidepoint(event.pos):
                    running = False

        window.fill(PANEL_TAN)
        window.blit(hint_font.render(
            "no map behind the card in the stub -- the real screen draws "
            "exploration here", True, STAT_BROWN), (40, 40))

        chosen = card_ui.get_selected()
        card_ui.render(window,
                       subtitle="%d PLACES · LAST: %s"
                                % (len(destinations), last_action),
                       can_go=chosen >= 0
                       and destinations[chosen][0] != HERE)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

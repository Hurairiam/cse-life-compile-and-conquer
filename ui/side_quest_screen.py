"""
CSE Life: Compile & Conquer
ui/side_quest_screen.py

The side quest list the PC in the player's room opens: "SELF STUDY"
over the topics the player took on, with the ones already read through
marked complete.

Drawn as a CARD OVER THE MAP, not a full-screen takeover, the same way
ui/teleport_screen.py and ui/activity_choice_screen.py are — the player
is using the thing they are standing next to, so the room stays visible
behind a dimming veil. The list itself is ui/ui_widgets.py::RowTable,
the shared game-side scroll control, for the reason that file gives:
a hand-rolled scroll offset is exactly what the widget library exists
to prevent. The palette and card geometry are still this file's own
(Build Plan §0.5) — a widget is imported, a screen's colours never are.

NO game logic, and in this screen that matters more than usual.
render() is handed the rows, which one is highlighted and whether START
is live; it decides none of it. **It never receives a quest it must not
draw.** Which quests exist at all is engine/side_quest_list.py's answer,
and that module hands over only the Unlocked and Completed ones — so
there is nothing here to grey out, no slot to leave empty, and no total
to count against. A declined or missed topic is not "hidden by the UI";
it never reaches the UI.

For the same reason the subtitle shows the days left in the term rather
than "n of 12". A count would be a leak.

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
ROW_GREEN = (150, 180, 125)     # a topic already read through
BTN_CONFIRM = (150, 180, 125)   # START
PANEL_TAN = (231, 214, 189)     # what a disabled button fades toward
VEIL = (24, 18, 14, 150)        # dim over the map behind the card

# -- layout ---------------------------------------------------
CARD_W = 560
CARD_H = 440
BORDER_CARD = 3
CARD_PAD = 10
CORNER_LEN = 14

TITLE_Y = 24
SUB_Y = 52

TABLE_X = 30                    # inset from the card's left edge
TABLE_Y = 76
TABLE_W = CARD_W - TABLE_X * 2
# Five rows at the shared 44 px pitch, under a 34 px header bar. Five
# because the list can reach twelve and a card tall enough for twelve
# would not leave the room visible behind it — the scrollbar is part of
# the design rather than an overflow accident.
TABLE_ROWS_VISIBLE = 5
TABLE_H = 34 + TABLE_ROWS_VISIBLE * 44

# TOPIC / DAYS / SHEETS / STATUS. STATUS is blank on a topic still to be
# read and "COMPLETE" on one that has been: two values, no third, and
# nothing that could stand for a quest the player never saw.
COLUMNS = ("TOPIC", "DAYS", "SHEETS", "")
# Sized off the longest label the skill tree has ("Data Structures",
# "Databases & SQL", "Version Control" — 15 characters at SIZE_BODY) and
# the longest status ("COMPLETE"), so nothing that can appear here gets
# truncated by RowTable's per-column clip.
COLUMN_OFFSETS = (12, 216, 296, 384)

BTN_W = 150
BTN_H = 44
BTN_Y = TABLE_Y + TABLE_H + 18

FONT_PATH = "assets/ui/PressStart2P.ttf"
SIZE_TITLE = 16
SIZE_BODY = 11
SIZE_LABEL = 9

TITLE_TEXT = "SELF STUDY"
COMPLETE_TEXT = "COMPLETE"
EMPTY_TEXT = "NOTHING SAVED ON THIS PC YET."
HINT_TEXT = "ARROWS + ENTER  |  CLICK  |  ESC CLOSES"


def format_quest_row(title: str, day_cost: int, sheets: int,
                     completed: bool = False) -> List[str]:
    """
    Turn one quest into the four cells the table draws.

    Module-level and outside the class, the way
    ui/teleport_screen.py::format_destination() and
    ui/load_game_screen.py::format_slot_row() are: the screen must not
    reach into a domain object (§6.1). The caller maps its rows through
    this and hands the result to set_rows().

    A completed topic keeps its sheet count — that is a fact about the
    topic, not a thing to be earned — and shows a dash for the day cost,
    because it will never be charged again.
    """
    return [str(title),
            "-" if completed else str(int(day_cost)),
            str(int(sheets)),
            COMPLETE_TEXT if completed else ""]


class SideQuestScreen:
    """
    Draws the self-study card.

    Owns geometry and the table's own interaction state (which row is
    selected, how far it is scrolled) — that is a widget's business, not
    the game's. It never fetches a quest and never starts one.
    """

    def __init__(self) -> None:
        """Build the table once; its rect follows the card each frame."""
        self.__fonts: dict = {}
        self.__veil: Optional[pygame.Surface] = None
        self.__table: RowTable = RowTable(
            pygame.Rect(0, 0, TABLE_W, TABLE_H), COLUMNS, COLUMN_OFFSETS)

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
        """Replace the topic list, already formatted."""
        self.__table.set_rows(rows, colours)

    def get_row_count(self) -> int:
        """How many topics are listed."""
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

    def get_start_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """The START button."""
        card = self.get_card_rect(screen)
        return pygame.Rect(card.x + TABLE_X, card.y + BTN_Y, BTN_W, BTN_H)

    def get_close_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """The CLOSE button."""
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
               can_start: bool = True) -> None:
        """
        Draw the card over whatever is already on `screen`.

        subtitle  : one line under the title, e.g. the days left
        can_start : draws START muted when the highlighted row cannot be
                    started right now — already read, or more days than
                    the term has left
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
        if self.__table.get_row_count() == 0:
            self.__draw_empty(screen)

        self.__draw_button(screen, self.get_start_rect(screen), "START",
                           BTN_CONFIRM, can_start)
        self.__draw_button(screen, self.get_close_rect(screen), "CLOSE",
                           HEADER_TAN, True)

        hint = self.__font(SIZE_LABEL).render(HINT_TEXT, True, STAT_BROWN)
        screen.blit(hint, (card.centerx - hint.get_width() // 2,
                           card.bottom - 26))

    def __draw_empty(self, screen: pygame.Surface) -> None:
        """
        One line where the rows would be, when there are none.

        Worded as "nothing saved yet", not "no quests available" — the
        player has no study material on this machine, and that is the
        whole of what they are told. Anything implying there could have
        been material here would be the leak this screen exists to
        avoid.
        """
        table = self.get_table_rect(screen)
        body = pygame.Rect(table.x, table.y + 34, table.w, table.h - 34)
        text = self.__font(SIZE_BODY).render(EMPTY_TEXT, True, STAT_BROWN)
        screen.blit(text, (body.centerx - text.get_width() // 2,
                           body.y + 26))

    def __draw_veil(self, screen: pygame.Surface) -> None:
        """Dim the room so the card reads as the thing being used."""
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
#   UP / DOWN or click -> select a topic
#   WHEEL              -> scroll the list past five rows
#   START / ENTER      -> prints what it would open
#   CLOSE / ESC        -> quit
#   E                  -> empty the list, to see the empty card
#   F11                -> toggle windowed / fullscreen
#
# The rows are built from the REAL quest definitions through
# engine/side_quest_list.py, against a hand-made run: some accepted,
# one read through, one declined and one slept through. The declined
# and missed ones must not appear -- that is the thing to look at.
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    from engine.quest_state import QuestStateMachine
    from engine.side_quest_list import entries, refusal

    class _Semester:
        def __init__(self, days):
            self.__days = days

        def get_time_pool_days(self):
            return self.__days

    class _Ctx:
        def __init__(self, machine, days):
            self.quest_states = machine
            self.__semester = _Semester(days)

        def semester(self):
            return self.__semester

    demo = QuestStateMachine()
    for term in (1, 2, 4, 6, 7, 8):
        demo.accept(demo.get_quest_for_semester(term))
    demo.mark_completed(demo.get_quest_for_semester(1))
    demo.mark_completed(demo.get_quest_for_semester(4))
    demo.decline(demo.get_quest_for_semester(3))
    demo.expire_unoffered_for_semester(5)
    DAYS = 30
    demo_ctx = _Ctx(demo, DAYS)

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Side quest screen test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    rows = entries(demo_ctx)
    card_ui = SideQuestScreen()

    def _refresh(shown):
        card_ui.set_rows(
            [format_quest_row(r["title"], r["day_cost"], r["sheets"],
                              r["completed"]) for r in shown],
            [ROW_GREEN if r["completed"] else None for r in shown])

    _refresh(rows)
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
                elif event.key == pygame.K_e:
                    rows = []
                    _refresh(rows)
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    window = pygame.display.set_mode(
                        SIZE, FULLSCREEN_FLAGS if is_fullscreen
                        else WINDOWED_FLAGS)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    picked = card_ui.get_selected()
                    last_action = ("START %s" % rows[picked]["quest_id"]
                                   if 0 <= picked < len(rows)
                                   else "START (nothing)")
                    print(last_action)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if card_ui.get_start_rect(window).collidepoint(event.pos):
                    picked = card_ui.get_selected()
                    last_action = ("START %s" % rows[picked]["quest_id"]
                                   if 0 <= picked < len(rows)
                                   else "START (nothing)")
                    print(last_action)
                elif card_ui.get_close_rect(window).collidepoint(event.pos):
                    running = False

        window.fill(PANEL_TAN)
        window.blit(hint_font.render(
            "no room behind the card in the stub -- the real screen draws "
            "exploration here.  E empties the list.", True, STAT_BROWN),
            (40, 40))

        chosen = card_ui.get_selected()
        card_ui.render(
            window,
            subtitle="DAYS LEFT: %d · LAST: %s" % (DAYS, last_action),
            can_start=(0 <= chosen < len(rows)
                       and refusal(demo_ctx, rows[chosen]["quest_id"])
                       is None))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

"""
CSE Life: Compile & Conquer
ui/activity_choice_screen.py

The three-way choice a classroom prop offers: sit the exam, attend
the lecture, or walk away.

Drawn as a CARD OVER THE MAP rather than a full-screen takeover. The
player is choosing what to do with the thing they are standing next
to, so the campus stays visible behind a dimming veil -- the same
relationship ui/popup.py has with the world.

NO game logic. render() is handed which entry is focused and whether
each one is currently selectable; it decides nothing. Whether an exam
can be sat, what a lecture costs and where "cancel" returns to are all
engine/states/activity.py's rulings.

Style: Nangiba Tasnim's tan pixel look (UI_STYLE_GUIDE §2/§4.2).
Missing art never blocks -- this screen uses no art at all.
"""
from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

import pygame

# -- palette (§2, declared per file -- Build Plan §0.5) -------
PANEL_TAN = (231, 214, 189)
CARD_TAN = (240, 228, 208)
HEADER_TAN = (214, 196, 168)
BORDER_BROWN = (169, 130, 94)
TEXT_COFFEE = (74, 53, 39)
CREDIT_HL = (155, 110, 70)
STAT_BROWN = (140, 110, 85)
ROW_BLUE = (120, 150, 190)
ROW_WHITE = (247, 243, 236)
BTN_CONFIRM = (150, 180, 125)
BTN_CANCEL = (199, 123, 107)
VEIL = (24, 18, 14, 150)        # dim over the map behind the card

# -- layout ---------------------------------------------------
CARD_W = 460
CARD_H = 300
BORDER_CARD = 3
CARD_PAD = 10
CORNER_LEN = 14

TITLE_Y = 26
SUB_Y = 54

BTN_W = 380
BTN_H = 46
BTN_GAP = 14
BTN_FIRST_Y = 96

FONT_PATH = "assets/ui/PressStart2P.ttf"
SIZE_TITLE = 16
SIZE_BODY = 11
SIZE_LABEL = 9

# The three entries, in draw order. `key` is what handle_events acts on.
ENTRY_EXAM = "exam"
ENTRY_LECTURE = "lecture"
ENTRY_CANCEL = "cancel"
ENTRIES: Tuple[Tuple[str, str], ...] = (
    (ENTRY_EXAM, "START EXAM"),
    (ENTRY_LECTURE, "START LECTURE"),
    (ENTRY_CANCEL, "CANCEL"),
)


class ActivityChoiceScreen:
    """
    Draws the exam / lecture / cancel card.

    Owns geometry only. `get_entry_rects()` is public so the state
    module can hit-test a click without this class deciding anything.
    """

    def __init__(self) -> None:
        """Fix the card and button geometry once; it never moves."""
        self.__fonts: dict = {}
        self.__card: pygame.Rect = pygame.Rect(0, 0, CARD_W, CARD_H)
        self.__veil: Optional[pygame.Surface] = None

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

    # -- geometry (the only thing this class knows) -----------
    def get_card_rect(self, screen: pygame.Surface) -> pygame.Rect:
        """The card, centred on the screen it will be drawn onto."""
        card = pygame.Rect(0, 0, CARD_W, CARD_H)
        card.center = (screen.get_width() // 2, screen.get_height() // 2)
        return card

    def get_entry_rects(self, screen: pygame.Surface) -> List[pygame.Rect]:
        """One hit box per entry, in ENTRIES order."""
        card = self.get_card_rect(screen)
        return [
            pygame.Rect(card.centerx - BTN_W // 2,
                        card.y + BTN_FIRST_Y + index * (BTN_H + BTN_GAP),
                        BTN_W, BTN_H)
            for index in range(len(ENTRIES))
        ]

    def get_entry_at(self, screen: pygame.Surface,
                     pos: Sequence[int]) -> int:
        """Index of the entry under a screen position, or -1."""
        for index, rect in enumerate(self.get_entry_rects(screen)):
            if rect.collidepoint(pos):
                return index
        return -1

    @staticmethod
    def get_entry_key(index: int) -> str:
        """The key of an entry by index, or "" when out of range."""
        if 0 <= index < len(ENTRIES):
            return ENTRIES[index][0]
        return ""

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface, focused_index: int = 0,
               disabled: Sequence[str] = (),
               subtitle: str = "") -> None:
        """
        Draw the card over whatever is already on `screen`.

        focused_index : which entry is highlighted (keyboard or hover)
        disabled      : entry keys that cannot be chosen right now,
                        drawn greyed; the caller still owns WHY
        subtitle      : one line under the title, e.g. the course name
        """
        self.__draw_veil(screen)
        card = self.get_card_rect(screen)
        self.__draw_card(screen, card)

        title = self.__font(SIZE_TITLE).render("WHAT NOW?", True, TEXT_COFFEE)
        screen.blit(title, (card.centerx - title.get_width() // 2,
                            card.y + TITLE_Y))
        if subtitle:
            sub = self.__font(SIZE_LABEL).render(subtitle.upper(), True,
                                                 STAT_BROWN)
            screen.blit(sub, (card.centerx - sub.get_width() // 2,
                              card.y + SUB_Y))

        blocked = set(disabled)
        for index, rect in enumerate(self.get_entry_rects(screen)):
            key, text = ENTRIES[index]
            self.__draw_entry(screen, rect, text,
                              focused=index == focused_index,
                              is_cancel=key == ENTRY_CANCEL,
                              is_disabled=key in blocked)

        hint = self.__font(SIZE_LABEL).render(
            "ARROWS + ENTER  |  CLICK  |  ESC CANCELS", True, STAT_BROWN)
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

    def __draw_entry(self, screen: pygame.Surface, rect: pygame.Rect,
                     text: str, focused: bool, is_cancel: bool,
                     is_disabled: bool) -> None:
        """One choice button, in its focused / normal / disabled state."""
        if is_disabled:
            fill, ink = HEADER_TAN, STAT_BROWN
        elif focused:
            fill = BTN_CANCEL if is_cancel else BTN_CONFIRM
            ink = ROW_WHITE
        else:
            fill, ink = HEADER_TAN, TEXT_COFFEE
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, 2)

        label = self.__font(SIZE_BODY).render(text, True, ink)
        screen.blit(label, (rect.centerx - label.get_width() // 2,
                            rect.centery - label.get_height() // 2))
        if is_disabled:
            note = self.__font(SIZE_LABEL).render("NOT AVAILABLE", True,
                                                  STAT_BROWN)
            screen.blit(note, (rect.right - note.get_width() - 8,
                               rect.bottom - note.get_height() - 4))

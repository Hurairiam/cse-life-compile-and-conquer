"""
ui/bed_popup.py
The three-choice question the bed asks (Task 7).

WHAT IT REPLACES
────────────────
The bed used to open a two-button ConfirmPopup: end the term, or don't.
Task 7 makes it three — advance, drain a named number of days, cancel —
and the middle one needs a number typed into it, which no widget in this
repo could take (recon item 11 found no stepper, no digit field, no
bounded-integer input anywhere).

WHY IT SUBCLASSES Modal
───────────────────────
Because everything except the buttons already exists there: the dim
overlay, the centred card, the ALL-CAPS title in the severity colour,
the body lines, the result bookkeeping and the "an open modal consumes
every event" firewall. `_draw_buttons()` and `_handle_open_event()` are
the two hooks Modal leaves for a subclass, and they are the two things
that differ. MessagePopup and ConfirmPopup are the precedent; a third
sibling cannot drift from them visually because none of the drawing is
repeated here.

TWO STAGES, ONE CARD
────────────────────
    MODE_MENU    three stacked buttons
    MODE_NUMBER  a digit field, its legal range, and OK / BACK

The number stage is inside the same card rather than a second popup, so
BACK returns to the choice rather than to the map — the player who
mistypes has not lost their place.

WHAT IT REFUSES, AND HOW
────────────────────────
ADVANCE is drawn visibly unavailable when the exams are not done —
greyed fill, muted ink — and a click or ENTER on it is ignored. The
brief asks for exactly that rather than a silent no-op, and the exam
count beside it says why without a sentence.

The number field takes digits only: there is no keystroke that can put a
minus sign, a decimal point or a letter into it, so "reject negatives,
zero and non-numeric input" is enforced by what can be typed rather than
by validating afterwards. Zero and over-range are refused at OK.

NO INVENTED PROSE (G2). The three option labels come from the brief and
are UI controls. Everything else drawn here is a label-plus-number
(DAYS, ALLOWED 1-38, EXAMS LEFT 2) or the title this prop already used —
never a sentence. The explanation of WHY advance is unavailable, and any
rejection message for a bad number, would both be dialogue; they are
Ayesha's and are reported as a gap rather than written here. The
controls carry the meaning in the meantime.

NO GAME LOGIC. This widget is told what is allowed and reports what was
chosen. `engine/exam_days.py` decides the range and
`engine/states/end_semester.py` acts on the result (§6.2).
"""
from __future__ import annotations

from typing import Optional, Tuple

import pygame

from ui.popup import (BORDER_BROWN, BTN_CANCEL, BTN_CONFIRM, BTN_H,
                      CARD_TAN, HEADER_TAN, SEVERITY_WARNING, SIZE_BODY,
                      STAT_BROWN, TEXT_COFFEE, Modal, load_font)

# -- results ---------------------------------------------------
RESULT_ADVANCE: str = "advance"
RESULT_DRAIN: str = "drain"
RESULT_CANCEL: str = "cancel"

# -- the two stages --------------------------------------------
MODE_MENU: str = "menu"
MODE_NUMBER: str = "number"

# -- layout ----------------------------------------------------
BOX_W          = 600
# Sized to its contents: the last row ends at OPTIONS_TOP + 2*PITCH +
# BTN_H = 252 from the box top, and 36 below that balances the title's
# margin above. Both stages end on the same row, so one height fits.
BOX_H          = 288
OPTION_W       = 420        # the three stacked choices
OPTION_PITCH   = 56
OPTIONS_TOP    = 96         # from the box top
BORDER_BTN     = 3

FIELD_W        = 200
FIELD_H        = 52
FIELD_TOP      = 110
SMALL_BTN_W    = 150
SMALL_BTN_GAP  = 24

SIZE_FIELD     = 22
SIZE_LABEL     = 10

MAX_DIGITS     = 3          # the day pool is 80; three digits is ample

# Option labels — the brief's own words, UI controls not dialogue.
LABEL_ADVANCE  = "ADVANCE SEMESTER"
LABEL_DRAIN    = "DRAIN TIMEPOOL"
LABEL_CANCEL   = "CANCEL"
LABEL_OK       = "OK"
LABEL_BACK     = "BACK"

# Field captions. Label-plus-number, never a sentence (G2).
CAPTION_DAYS   = "DAYS"
CAPTION_RANGE  = "ALLOWED %d - %d"
CAPTION_EXAMS  = "EXAMS LEFT %d"
CAPTION_NONE   = "ALLOWED NONE"


class BedPopup(Modal):
    """
    Advance / drain / cancel, with a bounded number field behind drain.

    Opened with what the rules allow — `can_advance`, the drain ceiling,
    and how many exams are outstanding — and asked afterwards what the
    player chose. It never consults the game itself.
    """

    def __init__(self, screen_w: int, screen_h: int) -> None:
        super().__init__(screen_w, screen_h, box_w=BOX_W, box_h=BOX_H)
        box = self.get_box_rect()
        left = box.centerx - OPTION_W // 2
        self.__options = [
            pygame.Rect(left, box.y + OPTIONS_TOP + index * OPTION_PITCH,
                        OPTION_W, BTN_H)
            for index in range(3)]

        self.__field = pygame.Rect(box.centerx - FIELD_W // 2,
                                   box.y + FIELD_TOP, FIELD_W, FIELD_H)
        buttons_y = self.__options[2].y
        self.__ok = pygame.Rect(
            box.centerx - SMALL_BTN_GAP // 2 - SMALL_BTN_W, buttons_y,
            SMALL_BTN_W, BTN_H)
        self.__back = pygame.Rect(
            box.centerx + SMALL_BTN_GAP // 2, buttons_y,
            SMALL_BTN_W, BTN_H)

        self.__mode: str = MODE_MENU
        self.__can_advance: bool = False
        self.__ceiling: int = 0
        self.__exams_left: int = 0
        self.__typed: str = ""
        self.__focus: int = 0
        self.__days: int = 0
        # This popup keeps its OWN choice rather than using Modal's
        # result slot: Modal.set_result() validates against its
        # VALID_RESULTS ("ok"/"confirm"/"cancel") and would refuse
        # ADVANCE and DRAIN outright. Widening that tuple would reach
        # into a file three other popups share for no benefit — the
        # choice codes here are this widget's vocabulary, not the
        # modal system's.
        self.__choice: Optional[str] = None

    # -- opening ----------------------------------------------
    def open_bed(self, can_advance: bool, ceiling: int,
                 exams_left: int, title: str = "END THE SEMESTER?",
                 accent: Tuple[int, int, int] = SEVERITY_WARNING) -> None:
        """
        Ask the question.

        `ceiling` is the most days the player may drain — already the
        exam floor subtracted, by engine/exam_days.py. 0 means the drain
        option is unavailable too.

        Named open_bed() rather than overriding open(): Modal.open() has
        a fixed (title, lines, accent) signature that three other
        popups rely on, and widening it would reach into their file.
        """
        super().open(title, (), accent)
        self.__mode = MODE_MENU
        self.__can_advance = bool(can_advance)
        self.__ceiling = max(0, int(ceiling))
        self.__exams_left = max(0, int(exams_left))
        self.__typed = ""
        self.__days = 0
        self.__choice = None
        self.__focus = 0 if self.__can_advance else 1

    # -- what was decided -------------------------------------
    def get_choice(self) -> Optional[str]:
        """The option chosen, or None while the card is undecided."""
        return self.__choice

    def take_choice(self) -> Optional[str]:
        """Read the choice once and clear it, so it fires exactly once."""
        choice, self.__choice = self.__choice, None
        return choice

    def get_days(self) -> int:
        """Days the player asked to drain. Only meaningful with DRAIN."""
        return self.__days

    def get_mode(self) -> str:
        """Which stage the card is showing."""
        return self.__mode

    def get_typed(self) -> str:
        """The digits currently in the field."""
        return self.__typed

    def get_ceiling(self) -> int:
        """The largest legal drain, as opened."""
        return self.__ceiling

    def can_advance(self) -> bool:
        """True while ADVANCE is offered rather than greyed."""
        return self.__can_advance

    def is_option_enabled(self, index: int) -> bool:
        """Whether the option at `index` may be chosen at all."""
        if index == 0:
            return self.__can_advance
        if index == 1:
            return self.__ceiling > 0
        return True

    # -- geometry ---------------------------------------------
    def get_option_rects(self):
        """The three choice rectangles, in draw order."""
        return list(self.__options)

    def get_field_rect(self) -> pygame.Rect:
        return self.__field

    def get_ok_button_rect(self) -> pygame.Rect:
        return self.__ok

    def get_back_button_rect(self) -> pygame.Rect:
        return self.__back

    # -- input ------------------------------------------------
    def _handle_open_event(self, event: pygame.event.Event) -> None:
        if self.__mode == MODE_MENU:
            self.__menu_event(event)
        else:
            self.__number_event(event)

    def __menu_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.__decide(RESULT_CANCEL)
            elif event.key == pygame.K_DOWN:
                self.__focus = (self.__focus + 1) % 3
            elif event.key == pygame.K_UP:
                self.__focus = (self.__focus - 1) % 3
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                               pygame.K_SPACE):
                self.__choose(self.__focus)
        elif event.type == pygame.MOUSEMOTION:
            for index, rect in enumerate(self.__options):
                if rect.collidepoint(event.pos):
                    self.__focus = index
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.__options):
                if rect.collidepoint(event.pos):
                    self.__choose(index)
                    return

    def __choose(self, index: int) -> None:
        """
        Act on one of the three, or refuse it.

        An unavailable option is IGNORED rather than closing the card:
        the player pressed something that is visibly greyed, and the
        useful response is to leave the question up.
        """
        if not self.is_option_enabled(index):
            return
        if index == 0:
            self.__decide(RESULT_ADVANCE)
        elif index == 1:
            self.__mode = MODE_NUMBER
            self.__typed = ""
        else:
            self.__decide(RESULT_CANCEL)

    def __number_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.__mode = MODE_MENU
                return
            if event.key == pygame.K_BACKSPACE:
                self.__typed = self.__typed[:-1]
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.__accept()
                return
            # Digits only. There is no keystroke that can put a sign, a
            # separator or a letter in here, so the field cannot hold
            # anything int() would refuse.
            digit = getattr(event, "unicode", "")
            if digit.isdigit() and len(self.__typed) < MAX_DIGITS:
                self.__typed += digit
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.__ok.collidepoint(event.pos):
                self.__accept()
            elif self.__back.collidepoint(event.pos):
                self.__mode = MODE_MENU

    def __accept(self) -> None:
        """
        Take the typed number, or refuse it and stay put.

        Zero, empty and anything over the ceiling are all refused the
        same way — the card stays open with the range still on screen.
        Refusing rather than clamping is deliberate: silently turning a
        typed 60 into 38 spends days the player did not ask for.
        """
        if not self.__typed:
            return
        wanted = int(self.__typed)
        if not 1 <= wanted <= self.__ceiling:
            return
        self.__days = wanted
        self.__decide(RESULT_DRAIN)

    def __decide(self, result: str) -> None:
        """Record the choice and close, the way Modal's siblings do."""
        self.__choice = result
        self.close()

    # -- drawing ----------------------------------------------
    def _draw_buttons(self, screen: pygame.Surface) -> None:
        if self.__mode == MODE_MENU:
            self.__draw_menu(screen)
        else:
            self.__draw_number(screen)

    def __draw_menu(self, screen: pygame.Surface) -> None:
        labels = (LABEL_ADVANCE, LABEL_DRAIN, LABEL_CANCEL)
        fills = (BTN_CONFIRM, HEADER_TAN, BTN_CANCEL)
        for index, rect in enumerate(self.__options):
            enabled = self.is_option_enabled(index)
            # Unavailable reads as flat and muted, never as a live
            # button that happens to do nothing.
            fill = fills[index] if enabled else HEADER_TAN
            ink = TEXT_COFFEE if enabled else STAT_BROWN
            pygame.draw.rect(screen, fill, rect)
            pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_BTN)
            font = load_font(SIZE_BODY)
            rendered = font.render(labels[index], True, ink)
            screen.blit(rendered,
                        (rect.centerx - rendered.get_width() // 2,
                         rect.centery - rendered.get_height() // 2))
            if index == self.__focus and enabled:
                self.__draw_focus(screen, rect)

        # Why ADVANCE is grey, said in numbers rather than a sentence.
        small = load_font(SIZE_LABEL)
        if not self.__can_advance:
            self._blit_centred(screen, small,
                               CAPTION_EXAMS % self.__exams_left,
                               STAT_BROWN, self.get_box_rect().centerx,
                               self.__options[0].y - 22)

    def __draw_number(self, screen: pygame.Surface) -> None:
        box = self.get_box_rect()
        small = load_font(SIZE_LABEL)
        self._blit_centred(screen, small, CAPTION_DAYS, STAT_BROWN,
                           box.centerx, self.__field.y - 24)

        pygame.draw.rect(screen, CARD_TAN, self.__field)
        pygame.draw.rect(screen, BORDER_BROWN, self.__field, BORDER_BTN)
        shown = self.__typed or "_"
        rendered = load_font(SIZE_FIELD).render(shown, True, TEXT_COFFEE)
        screen.blit(rendered,
                    (self.__field.centerx - rendered.get_width() // 2,
                     self.__field.centery - rendered.get_height() // 2))

        caption = (CAPTION_RANGE % (1, self.__ceiling) if self.__ceiling > 0
                   else CAPTION_NONE)
        self._blit_centred(screen, small, caption, STAT_BROWN,
                           box.centerx, self.__field.bottom + 12)

        legal = bool(self.__typed) and 1 <= int(self.__typed) <= self.__ceiling
        self._draw_button(screen, self.__ok, LABEL_OK,
                          BTN_CONFIRM if legal else HEADER_TAN)
        self._draw_button(screen, self.__back, LABEL_BACK, BTN_CANCEL)

    def __draw_focus(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        """The amber keyboard bracket ui/pause_menu.py draws."""
        from ui.popup import BAR_AMBER
        x = rect.left - 18
        top = rect.centery - 9
        pygame.draw.line(screen, BAR_AMBER, (x, top), (x + 6, top), 3)
        pygame.draw.line(screen, BAR_AMBER, (x, top), (x, top + 18), 3)
        pygame.draw.line(screen, BAR_AMBER, (x, top + 18),
                         (x + 6, top + 18), 3)

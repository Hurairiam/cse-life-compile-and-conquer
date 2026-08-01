"""
ui/exam_screen.py
CSE Life: Compile & Conquer — phase F9  (Feature 8, the exam itself)
─────────────────────────────────────────────────────────────
The three-tier MCQ screen: which course is being examined, which
tier is live, how long is left on the countdown, the question, and
four lettered options to pick from.

This file has NO game logic, and in particular THE SCREEN NEVER
GRADES. No correct-answer data ever reaches it — which is exactly
why academic/course.py::get_question() (which strips the answer) is
the only source of what is drawn here. Whether a pick was right,
what a timeout costs and when the exam ends are all
engine/exam_session.py's decisions.

The countdown's colour reuses the §2.2 traffic-light logic rather
than inventing a new one: BAR_GREEN above 10 s, BAR_AMBER 5-10 s,
BAR_RED under 5 s, with the numeral blinking on a ~500 ms cycle
inside the last 5. Nothing else moves — §7 forbids animated
decoration.

Self-contained by owner ruling (Build Plan §0.5): the palette and
layout constants below are copied verbatim from UI_STYLE_GUIDE.md
§2-§4 rather than imported from another screen, and the word-wrap
helper is private to this file rather than shared.

Layout, wrapping + test by Nangiba Tasnim (Dev 3).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pygame

# -------------------------------------------------------------
# PATHS
# -------------------------------------------------------------
# Anchored to this file, never the working directory, so the font and
# the icon resolve the same way whatever launched the game.
# -------------------------------------------------------------
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")
EXAM_ICON_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui",
                                   "icon_exam.png")

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues (§0.5).
PANEL_TAN     = (231, 214, 189)   # screen background behind the card
CARD_TAN      = (240, 228, 208)   # the card fill
HEADER_TAN    = (214, 196, 168)   # tier chip, table header, neutral fills
BORDER_BROWN  = (169, 130, 94)    # every outline, separator and corner mark
TEXT_COFFEE   = (74, 53, 39)      # primary text
CREDIT_HL     = (155, 110, 70)    # emphasised labels
STAT_BROWN    = (140, 110, 85)    # secondary / muted text
BAR_TRACK     = (222, 208, 186)   # empty part of the countdown bar (in-card)

ROW_WHITE     = (247, 243, 236)   # unselected option row
ROW_BLUE      = (120, 150, 190)   # focused option row

BAR_GREEN     = (167, 185, 133)   # countdown safe      (> 10 s)
BAR_AMBER     = (217, 169, 106)   # countdown warning   (5-10 s)
BAR_RED       = (199, 123, 107)   # countdown danger    (< 5 s), TIME UP strip

BTN_CONFIRM   = (150, 180, 125)   # the SUBMIT button
PLACEHOLDER   = (196, 178, 150)   # square drawn where the icon is missing
HINT_BROWN    = (150, 125, 100)   # stub-test hint line only

# -------------------------------------------------------------
# LAYOUT  (UI_STYLE_GUIDE §4 — fixed pixel constants)
# -------------------------------------------------------------
SCREEN_W       = 1280
SCREEN_H       = 720

CARD_MARGIN    = 24         # dense-screen card inset (§4.2)
CARD_PAD       = 14         # gap between card and inner border
CORNER_LEN     = 22         # corner bracket arm length
BORDER_CARD    = 3          # card frame weight
BORDER_ROW     = 2          # row borders, separators, bar outline

CONTENT_INSET  = 40         # gap from the card edge to its content

ICON_SIZE      = 24         # the exam icon, per §5.3
HEADER_Y       = 40         # header baseline, from the card top
CHIP_W         = 148        # tier chip
CHIP_H         = 30

TIMER_Y        = 96         # countdown row, from the card top
BAR_W          = 420        # countdown bar (§4.5)
BAR_H          = 16
BAR_LABEL_GAP  = 18         # gap between the bar and the numeric readout

QUESTION_Y     = 152        # first question line, from the card top
QUESTION_PITCH = 30         # gap between wrapped question lines
MAX_Q_LINES    = 3          # §4 — three lines, then truncate

OPTIONS_Y      = 268        # first option row, from the card top
ROW_H          = 38         # option row height (§4.4)
ROW_PITCH      = 44         # row height + a 6 px gap
LETTER_COL_W   = 40         # the "A)" column, per §4.4

BTN_W          = 220        # the SUBMIT button
BTN_H          = 44         # every button is 44 px tall (§4.6)
BTN_BOTTOM_GAP = 24
BORDER_BTN     = 3

STRIP_W        = 360        # the TIME UP strip
STRIP_H        = 48
STRIP_GAP      = 34         # gap below the last option row to the strip

SIZE_PROGRESS  = 16         # "2 / 3" and the countdown numeral
SIZE_COURSE    = 12         # course code + name
SIZE_QUESTION  = 13         # the question text
SIZE_ROW       = 11         # option rows, chip and button labels
SIZE_LABEL     = 10         # muted captions

# Countdown thresholds. These mirror §2.2's traffic-light rule rather
# than inventing a second one; only the units differ (seconds, not days).
TIME_SAFE_SECONDS: float = 10.0
TIME_WARN_SECONDS: float = 5.0

BLINK_PERIOD_SECONDS: float = 0.5   # numeral blink inside the last 5 s
TIME_UP_SECONDS: float = 0.4        # how long the TIME UP strip shows

ELLIPSIS = "..."

_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def load_font(size: int) -> pygame.font.Font:
    """
    Return the pixel font at `size`, cached across the module.

    Falls back to the mandatory Courier substitute so a missing TTF can
    never crash the exam (UI_STYLE_GUIDE §3).
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


def format_clock(seconds: float) -> str:
    """Seconds as `MM:SS`, e.g. 12.4 -> `00:12`. Never negative."""
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class ExamScreen:
    """
    Draws one exam question and its four options.

    Owns only its OWN presentation state: the cached icon and the
    short-lived TIME UP strip timer. Everything else is handed to
    render() (§6.1), and the caller reads get_option_rects() /
    get_submit_rect() to interpret clicks — the screen returns no
    decisions (§6.2).
    """

    def __init__(self) -> None:
        """Build the card geometry once; it never moves."""
        self.__card: pygame.Rect = pygame.Rect(
            CARD_MARGIN, CARD_MARGIN,
            SCREEN_W - CARD_MARGIN * 2, SCREEN_H - CARD_MARGIN * 2)
        self.__content_x: int = self.__card.x + CONTENT_INSET
        self.__content_w: int = self.__card.w - CONTENT_INSET * 2
        self.__submit: pygame.Rect = pygame.Rect(
            self.__card.right - CONTENT_INSET - BTN_W,
            self.__card.bottom - BTN_BOTTOM_GAP - BTN_H, BTN_W, BTN_H)
        self.__icon: Optional[pygame.Surface] = None
        self.__icon_loaded: bool = False
        self.__time_up_left: float = 0.0

    # -- geometry getters -------------------------------------
    def get_card_rect(self) -> pygame.Rect:
        """The framed card rectangle."""
        return self.__card

    def get_option_rects(self, count: int) -> List[pygame.Rect]:
        """The clickable rectangle for each of `count` option rows."""
        rects: List[pygame.Rect] = []
        for index in range(max(0, int(count))):
            rects.append(pygame.Rect(
                self.__content_x, self.__card.y + OPTIONS_Y + index * ROW_PITCH,
                self.__content_w, ROW_H))
        return rects

    def get_submit_rect(self) -> pygame.Rect:
        """The SUBMIT button rectangle."""
        return self.__submit

    # -- the TIME UP strip ------------------------------------
    def trigger_time_up(self) -> None:
        """
        Flash the TIME UP strip for TIME_UP_SECONDS.

        Called by the runner when engine/exam_session.tick() reports a
        timeout. The screen only shows the strip; it does not decide that
        time ran out.
        """
        self.__time_up_left = TIME_UP_SECONDS

    def update(self, dt: float) -> None:
        """Age the TIME UP strip. Safe to call every frame."""
        if self.__time_up_left > 0.0:
            self.__time_up_left = max(0.0, self.__time_up_left - float(dt))

    def is_showing_time_up(self) -> bool:
        """True while the TIME UP strip is on screen."""
        return self.__time_up_left > 0.0

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface, course_code: str = "",
               course_name: str = "", tier: str = "", tier_index: int = 0,
               question_lines: Any = (), options: Any = (),
               focused_index: int = -1, seconds_left: float = 0.0,
               seconds_limit: float = 0.0) -> None:
        """
        Draw the whole exam screen from handed-in values (§6.1).

        `question_lines` accepts either a raw string (wrapped here by the
        private helper) or an already-split sequence; `options` accepts
        either the `{"A": text}` dict Course hands back or a sequence of
        texts. Both shapes are normalised so a caller never has to
        pre-format for this screen's convenience.
        """
        screen.fill(PANEL_TAN)
        self.__draw_card(screen)
        self.__draw_header(screen, course_code, course_name, tier, tier_index)
        self.__draw_countdown(screen, seconds_left, seconds_limit)
        self.__draw_question(screen, question_lines)
        self.__draw_options(screen, options, focused_index)
        self.__draw_submit(screen)
        if self.is_showing_time_up():
            self.__draw_time_up(screen)

    def __draw_card(self, screen: pygame.Surface) -> None:
        """Framed card with an inner border and corner brackets (§4.2)."""
        pygame.draw.rect(screen, CARD_TAN, self.__card)
        pygame.draw.rect(screen, BORDER_BROWN, self.__card, BORDER_CARD)
        inner = self.__card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
        pygame.draw.rect(screen, BORDER_BROWN, inner, 1)
        self.__draw_corners(screen, inner)

    def __draw_corners(self, screen: pygame.Surface,
                       rect: pygame.Rect) -> None:
        """Two 3 px arms per corner — the franchise signature (§4.2)."""
        n = CORNER_LEN
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((rect.left, rect.top), (n, 0), (0, n)),
                ((rect.right, rect.top), (-n, 0), (0, n)),
                ((rect.left, rect.bottom), (n, 0), (0, -n)),
                ((rect.right, rect.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_header(self, screen: pygame.Surface, course_code: str,
                      course_name: str, tier: str, tier_index: int) -> None:
        """Icon, course identity, tier chip and the `n / 3` progress."""
        y = self.__card.y + HEADER_Y
        icon = self.__get_icon()
        if icon is not None:
            screen.blit(icon, (self.__content_x, y))
        else:
            self.__draw_placeholder(screen, self.__content_x, y)

        font = load_font(SIZE_COURSE)
        label = f"{course_code}  {course_name}".strip()
        text_x = self.__content_x + ICON_SIZE + 12
        # The header must not run under the progress readout on a long
        # course name, so it is truncated to the space actually available.
        max_px = self.__card.right - CONTENT_INSET - 200 - text_x
        rendered = font.render(self.__truncate(label, font, max_px), True,
                               TEXT_COFFEE)
        screen.blit(rendered, (text_x, y + (ICON_SIZE - rendered.get_height())
                               // 2))

        progress_font = load_font(SIZE_PROGRESS)
        progress = f"{min(tier_index + 1, 3)} / 3"
        rendered = progress_font.render(progress, True, TEXT_COFFEE)
        screen.blit(rendered, (self.__card.right - CONTENT_INSET
                               - rendered.get_width(),
                               y + (ICON_SIZE - rendered.get_height()) // 2))

        chip = pygame.Rect(self.__card.right - CONTENT_INSET - 100 - CHIP_W,
                           y - 3, CHIP_W, CHIP_H)
        pygame.draw.rect(screen, HEADER_TAN, chip)
        pygame.draw.rect(screen, BORDER_BROWN, chip, BORDER_ROW)
        self.__blit_centred(screen, load_font(SIZE_ROW), str(tier).upper(),
                            TEXT_COFFEE, chip.centerx, chip.centery)

    def __draw_countdown(self, screen: pygame.Surface, seconds_left: float,
                         seconds_limit: float) -> None:
        """
        The countdown bar and its numeric readout.

        Colour follows §2.2's traffic light; the numeral blinks on a
        ~500 ms cycle inside the last TIME_WARN_SECONDS. The blink phase
        is derived from seconds_left itself rather than a separate clock,
        so the screen needs no extra parameter and stays deterministic —
        the same input always draws the same frame, which is what makes
        this testable.
        """
        y = self.__card.y + TIMER_Y
        track = pygame.Rect(self.__content_x, y, BAR_W, BAR_H)
        pygame.draw.rect(screen, BAR_TRACK, track)

        limit = float(seconds_limit) if seconds_limit > 0 else 1.0
        ratio = max(0.0, min(1.0, float(seconds_left) / limit))
        colour = self.__countdown_colour(seconds_left)
        if ratio > 0.0:
            pygame.draw.rect(screen, colour,
                             (track.x, track.y, int(track.w * ratio), track.h))
        pygame.draw.rect(screen, BORDER_BROWN, track, BORDER_ROW)

        blink_on = True
        if seconds_left <= TIME_WARN_SECONDS:
            blink_on = int(seconds_left / BLINK_PERIOD_SECONDS) % 2 == 0
        if blink_on:
            font = load_font(SIZE_PROGRESS)
            rendered = font.render(format_clock(seconds_left), True, colour)
            screen.blit(rendered, (track.right + BAR_LABEL_GAP,
                                   track.centery - rendered.get_height() // 2))

        caption = load_font(SIZE_LABEL).render("TIME REMAINING", True,
                                               STAT_BROWN)
        screen.blit(caption, (self.__content_x, y - caption.get_height() - 6))

    @staticmethod
    def __countdown_colour(seconds_left: float) -> Tuple[int, int, int]:
        """§2.2 traffic light: green > 10 s, amber 5-10 s, red under 5 s."""
        if seconds_left > TIME_SAFE_SECONDS:
            return BAR_GREEN
        if seconds_left >= TIME_WARN_SECONDS:
            return BAR_AMBER
        return BAR_RED

    def __draw_question(self, screen: pygame.Surface,
                        question_lines: Any) -> None:
        """Draw the question, wrapped to at most MAX_Q_LINES lines."""
        font = load_font(SIZE_QUESTION)
        lines = self.__resolve_lines(question_lines, font, self.__content_w)
        y = self.__card.y + QUESTION_Y
        for line in lines:
            screen.blit(font.render(line, True, TEXT_COFFEE),
                        (self.__content_x, y))
            y += QUESTION_PITCH

    def __draw_options(self, screen: pygame.Surface, options: Any,
                       focused_index: int) -> None:
        """
        Four lettered option rows with full table styling (§4.4).

        The catalog's option texts reach 136 characters, which cannot fit
        one 38 px row at size 11, so a row truncates with an ellipsis
        rather than overflowing its border. Recorded in PHASELOG_F9 §8.
        """
        pairs = self.__resolve_options(options)
        rects = self.get_option_rects(len(pairs))
        font = load_font(SIZE_ROW)
        for index, ((letter, text), rect) in enumerate(zip(pairs, rects)):
            focused = index == focused_index
            pygame.draw.rect(screen, ROW_BLUE if focused else ROW_WHITE, rect)
            pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_ROW)
            separator_x = rect.x + LETTER_COL_W
            pygame.draw.line(screen, BORDER_BROWN, (separator_x, rect.y),
                             (separator_x, rect.bottom), BORDER_ROW)
            self.__blit_centred(screen, font, f"{letter})", TEXT_COFFEE,
                                rect.x + LETTER_COL_W // 2, rect.centery)
            body = self.__truncate(str(text), font,
                                   rect.right - separator_x - 20)
            rendered = font.render(body, True, TEXT_COFFEE)
            screen.blit(rendered, (separator_x + 12,
                                   rect.centery - rendered.get_height() // 2))

    def __draw_submit(self, screen: pygame.Surface) -> None:
        """The SUBMIT button: flat fill, 3 px border, ALL-CAPS (§4.6)."""
        pygame.draw.rect(screen, BTN_CONFIRM, self.__submit)
        pygame.draw.rect(screen, BORDER_BROWN, self.__submit, BORDER_BTN)
        self.__blit_centred(screen, load_font(SIZE_ROW), "SUBMIT",
                            TEXT_COFFEE, self.__submit.centerx,
                            self.__submit.centery)

    def __draw_time_up(self, screen: pygame.Surface) -> None:
        """
        The brief red TIME UP strip shown between tiers.

        Sits in the clear band BELOW the option rows: a three-line
        question reaches down to the options, so anything centred above
        them would land on the question text.
        """
        strip = pygame.Rect(0, 0, STRIP_W, STRIP_H)
        strip.center = (self.__card.centerx,
                        self.__card.y + OPTIONS_Y + 4 * ROW_PITCH
                        + STRIP_GAP + STRIP_H // 2)
        pygame.draw.rect(screen, BAR_RED, strip)
        pygame.draw.rect(screen, BORDER_BROWN, strip, BORDER_ROW)
        self.__blit_centred(screen, load_font(SIZE_PROGRESS), "TIME UP",
                            CARD_TAN, strip.centerx, strip.centery)

    # -- private helpers --------------------------------------
    def __resolve_lines(self, question_lines: Any, font: pygame.font.Font,
                        max_px: int) -> List[str]:
        """Accept a raw string or pre-split lines; always return <= 3 lines."""
        if isinstance(question_lines, str):
            return self.__wrap_lines(question_lines, font, max_px)
        lines = [str(line) for line in (question_lines or ())]
        if len(lines) <= MAX_Q_LINES:
            return lines
        return lines[:MAX_Q_LINES]

    def __wrap_lines(self, text: str, font: pygame.font.Font,
                     max_px: int) -> List[str]:
        """
        Greedy word-wrap to `max_px`, capped at MAX_Q_LINES.

        A single word wider than the box is hard-split rather than left to
        overflow. The last kept line is ellipsised if text remains, so a
        long question degrades visibly instead of silently vanishing.
        Private to this file by §0.5 — no shared wrap module exists.
        """
        words = str(text).split()
        lines: List[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and font.size(candidate)[0] > max_px:
                lines.append(current)
                current = word
            else:
                current = candidate
            while font.size(current)[0] > max_px and len(current) > 1:
                cut = len(current) - 1
                while cut > 1 and font.size(current[:cut])[0] > max_px:
                    cut -= 1
                lines.append(current[:cut])
                current = current[cut:]
            if len(lines) >= MAX_Q_LINES:
                break
        if current and len(lines) < MAX_Q_LINES:
            lines.append(current)
        if len(lines) == MAX_Q_LINES and font.size(text)[0] > max_px * MAX_Q_LINES:
            lines[-1] = self.__truncate(lines[-1] + ELLIPSIS, font, max_px)
        return lines[:MAX_Q_LINES]

    @staticmethod
    def __resolve_options(options: Any) -> List[Tuple[str, str]]:
        """Normalise a `{"A": text}` dict or a sequence into (letter, text)."""
        if isinstance(options, dict):
            return [(str(key).upper(), str(value))
                    for key, value in options.items()]
        pairs: List[Tuple[str, str]] = []
        for index, entry in enumerate(options or ()):
            if isinstance(entry, (tuple, list)) and len(entry) == 2:
                pairs.append((str(entry[0]).upper(), str(entry[1])))
            else:
                pairs.append((chr(ord("A") + index), str(entry)))
        return pairs

    @staticmethod
    def __truncate(text: str, font: pygame.font.Font, max_px: int) -> str:
        """Shorten `text` with an ellipsis until it fits `max_px`."""
        if max_px <= 0 or font.size(text)[0] <= max_px:
            return text
        cut = len(text)
        while cut > 0 and font.size(text[:cut] + ELLIPSIS)[0] > max_px:
            cut -= 1
        return text[:cut] + ELLIPSIS if cut > 0 else ""

    @staticmethod
    def __blit_centred(screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: Tuple[int, int, int],
                       centre_x: int, centre_y: int) -> None:
        """Draw text centred on a point."""
        rendered = font.render(text, True, colour)
        screen.blit(rendered, (centre_x - rendered.get_width() // 2,
                               centre_y - rendered.get_height() // 2))

    def __draw_placeholder(self, screen: pygame.Surface, x: int,
                           y: int) -> None:
        """The flat square the placeholder protocol draws for a missing icon."""
        pygame.draw.rect(screen, PLACEHOLDER, (x, y, ICON_SIZE, ICON_SIZE))
        pygame.draw.rect(screen, BORDER_BROWN, (x, y, ICON_SIZE, ICON_SIZE), 2)

    def __get_icon(self) -> Optional[pygame.Surface]:
        """
        The 24×24 exam icon, loaded once, or None while the PNG is missing.

        # [ICON PLACEHOLDER: assets/ui/icon_exam.png — exam / test paper,
        #  readable at 24×24] (§5.2/§5.3)
        """
        if self.__icon_loaded:
            return self.__icon
        self.__icon_loaded = True
        try:
            surface = pygame.image.load(EXAM_ICON_PATH).convert_alpha()
            self.__icon = pygame.transform.scale(surface,
                                                 (ICON_SIZE, ICON_SIZE))
        except (FileNotFoundError, OSError, pygame.error):
            self.__icon = None
        return self.__icon

    def get_missing_paths(self) -> List[str]:
        """Asset paths that failed to load — the §5.2 step-4 work queue."""
        if self.__icon_loaded and self.__icon is None:
            return [EXAM_ICON_PATH]
        return []


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   A-D / up-down -> pick an option      ENTER / SPACE -> submit
#   T             -> freeze the timer (inspect the layout)
#   N             -> next course from the real catalog
#   R             -> restart this exam
#   F11           -> toggle windowed / fullscreen
#   ESC           -> quit
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, PROJECT_ROOT)

    from academic.course_catalog import build_course_catalog
    from engine.exam_session import (QUESTION_TIME_LIMIT_SECONDS, ExamSession)

    pygame.init()

    SIZE = (SCREEN_W, SCREEN_H)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Exam screen test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    catalog = build_course_catalog()
    course_index = 0
    screen_ui = ExamScreen()
    timer_frozen = False
    focused = 0
    last_result = "-"

    def _new_session(index: int) -> ExamSession:
        """Start a fresh exam on one real catalog course."""
        session = ExamSession(catalog[index])
        session.start()
        return session

    exam = _new_session(course_index)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        screen_ui.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    window = pygame.display.set_mode(
                        SIZE,
                        FULLSCREEN_FLAGS if is_fullscreen else WINDOWED_FLAGS)
                elif event.key == pygame.K_t:
                    timer_frozen = not timer_frozen
                elif event.key == pygame.K_n:
                    course_index = (course_index + 1) % len(catalog)
                    exam, focused, last_result = (_new_session(course_index),
                                                  0, "-")
                elif event.key == pygame.K_r:
                    exam, focused, last_result = (_new_session(course_index),
                                                  0, "-")
                elif event.key in (pygame.K_DOWN, pygame.K_UP):
                    letters = exam.get_current_option_letters()
                    if letters:
                        step = 1 if event.key == pygame.K_DOWN else -1
                        focused = (focused + step) % len(letters)
                elif event.key in (pygame.K_a, pygame.K_b, pygame.K_c,
                                   pygame.K_d):
                    letters = exam.get_current_option_letters()
                    picked = chr(event.key).upper()
                    if picked in letters:
                        focused = letters.index(picked)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                   pygame.K_SPACE):
                    letters = exam.get_current_option_letters()
                    if letters and 0 <= focused < len(letters):
                        exam.submit_answer(letters[focused])
                        focused = 0
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                letters = exam.get_current_option_letters()
                for i, rect in enumerate(screen_ui.get_option_rects(
                        len(letters))):
                    if rect.collidepoint(event.pos):
                        focused = i
                if screen_ui.get_submit_rect().collidepoint(event.pos):
                    if letters and 0 <= focused < len(letters):
                        exam.submit_answer(letters[focused])
                        focused = 0

        if not timer_frozen and not exam.is_finished():
            if exam.tick(dt):
                screen_ui.trigger_time_up()
                focused = 0

        if exam.is_finished() and last_result == "-":
            outcome = exam.get_result()
            last_result = (f"{'PASS' if outcome.is_passed() else 'FAIL'}  "
                           f"{outcome.get_time_cost_days()}d  "
                           f"+{outcome.get_credits_awarded()}cr  "
                           f"{outcome.get_per_tier_outcome()}")
            print(last_result)

        course = catalog[course_index]
        question = exam.get_current_question() or {}
        screen_ui.render(
            window, course.get_course_code(), course.get_course_name(),
            exam.get_current_tier() or "DONE", exam.get_tier_index(),
            question.get("question_text", "Exam complete - press R or N."),
            question.get("options", {}), focused,
            exam.get_time_remaining(), QUESTION_TIME_LIMIT_SECONDS)

        if exam.is_finished():
            font = load_font(SIZE_ROW)
            window.blit(font.render(last_result, True, CREDIT_HL),
                        (CARD_MARGIN + CONTENT_INSET, SCREEN_H // 2 + 60))

        hint = hint_font.render(
            "A-D pick  |  ENTER submit  |  T freeze timer  |  N next course"
            "  |  R restart  |  F11  |  ESC", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()

    pygame.quit()

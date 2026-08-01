"""
ui/exam_result_screen.py
CSE Life: Compile & Conquer — phase F9  (Feature 8, the verdict)
─────────────────────────────────────────────────────────────
The card the player sees when the third question is answered: did
the exam pass, how each tier went, what it cost in days, and what
it earned in credits.

PASS and FAIL are deliberately, visibly different cards. One accent
colour drives the frame, the corner marks, the rules and the stat
fills (§2.5's one-accent-per-outcome pattern), so the two are told
apart at a glance and not by reading the title.

This file has NO game logic. render() draws what it is handed;
engine/exam_session.py decided all of it. Following
ui/endgame_screen.py (§6.7), the THEME IS PICKED INSIDE from the
title string rather than passed in, so the signature never changes
when the visuals do.

Self-contained by owner ruling (Build Plan §0.5): the palette and
layout constants below are copied verbatim from UI_STYLE_GUIDE.md
§2-§4 rather than imported from another screen.

Ceremonial layout (§4.8), themes + test by Nangiba Tasnim (Dev 3).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pygame

# -------------------------------------------------------------
# PATHS
# -------------------------------------------------------------
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues (§0.5).
PANEL_TAN     = (231, 214, 189)   # screen background behind the card
CARD_TAN      = (240, 228, 208)   # the card fill
HEADER_TAN    = (214, 196, 168)   # neutral stat-box fill
BORDER_BROWN  = (169, 130, 94)    # neutral outlines and separators
TEXT_COFFEE   = (74, 53, 39)      # primary text
CREDIT_HL     = (155, 110, 70)    # emphasised labels
STAT_BROWN    = (140, 110, 85)    # secondary / muted text
TITLE_SLATE   = (60, 70, 85)      # ceremonial title ink (§4.8)

ROW_WHITE     = (247, 243, 236)   # neutral row fill
ROW_GREEN     = (150, 180, 125)   # a correct tier
BAR_RED       = (199, 123, 107)   # a wrong tier
BAR_OVER      = (186, 74, 62)     # FAIL accent (§2.2)
BTN_CONFIRM   = (150, 180, 125)   # PASS accent
HINT_BROWN    = (150, 125, 100)   # the muted hint line

# -------------------------------------------------------------
# THEMES  (§6.7 — one accent per outcome, picked from the title)
# -------------------------------------------------------------
TITLE_PASSED: str = "EXAM PASSED"
TITLE_FAILED: str = "EXAM FAILED"

# `status_value` is shown when the attempt was Q&A-optimized, `status_alt`
# when it was not. On the FAIL card both read BACKLOGGED — a failed exam is
# backlogged however the questions went — so is_optimized changes nothing
# there. Keeping both keys means __draw_stats never sniffs a label string.
THEMES: Dict[str, Dict[str, Any]] = {
    TITLE_PASSED: {
        "accent": BTN_CONFIRM,
        "status_label": "PREPARATION",
        "status_value": "OPTIMIZED",
        "status_alt": "NOT OPTIMIZED",
        "status_fill": ROW_GREEN,
    },
    TITLE_FAILED: {
        "accent": BAR_OVER,
        "status_label": "STATUS",
        "status_value": "BACKLOGGED",
        "status_alt": "BACKLOGGED",
        "status_fill": BAR_RED,
    },
}
# An unrecognised title falls back to the FAIL theme on purpose: a card
# should never celebrate an outcome it could not identify.
DEFAULT_THEME: Dict[str, Any] = THEMES[TITLE_FAILED]

# -------------------------------------------------------------
# LAYOUT  (UI_STYLE_GUIDE §4.8 — the ceremonial card)
# -------------------------------------------------------------
SCREEN_W       = 1280
SCREEN_H       = 720

CARD_MARGIN    = 46         # ceremonial card inset (§4.8)
CARD_PAD       = 18         # gap between card and inner border
CORNER_LEN     = 26         # corner bracket arm length
BORDER_CARD    = 3
BORDER_ROW     = 2

TITLE_Y        = 96         # ceremonial title
SUBTITLE_Y     = 142        # "RESULT - CSE1102"
RULE_TOP_Y     = 176

TIER_Y         = 212        # first per-tier row
TIER_W         = 520        # centred
TIER_H         = 38
TIER_PITCH     = 44
TIER_LABEL_W   = 200        # the EASY / MEDIUM / HARD column

STATS_Y        = 358        # the three stat boxes
STAT_W         = 340
STAT_H         = 88
STAT_GAP       = 30

RULE_BOT_Y     = 486
FLAVOUR_Y      = 516        # first flavour line
FLAVOUR_PITCH  = 28
MAX_FLAVOUR    = 3
HINT_Y         = 620

RULE_HALF      = 300        # half-width of a ceremonial rule (§4.8)
RULE_GAP       = 14         # gap either side of the centre diamond
RULE_DIAMOND   = 7          # diamond half-width

SIZE_TITLE     = 26         # ceremonial title
SIZE_SUB       = 11         # subtitle and hint
SIZE_BODY      = 13         # flavour lines
SIZE_ROW       = 11         # tier rows and stat values
SIZE_LABEL     = 10         # stat captions

TIERS = ("easy", "medium", "hard")

# PressStart2P has NO check or cross glyph — U+2713 and U+2717 both
# render as the same .notdef box (verified). The style guide's ALL-CAPS
# word is the native idiom anyway, and the row's fill colour already
# carries the meaning. Recorded in PHASELOG_F9 §8.
MARK_CORRECT: str = "CORRECT"
MARK_WRONG: str = "WRONG"

_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def load_font(size: int) -> pygame.font.Font:
    """
    Return the pixel font at `size`, cached across the module.

    Falls back to the mandatory Courier substitute so a missing TTF can
    never crash the result card (UI_STYLE_GUIDE §3).
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


class ExamResultScreen:
    """
    Draws the PASS or FAIL card for one finished exam.

    Holds no result state — render() is handed every value, and the
    theme is derived from the title inside, so the same instance draws
    either outcome. The only thing it remembers is whether its entry
    sound has already played, so a per-frame render() cannot retrigger it.
    """

    def __init__(self, audio: Optional[Any] = None) -> None:
        """
        Build the card geometry once.

        `audio` is the optional AudioManager (Build Plan §F1 call-site
        convention): a screen with none injected behaves identically.
        """
        self.__card: pygame.Rect = pygame.Rect(
            CARD_MARGIN, CARD_MARGIN,
            SCREEN_W - CARD_MARGIN * 2, SCREEN_H - CARD_MARGIN * 2)
        self.__audio: Optional[Any] = audio
        self.__sfx_played: bool = False

    # -- geometry ---------------------------------------------
    def get_card_rect(self) -> pygame.Rect:
        """The framed ceremonial card rectangle."""
        return self.__card

    def get_tier_row_rects(self, count: int = 3) -> List[pygame.Rect]:
        """The per-tier row rectangles, top to bottom."""
        left = self.__card.centerx - TIER_W // 2
        return [pygame.Rect(left, self.__card.y + TIER_Y + i * TIER_PITCH,
                            TIER_W, TIER_H)
                for i in range(max(0, int(count)))]

    def get_stat_box_rects(self) -> List[pygame.Rect]:
        """The three stat-box rectangles, left to right."""
        total = STAT_W * 3 + STAT_GAP * 2
        left = self.__card.centerx - total // 2
        return [pygame.Rect(left + i * (STAT_W + STAT_GAP),
                            self.__card.y + STATS_Y, STAT_W, STAT_H)
                for i in range(3)]

    # -- entry ------------------------------------------------
    def enter(self, title: str) -> None:
        """
        Announce the card: fire the pass / fail SFX exactly once.

        Called by the state manager when the screen becomes visible.
        render() never plays sound, because it runs every frame.
        """
        if self.__sfx_played:
            return
        self.__sfx_played = True
        if self.__audio:
            self.__audio.play_sfx(
                "pass" if self.__is_pass(title) else "fail")

    def reset(self) -> None:
        """Re-arm the entry sound, for the next exam."""
        self.__sfx_played = False

    # -- theming ----------------------------------------------
    @staticmethod
    def __is_pass(title: str) -> bool:
        """True when this title names a passing outcome."""
        return str(title).strip().upper() == TITLE_PASSED

    def get_theme(self, title: str) -> Dict[str, Any]:
        """
        The colour theme for a title (§6.7).

        Public so a caller can tint a surrounding transition to match,
        and so the stub test can prove the two cards really differ.
        """
        return THEMES.get(str(title).strip().upper(), DEFAULT_THEME)

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface, title: str = TITLE_FAILED,
               course_code: str = "", per_tier: Any = (),
               time_cost_days: int = 0, credits_awarded: int = 0,
               is_optimized: bool = False,
               flavour_lines: Sequence[str] = ()) -> None:
        """
        Draw the whole result card from handed-in values (§6.1).

        The theme comes from `title`, so this signature stays stable even
        if the two cards are restyled completely.
        """
        theme = self.get_theme(title)
        accent = theme["accent"]

        screen.fill(PANEL_TAN)
        self.__draw_card(screen, accent)

        cx = self.__card.centerx
        self.__blit_centred(screen, load_font(SIZE_TITLE),
                            str(title).upper(), accent, cx,
                            self.__card.y + TITLE_Y)
        self.__blit_centred(screen, load_font(SIZE_SUB),
                            f"RESULT - {str(course_code).upper()}".strip(),
                            CREDIT_HL, cx, self.__card.y + SUBTITLE_Y)
        self.__draw_rule(screen, cx, self.__card.y + RULE_TOP_Y, accent)

        self.__draw_tiers(screen, per_tier)
        self.__draw_stats(screen, theme, time_cost_days, credits_awarded,
                          is_optimized)

        self.__draw_rule(screen, cx, self.__card.y + RULE_BOT_Y, accent)
        self.__draw_flavour(screen, flavour_lines)
        self.__blit_centred(screen, load_font(SIZE_SUB),
                            "PRESS ANY KEY TO CONTINUE", STAT_BROWN, cx,
                            self.__card.y + HINT_Y)

    def __draw_card(self, screen: pygame.Surface,
                    accent: Tuple[int, int, int]) -> None:
        """Ceremonial card: accent frame, inner border, corner marks (§4.8)."""
        pygame.draw.rect(screen, CARD_TAN, self.__card)
        pygame.draw.rect(screen, accent, self.__card, BORDER_CARD)
        inner = self.__card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
        pygame.draw.rect(screen, STAT_BROWN, inner, 1)
        self.__draw_corners(screen, inner, accent)

    def __draw_corners(self, screen: pygame.Surface, rect: pygame.Rect,
                       colour: Tuple[int, int, int]) -> None:
        """Two 3 px arms per corner in the accent — never omitted (§4.2)."""
        n = CORNER_LEN
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((rect.left, rect.top), (n, 0), (0, n)),
                ((rect.right, rect.top), (-n, 0), (0, n)),
                ((rect.left, rect.bottom), (n, 0), (0, -n)),
                ((rect.right, rect.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(screen, colour, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, colour, (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_rule(self, screen: pygame.Surface, cx: int, y: int,
                    colour: Tuple[int, int, int]) -> None:
        """Two 2 px segments with a small centre diamond (§4.8)."""
        pygame.draw.line(screen, colour, (cx - RULE_HALF, y),
                         (cx - RULE_GAP, y), 2)
        pygame.draw.line(screen, colour, (cx + RULE_GAP, y),
                         (cx + RULE_HALF, y), 2)
        pygame.draw.polygon(screen, colour, [
            (cx, y - RULE_DIAMOND + 1), (cx + RULE_DIAMOND, y),
            (cx, y + RULE_DIAMOND - 1), (cx - RULE_DIAMOND, y)])

    def __draw_tiers(self, screen: pygame.Surface, per_tier: Any) -> None:
        """
        One row per tier: EASY / MEDIUM / HARD and how it went.

        Correct rows fill ROW_GREEN, wrong rows BAR_RED — the colour is
        the signal; the word is the confirmation.
        """
        outcomes = self.__resolve_tiers(per_tier)
        rects = self.get_tier_row_rects(len(outcomes))
        font = load_font(SIZE_ROW)
        for (name, is_correct), rect in zip(outcomes, rects):
            pygame.draw.rect(screen, ROW_GREEN if is_correct else BAR_RED,
                             rect)
            pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_ROW)
            split = rect.x + TIER_LABEL_W
            pygame.draw.line(screen, BORDER_BROWN, (split, rect.y),
                             (split, rect.bottom), BORDER_ROW)
            label = font.render(str(name).upper(), True, TEXT_COFFEE)
            screen.blit(label, (rect.x + 14,
                                rect.centery - label.get_height() // 2))
            self.__blit_centred(
                screen, font,
                MARK_CORRECT if is_correct else MARK_WRONG, TEXT_COFFEE,
                (split + rect.right) // 2, rect.centery)

    def __draw_stats(self, screen: pygame.Surface, theme: Dict[str, Any],
                     time_cost_days: int, credits_awarded: int,
                     is_optimized: bool) -> None:
        """Three boxed stats: the time charged, the credits, the status."""
        boxes = self.get_stat_box_rects()
        # The third box is the one that differs most between the two cards,
        # so both its wording and its fill come from the theme.
        status = theme["status_value"] if is_optimized else theme["status_alt"]
        entries = (
            ("TIME COST", f"{int(time_cost_days)} DAYS", HEADER_TAN),
            ("CREDITS", f"+{int(credits_awarded)}", HEADER_TAN),
            (theme["status_label"], status, theme["status_fill"]),
        )
        label_font = load_font(SIZE_LABEL)
        value_font = load_font(SIZE_ROW)
        for (label, value, fill), box in zip(entries, boxes):
            pygame.draw.rect(screen, fill, box)
            pygame.draw.rect(screen, BORDER_BROWN, box, BORDER_ROW)
            self.__blit_centred(screen, label_font, str(label), STAT_BROWN,
                                box.centerx, box.y + 26)
            self.__blit_centred(screen, value_font, str(value), TEXT_COFFEE,
                                box.centerx, box.y + 58)

    def __draw_flavour(self, screen: pygame.Surface,
                       flavour_lines: Sequence[str]) -> None:
        """The closing lines under the bottom rule, centred."""
        font = load_font(SIZE_BODY)
        y = self.__card.y + FLAVOUR_Y
        for line in list(flavour_lines)[:MAX_FLAVOUR]:
            text = str(line).strip()
            if text:
                self.__blit_centred(screen, font, text, TEXT_COFFEE,
                                    self.__card.centerx, y)
            y += FLAVOUR_PITCH

    # -- helpers ----------------------------------------------
    @staticmethod
    def __resolve_tiers(per_tier: Any) -> List[Tuple[str, bool]]:
        """
        Normalise the per-tier outcome into ordered (name, is_correct).

        Accepts the `{"easy": True, ...}` dict ExamResult hands back, or
        a sequence of pairs, so a caller never reshapes for this screen.
        """
        if isinstance(per_tier, dict):
            return [(tier, bool(per_tier.get(tier, False))) for tier in TIERS]
        pairs: List[Tuple[str, bool]] = []
        for entry in (per_tier or ()):
            if isinstance(entry, (tuple, list)) and len(entry) == 2:
                pairs.append((str(entry[0]), bool(entry[1])))
        return pairs

    @staticmethod
    def __blit_centred(screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: Tuple[int, int, int],
                       centre_x: int, centre_y: int) -> None:
        """Draw text centred on a point."""
        rendered = font.render(text, True, colour)
        screen.blit(rendered, (centre_x - rendered.get_width() // 2,
                               centre_y - rendered.get_height() // 2))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   SPACE  -> toggle PASS / FAIL
#   1 / 2  -> vary which tiers were correct
#   F11    -> toggle windowed / fullscreen
#   ESC    -> quit
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (SCREEN_W, SCREEN_H)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Exam result test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    card = ExamResultScreen()

    # (title, per_tier, days, credits, optimized, flavour)
    cases = [
        (TITLE_PASSED, {"easy": True, "medium": True, "hard": True},
         10, 3, True,
         ["Every question answered correctly.",
          "The course is cleared and the credits are yours."]),
        (TITLE_FAILED, {"easy": True, "medium": False, "hard": False},
         14, 0, False,
         ["The medium and hard questions went wrong.",
          "The course returns to next semester's catalog."]),
        (TITLE_FAILED, {"easy": False, "medium": False, "hard": False},
         14, 0, False,
         ["Every question timed out.",
          "Read the material before the retake."]),
    ]
    index = 0
    card.enter(cases[index][0])

    running = True
    while running:
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
                elif event.key == pygame.K_SPACE:
                    index = (index + 1) % len(cases)
                    card.reset()
                    card.enter(cases[index][0])

        title, per_tier, days, credits_, optimized, flavour = cases[index]
        card.render(window, title, "CSE1102", per_tier, days, credits_,
                    optimized, flavour)

        hint = hint_font.render(
            "SPACE next case  |  F11 fullscreen  |  ESC quit",
            True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

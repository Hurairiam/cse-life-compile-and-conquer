"""
ui/certificate_screen.py
CSE Life: Compile & Conquer — phase F11  (Feature 9, certification)
─────────────────────────────────────────────────────────────
The diploma. The last artefact of a run: who finished, what they
finished with, and what they learned on the way.

It is NOT a second endgame screen. `ui/endgame_screen.py` already
renders all four epilogues and `engine/endgame_manager.py` already
routes them; the owner ruled both done and untouchable (Build Plan
§F11). This file adds only the certificate, which existed nowhere,
and it sits BESIDE the epilogue rather than replacing it:

    EndgameScreen     the ending, the epilogue prose, the verdict
    CertificateScreen the record — name, degree, ledger, transcript

The two agree by mirroring, not by sharing. The four ending titles
and the accent each one carries are duplicated into this file's own
THEMES table, exactly as §0.5 requires of every new UI file, and the
accent is chosen INSIDE render() from the title so the signature
never changes when the visuals do (§6.7). If a value here ever
disagrees with `ui/endgame_screen.py`, the style guide wins.

This file has NO game logic. Every number it draws is a parameter —
it never reads a Player, a SkillTree or an EndgameEvaluationManager,
and it decides nothing except which of four accents to use and how
wide a bar is.

Layout + test by Nangiba Tasnim (Dev 3).
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
SEAL_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui",
                              "icon_certificate.png")

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues, and nothing
# imported from another screen (Build Plan §0.5) — this file runs with
# no other new screen present.
PANEL_TAN     = (231, 214, 189)   # screen background behind the card
CARD_TAN      = (240, 228, 208)   # the diploma panel, lighter than the bg
TEXT_COFFEE   = (74, 53, 39)      # primary text on tan
STAT_BROWN    = (140, 110, 85)    # secondary / muted text on tan
BAR_TRACK_TAN = (222, 208, 186)   # stat-box fill and bar track, in-card
ROW_WHITE     = (247, 243, 236)   # a transcript row
PLACEHOLDER   = (196, 178, 150)   # square where the seal PNG is missing
HINT_BROWN    = (150, 125, 100)   # stub-test hint line only

DARK_BG       = (18, 16, 22)      # §2.4 prestige theme — TOP GRADUATE only
DARK_CARD     = (28, 26, 34)
DARK_TEXT     = (225, 220, 210)
DARK_STAT     = (150, 145, 155)
BAR_TRACK_DK  = (52, 48, 60)
DARK_ROW      = (44, 41, 52)      # a transcript row on the dark theme

# §2.5 — one accent per ending, the same four `ui/endgame_screen.py`
# uses. Duplicated deliberately (§0.5); the style guide is the source.
ACCENT_GOLD   = (255, 215, 90)
ACCENT_BRONZE = (170, 120, 60)
ACCENT_SLATE  = (45, 58, 71)
ACCENT_RED    = (160, 90, 80)

# -------------------------------------------------------------
# THE FOUR ENDINGS
# -------------------------------------------------------------
# These four strings are canonical. They are the keys in
# ui/endgame_screen.py::THEMES, content/epilogue_text.py::EPILOGUE_TEXT
# and engine/endgame_manager.py::determine_ending_title().
#
# KNOWN PRE-EXISTING MISMATCH — do not "fix" either content file:
# content/dialogues.py::EPILOGUE_TEXTS spells the two drop-out keys
# "DROP OUT with Strong Skills" / "DROP OUT with Weak Skills". main.py
# already flags that as an unresolved content-ownership question. This
# screen follows the canonical no-"with" form, and falls back to the
# default theme for anything it does not recognise — so the misspelled
# form renders as a bronze certificate rather than crashing.
# Restated in PHASELOG_F11 §8.
# -------------------------------------------------------------
TITLE_TOP: str = "TOP GRADUATE"
TITLE_AVERAGE: str = "AVERAGE GRADUATE"
TITLE_DROPOUT_STRONG: str = "DROP OUT Strong Skills"
TITLE_DROPOUT_WEAK: str = "DROP OUT Weak Skills"

ENDING_TITLES: Tuple[str, ...] = (TITLE_TOP, TITLE_AVERAGE,
                                  TITLE_DROPOUT_STRONG, TITLE_DROPOUT_WEAK)

# `award` decides the heading: a degree earns a CERTIFICATE, a run that
# ended early earns a RECORD OF ATTENDANCE. That is a real distinction,
# not a euphemism — the drop-out tiers get an honest document rather
# than a consolation certificate.
THEMES: Dict[str, Dict[str, Any]] = {
    TITLE_TOP: {
        "bg": DARK_BG, "card": DARK_CARD, "accent": ACCENT_GOLD,
        "body": DARK_TEXT, "stat": DARK_STAT, "track": BAR_TRACK_DK,
        "row": DARK_ROW, "award": True,
        "subtitle": "CONFERRED WITH DISTINCTION",
    },
    TITLE_AVERAGE: {
        "bg": PANEL_TAN, "card": CARD_TAN, "accent": ACCENT_BRONZE,
        "body": TEXT_COFFEE, "stat": STAT_BROWN, "track": BAR_TRACK_TAN,
        "row": ROW_WHITE, "award": True,
        "subtitle": "DEGREE CONFERRED",
    },
    TITLE_DROPOUT_STRONG: {
        "bg": PANEL_TAN, "card": CARD_TAN, "accent": ACCENT_SLATE,
        "body": TEXT_COFFEE, "stat": STAT_BROWN, "track": BAR_TRACK_TAN,
        "row": ROW_WHITE, "award": False,
        "subtitle": "NO DEGREE AWARDED",
    },
    TITLE_DROPOUT_WEAK: {
        "bg": PANEL_TAN, "card": CARD_TAN, "accent": ACCENT_RED,
        "body": TEXT_COFFEE, "stat": STAT_BROWN, "track": BAR_TRACK_TAN,
        "row": ROW_WHITE, "award": False,
        "subtitle": "NO DEGREE AWARDED",
    },
}
DEFAULT_THEME: Dict[str, Any] = THEMES[TITLE_AVERAGE]

HEADING_AWARD: str = "CERTIFICATE OF COMPLETION"
HEADING_RECORD: str = "RECORD OF ATTENDANCE"
CERTIFIES_LINE: str = "THIS CERTIFIES THAT"
DEGREE_LINE: str = "BACHELOR OF SCIENCE IN COMPUTER SCIENCE & ENGINEERING"
CONTINUE_HINT: str = "PRESS ANY KEY TO CONTINUE"

# Game-rule figures (IMPLEMENTATION_PLAN §3) — defaults only; the caller
# hands in the real numbers. Never retuned here.
CREDIT_GOAL_DEFAULT: int = 140
DAY_CAP_DEFAULT: int = 960
SKILL_MAX_DEFAULT: int = 10

# -------------------------------------------------------------
# LAYOUT  (UI_STYLE_GUIDE §4 — fixed pixel constants)
# -------------------------------------------------------------
SCREEN_W = 1280
SCREEN_H = 720

CARD_MARGIN  = 46           # ceremonial inset (§4.2)
CARD_PAD     = 18
CORNER_LEN   = 26
BORDER_CARD  = 3            # the outer frame
BORDER_INNER = 1            # the inner frame — both in the accent (§F11)
BORDER_ROW   = 2

# Every Y below is measured from the CARD's top edge, so the whole
# document moves together if the margin is ever retuned.
TITLE_Y        = 40
SUBTITLE_Y     = 76
RULE_TOP_Y     = 104
CERTIFIES_Y    = 132
NAME_Y         = 156
STUDENT_Y      = 200
DEGREE_Y       = 226
RULE_MID_Y     = 254

STATS_Y        = 274
STAT_W         = 340
STAT_H         = 76
STAT_GAP       = 20
STAT_LABEL_Y   = 14         # from the stat box top
STAT_DIVIDER_Y = 38
STAT_VALUE_Y   = 50

TRANSCRIPT_LABEL_Y = 372
TRANSCRIPT_Y   = 394
TRANSCRIPT_X   = 46         # from the card's left edge
COL_W          = 470
COL_GAP        = 32
ROW_H          = 26
ROW_PITCH      = 30
ROWS_PER_COL   = 5          # 2 columns x 5 = 10 skills fit above the seal
SKILL_LABEL_W  = 250        # label column inside a transcript row
SKILL_VALUE_W  = 96         # the "LEVEL n" column
SKILL_BAR_H    = 8
MORE_Y         = 554         # clear of the last transcript row
RULE_BOT_Y     = 576         # the closing rule, above the seal and hint

SEAL_SIZE      = 96
SEAL_INSET     = 26         # gap from the inner border to the seal
SEAL_BORDER    = 3

HINT_Y         = 596
HINT_PAD_X     = 16         # click padding around the continue hint
HINT_PAD_Y     = 10

RULE_HALF      = 300        # §4.8 rule: two segments + a centre diamond
RULE_GAP       = 14
RULE_DIAMOND   = 7
RULE_W         = 2

SIZE_NAME      = 28         # §3 — the one 28 on the screen
SIZE_NAME_FIT  = 16         # what a very long name falls back to
SIZE_TITLE     = 26
SIZE_VALUE     = 16
SIZE_BODY      = 13
SIZE_SUB       = 11
SIZE_LABEL     = 10

_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def load_font(size: int) -> pygame.font.Font:
    """
    Return the pixel font at `size`, cached across the module.

    Falls back to the mandatory Courier substitute so a missing TTF can
    never crash the screen (UI_STYLE_GUIDE §3).
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


def format_money(amount: float) -> str:
    """BDT the §7 way: thousands commas, no decimals — `48,200 BDT`."""
    return f"{float(amount):,.0f} BDT"


class CertificateScreen:
    """
    Draws the graduation certificate — or, for a run that ended early,
    the record of attendance.

    Holds no player state: every value arrives through render(). The
    only things it remembers are the card geometry, the seal surface and
    whether its entry sound has already played, so a per-frame render()
    cannot retrigger the sound.
    """

    def __init__(self, audio: Optional[Any] = None) -> None:
        """
        Build the card geometry once and arm the entry sound.

        `audio` is the optional AudioManager (Build Plan §F1 call-site
        convention): a screen with none injected behaves identically.
        """
        self.__card: pygame.Rect = pygame.Rect(
            CARD_MARGIN, CARD_MARGIN,
            SCREEN_W - CARD_MARGIN * 2, SCREEN_H - CARD_MARGIN * 2)
        self.__seal: Optional[pygame.Surface] = None
        self.__seal_loaded: bool = False
        self.__audio: Optional[Any] = audio
        self.__sfx_played: bool = False

    # -- geometry ---------------------------------------------
    def get_card_rect(self) -> pygame.Rect:
        """The framed diploma card."""
        return self.__card

    def get_inner_rect(self) -> pygame.Rect:
        """The inner frame — everything drawn stays inside it."""
        return self.__card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)

    def get_stat_box_rects(self) -> List[pygame.Rect]:
        """The three ledger boxes, left to right."""
        total = STAT_W * 3 + STAT_GAP * 2
        left = self.__card.centerx - total // 2
        return [pygame.Rect(left + index * (STAT_W + STAT_GAP),
                            self.__card.y + STATS_Y, STAT_W, STAT_H)
                for index in range(3)]

    def get_transcript_row_rects(self, count: int) -> List[pygame.Rect]:
        """
        The transcript row rectangles, filling column one top-to-bottom
        before column two — a reader's order, not a spreadsheet's.
        """
        rects: List[pygame.Rect] = []
        left = self.__card.x + TRANSCRIPT_X
        for index in range(max(0, int(count))):
            column, row = divmod(index, ROWS_PER_COL)
            rects.append(pygame.Rect(
                left + column * (COL_W + COL_GAP),
                self.__card.y + TRANSCRIPT_Y + row * ROW_PITCH,
                COL_W, ROW_H))
        return rects

    def get_seal_rect(self) -> pygame.Rect:
        """The square the certification seal is stamped in."""
        inner = self.get_inner_rect()
        return pygame.Rect(inner.right - SEAL_INSET - SEAL_SIZE,
                           inner.bottom - SEAL_INSET - SEAL_SIZE,
                           SEAL_SIZE, SEAL_SIZE)

    def get_continue_rect(self) -> pygame.Rect:
        """
        The clickable region around the continue hint.

        The hint is text rather than a 44 px button because §4.8's
        ceremonial layout ends on a hint line, not a control — so the
        text's own box is padded out to a comfortable target. A caller
        that would rather accept a click anywhere reads get_card_rect().
        """
        font = load_font(SIZE_LABEL)
        width, height = font.size(CONTINUE_HINT)
        return pygame.Rect(self.__card.centerx - width // 2 - HINT_PAD_X,
                           self.__card.y + HINT_Y - HINT_PAD_Y,
                           width + HINT_PAD_X * 2, height + HINT_PAD_Y * 2)

    # -- entry ------------------------------------------------
    def enter(self, ending_title: str = TITLE_AVERAGE) -> None:
        """
        Announce the certificate: fire its entry SFX exactly once.

        `confirm` for every ending, and `level_up` instead on the TOP
        GRADUATE branch — the one run that earned a flourish. Called by
        the state manager when the screen becomes visible; render()
        never plays sound, because it runs sixty times a second.
        """
        if self.__sfx_played:
            return
        self.__sfx_played = True
        if self.__audio:
            self.__audio.play_sfx(
                "level_up" if self.__is_top(ending_title) else "confirm")

    def reset(self) -> None:
        """Re-arm the entry sound, for the next run."""
        self.__sfx_played = False

    # -- theming ----------------------------------------------
    @staticmethod
    def __is_top(ending_title: str) -> bool:
        """True when this title names the distinction ending."""
        return str(ending_title).strip() == TITLE_TOP

    def get_theme(self, ending_title: str) -> Dict[str, Any]:
        """
        The colour theme for an ending title (§6.7).

        Public so a caller can tint a surrounding transition to match,
        and so the stub test can prove the four documents really differ.
        Unknown titles fall back to the AVERAGE GRADUATE theme, mirroring
        `ui/endgame_screen.py::DEFAULT_THEME` — including the misspelled
        `"DROP OUT with ..."` keys still living in content/dialogues.py.
        """
        return THEMES.get(str(ending_title).strip(), DEFAULT_THEME)

    def get_heading(self, ending_title: str, is_graduated: bool) -> str:
        """
        `CERTIFICATE OF COMPLETION`, or `RECORD OF ATTENDANCE`.

        Both the ending title AND the handed-in graduation flag must
        agree before a certificate is issued. The conservative reading is
        deliberate: if a caller passes a graduate title with
        `is_graduated=False`, the honest document is the attendance
        record, not a certificate this screen talked itself into.

        The literal `DROP OUT` prefix is also checked, so the misspelled
        `"DROP OUT with ..."` keys still living in content/dialogues.py
        can never produce a document headed CERTIFICATE OF COMPLETION on
        the strength of falling back to the default theme. Guarding here
        is not the same as fixing the content file, which §F11 forbids.
        """
        title = str(ending_title).strip()
        if title.upper().startswith("DROP OUT"):
            return HEADING_RECORD
        return HEADING_AWARD if (self.get_theme(title)["award"]
                                 and bool(is_graduated)) else HEADING_RECORD

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface,
               ending_title: str = TITLE_AVERAGE,
               player_name: str = "", student_id: str = "",
               credits: int = 0, credit_goal: int = CREDIT_GOAL_DEFAULT,
               days_used: int = 0, day_cap: int = DAY_CAP_DEFAULT,
               wallet: float = 0.0, skills: Any = (),
               is_graduated: bool = False) -> None:
        """
        Draw the whole certificate from handed-in values (§6.1).

        ending_title : one of the four canonical strings; anything else
                       falls back to the AVERAGE GRADUATE theme
        player_name  : shrinks from size 28 to 16, then truncates
        student_id   : drawn under the name; blank is fine
        credits      : credits earned, against `credit_goal` (140)
        days_used    : career days spent, against `day_cap` (960)
        wallet       : final balance in BDT
        skills       : `{skill_id: level}` — what a SkillTree exposes —
                       or a sequence of (label, level, max_level) rows.
                       Levels below 1 are left off the transcript; a
                       skill never practised is not a line on a diploma.
                       ORDER IS THE CALLER'S: rows are drawn in the order
                       handed in, so the caller decides what leads.
        is_graduated : gates the heading; see get_heading()
        """
        theme = self.get_theme(ending_title)
        rows = self.__resolve_skills(skills)
        centre = self.__card.centerx

        screen.fill(theme["bg"])
        self.__draw_card(screen, theme)

        self.__blit_centred(screen, load_font(SIZE_TITLE),
                            self.get_heading(ending_title, is_graduated),
                            theme["accent"], centre,
                            self.__card.y + TITLE_Y)
        self.__blit_centred(
            screen, load_font(SIZE_SUB),
            f"{str(ending_title).upper()}  --  {theme['subtitle']}",
            theme["stat"], centre, self.__card.y + SUBTITLE_Y)

        self.__draw_rule(screen, centre, self.__card.y + RULE_TOP_Y,
                         theme["accent"])
        self.__draw_identity(screen, theme, player_name, student_id)
        self.__draw_rule(screen, centre, self.__card.y + RULE_MID_Y,
                         theme["accent"])
        self.__draw_ledger(screen, theme, credits, credit_goal, days_used,
                           day_cap, wallet)
        self.__draw_transcript(screen, theme, rows)
        self.__draw_rule(screen, centre, self.__card.y + RULE_BOT_Y,
                         theme["accent"])
        self.__draw_seal(screen, theme)
        self.__blit_centred(screen, load_font(SIZE_LABEL), CONTINUE_HINT,
                            theme["stat"], centre, self.__card.y + HINT_Y)

    # -- piece-by-piece drawing -------------------------------
    def __draw_card(self, screen: pygame.Surface,
                    theme: Dict[str, Any]) -> None:
        """
        The DOUBLE frame that makes this read as a diploma rather than
        as one more card: a 3 px outer border and a 1 px inner border,
        both in the accent, with the corner brackets on the inner one
        (§4.2 — the franchise signature is never omitted).
        """
        pygame.draw.rect(screen, theme["card"], self.__card)
        pygame.draw.rect(screen, theme["accent"], self.__card, BORDER_CARD)
        inner = self.get_inner_rect()
        pygame.draw.rect(screen, theme["accent"], inner, BORDER_INNER)

        n = CORNER_LEN
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((inner.left, inner.top), (n, 0), (0, n)),
                ((inner.right, inner.top), (-n, 0), (0, n)),
                ((inner.left, inner.bottom), (n, 0), (0, -n)),
                ((inner.right, inner.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(screen, theme["accent"], (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, theme["accent"], (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_rule(self, screen: pygame.Surface, centre_x: int, y: int,
                    colour: Tuple[int, int, int]) -> None:
        """
        A §4.8 horizontal rule: two 2 px segments with a 14 px centre gap
        holding a 7 px half-width diamond.
        """
        pygame.draw.line(screen, colour, (centre_x - RULE_HALF, y),
                         (centre_x - RULE_GAP, y), RULE_W)
        pygame.draw.line(screen, colour, (centre_x + RULE_GAP, y),
                         (centre_x + RULE_HALF, y), RULE_W)
        pygame.draw.polygon(screen, colour, [
            (centre_x, y - RULE_DIAMOND + 1), (centre_x + RULE_DIAMOND, y),
            (centre_x, y + RULE_DIAMOND - 1), (centre_x - RULE_DIAMOND, y)])

    def __draw_identity(self, screen: pygame.Surface, theme: Dict[str, Any],
                        player_name: str, student_id: str) -> None:
        """The dedication block: who this document is about."""
        centre = self.__card.centerx
        self.__blit_centred(screen, load_font(SIZE_LABEL), CERTIFIES_LINE,
                            theme["stat"], centre,
                            self.__card.y + CERTIFIES_Y)

        inner = self.get_inner_rect()
        name = str(player_name).strip().upper() or "UNNAMED STUDENT"
        font = self.__fit_font(name, (SIZE_NAME, SIZE_NAME_FIT),
                               inner.w - 80)
        self.__blit_centred(screen, font,
                            self.__truncate(name, font, inner.w - 80),
                            theme["accent"], centre, self.__card.y + NAME_Y)

        if str(student_id).strip():
            self.__blit_centred(screen, load_font(SIZE_SUB),
                                f"STUDENT ID  {str(student_id).upper()}",
                                theme["stat"], centre,
                                self.__card.y + STUDENT_Y)
        self.__blit_centred(screen, load_font(SIZE_SUB), DEGREE_LINE,
                            theme["body"], centre, self.__card.y + DEGREE_Y)

    def __draw_ledger(self, screen: pygame.Surface, theme: Dict[str, Any],
                      credits: int, credit_goal: int, days_used: int,
                      day_cap: int, wallet: float) -> None:
        """
        The three ledger boxes, §7 number formats throughout:
        `140 / 140`, `936 / 960 DAYS`, `48,200 BDT`.
        """
        entries = (
            ("CREDITS EARNED", f"{int(credits)} / {int(credit_goal)}"),
            ("DURATION", f"{int(days_used)} / {int(day_cap)} DAYS"),
            ("FINAL BALANCE", format_money(wallet)),
        )
        for rect, (label, value) in zip(self.get_stat_box_rects(), entries):
            self.__draw_stat_box(screen, theme, rect, label, value)

    def __draw_stat_box(self, screen: pygame.Surface, theme: Dict[str, Any],
                        rect: pygame.Rect, label: str, value: str) -> None:
        """
        One §4.8 stat box: track-coloured fill, 1 px outline, a 1 px
        divider, and a label-over-value pair.
        """
        pygame.draw.rect(screen, theme["track"], rect)
        pygame.draw.rect(screen, theme["stat"], rect, 1)
        pygame.draw.line(screen, theme["stat"],
                         (rect.x + 12, rect.y + STAT_DIVIDER_Y),
                         (rect.right - 12, rect.y + STAT_DIVIDER_Y), 1)
        self.__blit_centred(screen, load_font(SIZE_LABEL), label,
                            theme["stat"], rect.centerx,
                            rect.y + STAT_LABEL_Y)
        self.__blit_centred(screen, load_font(SIZE_VALUE), value,
                            theme["body"], rect.centerx,
                            rect.y + STAT_VALUE_Y)

    def __draw_transcript(self, screen: pygame.Surface,
                          theme: Dict[str, Any],
                          rows: Sequence[Tuple[str, int, int]]) -> None:
        """
        Every practised skill as a row: label, `LEVEL n`, and a mini-bar
        (§4.4 table styling, §4.5 bar).

        Ten rows fit above the seal; a longer transcript is SUMMARISED
        rather than pushed off the card, because a diploma with text
        running past its own frame is worse than a diploma that says
        there was more.
        """
        centre = self.__card.centerx
        self.__blit_centred(screen, load_font(SIZE_LABEL),
                            "SKILLS TRANSCRIPT", theme["accent"], centre,
                            self.__card.y + TRANSCRIPT_LABEL_Y)

        capacity = ROWS_PER_COL * 2
        shown = list(rows[:capacity])
        if not shown:
            self.__blit_centred(
                screen, load_font(SIZE_SUB), "NO SKILLS RECORDED",
                theme["stat"], centre, self.__card.y + TRANSCRIPT_Y + 8)
            return

        font = load_font(SIZE_LABEL)
        for (label, level, ceiling), rect in zip(
                shown, self.get_transcript_row_rects(len(shown))):
            pygame.draw.rect(screen, theme["row"], rect)
            pygame.draw.rect(screen, theme["accent"], rect, BORDER_ROW)
            split = rect.x + SKILL_LABEL_W
            pygame.draw.line(screen, theme["accent"], (split, rect.y),
                             (split, rect.bottom), BORDER_ROW)

            text = self.__truncate(str(label).upper(), font,
                                   SKILL_LABEL_W - 16)
            rendered = font.render(text, True, theme["body"])
            screen.blit(rendered, (rect.x + 8,
                                   rect.centery - rendered.get_height() // 2))
            value = font.render(f"LEVEL {int(level)}", True, theme["accent"])
            screen.blit(value, (split + 10,
                                rect.centery - value.get_height() // 2))
            track = pygame.Rect(split + SKILL_VALUE_W,
                                rect.centery - SKILL_BAR_H // 2,
                                rect.right - (split + SKILL_VALUE_W) - 12,
                                SKILL_BAR_H)
            self.__draw_bar(screen, theme, track, level, ceiling)

        remaining = len(rows) - len(shown)
        if remaining > 0:
            self.__blit_centred(
                screen, load_font(SIZE_LABEL),
                f"+ {remaining} MORE SKILL(S) ON RECORD", theme["stat"],
                centre, self.__card.y + MORE_Y)

    def __draw_bar(self, screen: pygame.Surface, theme: Dict[str, Any],
                   track: pygame.Rect, value: int, ceiling: int) -> None:
        """A §4.5 bar: track, fill from the left clamped to 1.0, outline."""
        if track.w <= 0:
            return
        pygame.draw.rect(screen, theme["track"], track)
        limit = max(1, int(ceiling))
        ratio = min(max(float(value) / limit, 0.0), 1.0)
        filled = int(track.w * ratio)
        if filled > 0:
            pygame.draw.rect(screen, theme["accent"],
                             pygame.Rect(track.x, track.y, filled, track.h))
        pygame.draw.rect(screen, theme["stat"], track, 1)

    def __draw_seal(self, screen: pygame.Surface,
                    theme: Dict[str, Any]) -> None:
        """
        The certification seal, framed like a portrait (§4.9) so a
        missing PNG still leaves a deliberate-looking stamp.
        """
        box = self.get_seal_rect()
        # [ICON PLACEHOLDER: assets/ui/icon_certificate.png -- certification
        #  seal, 96x96. Missing today, so every certificate stamps the
        #  PLACEHOLDER square with a faded label (Style Guide §5.2/§5.3).]
        seal = self.__get_seal()
        if seal is not None:
            screen.blit(seal, box.topleft)
        else:
            pygame.draw.rect(screen, PLACEHOLDER, box)
            label = load_font(SIZE_LABEL).render("SEAL", True, STAT_BROWN)
            screen.blit(label, (box.centerx - label.get_width() // 2,
                                box.centery - label.get_height() // 2))
        pygame.draw.rect(screen, theme["accent"], box, SEAL_BORDER)

    # -- loading + normalising --------------------------------
    def __get_seal(self) -> Optional[pygame.Surface]:
        """
        Load the seal once, scaled to its box.

        A failed load is remembered as None, so a missing PNG costs one
        failed open per session rather than one per frame.
        """
        if self.__seal_loaded:
            return self.__seal
        self.__seal_loaded = True
        try:
            image = pygame.image.load(SEAL_PATH)
            image = image.convert_alpha() if pygame.display.get_init() \
                else image
            self.__seal = pygame.transform.scale(image,
                                                 (SEAL_SIZE, SEAL_SIZE))
        except (FileNotFoundError, OSError, pygame.error):
            self.__seal = None
        return self.__seal

    @staticmethod
    def __resolve_skills(skills: Any) -> List[Tuple[str, int, int]]:
        """
        Normalise the skills argument into (label, level, max_level) rows,
        dropping anything below level 1.

        Accepts a `{skill_id: level}` map — what a SkillTree exposes —
        with ids prettified for display, or a ready sequence of triples,
        so a caller never reshapes data for this screen's convenience.
        The order handed in is preserved; this screen does not rank.
        """
        rows: List[Tuple[str, int, int]] = []
        if isinstance(skills, dict):
            for key, value in skills.items():
                try:
                    level = int(value)
                except (TypeError, ValueError):
                    continue
                if level >= 1:
                    rows.append((str(key).replace("_", " "), level,
                                 SKILL_MAX_DEFAULT))
            return rows
        for entry in (skills or ()):
            if not isinstance(entry, (tuple, list)) or len(entry) < 2:
                continue
            try:
                level = int(entry[1])
                ceiling = int(entry[2]) if len(entry) > 2 \
                    else SKILL_MAX_DEFAULT
            except (TypeError, ValueError):
                continue
            if level >= 1:
                rows.append((str(entry[0]), level, ceiling))
        return rows

    @staticmethod
    def __fit_font(text: str, sizes: Sequence[int],
                   max_px: int) -> pygame.font.Font:
        """
        The largest of `sizes` at which `text` still fits `max_px`.

        A long name shrinks one step rather than being cut immediately —
        somebody's name is the one thing on this document that should
        not be abbreviated if it can be avoided.
        """
        chosen = load_font(sizes[-1])
        for size in sizes:
            font = load_font(size)
            if font.size(text)[0] <= max_px:
                return font
            chosen = font
        return chosen

    @staticmethod
    def __truncate(text: str, font: pygame.font.Font, max_px: int) -> str:
        """Shorten `text` with an ellipsis until it fits `max_px`."""
        if max_px <= 0 or font.size(text)[0] <= max_px:
            return text
        cut = len(text)
        while cut > 0 and font.size(text[:cut] + "...")[0] > max_px:
            cut -= 1
        return text[:cut] + "..." if cut > 0 else ""

    @staticmethod
    def __blit_centred(screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: Tuple[int, int, int],
                       centre_x: int, y: int) -> None:
        """Draw a line of text horizontally centred on `centre_x`."""
        surface = font.render(text, True, colour)
        screen.blit(surface, (centre_x - surface.get_width() // 2, y))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see all four documents.
# Abu Huraira removes this block when he plugs in the real game.
#   SPACE / any key -> next ending title (all four cycle)
#   S               -> cycle the transcript: full / sparse / empty / long
#   F11             -> toggle windowed / fullscreen
#   ESC             -> quit
#
# The skills come from a REAL core/skill_tree.py SkillTree stocked with
# increment_skill() calls over the 12 canonical ids, read back through
# get_skill_level() -- no fake skill store. Labels come from
# content/skill_tree_layout.py, which is keyed by those same 12 ids.
#
# assets/ui/icon_certificate.png does not exist, so every run also
# proves the §5.2 placeholder path: the seal stamps as a PLACEHOLDER
# square and nothing crashes.
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, PROJECT_ROOT)
    # Imported HERE, inside the runner: the class above imports nothing
    # from core/ or content/, so ui/ keeps its one-way dependency.
    from content.skill_tree_layout import NODE_ORDER, SKILL_NODES
    from core.skill_tree import SkillTree

    pygame.init()

    SIZE = (SCREEN_W, SCREEN_H)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Certificate screen test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    certificate = CertificateScreen()

    def stock_tree(pattern: str) -> SkillTree:
        """A real SkillTree filled in one of three shapes."""
        tree = SkillTree()
        if pattern == "sparse":
            for skill_id, level in (("programming_language", 4),
                                    ("dsa", 2), ("git", 1)):
                tree.increment_skill(skill_id, level)
        elif pattern == "long":
            for index, skill_id in enumerate(NODE_ORDER):
                tree.increment_skill(skill_id, 1 + index % 9)
        elif pattern == "full":
            for index, skill_id in enumerate(NODE_ORDER[:8]):
                tree.increment_skill(skill_id, 3 + index % 7)
        return tree

    def transcript_rows(tree: SkillTree) -> list:
        """
        (label, level, max_level) triples in canonical node order.

        The screen filters level 0 out itself; handing everything in
        proves that, and proves the display names really come from
        content/skill_tree_layout.py rather than from prettified ids.
        """
        return [(SKILL_NODES[skill_id]["display_name"],
                 tree.get_skill_level(skill_id),
                 SKILL_NODES[skill_id]["max_level"])
                for skill_id in NODE_ORDER]

    # (title, name, student id, credits, days used, wallet, graduated)
    RUNS = (
        (TITLE_TOP, "Nangiba Tasnim", "CSE-2021-0148", 140, 936, 48200.0,
         True),
        (TITLE_AVERAGE, "Abu Huraira", "CSE-2021-0072", 140, 958, 9400.0,
         True),
        (TITLE_DROPOUT_STRONG, "Saif Rahman", "CSE-2021-0311", 96, 960,
         31500.0, False),
        (TITLE_DROPOUT_WEAK, "Ayesha Saheba Mostofa", "CSE-2021-0205", 62,
         960, 1200.0, False),
    )
    PATTERNS = ("full", "sparse", "empty", "long")

    run_index = 0
    pattern_index = 0
    trees = {name: stock_tree(name) for name in PATTERNS}

    running = True
    while running:
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
                elif event.key == pygame.K_s:
                    pattern_index = (pattern_index + 1) % len(PATTERNS)
                else:
                    run_index = (run_index + 1) % len(RUNS)
                    certificate.reset()
                    certificate.enter(RUNS[run_index][0])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if certificate.get_continue_rect().collidepoint(event.pos):
                    run_index = (run_index + 1) % len(RUNS)

        title, name, student, credits_, days, money, graduated = \
            RUNS[run_index]
        pattern = PATTERNS[pattern_index]
        certificate.render(window, ending_title=title, player_name=name,
                           student_id=student, credits=credits_,
                           credit_goal=CREDIT_GOAL_DEFAULT, days_used=days,
                           day_cap=DAY_CAP_DEFAULT, wallet=money,
                           skills=transcript_rows(trees[pattern]),
                           is_graduated=graduated)

        hint = hint_font.render(
            f"[{pattern} transcript]  any key = next ending  |  "
            "S transcript  |  F11 fullscreen  |  ESC quit",
            True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

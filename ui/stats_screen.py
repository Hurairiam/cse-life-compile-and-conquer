"""
ui/stats_screen.py
CSE Life: Compile & Conquer — phase F10  (Feature 7, the profile)
─────────────────────────────────────────────────────────────
The player profile and transcript: who they are on the left, the
three resource gauges in the middle, every tracked skill on the
right, and the academic ledger along the bottom.

This file has NO game logic. Every number it draws is a parameter
(§6.1) — it never reads a Player, an AcademicHistory or a
SkillTree, and it computes nothing except the fill width of a bar.

Gauge colours reuse the §2.2 traffic light rather than inventing
one: the day pool is green above 30, amber 16-30 and red at or
under the 15-day firewall, which is a GAME RULE and not a styling
choice.

Self-contained by owner ruling (Build Plan §0.5): the palette and
layout constants below are copied verbatim from UI_STYLE_GUIDE.md
§2-§4 rather than imported from another screen.

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
PORTRAIT_PATH: str = os.path.join(PROJECT_ROOT, "assets", "portraits",
                                  "player_id.png")

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues (§0.5).
PANEL_TAN     = (231, 214, 189)   # screen background behind the card
CARD_TAN      = (240, 228, 208)   # the card fill
HEADER_TAN    = (214, 196, 168)   # section headers, neutral buttons
BORDER_BROWN  = (169, 130, 94)    # every outline and separator
TEXT_COFFEE   = (74, 53, 39)      # primary text
CREDIT_HL     = (155, 110, 70)    # emphasised labels
STAT_BROWN    = (140, 110, 85)    # secondary / muted text
BAR_TRACK     = (222, 208, 186)   # empty part of a bar (in-card)

ROW_WHITE     = (247, 243, 236)   # a skill row
ROW_BLUE      = (120, 150, 190)   # under-limit progress fill

BAR_GREEN     = (167, 185, 133)   # days safe    (> 30)
BAR_AMBER     = (217, 169, 106)   # days low     (16-30)
BAR_RED       = (199, 123, 107)   # days at the firewall (<= 15); backlog rows

PORTRAIT_BG    = (255, 255, 255)  # white behind the photo (§4.9)
PORTRAIT_FILL  = (190, 165, 135)  # placeholder block when the photo is gone
PORTRAIT_LABEL = (120, 95, 75)    # the faded "PHOTO" caption
HINT_BROWN     = (150, 125, 100)  # stub-test hint line only

# -------------------------------------------------------------
# LAYOUT  (UI_STYLE_GUIDE §4 — fixed pixel constants)
# -------------------------------------------------------------
SCREEN_W       = 1280
SCREEN_H       = 720

CARD_MARGIN    = 24         # dense-screen card inset (§4.2)
CARD_PAD       = 14
CORNER_LEN     = 22
BORDER_CARD    = 3
BORDER_ROW     = 2

TITLE_Y        = 40
CONTENT_Y      = 96         # top of all three columns, from the card top

LEFT_X         = 46         # identity column, from the card left
PORTRAIT_SIZE  = 150        # §4.9 allows 150-230
PORTRAIT_BORDER = 3
IDENTITY_GAP   = 18         # gap under the portrait
IDENTITY_PITCH = 24         # gap between identity lines

MID_X          = 250        # gauge column, from the card left
MID_W          = 380
GAUGE_PITCH    = 84         # gap between the three gauges
GAUGE_BAR_H    = 16         # (§4.5)
GAUGE_LABEL_GAP = 22        # gap from a gauge label down to its bar

LEDGER_Y       = 372        # the bottom ledger, from the card top
LEDGER_ROW_H   = 38         # (§4.4)
LEDGER_PITCH   = 44
# Three rows plus the "+N MORE" line is what fits above the card's inner
# border; a fourth row pushes that summary line off the card.
MAX_BACKLOG_ROWS = 3

RIGHT_X        = 690        # skills column, from the card left
RIGHT_W        = 496
SKILL_ROW_H    = 38         # (§4.4)
SKILL_PITCH    = 44
SKILL_LABEL_W  = 210        # the label column inside a skill row
SKILL_BAR_H    = 10

HEADER_H       = 26         # a section header strip
BTN_W          = 180
BTN_H          = 44         # every button is 44 px tall (§4.6)
BTN_GAP        = 24
BORDER_BTN     = 3

SIZE_TITLE     = 16
SIZE_VALUE     = 13         # gauge values
SIZE_BODY      = 11         # identity lines, buttons
SIZE_LABEL     = 10         # captions, skill rows

# Game-rule thresholds (§2.2 / IMPLEMENTATION_PLAN §3) — not styling.
DAYS_SAFE      = 30         # above this the day bar is green
DAYS_FIREWALL  = 15         # at or under this it is red

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


class StatsScreen:
    """
    Draws the player profile: identity, gauges, skills and the ledger.

    Holds no player state — every value arrives through render() — and
    the only thing it caches is the ID portrait surface.
    """

    def __init__(self) -> None:
        """Build the card and button geometry once."""
        self.__card: pygame.Rect = pygame.Rect(
            CARD_MARGIN, CARD_MARGIN,
            SCREEN_W - CARD_MARGIN * 2, SCREEN_H - CARD_MARGIN * 2)
        # BACK sits bottom-LEFT, under the identity column. The obvious
        # bottom-right spot is occupied: the skills column runs twelve
        # 44 px rows down to y=678, so a button there would sit on top of
        # the last two skills.
        self.__back: pygame.Rect = pygame.Rect(
            self.__card.x + LEFT_X, self.__card.bottom - BTN_GAP - BTN_H,
            BTN_W, BTN_H)
        self.__portrait: Optional[pygame.Surface] = None
        self.__portrait_loaded: bool = False

    # -- geometry ---------------------------------------------
    def get_card_rect(self) -> pygame.Rect:
        """The framed card rectangle."""
        return self.__card

    def get_back_rect(self) -> pygame.Rect:
        """The BACK button rectangle."""
        return self.__back

    def get_skill_row_rects(self, count: int) -> List[pygame.Rect]:
        """The rectangle for each skill row, top to bottom."""
        return [pygame.Rect(self.__card.x + RIGHT_X,
                            self.__card.y + CONTENT_Y + HEADER_H + 10
                            + index * SKILL_PITCH,
                            RIGHT_W, SKILL_ROW_H)
                for index in range(max(0, int(count)))]

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface, display_name: str = "",
               student_id: str = "", semester: int = 1,
               days_remaining: int = 80, day_pool: int = 80,
               credits_earned: int = 0, credit_goal: int = 140,
               career_days: int = 0, career_cap: int = 960,
               wallet: float = 0.0, skills: Any = (),
               completed_count: int = 0,
               backlog_courses: Sequence[str] = ()) -> None:
        """
        Draw the whole profile from handed-in values (§6.1).

        `skills` accepts either the `{skill_id: level}` map a SkillTree
        exposes or a sequence of (label, level, max_level) rows, so a
        caller never reshapes data for this screen's convenience.
        """
        screen.fill(PANEL_TAN)
        self.__draw_card(screen)
        screen.blit(load_font(SIZE_TITLE).render("PLAYER PROFILE", True,
                                                 TEXT_COFFEE),
                    (self.__card.x + LEFT_X, self.__card.y + TITLE_Y))

        self.__draw_identity(screen, display_name, student_id, semester,
                             days_remaining, day_pool)
        self.__draw_gauges(screen, credits_earned, credit_goal, career_days,
                           career_cap, wallet)
        self.__draw_skills(screen, skills)
        self.__draw_ledger(screen, completed_count, backlog_courses)
        self.__draw_button(screen, self.__back, "BACK", HEADER_TAN)

    def __draw_card(self, screen: pygame.Surface) -> None:
        """Framed card with an inner border and corner brackets (§4.2)."""
        pygame.draw.rect(screen, CARD_TAN, self.__card)
        pygame.draw.rect(screen, BORDER_BROWN, self.__card, BORDER_CARD)
        inner = self.__card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
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

    def __draw_identity(self, screen: pygame.Surface, display_name: str,
                        student_id: str, semester: int, days_remaining: int,
                        day_pool: int) -> None:
        """The ID portrait and the four identity lines under it (§4.9)."""
        box = pygame.Rect(self.__card.x + LEFT_X, self.__card.y + CONTENT_Y,
                          PORTRAIT_SIZE, PORTRAIT_SIZE)
        portrait = self.__get_portrait()
        if portrait is not None:
            pygame.draw.rect(screen, PORTRAIT_BG, box)
            screen.blit(portrait, (box.centerx - portrait.get_width() // 2,
                                   box.centery - portrait.get_height() // 2))
        else:
            # [IMAGE PLACEHOLDER: assets/portraits/player_id.png — the
            #  player's ID photo] (§4.9/§5.2)
            pygame.draw.rect(screen, PORTRAIT_FILL, box)
            caption = load_font(SIZE_LABEL).render("PHOTO", True,
                                                   PORTRAIT_LABEL)
            screen.blit(caption, (box.centerx - caption.get_width() // 2,
                                  box.centery - caption.get_height() // 2))
        pygame.draw.rect(screen, BORDER_BROWN, box, PORTRAIT_BORDER)

        font = load_font(SIZE_BODY)
        small = load_font(SIZE_LABEL)
        y = box.bottom + IDENTITY_GAP
        name = self.__truncate(str(display_name).upper(), font,
                               PORTRAIT_SIZE + 40)
        screen.blit(font.render(name, True, TEXT_COFFEE),
                    (box.x, y))
        y += IDENTITY_PITCH
        for label, value in (("ID", str(student_id)),
                             ("SEMESTER", f"Sem {int(semester)}"),
                             ("DAYS LEFT",
                              f"{int(days_remaining)}/{int(day_pool)}")):
            screen.blit(small.render(label, True, STAT_BROWN), (box.x, y))
            screen.blit(small.render(value, True, TEXT_COFFEE),
                        (box.x + 96, y))
            y += IDENTITY_PITCH

    def __draw_gauges(self, screen: pygame.Surface, credits_earned: int,
                      credit_goal: int, career_days: int, career_cap: int,
                      wallet: float) -> None:
        """The three resource gauges: credits, career clock, wallet."""
        left = self.__card.x + MID_X
        y = self.__card.y + CONTENT_Y
        self.__draw_header(screen, left, y, MID_W, "RESOURCES")
        y += HEADER_H + 16

        # Credits: blue under the goal, green once it is reached.
        self.__draw_gauge(
            screen, left, y, "CREDITS",
            f"{int(credits_earned)} / {int(credit_goal)}",
            credits_earned, credit_goal,
            BAR_GREEN if credits_earned >= credit_goal else ROW_BLUE)
        y += GAUGE_PITCH

        # Career clock: the 960-day hard cap. Fills toward danger, so the
        # traffic light is read on the REMAINING days, not the used ones.
        remaining_ratio = 1.0 - self.__ratio(career_days, career_cap)
        self.__draw_gauge(
            screen, left, y, "CAREER CLOCK",
            f"{int(career_days)} / {int(career_cap)} DAYS",
            career_days, career_cap,
            BAR_GREEN if remaining_ratio > 0.5
            else (BAR_AMBER if remaining_ratio > 0.2 else BAR_RED))
        y += GAUGE_PITCH

        screen.blit(load_font(SIZE_LABEL).render("WALLET", True, STAT_BROWN),
                    (left, y))
        screen.blit(load_font(SIZE_VALUE).render(format_money(wallet), True,
                                                 TEXT_COFFEE),
                    (left, y + GAUGE_LABEL_GAP))

    def __draw_gauge(self, screen: pygame.Surface, x: int, y: int,
                     label: str, value: str, current: float, total: float,
                     fill: Tuple[int, int, int]) -> None:
        """One captioned gauge: label, value and a proportional bar."""
        screen.blit(load_font(SIZE_LABEL).render(label, True, STAT_BROWN),
                    (x, y))
        rendered = load_font(SIZE_VALUE).render(value, True, TEXT_COFFEE)
        screen.blit(rendered, (x, y + GAUGE_LABEL_GAP))
        track = pygame.Rect(x, y + GAUGE_LABEL_GAP + 26, MID_W,
                            GAUGE_BAR_H)
        self.__draw_bar(screen, track, current, total, fill)

    def __draw_bar(self, screen: pygame.Surface, track: pygame.Rect,
                   current: float, total: float,
                   fill: Tuple[int, int, int]) -> None:
        """A track, a proportional fill and a 2 px outline (§4.5)."""
        pygame.draw.rect(screen, BAR_TRACK, track)
        ratio = self.__ratio(current, total)
        if ratio > 0:
            pygame.draw.rect(screen, fill,
                             (track.x, track.y, int(track.w * ratio),
                              track.h))
        pygame.draw.rect(screen, BORDER_BROWN, track, BORDER_ROW)

    def __draw_skills(self, screen: pygame.Surface, skills: Any) -> None:
        """Every tracked skill as a label + mini-bar row (§4.4)."""
        rows = self.__resolve_skills(skills)
        left = self.__card.x + RIGHT_X
        self.__draw_header(screen, left, self.__card.y + CONTENT_Y, RIGHT_W,
                           "SKILLS")
        rects = self.get_skill_row_rects(len(rows))
        font = load_font(SIZE_LABEL)
        for (label, level, max_level), rect in zip(rows, rects):
            pygame.draw.rect(screen, ROW_WHITE, rect)
            pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_ROW)
            split = rect.x + SKILL_LABEL_W
            pygame.draw.line(screen, BORDER_BROWN, (split, rect.y),
                             (split, rect.bottom), BORDER_ROW)
            text = self.__truncate(str(label).upper(), font,
                                   SKILL_LABEL_W - 16)
            rendered = font.render(text, True, TEXT_COFFEE)
            screen.blit(rendered, (rect.x + 8,
                                   rect.centery - rendered.get_height() // 2))
            value = font.render(f"LV {int(level)}", True, CREDIT_HL)
            screen.blit(value, (split + 10,
                                rect.centery - value.get_height() // 2))
            track = pygame.Rect(split + 76, rect.centery - SKILL_BAR_H // 2,
                                rect.right - (split + 76) - 12, SKILL_BAR_H)
            self.__draw_bar(screen, track, level, max_level, ROW_BLUE)

    def __draw_ledger(self, screen: pygame.Surface, completed_count: int,
                      backlog_courses: Sequence[str]) -> None:
        """Completed / backlogged counts, and the backlog list when it bites."""
        left = self.__card.x + MID_X
        y = self.__card.y + LEDGER_Y
        backlog = [str(code) for code in (backlog_courses or ())]
        self.__draw_header(screen, left, y, MID_W, "ACADEMIC RECORD")
        y += HEADER_H + 14

        small = load_font(SIZE_LABEL)
        body = load_font(SIZE_BODY)
        for label, value in (("COMPLETED", str(int(completed_count))),
                             ("BACKLOGGED", str(len(backlog)))):
            screen.blit(small.render(label, True, STAT_BROWN), (left, y))
            screen.blit(body.render(value, True, TEXT_COFFEE), (left + 150, y))
            y += IDENTITY_PITCH

        if not backlog:
            return
        y += 8
        screen.blit(small.render("BACKLOG", True, BAR_RED), (left, y))
        y += 20
        # A long backlog is summarised rather than pushed off the card.
        for code in backlog[:MAX_BACKLOG_ROWS]:
            row = pygame.Rect(left, y, MID_W, LEDGER_ROW_H)
            pygame.draw.rect(screen, ROW_WHITE, row)
            pygame.draw.rect(screen, BAR_RED, row, BORDER_ROW)
            rendered = small.render(self.__truncate(code.upper(), small,
                                                    MID_W - 20), True,
                                    TEXT_COFFEE)
            screen.blit(rendered, (row.x + 10,
                                   row.centery - rendered.get_height() // 2))
            y += LEDGER_PITCH
        extra = len(backlog) - MAX_BACKLOG_ROWS
        if extra > 0:
            screen.blit(small.render(f"+{extra} MORE", True, STAT_BROWN),
                        (left, y))

    def __draw_header(self, screen: pygame.Surface, x: int, y: int,
                      width: int, label: str) -> None:
        """A 26 px section header strip in HEADER_TAN with a 2 px border."""
        strip = pygame.Rect(x, y, width, HEADER_H)
        pygame.draw.rect(screen, HEADER_TAN, strip)
        pygame.draw.rect(screen, BORDER_BROWN, strip, BORDER_ROW)
        rendered = load_font(SIZE_LABEL).render(label.upper(), True,
                                                TEXT_COFFEE)
        screen.blit(rendered, (strip.x + 10,
                               strip.centery - rendered.get_height() // 2))

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, fill: Tuple[int, int, int]) -> None:
        """One flat button: fill, 3 px border, ALL-CAPS label (§4.6)."""
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_BTN)
        rendered = load_font(SIZE_BODY).render(label.upper(), True,
                                               TEXT_COFFEE)
        screen.blit(rendered, (rect.centerx - rendered.get_width() // 2,
                               rect.centery - rendered.get_height() // 2))

    # -- helpers ----------------------------------------------
    @staticmethod
    def __ratio(current: float, total: float) -> float:
        """`current / total` clamped to 0.0-1.0, safe when total is 0."""
        if total <= 0:
            return 0.0
        return max(0.0, min(1.0, float(current) / float(total)))

    @staticmethod
    def __resolve_skills(skills: Any) -> List[Tuple[str, int, int]]:
        """
        Normalise the skills argument into (label, level, max_level) rows.

        Accepts a `{skill_id: level}` map — what a SkillTree exposes —
        with ids prettified for display, or a ready sequence of triples.
        """
        if isinstance(skills, dict):
            return [(str(key).replace("_", " "), int(value), 10)
                    for key, value in skills.items()]
        rows: List[Tuple[str, int, int]] = []
        for entry in (skills or ()):
            if isinstance(entry, (tuple, list)) and len(entry) >= 2:
                label = str(entry[0])
                level = int(entry[1])
                ceiling = int(entry[2]) if len(entry) > 2 else 10
                rows.append((label, level, ceiling))
        return rows

    @staticmethod
    def __truncate(text: str, font: pygame.font.Font, max_px: int) -> str:
        """Shorten `text` with an ellipsis until it fits `max_px`."""
        if max_px <= 0 or font.size(text)[0] <= max_px:
            return text
        cut = len(text)
        while cut > 0 and font.size(text[:cut] + "...")[0] > max_px:
            cut -= 1
        return text[:cut] + "..." if cut > 0 else ""

    def __get_portrait(self) -> Optional[pygame.Surface]:
        """
        The ID photo scaled into the portrait box, or None when missing.

        The asset is 92x92 and the box is 150x150, so it is scaled up
        with `scale` (never `smoothscale`) to keep the pixels crisp.
        """
        if self.__portrait_loaded:
            return self.__portrait
        self.__portrait_loaded = True
        try:
            surface = pygame.image.load(PORTRAIT_PATH).convert_alpha()
            size = PORTRAIT_SIZE - PORTRAIT_BORDER * 2
            self.__portrait = pygame.transform.scale(surface, (size, size))
        except (FileNotFoundError, OSError, pygame.error):
            self.__portrait = None
        return self.__portrait

    def get_missing_paths(self) -> List[str]:
        """Asset paths that failed to load — the §5.2 step-4 work queue."""
        if self.__portrait_loaded and self.__portrait is None:
            return [PORTRAIT_PATH]
        return []


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   SPACE -> cycle fresh / mid-degree / near-graduation / firewall
#   B     -> toggle a long backlog on and off
#   F11   -> toggle windowed / fullscreen
#   ESC   -> quit
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, PROJECT_ROOT)

    from core.skill_tree import SkillTree
    from engine.endgame_manager import EndgameEvaluationManager

    pygame.init()

    SIZE = (SCREEN_W, SCREEN_H)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Stats screen test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    ui = StatsScreen()
    tracked = list(EndgameEvaluationManager.TRACKED_SKILL_IDS)

    def _tree(levels: Dict[str, int]) -> Dict[str, int]:
        """A REAL SkillTree stocked through increment_skill(), as a map."""
        tree = SkillTree()
        for skill_id, level in levels.items():
            tree.increment_skill(skill_id, level)
        # Every tracked skill is shown, including the untouched ones.
        return {skill_id: tree.get_skill_level(skill_id)
                for skill_id in tracked}

    cases = [
        ("Fresh student", "CSE-2026-001", 1, 80, 0, 0,
         0.0, _tree({}), 0, []),
        ("Nangiba Tasnim", "CSE-2026-014", 7, 46, 84, 640,
         48200.0, _tree({"programming_language": 6, "dsa": 4, "git": 5,
                         "oop": 3, "databases_sql": 2, "linux_cli": 3}),
         28, ["PHY101", "MAT120"]),
        ("Nangiba Tasnim", "CSE-2026-014", 11, 22, 132, 880,
         96500.0, _tree({skill: 8 for skill in tracked}), 44, []),
        ("Nangiba Tasnim", "CSE-2026-014", 12, 9, 138, 940,
         12000.0, _tree({skill: 9 for skill in tracked}), 46,
         ["CSE4108"]),
    ]
    index = 0
    long_backlog = False

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
                elif event.key == pygame.K_b:
                    long_backlog = not long_backlog

        (name, sid, sem, days, credits_, career, money, skill_map,
         done, backlog) = cases[index]
        if long_backlog:
            backlog = ["PHY101", "MAT120", "CSE2216", "EEE1101", "CHE101",
                       "CSE3202"]

        ui.render(window, display_name=name, student_id=sid, semester=sem,
                  days_remaining=days, day_pool=80, credits_earned=credits_,
                  credit_goal=140, career_days=career, career_cap=960,
                  wallet=money, skills=skill_map, completed_count=done,
                  backlog_courses=backlog)

        hint = hint_font.render(
            "SPACE next profile  |  B toggle long backlog  |  F11  |  ESC",
            True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

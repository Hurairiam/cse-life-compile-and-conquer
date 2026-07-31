"""
CSE Life: Compile & Conquer
play_registration.py  —  multi-semester registration driver (phase R3)

Run this to watch the catalog actually change between terms:

    python play_registration.py            # seeded, reproducible
    python play_registration.py 12345      # your own seed

It exists to prove the loop the owner asked about — that the course
list updates each semester, that a failed course comes back pinned to
the top in red, and that a newly unlocked one appears — over REAL game
objects rather than fake ones:

    academic/course_catalog.py     the real 65 courses
    academic/academic_history.py   a real transcript
    engine/registration_manager.py the real 15-credit gatekeeper
    engine/catalog_builder.py      R1's ordering layer
    ui/registration_screen.py      R2's screen, unmodified here
    ui/hud.py                      the real HUD, imported and never edited

THIS IS A TEST DOUBLE FOR THE SEMESTER LOOP, NOT THE REAL ONE.
CONFIRM ends the term and simulates it: some registered courses pass,
the rest fail into the backlog. It deliberately touches NO GameSession,
NO GameClock and NO Player, and it deducts no time. The real semester
turnover — time pool, exams, the career clock — belongs to
`IMPLEMENTATION_PLAN.md` Phase A4 and is not this file's business. What
this file drives is the registration screen and nothing else.

The scroll offset lives HERE, in the caller, exactly as
REGISTRATION_CATALOG_PLAN.md §R2.7 specifies. The screen owns the
arithmetic; the runner owns the integer and the wheel event.

Created by Nangiba Tasnim (Dev 3), branch nangiba-temp-01.
"""
from __future__ import annotations

import os
import random
import sys
from typing import Any, Dict, List, Optional, Tuple

import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from academic.academic_history import AcademicHistory       # noqa: E402
from academic.course_catalog import build_course_catalog    # noqa: E402
from engine.catalog_builder import SemesterCatalogBuilder   # noqa: E402
from engine.registration_manager import RegistrationManager  # noqa: E402
from ui.hud import HUD                                      # noqa: E402
from ui.registration_screen import RegistrationScreen       # noqa: E402

# -- palette --------------------------------------------------
# The runner draws one debug strip of its own, so it needs four colours
# from UI_STYLE_GUIDE.md §2. Declared here rather than imported from a
# screen (FEATURE_BUILD_PLAN §0.5).
HEADER_TAN   = (214, 196, 168)   # the debug plate fill (§2.1)
BORDER_BROWN = (169, 130, 94)    # its outline
TEXT_COFFEE  = (74, 53, 39)      # the debug text
HINT_BROWN   = (150, 125, 100)   # the key hint

# -------------------------------------------------------------
# LAYOUT + TUNING
# -------------------------------------------------------------
SCREEN_SIZE: Tuple[int, int] = (1280, 720)
WINDOWED_FLAGS = pygame.SCALED
FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN
FPS_CAP = 60

HUD_STRIP_H = 44            # ui/hud.py's own height (§4.3)
# The band between the credit footer box (ends y 608) and the card's
# inner border (y 682) is 74 px of free space. The debug plate takes
# 612-658 and the hint line 664-680, so neither crosses the frame.
DEBUG_Y = 612
HINT_Y = 664
PLATE_PAD = 8
PLATE_BORDER_W = 2

# The semester simulation. Half the load passes, rounded up, so a
# player who registers an odd number is not punished for it.
PASS_RATIO = 0.5
# Not arbitrary: with this seed the very first CONFIRM fails three
# courses AND passes the programming gateway, so semester 2 opens
# showing both markers at once -- three red RETAKE rows pinned to the
# top and two NEW rows below them. A seed that failed the gateway would
# unlock nothing and the NEW tag would not appear until semester 3,
# which makes the default run demonstrate only half the feature.
DEFAULT_SEED = 3
FINAL_SEMESTER = 12         # IMPLEMENTATION_PLAN §3 — 12 semesters
DAY_POOL = 80               # the per-semester pool, for the HUD only


class RegistrationDriver:
    """
    Owns the window, the real game objects, and the scroll integer.

    Every decision the screen refuses to make lives here: which course a
    click landed on, whether the credit cap allows it, what happens when
    a semester ends. The screen is handed values and draws them.
    """

    def __init__(self, seed: int = DEFAULT_SEED) -> None:
        """Open the window and build one of everything, real."""
        pygame.init()
        self.__is_fullscreen: bool = False
        self.__window: pygame.Surface = pygame.display.set_mode(
            SCREEN_SIZE, WINDOWED_FLAGS)
        pygame.display.set_caption("CSE Life — registration sandbox")
        self.__clock: pygame.time.Clock = pygame.time.Clock()
        self.__debug_font: pygame.font.Font = pygame.font.SysFont(
            "Courier", 13)

        self.__screen: RegistrationScreen = RegistrationScreen(*SCREEN_SIZE)
        self.__hud: HUD = HUD()

        self.__seed: int = int(seed)
        self.__rng: random.Random = random.Random(self.__seed)
        self.__manager: RegistrationManager = RegistrationManager()
        self.__builder: SemesterCatalogBuilder = SemesterCatalogBuilder(
            self.__manager)

        self.__full_catalog: List[Any] = []
        self.__history: AcademicHistory = AcademicHistory()
        self.__catalog: List[Any] = []
        self.__backlogged: List[Any] = []
        self.__newly_unlocked: List[Any] = []
        self.__semester: int = 1
        self.__scroll_offset: int = 0
        self.__last_result: str = "semester 1 — nothing registered yet"
        self.__running: bool = True

        self.reset()

    # -- game state -------------------------------------------
    def reset(self) -> None:
        """
        Start a fresh degree at semester 1.

        The catalog is rebuilt from scratch because `record_completion()`
        mutates the Course objects themselves — reusing the old list
        would carry every completion flag into the new run.
        """
        self.__full_catalog = build_course_catalog()
        self.__history = AcademicHistory()
        self.__manager.clear_selection()
        self.__builder.clear_snapshot()
        self.__semester = 1
        self.__scroll_offset = 0
        self.__rng = random.Random(self.__seed)
        self.__last_result = "semester 1 — nothing registered yet"
        self.__rebuild()

    def __rebuild(self) -> None:
        """Re-read the catalog through R1's ordering layer."""
        self.__catalog = self.__builder.build(self.__full_catalog,
                                              self.__history)
        self.__backlogged = self.__builder.get_backlogged(
            self.__full_catalog, self.__history)
        self.__newly_unlocked = self.__builder.get_newly_unlocked(
            self.__catalog)
        self.__scroll_offset = self.__screen.clamp_scroll(
            self.__scroll_offset, len(self.__catalog))

    def __end_semester(self) -> None:
        """
        Confirm the registration and simulate the term.

        Roughly half the registered courses pass and the rest fail into
        the backlog, through the REAL AcademicHistory calls
        `MainQuest.execute_action()` uses. The snapshot is taken BEFORE
        the simulation, so next term's "new" means "unlocked by what
        just happened".

        No time is deducted and no clock is touched — see the module
        docstring.
        """
        registered = self.__manager.get_selected_courses()
        if not registered:
            self.__last_result = "nothing selected — pick some courses first"
            return
        if self.__semester >= FINAL_SEMESTER:
            self.__last_result = (f"semester {FINAL_SEMESTER} is the last — "
                                  f"press R to start over")
            return

        self.__builder.snapshot(self.__catalog)

        shuffled = list(registered)
        self.__rng.shuffle(shuffled)
        pass_count = max(1, round(len(shuffled) * PASS_RATIO))
        passed = shuffled[:pass_count]
        failed = shuffled[pass_count:]

        for course in passed:
            self.__history.record_completion(course)
        for course in failed:
            self.__history.mark_course_incomplete(course)
            self.__history.add_backlog(course)

        self.__manager.clear_selection()
        self.__semester += 1
        self.__scroll_offset = 0        # a new term starts at the top
        self.__rebuild()
        self.__last_result = (
            f"passed {sorted(c.get_course_code() for c in passed)} · "
            f"FAILED {sorted(c.get_course_code() for c in failed)}")

    def __toggle_course(self, index: int) -> None:
        """
        Select or deselect the course at an ABSOLUTE catalog index.

        Selection goes through the real `RegistrationManager`, so the
        15-credit cap is enforced by the engine and not by this runner.
        A rejection is silent — the credit bar turns amber then red and
        explains itself, exactly as `main.py` does today.
        """
        if not 0 <= index < len(self.__catalog):
            return
        course = self.__catalog[index]
        if course in self.__manager.get_selected_courses():
            self.__manager.deselect_course(course)
        else:
            self.__manager.select_course(course)

    # -- the loop ---------------------------------------------
    def run(self) -> None:
        """Run until the window closes."""
        print(f"registration sandbox — seed {self.__seed} (reproducible)")
        while self.__running:
            self.__clock.tick(FPS_CAP)
            self.__handle_events()
            self.__draw()
            pygame.display.flip()
        pygame.quit()

    def __handle_events(self) -> None:
        """Route input. The runner owns the scroll integer (§R2.7)."""
        total = len(self.__catalog)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.__running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.__running = False
                elif event.key == pygame.K_F11:
                    self.__toggle_fullscreen()
                elif event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_DOWN:
                    self.__scroll(1)
                elif event.key == pygame.K_UP:
                    self.__scroll(-1)
                elif event.key == pygame.K_PAGEDOWN:
                    self.__scroll(self.__screen.get_visible_row_count())
                elif event.key == pygame.K_PAGEUP:
                    self.__scroll(-self.__screen.get_visible_row_count())

            elif event.type == pygame.MOUSEWHEEL:
                # The exact three-line pattern §R2.7 documents for the lead.
                self.__scroll_offset = self.__screen.clamp_scroll(
                    self.__scroll_offset - event.y, total)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.__handle_click(event.pos, total)

    def __handle_click(self, pos, total: int) -> None:
        """Buttons first, then the scroll arrows, then the rows."""
        if self.__screen.get_confirm_rect().collidepoint(pos):
            self.__end_semester()
        elif self.__screen.get_cancel_rect().collidepoint(pos):
            self.__manager.clear_selection()
            self.__last_result = "selection cleared"
        elif self.__screen.get_scroll_up_rect().collidepoint(pos):
            self.__scroll(-1)
        elif self.__screen.get_scroll_down_rect().collidepoint(pos):
            self.__scroll(1)
        else:
            # ABSOLUTE index, so a click is correct at any scroll
            # position. This is the whole point of get_row_index_at().
            self.__toggle_course(self.__screen.get_row_index_at(
                pos, self.__scroll_offset, total))

    def __scroll(self, delta: int) -> None:
        """Move the offset, clamped by the screen's own arithmetic."""
        self.__scroll_offset = self.__screen.clamp_scroll(
            self.__scroll_offset + delta, len(self.__catalog))

    def __toggle_fullscreen(self) -> None:
        """F11 — windowed <-> fullscreen, both SCALED (§4.1)."""
        self.__is_fullscreen = not self.__is_fullscreen
        self.__window = pygame.display.set_mode(
            SCREEN_SIZE,
            FULLSCREEN_FLAGS if self.__is_fullscreen else WINDOWED_FLAGS)

    # -- drawing ----------------------------------------------
    def __draw(self) -> None:
        """The real screen, the real HUD on top, then the debug strip."""
        self.__screen.render(
            self.__window,
            visible_courses=self.__catalog,
            selected=self.__manager.get_selected_courses(),
            confirmed=[],
            current_credits=self.__manager.get_current_selected_credits(),
            credit_limit=self.__manager.get_max_credit_limit(),
            player_name="Player",
            student_id="8324782",
            semester=self.__semester,
            backlogged=self.__backlogged,
            scroll_offset=self.__scroll_offset,
            newly_unlocked=self.__newly_unlocked)

        # The real HUD, drawn last so the strip/card overlap is visible
        # in situ — this runner exists partly to expose that.
        self.__hud.render(
            self.__window, time_pool=DAY_POOL,
            wallet=0.0, semester=self.__semester,
            credits=self.__history.get_total_credits_earned())

        self.__draw_debug()
        self.__draw_hint()

    def __draw_debug(self) -> None:
        """One plate of live numbers, below the credit footer box."""
        total = len(self.__catalog)
        lines = [
            f"semester {self.__semester}/{FINAL_SEMESTER}  |  "
            f"catalog {total}  |  backlog {len(self.__backlogged)}  |  "
            f"new {len(self.__newly_unlocked)}  |  "
            f"scroll {self.__scroll_offset}/"
            f"{self.__screen.get_max_scroll(total)}  |  "
            f"completed {len(self.__history.get_completed_course_codes())}",
            f"last term: {self.__last_result}"[:96],
        ]
        width = max(self.__debug_font.size(line)[0] for line in lines)
        height = self.__debug_font.get_height() * len(lines) + 4
        plate = pygame.Rect(60, DEBUG_Y, width + PLATE_PAD * 2,
                            height + PLATE_PAD * 2)
        # Dev text straight onto the card is readable, but a boxed footer
        # fill (§2.1) is what the style guide already uses for exactly
        # this and keeps the debug strip visibly separate from the UI.
        pygame.draw.rect(self.__window, HEADER_TAN, plate)
        pygame.draw.rect(self.__window, BORDER_BROWN, plate, PLATE_BORDER_W)
        for index, line in enumerate(lines):
            self.__window.blit(
                self.__debug_font.render(line, True, TEXT_COFFEE),
                (plate.x + PLATE_PAD,
                 plate.y + PLATE_PAD +
                 index * (self.__debug_font.get_height() + 4)))

    def __draw_hint(self) -> None:
        """The muted bottom-right key hint every runner carries."""
        hint = self.__debug_font.render(
            "Wheel/arrows scroll  |  Click rows  |  CONFIRM ends the term"
            "  |  R reset  |  F11  |  ESC", True, HINT_BROWN)
        self.__window.blit(
            hint, (self.__window.get_width() - hint.get_width() - 62,
                   HINT_Y))

    # -- read-only accessors (used by the acceptance run) -----
    def get_semester(self) -> int:
        """The current semester number."""
        return self.__semester

    def get_catalog(self) -> List[Any]:
        """The ordered catalog as it stands, as a copy."""
        return list(self.__catalog)

    def get_backlogged(self) -> List[Any]:
        """The backlog block as it stands, as a copy."""
        return list(self.__backlogged)

    def get_newly_unlocked(self) -> List[Any]:
        """The newly unlocked block as it stands, as a copy."""
        return list(self.__newly_unlocked)

    def get_scroll_offset(self) -> int:
        """The offset this runner currently owns."""
        return self.__scroll_offset


# -------------------------------------------------------------
# STUB TEST -- this file IS the runner; running it drives the real
# registration screen over the real catalog.
# Abu Huraira deletes it when the real semester loop takes over.
#   Wheel / arrows / PgUp / PgDn / the two arrow buttons -> scroll
#   Click a row   -> select (blue), respecting the real 15-credit cap
#   CONFIRM       -> end the term: ~half pass, the rest go to backlog
#   CANCEL        -> clear the selection
#   R             -> reset to semester 1 (same seed, same run)
#   F11           -> toggle windowed / fullscreen
#   ESC           -> quit
#
# Pass a seed to reproduce a particular run:  python play_registration.py 7
# -------------------------------------------------------------
if __name__ == "__main__":
    requested_seed = DEFAULT_SEED
    if len(sys.argv) > 1:
        try:
            requested_seed = int(sys.argv[1])
        except ValueError:
            print(f"ignoring non-numeric seed {sys.argv[1]!r}")
    RegistrationDriver(requested_seed).run()

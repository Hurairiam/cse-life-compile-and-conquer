"""
semester.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation
Semester manages the 80-day time pool and registered course /
quest arrays for ONE academic term. A fresh Semester instance
is created each cycle by GameClock.advanceSemester(); the
Player profile (AcademicHistory, SkillTree, wallet, credits)
persists independently and is never reset.
─────────────────────────────────────────────────────────────
FIX (this version): all_courses_attempted() was calling
course.get_is_completed(), which does not exist on Course —
the real getter is is_completed(). Corrected below.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from academic.course import Course
    from academic.quest import Quest

# Matches Player's own default pool size (core/character/player.py)
# and the GameClock.MIN_MAIN_QUEST_TIME_BORDER firewall threshold.
_DEFAULT_TIME_POOL_DAYS: int = 80


class Semester:
    """
    Represents a single academic term's mutable state:
    the time pool, the courses registered for the term, and
    the pool of active quests (Main + Side) offered this term.

    OOP: Encapsulation — time pool and lists are private,
         mutated only via validated public methods.
    """

    def __init__(self, semester_number: int) -> None:
        self.__semester_number: int = semester_number
        self.__time_pool_days: int = _DEFAULT_TIME_POOL_DAYS
        self.__max_time_pool_days: int = _DEFAULT_TIME_POOL_DAYS
        self.__registered_courses: list[Course] = []
        self.__active_quest_pool: list[Quest] = []

    # ── Identity ──────────────────────────────────────────────────

    def get_semester_number(self) -> int:
        """Return this term's ordinal number (1, 2, 3, ...)."""
        return self.__semester_number

    # ── Time Pool ─────────────────────────────────────────────────

    def get_time_pool_days(self) -> int:
        """Return the days remaining in this semester's time pool."""
        return self.__time_pool_days

    def deduct_time(self, days: int) -> bool:
        """
        Deduct days from the semester's time pool.
        Returns False without changing state if days < 0 or if
        the pool has insufficient days remaining.

        Note: this tracks the SEMESTER's own pool. GameClock is
        responsible for mirroring the deduction onto the Player
        (player.deduct_time_pool_days()) so both stay in sync —
        Semester does not reach into Player directly.
        """
        if days < 0:
            return False
        if self.__time_pool_days >= days:
            self.__time_pool_days -= days
            return True
        return False

    def is_semester_complete(self) -> bool:
        """
        Return True once the time pool is fully exhausted (0 days
        left). Used by GameClock.checkSemesterEndState() alongside
        the "all registered courses attempted" check to decide
        whether to advance to the next semester.
        """
        return self.__time_pool_days <= 0

    # ── Registered Courses ────────────────────────────────────────

    def register_course(self, course: Course) -> None:
        """
        Add a course to this semester's registered list.
        Called by RegistrationManager.confirmRegistration() once
        credit-limit and prerequisite checks have passed.
        Duplicate registrations of the same course are ignored.
        """
        if course not in self.__registered_courses:
            self.__registered_courses.append(course)

    def deregister_course(self, course: Course) -> None:
        """
        Remove a course from this semester's registered list.
        Called by RegistrationManager.deselectCourse() before
        registration is confirmed.
        """
        if course in self.__registered_courses:
            self.__registered_courses.remove(course)

    def get_registered_courses(self) -> list[Course]:
        """Return a copy of the currently registered course list."""
        return list(self.__registered_courses)

    def all_courses_attempted(self) -> bool:
        """
        Return True if every registered course has had its exam
        attempted this semester — whether the outcome was a PASS
        (is_completed() True) or a FAIL (is_backlogged() True).
        Empty registration counts as vacuously complete.

        FIX (this version): previously this only checked
        course.is_completed(), which is True ONLY on a pass. A
        failed course sets is_backlogged() True and is_completed()
        stays False (see course.py's mark_backlogged()), so a
        semester with even one failed course could never satisfy
        this check under the old logic — even though that course's
        exam genuinely was attempted. Now either flag counts.
        """
        return all(
            course.is_completed() or course.is_backlogged()
            for course in self.__registered_courses
        )

    # ── Active Quest Pool ──────────────────────────────────────────

    def add_quest(self, quest: Quest) -> None:
        """
        Add a quest (MainQuest or SideQuest) to this semester's
        active pool. MainQuests are typically seeded from the
        registered course list; SideQuests are offered by NPCs.
        """
        if quest not in self.__active_quest_pool:
            self.__active_quest_pool.append(quest)

    def get_active_quest_pool(self) -> list[Quest]:
        """Return a copy of the active quest pool for this term."""
        return list(self.__active_quest_pool)

    # ── Lifecycle ────────────────────────────────────────────────

    def play_intro_monologue(self) -> None:
        """
        Print the semester's opening narrative beat.
        Purely presentational — no state mutation.
        [Full narrative text to be supplied by the narrative/UI layer;
        placeholder text below keeps this callable standalone.]
        """
        print(
            f"\n--- Semester {self.__semester_number} begins. "
            f"{self.__time_pool_days} days on the clock. ---\n"
        )

    def terminate(self) -> None:
        """
        Close out this semester instance. Clears the registered
        course and quest lists (the Course objects themselves are
        NOT destroyed — passed courses live on in AcademicHistory,
        failed ones live on in the backlog; only this term's local
        bookkeeping is cleared).
        Called by GameClock right before a new Semester is
        instantiated for the next term.
        """
        self.__registered_courses.clear()
        self.__active_quest_pool.clear()
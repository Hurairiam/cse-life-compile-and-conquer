"""
academic/semester.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation + Composition
Semester manages the 80-day time pool and registered course /
quest arrays for ONE academic term. A fresh Semester instance
is created each cycle by GameClock; the Player profile 
(AcademicHistory, SkillTree, wallet, credits) persists independently.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from academic.course import Course
    from academic.quest import Quest

# Default time pool size matching Player's default pool size
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

    # ── Getters & Identity ────────────────────────────────────────

    def get_semester_number(self) -> int:
        """Return this term's ordinal number (1, 2, 3, ...)."""
        return self.__semester_number

    def get_time_pool_days(self) -> int:
        """Return the days remaining in this semester's time pool."""
        return self.__time_pool_days

    def get_max_time_pool_days(self) -> int:
        """Return the maximum days this semester started with."""
        return self.__max_time_pool_days

    # ── Time Management ───────────────────────────────────────────

    def deduct_time(self, days: int) -> bool:
        """
        Deduct days from the semester's time pool.
        Returns False without changing state if days < 0 or if
        the pool has insufficient days remaining.
        """
        if days < 0:
            return False
        if self.__time_pool_days >= days:
            self.__time_pool_days -= days
            return True
        return False

    def is_semester_complete(self) -> bool:
        """Return True once the time pool is fully exhausted (0 days left)."""
        return self.__time_pool_days <= 0

    # ── Registered Courses ────────────────────────────────────────

    def register_course(self, course: Course) -> None:
        """
        Add a course to this semester's registered list.
        Duplicate registrations of the same course are ignored.
        """
        if course not in self.__registered_courses:
            self.__registered_courses.append(course)

    def add_course(self, course: Course) -> None:
        """Alias for register_course() for backward compatibility."""
        self.register_course(course)

    def deregister_course(self, course: Course) -> None:
        """Remove a course from this semester's registered list."""
        if course in self.__registered_courses:
            self.__registered_courses.remove(course)

    def get_registered_courses(self) -> list[Course]:
        """Return a shallow copy of the currently registered course list."""
        return list(self.__registered_courses)

    def all_courses_attempted(self) -> bool:
        """
        Return True if every registered course has had its exam
        attempted this semester (either passed or backlogged).
        """
        return all(
            course.is_completed() or course.is_backlogged()
            for course in self.__registered_courses
        )

    # ── Active Quest Pool ──────────────────────────────────────────

    def add_quest(self, quest: Quest) -> None:
        """Add a quest to this semester's active pool."""
        if quest not in self.__active_quest_pool:
            self.__active_quest_pool.append(quest)

    def get_active_quest_pool(self) -> list[Quest]:
        """Return a shallow copy of the active quest pool for this term."""
        return list(self.__active_quest_pool)

    # ── Lifecycle Methods ──────────────────────────────────────────

    def play_intro_monologue(self) -> None:
        """Trigger the semester opening narrative beat."""
        print(
            f"\n--- Semester {self.__semester_number} begins. "
            f"{self.__time_pool_days} days on the clock. ---\n"
        )

    def terminate(self) -> None:
        """Close out this semester instance by clearing local trackers."""
        self.__registered_courses.clear()
        self.__active_quest_pool.clear()

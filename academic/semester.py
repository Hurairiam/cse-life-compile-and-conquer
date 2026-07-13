"""
academic/semester.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation + Composition
Semester owns the active course pool and the 80-day time pool
for one academic term. It is destroyed at the end of each
semester cycle — Player and AcademicHistory survive it.
─────────────────────────────────────────────────────────────
Sprint 2 — Created by Abu Huraira (dev1-engine-architect)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from academic.course import Course
    from academic.quest import Quest


class Semester:
    """
    Represents one academic semester (80-day time pool).
    Instantiated fresh each semester by GameSession.
    Composition target: GameSession *-- Semester.
    """

    def __init__(self, semester_number: int) -> None:
        self.__semester_number: int = semester_number
        self.__time_pool_days: int = 80
        self.__max_time_pool_days: int = 80
        self.__registered_courses: list[Course] = []
        self.__active_quest_pool: list[Quest] = []

    # ── Getters ───────────────────────────────────────────────

    def get_semester_number(self) -> int:
        """Return the sequential number of this semester."""
        return self.__semester_number

    def get_time_pool_days(self) -> int:
        """Return remaining days in this semester's time pool."""
        return self.__time_pool_days

    def get_max_time_pool_days(self) -> int:
        """Return the maximum days this semester started with."""
        return self.__max_time_pool_days

    def get_registered_courses(self) -> list:
        """Return a shallow copy of the registered course list."""
        return list(self.__registered_courses)

    # ── Time Management ───────────────────────────────────────

    def deduct_time(self, days: int) -> bool:
        """
        Deduct days from the time pool.
        Returns False and makes no change if insufficient days remain.
        """
        if days < 0:
            return False
        if self.__time_pool_days >= days:
            self.__time_pool_days -= days
            return True
        return False

    def is_semester_complete(self) -> bool:
        """
        Return True if the time pool has been exhausted.
        Does NOT check whether all courses were attempted.
        [Sprint 2 — logic complete]
        """
        return self.__time_pool_days <= 0

    # ── Course Registration ───────────────────────────────────

    def add_course(self, course: Course) -> None:
        """
        Add a course to this semester's registered course list.
        Called by RegistrationManager during confirm_registration().
        [Sprint 2]
        """
        if course not in self.__registered_courses:
            self.__registered_courses.append(course)

    def play_intro_monologue(self) -> None:
        """
        Trigger the semester opening narrative monologue.
        Actual text loaded from content/dialogues.py (Ayesha's layer).
        [Sprint 3 — wired to DialogueManager]
        """
        pass

    def terminate(self) -> None:
        """
        Called at semester end. Clears the active quest pool.
        Registered courses are NOT cleared here — AcademicHistory
        decides their fate (completion or backlog).
        [Sprint 2]
        """
        self.__active_quest_pool.clear()

"""
course.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation
Course encapsulates all academic metadata for one subject.
The self-referential prerequisite array drives the dynamic
catalog filtering in RegistrationManager.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from academic.academic_history import AcademicHistory


class Course:
    """
    Represents one academic subject unit.

    Key mechanic: A Course instance PERSISTS across semesters.
    If isPassed = False after an exam, the same object is pushed
    to the backlog and re-offered in the next semester's catalog —
    no new instance is created, no penalty counter is added.

    OOP: Encapsulation — all fields private, mutated via setters.
    """

    def __init__(
        self,
        course_id: str,
        course_name: str,
        credit_value: int
    ) -> None:
        self.__course_id: str = course_id
        self.__course_name: str = course_name
        self.__credit_value: int = credit_value
        self.__is_completed: bool = False
        self.__is_passed: bool = False
        self.__prerequisite_course_ids: list[str] = []

    # ── Getters ───────────────────────────────────────────────────

    def get_course_id(self) -> str:
        return self.__course_id

    def get_course_name(self) -> str:
        return self.__course_name

    def get_credit_value(self) -> int:
        return self.__credit_value

    def get_is_completed(self) -> bool:
        return self.__is_completed

    def get_is_passed(self) -> bool:
        return self.__is_passed

    # ── Setters / Mutators ────────────────────────────────────────

    def set_passed_status(self, status: bool) -> None:
        """Set isPassed flag after exam evaluation."""
        self.__is_passed = status

    def mark_completed(self) -> None:
        """Mark course as completed (called after successful exam)."""
        self.__is_completed = True

    # ── Prerequisite Check ────────────────────────────────────────

    def are_prerequisites_satisfied(self, history: AcademicHistory) -> bool:
        """
        Check if all prerequisite courses have been completed
        by querying the player's AcademicHistory.
        Returns True if no prerequisites exist (free entry course).
        Used by RegistrationManager.filterVisibleCatalog() to hide
        courses whose prerequisites are unsatisfied.
        """
        for prereq_id in self.__prerequisite_course_ids:
            if not history.is_prerequisite_satisfied(prereq_id):
                return False
        return True

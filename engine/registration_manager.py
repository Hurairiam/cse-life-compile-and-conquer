"""
engine/registration_manager.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation + Separation of Concerns
RegistrationManager is the gatekeeper for course selection.
It enforces the 15-credit cap, filters the catalog by
prerequisites, and re-injects backlogged courses each semester.

Nangiba's RegistrationScreen reads filtered data FROM this
class — it never modifies game state directly.
No Pygame code lives here — pure Python logic only.
─────────────────────────────────────────────────────────────
Sprint 2 — Created by Abu Huraira (dev1-hurairiam-core)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from academic.course import Course
from academic.semester import Semester
from academic.academic_history import AcademicHistory

if TYPE_CHECKING:
    from engine.game_session import GameSession


class RegistrationManager:
    """
    Manages the course registration phase each semester.
    Enforces the MAX_CREDIT_LIMIT and prerequisite visibility
    rules defined in the class diagram.

    Key responsibilities:
    - Filter visible course catalog by prerequisite satisfaction
    - Validate credit limit on every selection attempt
    - Inject backlogged courses back into the selectable pool
    - Confirm registration by populating the active Semester
    - Calculate tuition fee for post-Semester-12 billing

    Does NOT render anything — Nangiba's UI layer handles display.
    """

    __MAX_CREDIT_LIMIT: int = 15
    __FLAT_TUITION_RATE: float = 5000.0

    def __init__(self) -> None:
        self.__current_selected_credits: int = 0
        self.__selected_courses: list[Course] = []

    # ── Credit Validation ─────────────────────────────────────

    def get_current_selected_credits(self) -> int:
        """Return total credits currently selected this session."""
        return self.__current_selected_credits

    def get_selected_courses(self) -> list[Course]:
        """Return a copy of the currently selected course list."""
        return list(self.__selected_courses)

    def validate_credit_limit(self, course: Course) -> bool:
        """
        Return True if adding this course would not exceed
        the 15-credit cap. Does NOT add the course — purely
        a read-only check used before select_course().
        """
        return (
            self.__current_selected_credits + course.get_credit_value()
            <= self.__MAX_CREDIT_LIMIT
        )

    # ── Course Selection ──────────────────────────────────────

    def select_course(self, course: Course) -> bool:
        """
        Attempt to add a course to the current selection.
        Returns True if added successfully.
        Returns False if credit limit would be exceeded
        or if the course is already in the selection.
        """
        if course in self.__selected_courses:
            return False
        if not self.validate_credit_limit(course):
            return False
        self.__selected_courses.append(course)
        self.__current_selected_credits += course.get_credit_value()
        return True

    def deselect_course(self, course: Course) -> None:
        """
        Remove a course from the current selection and
        decrement the credit counter accordingly.
        Silently ignored if the course was not selected.
        """
        if course in self.__selected_courses:
            self.__selected_courses.remove(course)
            self.__current_selected_credits -= course.get_credit_value()

    def clear_selection(self) -> None:
        """
        Reset the entire selection state.
        Called at the start of each registration session
        and automatically after confirm_registration().
        """
        self.__selected_courses.clear()
        self.__current_selected_credits = 0

    # ── Catalog Filtering ─────────────────────────────────────

    def filter_visible_catalog(
        self,
        full_catalog: list[Course],
        history: AcademicHistory
    ) -> list[Course]:
        """
        Return only courses whose prerequisites are all satisfied
        according to the player's AcademicHistory.
        Courses with no prerequisites are always visible.
        Already-completed courses are excluded from the result.
        """
        visible: list[Course] = []
        for course in full_catalog:
            if course.get_is_completed():
                continue
            if course.are_prerequisites_satisfied(history):
                visible.append(course)
        return visible

    def build_semester_catalog(
        self,
        full_catalog: list[Course],
        history: AcademicHistory
    ) -> list[Course]:
        """
        Build the full selectable catalog for the registration
        screen by merging the base catalog with backlogged courses
        from AcademicHistory, then filtering by prerequisites.

        Backlogged courses are the same Course instances that were
        previously registered and failed — they compete for the
        15-credit cap like any other course selection.
        """
        backlog_ids: list[str] = history.get_backlog_courses()

        # Build a set of course IDs already in the full catalog
        # to avoid duplicating backlog courses that are already there
        catalog_ids: set[str] = {c.get_course_id() for c in full_catalog}

        merged: list[Course] = list(full_catalog)

        # Inject backlogged courses not already in the catalog
        # Note: in practice, backlogged Course objects should be
        # stored and retrieved from a course registry (Sprint 3).
        # For now we match by ID against the full_catalog itself.
        for course in full_catalog:
            if (course.get_course_id() in backlog_ids
                    and course.get_course_id() not in catalog_ids):
                merged.append(course)

        return self.filter_visible_catalog(merged, history)

    # ── Confirmation ──────────────────────────────────────────

    def confirm_registration(self, semester: Semester) -> bool:
        """
        Lock in the current selection by adding each selected
        course to the active Semester's registered course list.
        Resets internal selection state after confirmation.
        Returns True if at least one course was registered,
        False if the selection was empty.
        """
        if not self.__selected_courses:
            return False

        for course in self.__selected_courses:
            semester.add_course(course)

        self.clear_selection()
        return True

    # ── Tuition ───────────────────────────────────────────────

    def calculate_tuition_fee(
        self,
        backlogged_courses: list[Course]
    ) -> float:
        """
        Calculate the total tuition fee for backlogged courses.
        Applied post-Semester-12 at registration time only.
        Formula: sum of (creditValue * FLAT_TUITION_RATE)
        for every course in the backlogged list.
        [Sprint 3 — triggered when semesterNumber > 12]
        """
        total: float = 0.0
        for course in backlogged_courses:
            total += course.get_credit_value() * self.__FLAT_TUITION_RATE
        return total

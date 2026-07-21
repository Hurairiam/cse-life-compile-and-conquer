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
        the 15-credit cap. Does NOT add the course.
        [Sprint 2 — stub]
        """
        pass

    # ── Course Selection ──────────────────────────────────────

    def select_course(self, course: Course) -> bool:
        """
        Attempt to add a course to the current selection.
        Returns True if added, False if credit limit exceeded
        or course already selected.
        [Sprint 2 — stub]
        """
        pass

    def deselect_course(self, course: Course) -> None:
        """
        Remove a course from the current selection and
        decrement the credit counter accordingly.
        [Sprint 2 — stub]
        """
        pass

    def clear_selection(self) -> None:
        """
        Reset the entire selection — called at the start of
        each registration session or after confirmation.
        [Sprint 2 — stub]
        """
        pass

    # ── Catalog Filtering ─────────────────────────────────────

    def filter_visible_catalog(
        self,
        full_catalog: list[Course],
        history: AcademicHistory
    ) -> list[Course]:
        """
        Return only courses whose prerequisites are satisfied.
        Backlogged courses are already included in full_catalog
        before this is called — this only filters by prerequisites.
        [Sprint 2 — stub]
        """
        pass

    def build_semester_catalog(
        self,
        full_catalog: list[Course],
        history: AcademicHistory
    ) -> list[Course]:
        """
        Build the full selectable catalog for the registration
        screen. Merges the base catalog with backlogged courses
        from history, then passes through filter_visible_catalog().
        [Sprint 2 — stub]
        """
        pass

    # ── Confirmation ──────────────────────────────────────────

    def confirm_registration(self, semester: Semester) -> bool:
        """
        Lock in the current selection. Adds each selected course
        to the active Semester's registered course list.
        Resets internal selection state after confirmation.
        Returns True if at least one course was registered.
        [Sprint 2 — stub]
        """
        pass

    # ── Tuition ───────────────────────────────────────────────

    def calculate_tuition_fee(
        self,
        backlogged_courses: list[Course]
    ) -> float:
        """
        Calculate the total tuition fee for backlogged courses.
        Applied post-Semester-12 at registration time.
        Formula: sum(course.creditValue * FLAT_TUITION_RATE)
        for each course in backlogged_courses.
        [Sprint 3 — activated when semesterNumber > 12]
        """
        pass

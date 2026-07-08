"""
academic_history.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation
AcademicHistory is the permanent academic ledger for the Player.
All completed course IDs, credit totals, and backlog tracking
are private — mutated only through validated public pipelines.
Survives across all semester resets (aggregated by Player).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from academic.course import Course


class AcademicHistory:
    """
    Permanent academic record for the player.
    Tracks completed courses, total credits, and backlogged courses.
    Used by RegistrationManager to filter the course catalog
    and by EndgameEvaluationManager to assess graduation status.

    OOP: Encapsulation — all lists are private, mutated via methods.
    """

    def __init__(self) -> None:
        self.__completed_course_ids: list[str] = []
        self.__total_credits_earned: int = 0
        self.__backlog_course_ids: list[str] = []

    # ── Prerequisite Check ────────────────────────────────────────

    def is_prerequisite_satisfied(self, course_id: str) -> bool:
        """
        Return True if the given course ID appears in the
        completed courses list. Used by RegistrationManager to
        decide whether to show a course in the catalog.
        """
        return course_id in self.__completed_course_ids

    # ── Completion Recording ──────────────────────────────────────

    def record_completion(self, course: Course) -> None:
        """
        Record a successfully passed course.
        Adds the courseID to completedCourseIDs and accumulates
        its credit value into totalCreditsEarned.
        Also removes the course from backlog if it was backlogged.
        [Sprint 3 — full integration with MainQuest.executeAction()]
        """
        pass

    def mark_course_incomplete(self, course: Course) -> None:
        """
        Mark a course as failed (isPassed = False).
        Does NOT add to backlog here — addBacklog() handles that.
        [Sprint 3 — implementation]
        """
        pass

    def add_backlog(self, course: Course) -> None:
        """
        Push a failed course's ID into the backlog list.
        RegistrationManager reads this list each semester to
        re-inject backlogged courses into the selectable catalog.
        The same Course instance is reused — no penalty counter.
        [Sprint 3 — implementation]
        """
        pass

    # ── Getters ───────────────────────────────────────────────────

    def get_total_credits_earned(self) -> int:
        """Return the cumulative credits earned across all semesters."""
        return self.__total_credits_earned

    def get_backlog_courses(self) -> list[str]:
        """
        Return the list of backlogged course IDs.
        Called by RegistrationManager.loadBackloggedCourses()
        at the start of each new semester.
        """
        return list(self.__backlog_course_ids)

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
        Also removes the course from backlog if it was backlogged
        (a course can only be "in progress" or "done", never both).
        Idempotent: calling this twice for the same course will not
        double-count credits.
        """
        course_id = course.get_course_id()

        if course_id in self.__completed_course_ids:
            return

        self.__completed_course_ids.append(course_id)
        self.__total_credits_earned += course.get_credit_value()

        if course_id in self.__backlog_course_ids:
            self.__backlog_course_ids.remove(course_id)

    def mark_course_incomplete(self, course: Course) -> None:
        """
        Mark a course as failed (isPassed = False).
        Does NOT add to backlog here — addBacklog() handles that,
        since MainQuest.executeAction() calls both in sequence
        (per the SSD: markCourseIncomplete() then addBacklog()).
        """
        course.set_passed_status(False)

    def add_backlog(self, course: Course) -> None:
        """
        Push a failed course's ID into the backlog list.
        RegistrationManager reads this list each semester to
        re-inject backlogged courses into the selectable catalog.
        The same Course instance is reused — no penalty counter,
        no duplicate entries if already backlogged.
        """
        course_id = course.get_course_id()
        if course_id not in self.__backlog_course_ids:
            self.__backlog_course_ids.append(course_id)

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
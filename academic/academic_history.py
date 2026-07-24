"""
academic_history.py

CSE Life: Compile & Conquer
Academic Package — Permanent Academic Ledger
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation
AcademicHistory is the permanent academic record for the Player.
It survives across every semester reset (aggregated inside Player,
never inside Semester), and is the single source of truth for:

    1. Which courses have been completed (feeds prerequisite checks)
    2. Total credits earned (feeds graduation evaluation)
    3. Which courses are currently backlogged (feeds catalog re-injection)

STATUS: Rebuilt to match the CURRENT Course API — earlier drafts
called course.get_course_id() / course.set_passed_status(), which
do not exist on Course anymore. This version uses the real methods:
get_course_code(), mark_completed(), mark_backlogged().
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from academic.course import Course


class AcademicHistory:
    """
    Permanent academic record for the player.
    Tracks completed course codes, total credits earned, and
    backlogged course codes. Used by RegistrationManager to
    filter the course catalog, and (later) by
    EndgameEvaluationManager to assess graduation status.

    OOP: Encapsulation — all lists/counters are private, mutated
         only through validated public methods below.
    """

    def __init__(self) -> None:
        self.__completed_course_codes: List[str] = []
        self.__total_credits_earned: int = 0
        self.__backlog_course_codes: List[str] = []

    # ── Prerequisite Check ────────────────────────────────────────

    def is_prerequisite_satisfied(self, course_code: str) -> bool:
        """
        Return True if the given course code (or category tag, e.g.
        "GED_CORE_1") appears in the completed courses list.
        Used by Course.are_prerequisites_satisfied() / the catalog
        filter to decide whether a course should be shown/selectable.
        """
        if not course_code:
            return False
        return course_code.strip().upper() in self.__completed_course_codes

    # ── Completion Recording ──────────────────────────────────────

    def record_completion(self, course: Course) -> None:
        """
        Record a successfully passed course.
        - Adds its course code to completedCourseCodes (once — this
          call is idempotent, calling it twice will NOT double-count
          credits).
        - Accumulates its credit value into totalCreditsEarned.
        - Removes it from the backlog list if it was previously
          backlogged (a course is either "in progress/failed" or
          "done" — never both at once).
        - Syncs the Course object's own lifecycle flag by calling
          course.mark_completed(), so is_completed()/is_backlogged()
          stay consistent with this ledger.
        """
        course_code = course.get_course_code()

        if course_code not in self.__completed_course_codes:
            self.__completed_course_codes.append(course_code)
            self.__total_credits_earned += course.get_credit_value()

        if course_code in self.__backlog_course_codes:
            self.__backlog_course_codes.remove(course_code)

        course.mark_completed()

    def mark_course_incomplete(self, course: Course) -> None:
        """
        Mark a course as failed for this attempt.
        Flips the Course object's own lifecycle flags via
        mark_backlogged() (is_completed -> False, is_backlogged -> True).
        Does NOT touch the ledger's backlog list here — add_backlog()
        handles that separately, since MainQuest.execute_action() is
        expected to call both in sequence: mark_course_incomplete()
        then add_backlog().
        """
        course.mark_backlogged()

    def add_backlog(self, course: Course) -> None:
        """
        Push a failed course's code into the backlog ledger.
        RegistrationManager reads this list each semester to
        re-inject backlogged courses into the selectable catalog.
        The same Course instance is reused — no duplicate entries
        if the course is already backlogged.
        """
        course_code = course.get_course_code()
        if course_code not in self.__backlog_course_codes:
            self.__backlog_course_codes.append(course_code)

    # ── Getters ───────────────────────────────────────────────────

    def get_total_credits_earned(self) -> int:
        """Return the cumulative credits earned across all semesters."""
        return self.__total_credits_earned

    def get_completed_course_codes(self) -> List[str]:
        """Return a defensive copy of all completed course codes."""
        return list(self.__completed_course_codes)

    def get_backlog_courses(self) -> List[str]:
        """
        Return the list of backlogged course codes.
        Called by RegistrationManager at the start of each new
        semester to rebuild the selectable catalog.
        """
        return list(self.__backlog_course_codes)
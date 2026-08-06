"""
engine/catalog_builder.py
CSE Life: Compile & Conquer — Registration catalog, phase R1
─────────────────────────────────────────────────────────────
PURE PYTHON. No pygame, no UI imports (Build Plan §0.7).

The one place that decides what ORDER the registration catalog
appears in: backlogged retakes pinned to the top, in the order
they were failed, then everything else in the catalog's own order.

    RegistrationManager.build_semester_catalog()   what is visible
                    │
                    ▼
    SemesterCatalogBuilder                         what order it is in
                    │
                    ▼
    ui/registration_screen.py                      how it is drawn

WHAT THIS MODULE DELIBERATELY DOES NOT DO
─────────────────────────────────────────
It does not filter by prerequisites and it does not re-inject
backlogged courses, because BOTH ALREADY WORK and belong to
`engine/registration_manager.py`:

  * `filter_visible_catalog()` drops completed courses and keeps
    only those whose prerequisites are satisfied — 43 of the 65
    courses are visible at semester 1, not a handful.
  * a backlogged course is never dropped, because
    `mark_backlogged()` leaves `is_completed()` False. The same
    Course instance is simply still there next term.

So this class WRAPS that method and never reimplements it. Two
reasons: one implementation of a rule is always better than two,
and if the lead ever repairs the known no-op in
`build_semester_catalog()`'s backlog loop (IMPLEMENTATION_PLAN §4
defect #4), this module inherits the fix for free.

COURSE IDENTITY IS LOAD-BEARING. A failed course is the SAME
object re-offered later (IMPLEMENTATION_PLAN §2.5). Nothing here
constructs, copies or replaces a Course — every element returned
is an object that came out of the input list.

Created by Nangiba Tasnim (Dev 3), branch nangiba-temp-01.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

if TYPE_CHECKING:                       # imported for type hints only, so
    from academic.course import Course  # this module stays cheap to import


class SemesterCatalogBuilder:
    """
    Orders one semester's registration catalog.

    OOP: Encapsulation — the snapshot used for new-unlock detection is
    private and only reachable through `snapshot()` /
    `get_newly_unlocked()`. Nothing here mutates a Course, an
    AcademicHistory or the RegistrationManager it was handed; every
    method is a read plus a reorder.

    The ordering is STABLE and TOTAL: the same inputs always produce
    the same list, in the same order, with no set iteration anywhere on
    the ordering path. Sets appear only as membership tests, never as
    something iterated — a set's iteration order is an implementation
    detail, and a catalog that reshuffled itself between frames would
    be unusable.
    """

    def __init__(self, registration_manager: Any) -> None:
        """
        Wrap the manager that owns prerequisite filtering.

        `registration_manager` is a `engine.registration_manager.
        RegistrationManager`; it is typed loosely so a test double with
        the one method this class calls works just as well.
        """
        self.__manager: Any = registration_manager
        self.__snapshot_codes: Optional[set] = None
        self.__unmatched_backlog_codes: List[str] = []

    # ── the catalog ───────────────────────────────────────────

    def build(self, full_catalog: Sequence["Course"],
              history: Any, current_semester_number: int) -> List["Course"]:
        """
        The semester's catalog, backlogged courses first.

        Retakes lead so a player never has to hunt for the course that
        just cost them a term; everything else follows in the order
        `build_semester_catalog()` returned it, which is course-code
        order and therefore already meaningful.

        CHANGE: current_semester_number is now required — it's passed
        straight through to RegistrationManager.build_semester_catalog(),
        which gates visibility by Course.is_offered_in_semester() as
        well as prerequisites. Callers get this from
        ctx.semester().get_semester_number().
        """
        backlogged, regular = self.partition(
            full_catalog, history, current_semester_number)
        return backlogged + regular

    def partition(self, full_catalog: Sequence["Course"],
                  history: Any, current_semester_number: int
                  ) -> Tuple[List["Course"], List["Course"]]:
        """
        Split the visible catalog into (backlogged, regular).

        Both halves are term + prerequisite-filtered, because both
        come out of the single `build_semester_catalog()` call this
        makes — the filtering is never repeated here.

        The backlog half follows `AcademicHistory.get_backlog_courses()`
        LEDGER order (oldest failure first), so a course deferred term
        after term keeps its place at the top instead of shuffling. The
        regular half keeps the catalog's own order and is deliberately
        NOT re-sorted.

        A course that is both backlogged and otherwise-visible
        appears exactly once, in the backlog half only.
        """
        visible: List["Course"] = list(
            self.__manager.build_semester_catalog(
                full_catalog, history, current_semester_number))
        by_code: Dict[str, "Course"] = {}
        for course in visible:
            # First wins: if a catalog ever carried two objects with one
            # code, the earlier one is the instance the rest of the game
            # is already holding.
            by_code.setdefault(course.get_course_code(), course)

        backlogged: List["Course"] = []
        matched_codes: set = set()
        self.__unmatched_backlog_codes = []
        for code in self.__backlog_codes(history):
            course = by_code.get(code)
            if course is None:
                # A backlogged code with no visible course — the player
                # failed something that is no longer offered. Skipped
                # silently rather than raising or emitting a None; the
                # count is readable through get_unmatched_backlog_codes().
                self.__unmatched_backlog_codes.append(code)
                continue
            if code in matched_codes:
                continue                       # a duplicated ledger entry
            matched_codes.add(code)
            backlogged.append(course)

        regular: List["Course"] = [
            course for course in visible
            if course.get_course_code() not in matched_codes]
        return (backlogged, regular)

    def get_backlogged(self, full_catalog: Sequence["Course"],
                       history: Any, current_semester_number: int
                       ) -> List["Course"]:
        """Just the backlog subset, in ledger order."""
        return self.partition(full_catalog, history, current_semester_number)[0]

    def get_unmatched_backlog_codes(self) -> List[str]:
        """
        Backlog codes the last `partition()` could not match to a visible
        course. Normally empty; exposed so the condition is observable
        rather than silent.
        """
        return list(self.__unmatched_backlog_codes)

    # ── new-unlock tracking ───────────────────────────────────

    def snapshot(self, catalog: Sequence["Course"]) -> None:
        """
        Record the current course codes as the baseline that
        `get_newly_unlocked()` compares against.

        Call once per semester turnover, before rebuilding. Calling it
        again simply moves the baseline forward.
        """
        self.__snapshot_codes = {course.get_course_code()
                                 for course in catalog}

    def has_snapshot(self) -> bool:
        """True once `snapshot()` has been called at least once."""
        return self.__snapshot_codes is not None

    def clear_snapshot(self) -> None:
        """Forget the baseline — a fresh run starts with nothing new."""
        self.__snapshot_codes = None

    def get_newly_unlocked(self,
                           catalog: Sequence["Course"]) -> List["Course"]:
        """
        Courses in `catalog` whose codes were absent from the last
        snapshot, in the order they appear in `catalog`.

        Empty before the first `snapshot()` — semester 1 is not "all
        new", and a screen that tagged all 43 opening courses NEW would
        be telling the player nothing.

        This is a DISPLAY HINT ONLY. It never affects ordering and never
        affects whether a course can be selected.
        """
        if self.__snapshot_codes is None:
            return []
        baseline = self.__snapshot_codes
        return [course for course in catalog
                if course.get_course_code() not in baseline]

    # ── private helpers ───────────────────────────────────────

    @staticmethod
    def __backlog_codes(history: Any) -> List[str]:
        """
        The backlog ledger as a list of codes, defensively.

        `get_backlog_courses()` returns codes, not Course objects — the
        name is a long-standing wart in `academic/academic_history.py`
        and is exactly the kind of thing that produces an AttributeError
        three call frames away. Normalising here keeps that confusion
        contained to one method.
        """
        try:
            codes = history.get_backlog_courses()
        except AttributeError:
            return []
        return [str(code) for code in (codes or ())]


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to inspect the ordering.
# Abu Huraira removes this block when he plugs in the real game.
#
#     python -m engine.catalog_builder
#
# There is no window and no F11: this module is pure Python and
# draws nothing, so its stub is a plain-text dump. It simulates
# three semesters over the REAL 65-course catalog -- register six,
# pass four, fail two, advance -- and prints the catalog head each
# term with [BACKLOG] and [NEW] markers, so the ordering can be
# checked before any pixel is drawn.
# -------------------------------------------------------------
if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    from academic.academic_history import AcademicHistory
    from academic.course_catalog import build_course_catalog
    from engine.registration_manager import RegistrationManager

    HEAD_ROWS = 10          # how much of each catalog to print
    REGISTER_PER_TERM = 6   # a full 15-credit load, roughly
    FAIL_PER_TERM = 2       # how many of them go to the backlog

    demo_catalog = build_course_catalog()
    demo_history = AcademicHistory()
    demo_builder = SemesterCatalogBuilder(RegistrationManager())

    def dump(term: int, courses: list, fresh: list) -> None:
        """Print the head of one semester's catalog with its markers."""
        fresh_codes = {c.get_course_code() for c in fresh}
        backlog_codes = set(demo_history.get_backlog_courses())
        print(f"\nSEMESTER {term}  --  {len(courses)} courses visible, "
              f"{len(backlog_codes)} backlogged, {len(fresh)} newly unlocked")
        print("     code       cr  name")
        print("     " + "-" * 62)
        for index, course in enumerate(courses[:HEAD_ROWS]):
            code = course.get_course_code()
            tag = "[BACKLOG]" if code in backlog_codes else \
                  ("[NEW]" if code in fresh_codes else "")
            print(f"  {index:>2} {code:<10} {course.get_credit_value():>2}  "
                  f"{course.get_course_name()[:34]:<34} {tag}")
        if len(courses) > HEAD_ROWS:
            print(f"     ... {len(courses) - HEAD_ROWS} more")

    for semester in range(1, 4):
        catalog = demo_builder.build(demo_catalog, demo_history, semester)
        newly = demo_builder.get_newly_unlocked(catalog)
        dump(semester, catalog, newly)

        # Snapshot BEFORE the term is simulated, so next semester's
        # "new" means "unlocked by what just happened".
        demo_builder.snapshot(catalog)

        registered = catalog[:REGISTER_PER_TERM]
        if not registered:
            break
        # The LAST two of the load fail. Failing the first two would keep
        # failing the same gateway course every term, nothing downstream
        # would ever unlock, and the [NEW] marker would never fire --
        # which would make this dump prove only half of what it should.
        passed = registered[:-FAIL_PER_TERM]
        failed = registered[-FAIL_PER_TERM:]
        for done in passed:
            demo_history.record_completion(done)
        for flunked in failed:
            demo_history.mark_course_incomplete(flunked)
            demo_history.add_backlog(flunked)
        print(f"     registered {[c.get_course_code() for c in registered]}")
        print(f"     passed     {[c.get_course_code() for c in passed]}")
        print(f"     FAILED     {[c.get_course_code() for c in failed]}")

    print("\nfinal backlog ledger:", demo_history.get_backlog_courses())
    print("completed:", len(demo_history.get_completed_course_codes()),
          "courses,", demo_history.get_total_credits_earned(), "credits")
    if demo_builder.get_unmatched_backlog_codes():
        print("unmatched backlog codes:",
              demo_builder.get_unmatched_backlog_codes())
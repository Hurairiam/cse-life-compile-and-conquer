"""
engine/exam_days.py
How many days this term's unsat exams still need. One answer, one place.

WHY THIS FILE EXISTS
────────────────────
Task 7 needs the same number twice: it gates "advance to next semester"
and it floors "drain timepool". The brief calls it "days still needed to
complete all remaining exams this semester" and assumes the repo has it.

IT DOES NOT. Recon found the number nowhere — only the three ingredients,
in three different modules:

    engine/final_exam.py::registered_count(ctx)  how many exams the term set
    ctx.exam["course_index"]                     how many have been sat
    academic/quest.py::MainQuest.execute_action  what one costs

So it is computed here, once, and both options call it. Two call sites
deriving it separately is exactly the drift the phase brief forbids —
a gate that says "you may leave" while the floor still reserves days for
an exam is a save the player cannot finish.

WHY 14 AND NOT 10
─────────────────
`MainQuest.execute_action()` charges `10 if self.__is_optimized else 14`.
Optimisation is decided per attempt, at attempt time, so the cost of an
exam the player has NOT sat yet is not knowable now — it is 10 or 14 and
nothing here can tell which.

The floor therefore reserves the LARGER. Reserving 14 and needing 10
leaves the player four spare days; reserving 10 and needing 14 strands
an exam they can no longer afford, with no way back. One of those errors
is a rounding difference and the other ends a run, so this is not a
tuning choice — it is the only safe direction, and STANDARD_DAY_COST is
named rather than inlined so the reason survives.

NOTHING HERE SPENDS ANYTHING. It reports. engine/day_drain.py does the
spending, through GameClock, as it already did.
"""
from __future__ import annotations

from typing import Any

from engine import day_drain, final_exam

# academic/quest.py::MainQuest.execute_action() — the two costs an exam
# attempt can carry. Read as constants rather than imported because they
# are local ints inside that method, not module-level names.
OPTIMIZED_DAY_COST: int = 10
STANDARD_DAY_COST: int = 14


def remaining_exams(ctx: Any) -> int:
    """
    How many of this term's registered exams have not been sat.

    `course_index` is the exam screen's own cursor — the same value
    `final_exam.is_finished()` compares against the registered count, so
    this cannot disagree with the gate about what "finished" means.
    """
    try:
        sat = int(ctx.exam.get("course_index", 0))
    except (AttributeError, TypeError, ValueError):
        sat = 0
    return max(0, final_exam.registered_count(ctx) - sat)


def days_needed(ctx: Any) -> int:
    """
    Days that must stay in the pool for every remaining exam.

    THE number. The gate and the floor both read this and nothing else.
    Zero once the exams are done, which is what makes the floor vanish
    exactly when the gate opens.
    """
    return remaining_exams(ctx) * STANDARD_DAY_COST


def drainable(ctx: Any) -> int:
    """
    The most days the player may drain without stranding an exam.

    `day_drain.passable()` is the ceiling that already existed — the
    term's remaining days, never more than the player's own pool holds —
    and the exam reserve comes off it. Never negative: a term already
    below its own reserve offers nothing to drain rather than a negative
    range no input could satisfy.
    """
    return max(0, day_drain.passable(ctx) - days_needed(ctx))


def can_drain(ctx: Any) -> bool:
    """True when there is at least one day the player may spend."""
    return drainable(ctx) > 0


def can_advance(ctx: Any) -> bool:
    """
    True when the term may be closed.

    Delegated to `final_exam.is_finished()` rather than re-tested as
    `remaining_exams(ctx) == 0`: that module has owned the question since
    Phase 7 and `engine/states/end_semester.py` has always asked it. Two
    spellings of the same predicate is how they start disagreeing.
    """
    return final_exam.is_finished(ctx)


def is_in_range(ctx: Any, days: Any) -> bool:
    """
    True when `days` is a legal amount to drain.

    Rejects non-numeric input, negatives and zero as well as anything
    over the ceiling — all four are the same answer to the caller, and
    deciding them here keeps the popup free of validation rules.
    """
    try:
        wanted = int(days)
    except (TypeError, ValueError):
        return False
    return 1 <= wanted <= drainable(ctx)


def clamp(ctx: Any, days: Any) -> int:
    """`days` pulled into the legal range, or 0 when there is none."""
    ceiling = drainable(ctx)
    if ceiling <= 0:
        return 0
    try:
        wanted = int(days)
    except (TypeError, ValueError):
        return 0
    return max(1, min(wanted, ceiling))


# -------------------------------------------------------------
# STUB TEST — the repo's convention for a module with no suite.
#     py -m engine.exam_days
# -------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    from academic.semester import Semester
    from core.character.player import Player
    from engine.game_clock import GameClock

    class _Session:
        def __init__(self, player, semester):
            self.player, self.sem = player, semester

        def get_active_semester(self):
            return self.sem

        def get_active_player(self):
            return self.player

        def get_is_frozen(self):
            return False

        def increment_global_clock(self, days):
            pass

    class _Ctx:
        """Real Player, Semester and GameClock; courses faked by count."""

        def __init__(self, courses=3, sat=0, spent=0):
            self.__player = Player()
            self.__sem = Semester(1)
            if spent:
                self.__sem.deduct_time(spent)
                self.__player.deduct_time_pool_days(spent)
            self.__courses = ["c"] * courses
            self.exam = {"course_index": sat}
            self.session = _Session(self.__player, self.__sem)
            self.game_clock = GameClock(self.session)
            self.__sem.get_registered_courses = lambda: self.__courses

        def semester(self):
            return self.__sem

        def player(self):
            return self.__player

    # -- a fresh term: three exams unsat, 42 days reserved ---------
    fresh = _Ctx(courses=3, sat=0)
    assert remaining_exams(fresh) == 3
    assert days_needed(fresh) == 42, days_needed(fresh)
    assert drainable(fresh) == 80 - 42 == 38
    assert can_drain(fresh) and not can_advance(fresh)

    # -- two sat, one to go ----------------------------------------
    partway = _Ctx(courses=3, sat=2)
    assert remaining_exams(partway) == 1 and days_needed(partway) == 14
    assert drainable(partway) == 66
    assert not can_advance(partway), "advance opened with an exam unsat"

    # -- all sat: the reserve disappears as the gate opens ---------
    done = _Ctx(courses=3, sat=3)
    assert remaining_exams(done) == 0 and days_needed(done) == 0
    assert can_advance(done), "advance stayed shut with every exam sat"
    assert drainable(done) == 80, "the reserve outlived the exams"

    # -- the floor bites: 20 days left, 1 exam owed ---------------
    tight = _Ctx(courses=3, sat=2, spent=60)
    assert day_drain.passable(tight) == 20 and days_needed(tight) == 14
    assert drainable(tight) == 6, drainable(tight)
    assert is_in_range(tight, 6) and not is_in_range(tight, 7)
    assert clamp(tight, 99) == 6 and clamp(tight, 0) == 1

    # -- already under the reserve: nothing to drain, never negative
    stranded = _Ctx(courses=3, sat=2, spent=70)
    assert day_drain.passable(stranded) == 10 and days_needed(stranded) == 14
    assert drainable(stranded) == 0, "offered days that are not there"
    assert not can_drain(stranded) and not is_in_range(stranded, 1)
    assert clamp(stranded, 5) == 0

    # -- the four rejections are one answer ------------------------
    for bad in (0, -1, "", "abc", None, 3.9e9):
        assert not is_in_range(fresh, bad), "accepted %r" % (bad,)
    assert is_in_range(fresh, "12"), "refused a numeric string"

    # -- a term with nothing registered has nothing to reserve -----
    empty = _Ctx(courses=0, sat=0)
    assert remaining_exams(empty) == 0 and days_needed(empty) == 0
    assert not can_advance(empty), "a term with no exams claimed to be done"

    print("exam_days: all checks passed")

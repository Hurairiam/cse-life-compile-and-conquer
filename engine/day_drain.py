"""
engine/day_drain.py
Passing the rest of the semester in one go: the action, and the rule.

WHY THIS IS ITS OWN FILE
────────────────────────
The same reason engine/menu_prop.py, engine/day_warning.py and
engine/final_exam.py are: a new module cannot produce a merge conflict.
Nothing shared needed opening for the behaviour at all — the only edits
outside this phase's own two new files are one appended ScreenState
member and one appended MENU_REGISTRY row.

Named beside engine/day_warning.py rather than after the screen, because
the screen is engine/states/pass_days.py and two modules with the same
basename in different packages read as a mistake even when they import
fine. "Drain" is also the one verb in this game that cannot be misread —
"pass" already means something to anybody sitting an exam.

IT SPENDS DAYS THE WAY EVERYTHING ELSE DOES
───────────────────────────────────────────
`PassDaysAction` is a TimeConsumable put through
`GameClock.process_time_consumable()`, the single entry point for every
time-costing action in the game. That is not ceremony, it is the whole
reason Phase 6's warning popup and Phase 6's HUD chip fire on the way
down without one line of either being repeated here: the clock deducts
the semester's own counter, `day_warning.check()` reads that counter
every frame from exploration.update(), and state_router derives the chip
from it every frame as well. Crossing the threshold by passing days is
therefore indistinguishable from crossing it by sitting an exam.

`GateEntryAction` (engine/gate_evaluator.py) is the precedent for a
TimeConsumable that is not a Quest, run through the clock the same way
by engine/gate_service.py.

WHAT IT DOES NOT DO (owner ruling, Phase 11)
────────────────────────────────────────────
Reaching zero days triggers nothing on its own in this game — there is
no daily tick, `Semester.is_semester_complete()` is called by nothing,
and Phase 6 removed the one automatic reaction a low pool ever had. This
module keeps it that way: it drains, and hands the player back to the
map. It does not open the exam, and it does not roll the semester over.
Those doors are still `engine/states/exam.py` and the end_semester prop,
reached on purpose.

It also does not refuse while exams are unsat (the other half of the
same ruling). A term drained before its finals will backlog whatever was
never sat, exactly as a term that ran out of days already does — the
confirmation names the cost and CANCEL is always there.
"""
from __future__ import annotations

from core.interfaces import TimeConsumable
from engine import day_warning


class PassDaysAction(TimeConsumable):
    """
    Spend a fixed number of days and buy nothing with them.

    Every other TimeConsumable in the game exchanges days for something
    — credits, EXP, a door. This one is the whole point of the prop: the
    days are the cost *and* the effect, so execute_action() deducts and
    returns.

    The cost is fixed at construction, the way GateEntryAction fixes a
    toll, because GameClock reads get_time_cost() BEFORE calling
    execute_action() and advances the global career clock by it. A cost
    that recomputed itself between those two calls is precisely the
    drift MainQuest.get_time_cost() was overridden to stop.

    OOP: Polymorphism — GameClock runs this without knowing it is a prop.
    """

    def __init__(self, days: int) -> None:
        self.__days: int = max(0, int(days))

    @classmethod
    def for_semester(cls, ctx):
        """
        The action for the term as it stands, or None when there is
        nothing left to pass.

        None rather than a zero-day action, for the reason
        GateEntryAction.for_gate() refuses a free gate: a zero-cost item
        pushed through the clock advances the global career clock by
        nothing and reads, in every log and every counter, as an action
        that happened.
        """
        days = passable(ctx)
        if days <= 0:
            return None
        return cls(days)

    def get_time_cost(self) -> int:
        """Days this costs. Read by GameClock before execute_action()."""
        return self.__days

    def execute_action(self, player) -> None:
        """
        Take the days off the player's own pool.

        GameClock takes the same number off the semester's pool straight
        afterwards — the two counters are separate ints and the clock is
        the one place that touches both (see its own BUG FIX note).
        `passable()` guarantees the player can afford this, so the
        deduction cannot silently refuse and leave the two pools apart.
        """
        if self.__days > 0:
            player.deduct_time_pool_days(self.__days)


# ── the rule ───────────────────────────────────────────────────

def remaining(ctx) -> int:
    """
    Days left in the active semester.

    Deliberately delegated to engine/day_warning.py rather than reading
    the semester here. Phase 6 built that module to be the single front
    door for the day rule and named this phase as one of its two callers;
    a second reader of the same counter would be a second place to change
    when it moves.
    """
    return day_warning.remaining(ctx)


def passable(ctx) -> int:
    """
    Days this action may actually charge: the term's remaining days,
    never more than the player's own pool holds.

    THE TWO POOLS. `Player.__time_pool_days` and
    `Semester.__time_pool_days` are independent ints, kept in step by
    GameClock deducting the same number from each. One place still
    parts them: `save_bridge.restore()` rebuilds the Player with a full
    80 days and replays the term's spend onto the Semester only, so a
    loaded game has a player pool at or above the term's.

    In every reachable state the term's count is therefore the smaller
    one, which is exactly what the brief asks to drain — so the min()
    changes no number in practice. What it buys is a guarantee: the cost
    GameClock reads, the days execute_action() takes off the player and
    the days GameClock takes off the semester are one number and cannot
    disagree, whatever a save file turns out to hold.
    """
    days = remaining(ctx)
    try:
        pool = int(ctx.player().get_time_pool_days())
    except (AttributeError, TypeError, ValueError):
        pool = days
    return max(0, min(int(days), pool))


def can_pass(ctx) -> bool:
    """True when there is at least one day left to pass."""
    return passable(ctx) > 0


def drain(ctx) -> int:
    """
    Pass every remaining day of the term. Returns how many were passed.

    Measured off the semester's counter before and after rather than
    reported from the action's own cost: `process_time_consumable()`
    does nothing at all on a frozen session, and a caller that trusted
    the intent would report a spend that never happened.
    """
    action = PassDaysAction.for_semester(ctx)
    if action is None:
        return 0
    before = remaining(ctx)
    ctx.game_clock.process_time_consumable(action)
    return max(0, before - remaining(ctx))


# -------------------------------------------------------------
# STUB TEST — the repo's convention for a module with no suite.
# Runs headless against the REAL GameClock, Semester and Player, so
# what it proves is the pipeline and not a mock of it.
#     py -m engine.day_drain
# (as a module, so the project root stays on the import path)
# -------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    from academic.semester import Semester
    from core.character.player import Player
    from engine.game_clock import GameClock

    class _Session:
        """The three things GameClock asks a session for."""

        def __init__(self, player, semester, frozen=False):
            self.player, self.sem = player, semester
            self.frozen, self.clock_days = frozen, 0

        def get_active_semester(self):
            return self.sem

        def get_active_player(self):
            return self.player

        def get_is_frozen(self):
            return self.frozen

        def increment_global_clock(self, days):
            self.clock_days += days

    class _Ctx:
        def __init__(self, spent=0, frozen=False, player_days=None):
            self.__player = Player()
            self.__sem = Semester(1)
            if spent:
                self.__sem.deduct_time(spent)
                self.__player.deduct_time_pool_days(spent)
            if player_days is not None:
                # A loaded save: restore() replays the spend onto the
                # semester only, so the player pool sits higher.
                self.__player.reset_time_pool()
                self.__player.deduct_time_pool_days(80 - player_days)
            self.session = _Session(self.__player, self.__sem, frozen)
            self.game_clock = GameClock(self.session)

        def semester(self):
            return self.__sem

        def player(self):
            return self.__player

    # -- nothing to pass -------------------------------------------
    empty = _Ctx(spent=80)
    assert remaining(empty) == 0 and passable(empty) == 0
    assert not can_pass(empty), "offered to pass a term with no days"
    assert PassDaysAction.for_semester(empty) is None, "built a 0-day action"
    assert drain(empty) == 0 and empty.session.clock_days == 0

    # -- a full term ------------------------------------------------
    full = _Ctx()
    assert passable(full) == 80 and can_pass(full)
    assert PassDaysAction.for_semester(full).get_time_cost() == 80
    assert drain(full) == 80, "did not pass every day"
    assert remaining(full) == 0, "semester pool not drained"
    assert full.player().get_time_pool_days() == 0, "player pool not drained"
    assert full.session.clock_days == 80, "global career clock did not move"
    assert not can_pass(full), "still offering days after the drain"
    assert drain(full) == 0, "drained a second time"

    # -- a part-spent term -----------------------------------------
    part = _Ctx(spent=48)
    assert passable(part) == 32
    assert drain(part) == 32 and remaining(part) == 0
    assert part.session.clock_days == 32, "clock advanced by the wrong count"

    # -- one day ----------------------------------------------------
    one = _Ctx(spent=79)
    assert passable(one) == 1 and drain(one) == 1 and remaining(one) == 0

    # -- the cost never outruns the player's own pool ---------------
    loaded = _Ctx(player_days=80)
    loaded.semester().deduct_time(60)              # a loaded save: 20 / 80
    assert remaining(loaded) == 20 and passable(loaded) == 20
    assert drain(loaded) == 20 and remaining(loaded) == 0
    assert loaded.player().get_time_pool_days() == 60, "took the wrong pool"
    assert loaded.session.clock_days == 20

    short = _Ctx()
    short.player().deduct_time_pool_days(75)       # player 5, semester 80
    assert passable(short) == 5, "cost outran the pool it deducts from"
    assert drain(short) == 5, "the two pools disagreed"
    assert short.player().get_time_pool_days() == 0
    assert short.session.clock_days == 5

    # -- a frozen session spends nothing, and says so ---------------
    frozen = _Ctx(frozen=True)
    assert can_pass(frozen), "the rule is about days, not the freeze"
    assert drain(frozen) == 0, "reported a spend a frozen clock refused"
    assert remaining(frozen) == 80 and frozen.session.clock_days == 0

    # -- the Phase 6 threshold is crossed, not re-implemented -------
    crossing = _Ctx(spent=20)                      # 60 days, well clear
    assert not day_warning.is_low(crossing)
    drain(crossing)
    assert day_warning.is_low(crossing), "the drain did not cross the rule"
    assert day_warning.hud_days(crossing) == 0, "no chip after the drain"

    print("day_drain: all checks passed")

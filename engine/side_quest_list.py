"""
engine/side_quest_list.py
CSE Life: Compile & Conquer
Phase 14 — what the PC in the player's room is allowed to show

One job: turn the quest state machine plus the days left in the term
into the rows a list can draw, and answer whether a row may be started.

WHY THIS IS ITS OWN FILE
────────────────────────
Recon hazard #4, and the precedent `engine/menu_prop.py`,
`engine/day_drain.py`, `engine/final_exam.py` and `engine/quest_offer.py`
all set: a new file cannot produce a merge conflict, and the visibility
rule below is the one thing in this phase that must not be got wrong
twice in two places. `engine/states/side_quests.py` draws and takes
input; every decision about what exists and what may be started is
here, with no pygame, no screen state and no UI in sight — so it can be
tested headless, and it is.

THE VISIBILITY RULE, AND WHY IT IS ABSOLUTE
───────────────────────────────────────────
    Unlocked   shown, selectable
    Completed  shown, marked complete, not selectable
    Unoffered  HIDDEN
    Declined   HIDDEN
    Missed     HIDDEN

The three hidden states are hidden ENTIRELY. Not greyed, not a locked
slot, not a gap in a numbering, not a "3 of 12" counter anywhere on the
card. A player who declined Rafi in semester 3 must be unable to tell
that anything was ever on offer — the consequence of that answer is
Phase 16's ending to reveal, and one stray count on this screen would
give it away eight semesters early.

`listed_ids()` is the only function that decides membership, and it
reads `get_unlocked_quests()` + `get_completed_quests()` — the two
positive lists — rather than filtering the twelve and skipping some.
There is nothing in this module that can enumerate a hidden quest, so
nothing downstream can accidentally count one.

THE DAY RULE — TWO OF THEM NOW
──────────────────────────────
1. A quest costs `day_cost` days (2 for all twelve today). With fewer
   days than that left in the term, the quest is not startable.
2. **Phase 17.** Once the term has run down to the end-of-semester
   threshold, NO new lecture may be started at all, whatever it costs
   and however many days are notionally left.

Both are checked in one place, `is_startable()`, and the reason each
one refuses is spelled out by `refusal()`. The confirmation is never
opened, nothing is deducted, and there is no override for either.

Phase 14 wrote "nothing here consults the firewall, so there is exactly
one place for Phase 17 to land". This is that landing: `is_locked_out()`
below. It reads `engine/day_warning.py` — Phase 6's single front door
onto `GameClock.get_min_border()` — so there is still exactly one 15 in
the codebase and not one number in this file.

WHAT THE LOCKOUT DOES NOT DO (Decision D1 and the NOTES reading, owner
ruling, Phase 17)
─────────────────────────────────────────────────────────────────────
  * It does not touch the NPC offer. D1 answer (a): the offer is still
    presented and can still be accepted below the threshold, so
    `engine/quest_offer.py` and `engine/dialogue_flow.py` are not
    opened by this phase at all.
  * It does not change one quest state. A quest already Unlocked stays
    Unlocked, stays listed on the PC, and is startable again the moment
    the next term refills the pool. Blocking here writes nothing —
    `refusal()` is a pure function and always was.
  * It does not hide anything. The rows are exactly the rows Phase 14
    listed; only START is refused.

WHAT THIS MODULE DOES NOT DO
────────────────────────────
It does not modify the state machine — no `accept`, no `decline`, no
`mark_completed`. It does not deduct days, open a lecture or touch the
skill tree. Confirming a quest logs the id and stops, which is the whole
of this phase's last line: the reader is Phase 15's.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from content.level_registry import get_skill_display_name
from content.side_quest_definitions import (
    get_day_cost,
    get_lecture_sheets,
    get_skill_id,
)
from engine.quest_state import (
    STATE_COMPLETED,
    STATE_UNLOCKED,
    QuestStateError,
    QuestStateMachine,
)

# What a confirmed selection writes to stdout. Phase 15 replaces the
# print with a call into the reader; the prefix is here so the line is
# greppable and so a test can assert on it rather than on formatting.
LOG_PREFIX: str = "[side quest] confirmed: "

# Remembered so the log line has somewhere to be read back from — by the
# tests today, and by Phase 15 when it hands the id to the reader.
# Module-level and transient by design, the way engine/states/teleport.py
# keeps its destination list: a confirmation is not a decision the save
# file has any business carrying, and nothing is written to the machine
# here for it to disagree with.
__last_confirmed: Optional[str] = None

# What threshold() answers when the context has no clock to ask. Below
# every possible day count, so the lockout simply never applies rather
# than applying wrongly — see threshold().
NO_THRESHOLD: int = -1


# ── reading the world ──────────────────────────────────────────

def machine_of(ctx: Any) -> Optional[QuestStateMachine]:
    """
    The quest state machine on a context, or None.

    None rather than an exception: the editor, the standalone harnesses
    and a half-built AppContext all have no machine, and a PC that opens
    an empty list beats one that takes the game down.
    """
    machine = getattr(ctx, "quest_states", None)
    if not isinstance(machine, QuestStateMachine):
        return None
    return machine


def days_left(ctx: Any) -> int:
    """
    Days left in the current semester, or 0 when there is no semester.

    The SEMESTER's counter, not the Player's. Recon §7 records that the
    two are separate ints and that the HUD and the firewall both read
    this one — so the number quoted on this card is the number the
    player can already see in the strip at the top of the screen.
    """
    getter = getattr(ctx, "semester", None)
    if getter is None:
        return 0
    try:
        semester = getter()
        return int(semester.get_time_pool_days())
    except (AttributeError, TypeError, ValueError):
        return 0


# ── the end-of-term lockout (Phase 17) ─────────────────────────

def threshold(ctx: Any) -> int:
    """
    Days at or below which no new lecture may be started, or
    NO_THRESHOLD when this context has no clock to ask.

    DELEGATED, NOT REDEFINED. `engine/day_warning.py::threshold()` is
    Phase 6's single front door onto `GameClock.get_min_border()` — the
    "15-Day Borderline Firewall" the clock has owned since Sprint 2 —
    and its own docstring names this phase as the caller. Writing a 15
    in here would be two numbers claiming to be one rule.

    IMPORTED LAZILY, for the reason `engine/dialogue_flow.py` imports
    `ui.popup` lazily: day_warning reaches into `ui/popup.py` for its
    severity constant, and the whole point of this module is that it can
    be read with no pygame and no display. The import lands in
    sys.modules on the first call and costs a dict lookup after that.

    NO_THRESHOLD is the quiet answer, matching `machine_of()` and
    `days_left()`: the editor, the standalone harnesses and the stub
    contexts these rules are tested with have no `game_clock`, and the
    honest reading of "there is no clock" is that there is no
    end-of-term rule to enforce — not that everything is locked.
    """
    from engine import day_warning
    try:
        return int(day_warning.threshold(ctx))
    except (AttributeError, TypeError, ValueError):
        return NO_THRESHOLD


def is_locked_out(ctx: Any) -> bool:
    """
    True once the term has run down far enough to refuse new lectures.

    The verdict itself is `day_warning.is_low()` rather than a compare
    written out here, so the popup Phase 6 fires and the block this
    phase applies can never disagree about where the line is: the
    player is told the term is running out by exactly the rule that
    then stops them taking anything new on.
    """
    from engine import day_warning
    try:
        return bool(day_warning.is_low(ctx))
    except (AttributeError, TypeError, ValueError):
        return False


def listed_ids(ctx: Any) -> List[str]:
    """
    The quest ids this PC may show, in semester order.

    Unlocked and Completed only, and built from the machine's two
    positive lists rather than by filtering the twelve — see the module
    docstring. Both lists already come back in semester order, so
    merging them by that order keeps a run reading as a run.
    """
    machine = machine_of(ctx)
    if machine is None:
        return []
    shown = set(machine.get_unlocked_quests()) | set(
        machine.get_completed_quests())
    # get_all_states() is the machine's own semester ordering; the
    # membership test above is what keeps the hidden three out.
    return [quest_id for quest_id in machine.get_all_states()
            if quest_id in shown]


# ── one row's worth of facts ───────────────────────────────────

def entry(ctx: Any, quest_id: str) -> Dict[str, Any]:
    """
    Everything a row needs about one quest, and nothing else.

    Keys: quest_id, title, day_cost, sheets, completed, affordable.
    `title` is the skill tree's own display name for the skill this
    quest feeds ("Git & GitHub"), so the PC and the tree call the same
    topic the same thing.
    """
    machine = machine_of(ctx)
    state = ""
    if machine is not None:
        try:
            state = machine.get_state(quest_id)
        except QuestStateError:                 # unknown id -> not shown
            state = ""
    day_cost = get_day_cost(quest_id)
    return {
        "quest_id": quest_id,
        "title": get_skill_display_name(get_skill_id(quest_id)),
        "day_cost": day_cost,
        "sheets": len(get_lecture_sheets(quest_id)),
        "completed": state == STATE_COMPLETED,
        "affordable": days_left(ctx) >= day_cost,
    }


def entries(ctx: Any) -> List[Dict[str, Any]]:
    """Every row the card shows, in the order it shows them."""
    return [entry(ctx, quest_id) for quest_id in listed_ids(ctx)]


# ── may this row be started? ───────────────────────────────────

def is_startable(ctx: Any, quest_id: Any) -> bool:
    """
    True when this quest may be confirmed right now.

    Four ways to be False, and `refusal()` names each of them: the
    quest is not on this list at all, it is already Completed, the term
    has run down past the end-of-semester threshold, or it has fewer
    days left than the quest costs. There is no fifth, and no override.
    """
    return refusal(ctx, quest_id) is None


def refusal(ctx: Any, quest_id: Any) -> Optional[Tuple[str, List[str]]]:
    """
    Why this quest cannot be started — (title, body lines) — or None.

    Shaped for `ui/popup.py`, which draws at most three centred body
    lines, and no message below is longer than that. A refusal always
    says the number it is refusing on, because "not enough days" without
    the two figures is a wall rather than an answer — and the lockout
    quotes both the days left and the threshold for the same reason.
    """
    machine = machine_of(ctx)
    if machine is None or quest_id not in listed_ids(ctx):
        # Not a row on this card. Unreachable from the list itself,
        # which only ever offers what listed_ids() produced.
        return ("NOTHING SELECTED",
                ["There is no lecture here to open."])

    state = machine.get_state(quest_id)
    if state == STATE_COMPLETED:
        return ("ALREADY READ",
                ["You have been through these notes.",
                 "There is nothing new left in them."])
    if state != STATE_UNLOCKED:
        # Belt and braces: listed_ids() cannot produce one of these.
        return ("NOTHING SELECTED",
                ["There is no lecture here to open."])

    left = days_left(ctx)
    # THE END-OF-TERM LOCKOUT (Phase 17), ABOVE THE COST CHECK.
    # It is the wider rule of the two: below the threshold nothing new
    # may be started whatever it costs, so a topic the player could
    # otherwise afford is refused here and refused for the right reason.
    # Checked BELOW the state checks so a Completed topic still reads
    # "ALREADY READ" — the term running out is not why that one is shut.
    #
    # Phrased as one sentence across the last two lines, the way
    # engine/day_warning.py's own popup is: three lines is the popup's
    # hard maximum and this uses all of them.
    if is_locked_out(ctx):
        return ("TOO LATE IN THE TERM",
                ["Only %s left before the exams." % __days(left),
                 "No new lecture may be started",
                 "with %s or fewer." % __days(threshold(ctx))])

    cost = get_day_cost(quest_id)
    if left < cost:
        return ("NOT ENOUGH DAYS",
                ["This lecture needs %s." % __days(cost),
                 "You have %s left in this term." % __days(left)])
    return None


def confirmation(ctx: Any, quest_id: Any) -> Tuple[str, List[str]]:
    """
    The question asked before a lecture is started — (title, lines).

    States the day cost and warns that the lecture has to be finished in
    one sitting, which is the part the player cannot find out any other
    way. Three lines exactly, the popup's hard maximum.
    """
    row = entry(ctx, quest_id)
    return ("START THIS LECTURE?",
            ["%s · %d sheet%s." % (row["title"], row["sheets"],
                                   "" if row["sheets"] == 1 else "s"),
             "It costs %s of this term." % __days(row["day_cost"]),
             "It must be finished in one sitting."])


# ── confirming ─────────────────────────────────────────────────

def confirm(quest_id: Any) -> str:
    """
    Record a confirmed selection and return the id.

    This is where the phase deliberately stops. No lecture is opened, no
    day is deducted and the state machine is not touched — Phase 15 owns
    the reader and Phase 17 owns the cost. The caller has already run
    `is_startable()`; this writes nothing that could disagree with it.
    """
    global __last_confirmed
    __last_confirmed = str(quest_id)
    print("%s%s" % (LOG_PREFIX, __last_confirmed))
    return __last_confirmed


def get_last_confirmed() -> Optional[str]:
    """The last quest id confirmed on this PC, or None."""
    return __last_confirmed


def reset() -> None:
    """Forget the last confirmation. For the tests, and for a new run."""
    global __last_confirmed
    __last_confirmed = None


# ── private ────────────────────────────────────────────────────

def __days(count: int) -> str:
    """"2 days" / "1 day" — singular is worth the three lines."""
    return "%d day%s" % (count, "" if count == 1 else "s")


# -------------------------------------------------------------
# STUB TEST -- show what the PC would list for a hand-made run:
#
#     python -m engine.side_quest_list
#
# The full visibility, day-block and ordering coverage is in
# tests/test_side_quest_list.py. Headless -- no pygame, no display,
# and nothing is written.
# -------------------------------------------------------------
if __name__ == "__main__":
    from engine.game_clock import GameClock
    from engine.game_session import GameSession

    class _Semester:
        def __init__(self, days):
            self.__days = days

        def get_time_pool_days(self):
            return self.__days

    class _Ctx:
        def __init__(self, machine, days):
            self.quest_states = machine
            self.__semester = _Semester(days)
            # The REAL clock, so the threshold this demo prints is the
            # one the game enforces rather than a number typed twice.
            self.game_clock = GameClock(GameSession())

        def semester(self):
            return self.__semester

    state_machine = QuestStateMachine()
    # Taken and read: 1. Taken, not read: 2 and 4. Refused: 3.
    # Slept through: 5. Never offered: 6-12.
    for term in (1, 2, 3, 4):
        if term == 3:
            state_machine.decline(state_machine.get_quest_for_semester(term))
        else:
            state_machine.accept(state_machine.get_quest_for_semester(term))
    state_machine.mark_completed(state_machine.get_quest_for_semester(1))
    state_machine.expire_unoffered_for_semester(5)

    # 40 is an ordinary mid-term; 16 is the last day new study is
    # allowed; 15 and 1 are both locked out by the same rule.
    for pool in (40, 16, 15, 1):
        context = _Ctx(state_machine, pool)
        print("\n%d day%s left in the term%s"
              % (pool, "" if pool == 1 else "s",
                 "   -- LOCKED OUT (threshold %d)" % threshold(context)
                 if is_locked_out(context) else ""))
        print("%-26s %-6s %-7s %s"
              % ("TOPIC", "DAYS", "SHEETS", "START?"))
        for row in entries(context):
            why = refusal(context, row["quest_id"])
            print("%-26s %-6d %-7d %s"
                  % (row["title"] + (" · COMPLETE" if row["completed"]
                                     else ""),
                     row["day_cost"], row["sheets"],
                     "yes" if why is None else "no  (%s)" % why[0]))
        print("rows shown: %d of 12 quests -- the other %d are invisible "
              "to this card" % (len(entries(context)),
                                12 - len(entries(context))))

    print("\nconfirming the first startable row:")
    live = _Ctx(state_machine, 40)
    for row in entries(live):
        if is_startable(live, row["quest_id"]):
            confirm(row["quest_id"])
            break
    print("last confirmed  : %r" % get_last_confirmed())
    print("nothing started : no lecture, no days spent, machine untouched")

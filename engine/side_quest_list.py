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

THE DAY RULE
────────────
A quest costs `day_cost` days (2 for all twelve today). With fewer days
than that left in the term, the quest is not startable: the
confirmation is never opened, nothing is deducted, and there is no
override. That is checked in one place, `is_startable()`, and the
reason it refuses is spelled out by `refusal()`.

This is NOT the 15-day side-activity firewall. That threshold is
`GameClock.is_eligible_for_side_activities()` and it belongs to Phase
17, which owns every other day rule around side quests. Nothing here
consults it, so there is exactly one place for Phase 17 to land.

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

    Three ways to be False, and `refusal()` names each of them: the
    quest is not on this list at all, it is already Completed, or the
    term has fewer days left than it costs. There is no fourth, and no
    override.
    """
    return refusal(ctx, quest_id) is None


def refusal(ctx: Any, quest_id: Any) -> Optional[Tuple[str, List[str]]]:
    """
    Why this quest cannot be started — (title, body lines) — or None.

    Shaped for `ui/popup.py`, which draws at most three centred body
    lines, so every message below is two. A refusal always says the
    number it is refusing on, because "not enough days" without the two
    figures is a wall rather than an answer.
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

    cost = get_day_cost(quest_id)
    left = days_left(ctx)
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
    class _Semester:
        def __init__(self, days):
            self.__days = days

        def get_time_pool_days(self):
            return self.__days

    class _Ctx:
        def __init__(self, machine, days):
            self.quest_states = machine
            self.__semester = _Semester(days)

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

    for pool in (40, 1):
        context = _Ctx(state_machine, pool)
        print("\n%d day%s left in the term"
              % (pool, "" if pool == 1 else "s"))
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

"""
engine/skill_completion.py
Is a skill completed? The one place that answers.

WHY THERE IS NO NEW FLAG
────────────────────────
Task 4 asks for a binary "completed" on a skill, set by the player going
through that skill's side-quest lecture(s), and insists nothing else may
define a second notion of completed. The repo already stores exactly that
fact, in exactly one place:

  * `content/side_quest_definitions.py` maps each of the twelve side
    quests to one skill id, 1:1 and onto — the same twelve ids
    `engine/save_bridge.py::TRACKED_SKILL_IDS` lists;
  * `engine/quest_state.py` moves a quest to STATE_COMPLETED, and
    `engine/lecture_reader.py::__complete()` is the only caller that ever
    does — reached only by reading a lecture to its last sheet.

So "this skill is completed" IS "its side quest is Completed". Storing a
second boolean beside it would be the second notion the task forbids, and
the two would drift the first time one was written without the other.

WHAT THIS BUYS, FOR FREE
────────────────────────
  * **Save compatibility.** The quest states are already in the payload
    (`save_bridge.capture()` -> `quest_state.to_state()`), already
    restored, and `from_state(None)` hands back twelve Unoffered quests.
    A save written before this change loads as "nothing completed yet",
    which is true of it. SAVE_SCHEMA_VERSION does not move and no
    migration runs. A pre-change save carrying numeric levels still
    loads: `save_bridge.restore()` replays them onto the tree, nothing
    reads them any more, and nothing crashes.
  * **The lecture path is already the trigger.** Task 1's skip button
    calls the same `lecture_reader` completion path, so it flips this
    flag without knowing this module exists.

A NEW MODULE ON PURPOSE
───────────────────────
The rule `engine/menu_prop.py`, `engine/day_drain.py`,
`engine/final_exam.py` and `engine/ending_gate.py` already set: new logic
lives in a new file and the shared modules take the smallest possible
call site. No pygame and no screen state here, so this is testable
headless. It is — see the stub at the bottom.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set

from content.side_quest_definitions import QUEST_IDS, get_skill_id
from engine.quest_state import (STATE_COMPLETED, STATE_UNLOCKED,
                                QuestStateMachine)

# skill_id -> quest_id, built once off the definitions table so the
# mapping is never restated. Quests whose definition carries no skill id
# are dropped rather than mapped to "", which would collide.
SKILL_TO_QUEST: Dict[str, str] = {
    get_skill_id(quest_id): quest_id
    for quest_id in QUEST_IDS
    if get_skill_id(quest_id)
}


def machine_of(source: Any) -> Optional[QuestStateMachine]:
    """
    The QuestStateMachine behind `source`, or None.

    Callers hold different things: a screen has an AppContext, a test has
    a bare machine. Same shape — and same reason — as
    `engine/ending_gate.py::machine_of()` and
    `engine/quest_offer.py::machine_of()`.
    """
    if isinstance(source, QuestStateMachine):
        return source
    machine = getattr(source, "quest_states", None)
    if isinstance(machine, QuestStateMachine):
        return machine
    return None


def quest_for_skill(skill_id: Any) -> str:
    """The side quest that completes this skill, or "" for an unknown id."""
    return SKILL_TO_QUEST.get(str(skill_id or ""), "")


def state_of(source: Any, skill_id: Any) -> str:
    """
    The raw quest state behind a skill, or "" when it cannot be read.

    "" rather than STATE_UNOFFERED for an unknown skill or a missing
    machine: those are "no answer", not "not offered yet", and a caller
    drawing a label wants to tell them apart.
    """
    machine = machine_of(source)
    quest_id = quest_for_skill(skill_id)
    if machine is None or not quest_id:
        return ""
    try:
        return str(machine.get_state(quest_id))
    except (AttributeError, TypeError, ValueError):
        return ""


def is_completed(source: Any, skill_id: Any) -> bool:
    """
    True when this skill's side quest has been read to its last sheet.

    THE single source of truth for Task 4. Everything that draws or gates
    on "completed" asks this and nothing else.
    """
    return state_of(source, skill_id) == STATE_COMPLETED


def is_started(source: Any, skill_id: Any) -> bool:
    """True when the quest was accepted but not yet finished."""
    return state_of(source, skill_id) == STATE_UNLOCKED


def completed_skill_ids(source: Any) -> Set[str]:
    """Every skill id whose side quest is Completed."""
    return {skill_id for skill_id in SKILL_TO_QUEST
            if is_completed(source, skill_id)}


def completed_count(source: Any) -> int:
    """How many of the twelve skills are completed."""
    return len(completed_skill_ids(source))


# -------------------------------------------------------------
# STUB TEST — the repo's convention for a module with no suite.
# Runs headless against the REAL QuestStateMachine.
#     py -m engine.skill_completion
# -------------------------------------------------------------
if __name__ == "__main__":
    from content.side_quest_definitions import QUEST_COUNT
    from engine.save_bridge import TRACKED_SKILL_IDS

    # -- the mapping is 1:1 and onto the twelve tracked skills ------
    assert len(SKILL_TO_QUEST) == QUEST_COUNT, (
        "expected one quest per skill, got %d for %d quests"
        % (len(SKILL_TO_QUEST), QUEST_COUNT))
    assert set(SKILL_TO_QUEST) == set(TRACKED_SKILL_IDS), (
        "skill ids drifted from save_bridge.TRACKED_SKILL_IDS: %s"
        % (set(SKILL_TO_QUEST) ^ set(TRACKED_SKILL_IDS),))

    class _Ctx:
        def __init__(self, machine):
            self.quest_states = machine

    machine = QuestStateMachine()
    ctx = _Ctx(machine)

    # -- nothing completed on a fresh machine ----------------------
    assert completed_count(ctx) == 0, "a fresh run had completed skills"
    assert not is_completed(ctx, "git")
    assert not is_started(ctx, "git")

    # -- accepting is not completing -------------------------------
    git_quest = quest_for_skill("git")
    assert git_quest, "git has no side quest"
    machine.accept(git_quest)
    assert is_started(ctx, "git"), "an accepted quest did not read as started"
    assert not is_completed(ctx, "git"), "accepting completed the skill"
    assert completed_count(ctx) == 0

    # -- completing flips exactly one skill ------------------------
    machine.mark_completed(git_quest)
    assert is_completed(ctx, "git"), "the completed quest did not flip"
    assert not is_started(ctx, "git"), "completed still read as started"
    assert completed_skill_ids(ctx) == {"git"}, "a second skill moved"

    # -- a bare machine works as a source too ----------------------
    assert is_completed(machine, "git"), "a bare machine was not accepted"

    # -- unknown ids and missing machines answer, never raise ------
    assert quest_for_skill("not_a_skill") == ""
    assert state_of(ctx, "not_a_skill") == ""
    assert not is_completed(ctx, "not_a_skill")
    assert not is_completed(object(), "git"), "a machineless source raised"
    assert not is_completed(ctx, None)

    print("skill_completion: all checks passed")

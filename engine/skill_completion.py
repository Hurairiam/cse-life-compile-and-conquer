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


# ── what the stats screen draws (Task 3) ───────────────────────
#
# Both of these read `state_of()` and nothing else, so the label and the
# bar are the same derivation the flag is — Task 3's "no second
# derivation" is structural here, not a promise.

LABEL_COMPLETED: str = "COMPLETED"
LABEL_NOT_COMPLETED: str = "NOT COMPLETED"

# Unoffered / Declined / Missed read as no progress; Unlocked means the
# player took the quest and owes the reading; Completed is done.
PROGRESS_STARTED: float = 0.5
PROGRESS_DONE: float = 1.0


def status_label(source: Any, skill_id: Any) -> str:
    """
    The word drawn where "LV n" used to be.

    Two states only, upper-cased to match every other label on the stats
    screen (its rows already `.upper()` the skill name, and its headers
    are SKILLS / ACADEMIC RECORD). These are UI status labels, not
    dialogue — G2 does not route them through Ayesha — and they are kept
    to the two words the brief specifies.
    """
    return (LABEL_COMPLETED if is_completed(source, skill_id)
            else LABEL_NOT_COMPLETED)


def progress_ratio(source: Any, skill_id: Any) -> float:
    """
    How full the stats screen's bar should be, 0.0 to 1.0.

    Three real steps, not two: empty before the quest is taken, half once
    it is Unlocked and the player owes the reading, full when it is
    Completed. Owner ruling (Open question C) — the bar has to keep
    reflecting real progress once the numeric level it used to read is
    gone, and "accepted but not read" IS progress the player made.
    """
    state = state_of(source, skill_id)
    if state == STATE_COMPLETED:
        return PROGRESS_DONE
    if state == STATE_UNLOCKED:
        return PROGRESS_STARTED
    return 0.0


class CompletionView:
    """
    A read-only stand-in for a SkillTree, answering off the flag.

    WHY THIS EXISTS. `content/skill_tree_layout.py::build_view_model()`
    is Saif's, and the whole skill tree screen — node fills, connectors,
    prerequisites, the detail panel — is derived from what
    `get_skill_level()` reports. With the grant and Invest gone every
    real level is 0, so that screen would draw twelve LOCKED nodes
    forever: a regression Task 4 did not ask for and Task 3's "keep
    reflecting real progress" argues against.

    Rather than edit a teammate's layout module or reimplement the
    screen, this reports a level that ENCODES the flag, and
    `resolve_state()` then reads exactly the states the player earned:

        completed -> ceiling  -> MASTERED
        unlocked  -> half     -> UNLOCKED
        otherwise -> 0        -> AVAILABLE or LOCKED, by prerequisites

    `resolve_state()` returns MASTERED for any node at its ceiling
    whatever its prerequisites say, which is what makes a completed
    skill read as completed even when the quest before it was declined.

    It is a VIEW: nothing here mutates, and `increment_skill` is
    deliberately absent so an accidental write fails loudly instead of
    landing somewhere nothing reads.
    """

    def __init__(self, source: Any, ceiling: int = 10) -> None:
        self.__source = source
        self.__ceiling = max(1, int(ceiling))

    def get_skill_level(self, skill_id: str) -> int:
        """The flag, expressed as the number the layout module wants."""
        ratio = progress_ratio(self.__source, skill_id)
        if ratio >= PROGRESS_DONE:
            return self.__ceiling
        if ratio > 0.0:
            return max(1, int(self.__ceiling * ratio))
        return 0

    def is_skill_unlocked(self, skill_id: str) -> bool:
        """True once the quest behind this skill has been taken."""
        return self.get_skill_level(skill_id) >= 1


def tree_view(source: Any) -> CompletionView:
    """The stand-in to hand `build_view_model()` instead of a SkillTree."""
    return CompletionView(source)


def stats_rows(source: Any) -> list:
    """
    (label, ratio, status) for every skill, in the screen's own order.

    Ordered by `content/skill_tree_layout.py::SKILL_NODES` — the order
    `engine/progression.py::skill_levels()` used to hand the stats screen
    — so the rows do not shuffle under the player just because what fills
    them changed.

    The label stays the prettified skill id the screen already drew
    ("programming language"); Task 3 changes the value column, not the
    name column.
    """
    from content.skill_tree_layout import SKILL_NODES
    return [(str(skill_id).replace("_", " "),
             progress_ratio(source, skill_id),
             status_label(source, skill_id))
            for skill_id in SKILL_NODES]


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

    # -- Task 3: the label and the bar, off the same one state -----
    assert status_label(ctx, "git") == LABEL_COMPLETED
    assert progress_ratio(ctx, "git") == PROGRESS_DONE
    assert status_label(ctx, "oop") == LABEL_NOT_COMPLETED
    assert progress_ratio(ctx, "oop") == 0.0

    oop_quest = quest_for_skill("oop")
    machine.accept(oop_quest)
    assert progress_ratio(ctx, "oop") == PROGRESS_STARTED, \
        "an accepted quest showed no progress"
    assert status_label(ctx, "oop") == LABEL_NOT_COMPLETED, \
        "accepted is not completed"

    rows = stats_rows(ctx)
    assert len(rows) == QUEST_COUNT, \
        "expected %d stat rows, got %d" % (QUEST_COUNT, len(rows))
    by_label = {label: (ratio, status) for label, ratio, status in rows}
    assert by_label["git"] == (PROGRESS_DONE, LABEL_COMPLETED)
    assert by_label["oop"] == (PROGRESS_STARTED, LABEL_NOT_COMPLETED)
    assert by_label["docker"] == (0.0, LABEL_NOT_COMPLETED)
    assert all(0.0 <= ratio <= 1.0 for _, ratio, _ in rows), \
        "a bar ratio fell outside 0..1"
    # No row may carry a number the screen could mistake for a level.
    assert all(status in (LABEL_COMPLETED, LABEL_NOT_COMPLETED)
               for _, _, status in rows)

    print("skill_completion: all checks passed")

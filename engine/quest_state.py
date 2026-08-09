"""
engine/quest_state.py
CSE Life: Compile & Conquer
Phase 12 — the side quest state machine

Every one of the twelve side quests is in exactly one of five states,
and there are exactly four ways to move between them:

    Unoffered ──accept()──────────> Unlocked ──mark_completed()──> Completed
        │
        ├──────decline()──────────> Declined
        │
        └──expire_unoffered_for_semester()──> Missed

Declined, Missed and Completed are terminal. Nothing leaves them, and
nothing re-enters Unoffered. Any other move raises QuestStateError —
loudly, never as a silent no-op, because a side quest that quietly
un-completes itself is the kind of bug that only shows up as a wrong
ending eight semesters later.

This lives in its own module on purpose, and holds no pygame, no screen
state and no UI. `engine/menu_prop.py` and `engine/return_points.py`
already set that rule (recon hazard #4): new logic goes in a new file,
and the busy shared modules carry a call rather than a branch. The only
edits outside this file are three call sites — the machine on
AppContext, and one key each in `capture()` and `restore()`.

WHAT THIS MODULE DOES NOT DO. It does not deduct days (Phase 17), does
not open dialogue or a reply list (Phase 13), does not draw anything
(Phases 14-16) and does not touch the skill tree. It answers questions
and records answers.

API NAMES. The brief spells the public surface GetState / CanOffer /
IsHighlySkilled. The repository is snake_case throughout — every
accessor in `core/`, `academic/` and `engine/` is `get_*` — so the
names are transliterated and the mapping is:

    GetState(quest_id)                  get_state(quest_id)
    GetQuestForSemester(semester)       get_quest_for_semester(semester)
    CanOffer(npc_id, semester)          can_offer(npc_id, semester)
    Accept(quest_id) / Decline(...)     accept(quest_id) / decline(...)
    MarkCompleted(quest_id)             mark_completed(quest_id)
    ExpireUnofferedForSemester(sem)     expire_unoffered_for_semester(sem)
    GetUnlockedQuests()                 get_unlocked_quests()
    GetCompletedQuests()                get_completed_quests()
    IsHighlySkilled()                   is_highly_skilled()
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from content.side_quest_definitions import (
    QUEST_IDS,
    get_definition,
    get_npc_id,
    get_quest_for_semester,
)

# ── the five states ────────────────────────────────────────────
# Plain strings rather than an Enum: these go straight into the save
# file, which engine/save_manager.py describes as "a dictionary of
# primitives", and a string survives a hand-edited save, a schema
# change and a debugger print without any decoding step. The repo
# already does this for every other closed set of authored values —
# INTERACTION_KINDS, ON_COMPLETE_MODES, FACINGS.

STATE_UNOFFERED: str = "unoffered"
STATE_DECLINED: str = "declined"
STATE_MISSED: str = "missed"
STATE_UNLOCKED: str = "unlocked"
STATE_COMPLETED: str = "completed"

QUEST_STATES: Tuple[str, ...] = (
    STATE_UNOFFERED, STATE_DECLINED, STATE_MISSED,
    STATE_UNLOCKED, STATE_COMPLETED,
)

# Where a quest is finished for the run, whichever way it got there.
TERMINAL_STATES: Tuple[str, ...] = (
    STATE_DECLINED, STATE_MISSED, STATE_COMPLETED,
)

# The whole rulebook, and the only place transitions are decided. Every
# (from, to) pair NOT in this set raises — including the identity pairs,
# so accepting a quest twice is an error rather than a shrug.
LEGAL_TRANSITIONS: frozenset = frozenset((
    (STATE_UNOFFERED, STATE_DECLINED),
    (STATE_UNOFFERED, STATE_MISSED),
    (STATE_UNOFFERED, STATE_UNLOCKED),
    (STATE_UNLOCKED, STATE_COMPLETED),
))


class QuestStateError(Exception):
    """An illegal transition, or a quest id that is not one of the
    twelve. Raised rather than swallowed — see the module docstring."""


class QuestStateMachine:
    """
    The live state of all twelve side quests.

    Constructed empty, meaning all twelve Unoffered, which is exactly
    what a new game and a pre-Phase-12 save both want. One of these
    hangs off AppContext as `ctx.quest_states`.
    """

    def __init__(self) -> None:
        """Every quest Unoffered, in semester order."""
        self.__states: Dict[str, str] = {
            quest_id: STATE_UNOFFERED for quest_id in QUEST_IDS}

    # ── reading ────────────────────────────────────────────────
    def get_state(self, quest_id: Any) -> str:
        """
        This quest's state.

        Raises QuestStateError for an id that is not one of the twelve.
        A typo'd id is a caller bug, and answering "unoffered" for one
        would let the bug run for the rest of the playthrough.
        """
        return self.__states[self.__key(quest_id)]

    def get_all_states(self) -> Dict[str, str]:
        """{quest_id: state} for all twelve, in semester order. A copy,
        so a caller reporting on it cannot edit the machine."""
        return {quest_id: self.__states[quest_id] for quest_id in QUEST_IDS}

    def get_quest_for_semester(self, semester: Any) -> Optional[str]:
        """The quest id offered in this semester, or None outside 1-12.
        A pass-through to the definitions table, so a caller holding the
        machine does not also need to import the data module."""
        return get_quest_for_semester(semester)

    def can_offer(self, npc_id: Any, semester: Any) -> bool:
        """
        True when this NPC has this semester's quest to offer and it has
        not been answered yet.

        `npc_id` is the short NPC_REGISTRY type id ("purnno"), which is
        what `engine/states/exploration.py::__talk` holds when the
        player presses E. Three things must all hold: the semester has a
        quest, this NPC is the one who offers it, and it is still
        Unoffered — so an accepted, declined or missed quest is never
        put a second time. Never raises: an unknown NPC or a semester
        outside 1-12 is simply False.
        """
        quest_id = get_quest_for_semester(semester)
        if quest_id is None:
            return False
        if str(npc_id or "").strip() != get_npc_id(quest_id):
            return False
        return self.__states[quest_id] == STATE_UNOFFERED

    def get_unlocked_quests(self) -> List[str]:
        """Quest ids accepted but not yet finished, in semester order."""
        return self.__in_state(STATE_UNLOCKED)

    def get_completed_quests(self) -> List[str]:
        """Quest ids fully read through, in semester order."""
        return self.__in_state(STATE_COMPLETED)

    def is_highly_skilled(self) -> bool:
        """
        True only when all twelve are Completed.

        The ending gate (Phase 16). Eleven out of twelve is False — the
        count is deliberately `all`, not a threshold, so no later tuning
        of the number can happen by accident here.
        """
        return all(self.__states[quest_id] == STATE_COMPLETED
                   for quest_id in QUEST_IDS)

    # ── writing ────────────────────────────────────────────────
    def accept(self, quest_id: Any) -> None:
        """Player took the offer: Unoffered -> Unlocked."""
        self.__transition(quest_id, STATE_UNLOCKED)

    def decline(self, quest_id: Any) -> None:
        """Player refused the offer: Unoffered -> Declined. Terminal."""
        self.__transition(quest_id, STATE_DECLINED)

    def mark_completed(self, quest_id: Any) -> None:
        """Every lecture sheet read: Unlocked -> Completed. Terminal.

        Raises for a quest that was never accepted, so a completion can
        never be recorded for a quest the player did not take."""
        self.__transition(quest_id, STATE_COMPLETED)

    def expire_unoffered_for_semester(self, semester: Any) -> Optional[str]:
        """
        The semester ended. If its quest was never put to the player, it
        is Missed. Returns the quest id it expired, or None.

        This is the ONE method that is allowed to do nothing, and it is
        not an exception to the rule above: it is not a request to move
        a particular quest, it is "this term is over". A quest already
        Accepted, Declined or Completed has had its answer and keeps it;
        only a still-Unoffered one is Missed. A semester outside 1-12
        has no quest and returns None.
        """
        quest_id = get_quest_for_semester(semester)
        if quest_id is None:
            return None
        if self.__states[quest_id] != STATE_UNOFFERED:
            return None
        self.__transition(quest_id, STATE_MISSED)
        return quest_id

    # ── save payload ───────────────────────────────────────────
    def to_dict(self) -> Dict[str, str]:
        """The twelve states as plain JSON types."""
        return {quest_id: self.__states[quest_id] for quest_id in QUEST_IDS}

    def load(self, saved: Any) -> None:
        """
        Replace the twelve states from a save, dropping anything that
        does not belong.

        Deliberately tolerant, because this is the one entry point that
        reads a file a player could have hand-edited, and refusing to
        load a save is worse than starting one quest in the wrong place:
        anything that is not a dict, a quest id that is not one of the
        twelve, and a state name that is not one of the five all fall
        back to Unoffered rather than raising. `accept()` and friends
        stay strict — those are called by code, not by a file.
        """
        self.__states = {quest_id: STATE_UNOFFERED for quest_id in QUEST_IDS}
        if not isinstance(saved, dict):
            return
        for quest_id, state in saved.items():
            key = str(quest_id or "").strip().upper()
            if key not in self.__states:
                continue
            name = str(state or "").strip().lower()
            if name in QUEST_STATES:
                self.__states[key] = name

    # ── private ────────────────────────────────────────────────
    def __key(self, quest_id: Any) -> str:
        """Normalise an id and prove it is one of the twelve."""
        key = str(quest_id or "").strip().upper()
        if key not in self.__states:
            raise QuestStateError("unknown side quest id: %r" % (quest_id,))
        return key

    def __transition(self, quest_id: Any, target: str) -> None:
        """The only writer. Refuses anything outside LEGAL_TRANSITIONS."""
        key = self.__key(quest_id)
        current = self.__states[key]
        if (current, target) not in LEGAL_TRANSITIONS:
            raise QuestStateError(
                "%s: illegal transition %s -> %s (legal moves from %s: %s)"
                % (key, current, target, current,
                   ", ".join(sorted(to for (frm, to) in LEGAL_TRANSITIONS
                                    if frm == current)) or "none, terminal"))
        self.__states[key] = target

    def __in_state(self, state: str) -> List[str]:
        """Quest ids in one state, in semester order."""
        return [quest_id for quest_id in QUEST_IDS
                if self.__states[quest_id] == state]


# ── the save bridge ────────────────────────────────────────────
# Module-level to_state/from_state, the shape engine/return_points.py
# already uses, so engine/save_bridge.py calls this the same way it
# calls that one.

def to_state(ctx: Any) -> Dict[str, str]:
    """The twelve states as plain JSON types, from a live context."""
    machine = getattr(ctx, "quest_states", None)
    if not isinstance(machine, QuestStateMachine):
        return QuestStateMachine().to_dict()
    return machine.to_dict()


def from_state(saved: Any) -> QuestStateMachine:
    """
    Rebuild the machine from a save.

    A save written before this phase carries no quest block at all, and
    lands here as None — which loads as twelve Unoffered quests, exactly
    a fresh run. That is the whole of the version handling the brief
    asks for, and it is why SAVE_SCHEMA_VERSION does not move: the two
    keys added before this one (`world.dialogue_choices`,
    `world.return_positions`) were additive and tolerant in the same
    way, and bumping would only mean older builds refusing saves they
    could otherwise read.
    """
    machine = QuestStateMachine()
    machine.load(saved)
    return machine


# -------------------------------------------------------------
# STUB TEST -- show the state of all twelve quests through the
# public API, which is this phase's acceptance criterion:
#
#     python -m engine.quest_state
#
# The full transition, persistence and ending-gate coverage is in
# tests/test_quest_state.py. Headless -- no pygame, no display, and
# nothing is written.
# -------------------------------------------------------------
if __name__ == "__main__":
    machine = QuestStateMachine()

    # A plausible run: some taken, one refused, one slept through.
    for semester in (1, 2, 3, 4):
        machine.accept(machine.get_quest_for_semester(semester))
    for semester in (1, 2, 3):
        machine.mark_completed(machine.get_quest_for_semester(semester))
    machine.decline(machine.get_quest_for_semester(5))
    machine.expire_unoffered_for_semester(6)

    print("%-4s %-8s %-24s %s" % ("SEM", "NPC", "QUEST ID", "STATE"))
    for quest_id, state in machine.get_all_states().items():
        definition = get_definition(quest_id)
        print("%-4d %-8s %-24s %s" % (definition["semester"],
                                      definition["npc_id"], quest_id, state))

    print("\nunlocked        : %s" % ", ".join(machine.get_unlocked_quests()))
    print("completed       : %s" % ", ".join(machine.get_completed_quests()))
    print("highly skilled  : %s" % machine.is_highly_skilled())
    print("can_offer(purnno, 1) : %s" % machine.can_offer("purnno", 1))
    print("can_offer(rahman, 9) : %s" % machine.can_offer("rahman", 9))
    print("can_offer(purnno, 9) : %s" % machine.can_offer("purnno", 9))

    try:
        machine.accept(machine.get_quest_for_semester(5))
    except QuestStateError as error:
        print("\nrefused: %s" % error)

"""
tests/test_quest_state.py
CSE Life: Compile & Conquer
Phase 12 — coverage for the side quest data layer and state machine

    python -m tests.test_quest_state

Headless and self-contained: no pygame, no display, and the only thing
written to disk is a throwaway temporary directory, exactly the way
engine/save_manager.py's own stub test works. The real saves/ folder is
never touched, so running this can never damage a playthrough.

What is covered, in the brief's own words:

    each legal transition                    test_legal_*
    every illegal transition rejected        test_illegal_transitions_*
    save/load round-trip preserves all 12    test_round_trip_*
    IsHighlySkilled false at 11/12, true 12  test_is_highly_skilled_*
    a save without quest data loads cleanly  test_pre_phase_12_save_*

plus the definitions file's own validation rules, since a state machine
over a broken table would pass every test above and still be wrong.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

from content.side_quest_definitions import (
    QUEST_COUNT,
    QUEST_IDS,
    SEMESTER_MAX,
    SEMESTER_MIN,
    SIDE_QUEST_DEFINITIONS,
    SideQuestDefinitionError,
    get_definition,
    get_lecture_sheets,
    get_quest_for_semester,
    get_semester,
    validate,
)
from content.side_quest_lectures import DEFAULT_SHEET, get_sheet
from engine.quest_state import (
    LEGAL_TRANSITIONS,
    QUEST_STATES,
    STATE_COMPLETED,
    STATE_DECLINED,
    STATE_MISSED,
    STATE_UNLOCKED,
    STATE_UNOFFERED,
    TERMINAL_STATES,
    QuestStateError,
    QuestStateMachine,
    from_state,
    to_state,
)
from engine.save_manager import SaveManager, build_state

FIRST_QUEST: str = QUEST_IDS[0]


# ── helpers ────────────────────────────────────────────────────

def machine_in(state: str, quest_id: str = FIRST_QUEST) -> QuestStateMachine:
    """A machine with one quest driven into `state` through the public
    API only — no reaching into the private dict, so a test can never
    set up a state the game itself could not reach."""
    machine = QuestStateMachine()
    if state == STATE_UNOFFERED:
        pass
    elif state == STATE_DECLINED:
        machine.decline(quest_id)
    elif state == STATE_MISSED:
        machine.expire_unoffered_for_semester(get_semester(quest_id))
    elif state == STATE_UNLOCKED:
        machine.accept(quest_id)
    elif state == STATE_COMPLETED:
        machine.accept(quest_id)
        machine.mark_completed(quest_id)
    else:
        raise AssertionError("no way to reach %r" % state)
    assert machine.get_state(quest_id) == state
    return machine


# The three per-quest mutators, and the state each one moves a quest to.
# expire_unoffered_for_semester() is not here: it takes a semester
# rather than a quest and is a documented no-op off Unoffered, so it
# gets its own cases below.
OPERATIONS = (
    (STATE_UNLOCKED, "accept",
     lambda machine, quest_id: machine.accept(quest_id)),
    (STATE_DECLINED, "decline",
     lambda machine, quest_id: machine.decline(quest_id)),
    (STATE_COMPLETED, "mark_completed",
     lambda machine, quest_id: machine.mark_completed(quest_id)),
)


def raises(error_type, call, *args) -> Exception:
    """Run `call` and return the exception it raised, or fail."""
    try:
        call(*args)
    except error_type as error:
        return error
    raise AssertionError("expected %s, nothing was raised"
                         % error_type.__name__)


# ── the definitions file ───────────────────────────────────────

def test_definitions_validate_at_import() -> None:
    """The table passed validate() on the way in, and passes it again."""
    validate()


def test_definitions_count() -> None:
    """Exactly twelve entries, no more and no fewer."""
    assert len(SIDE_QUEST_DEFINITIONS) == QUEST_COUNT
    assert len(QUEST_IDS) == QUEST_COUNT


def test_definitions_semesters_unique() -> None:
    """Semesters 1-12, each used exactly once."""
    semesters = sorted(entry["semester"]
                       for entry in SIDE_QUEST_DEFINITIONS.values())
    assert semesters == list(range(SEMESTER_MIN, SEMESTER_MAX + 1))
    for semester in semesters:
        assert get_quest_for_semester(semester) in SIDE_QUEST_DEFINITIONS


def test_definitions_no_duplicate_ids() -> None:
    """No repeated quest_id and no repeated skill_id."""
    quest_ids = list(SIDE_QUEST_DEFINITIONS)
    assert len(set(quest_ids)) == len(quest_ids)
    skill_ids = [entry["skill_id"]
                 for entry in SIDE_QUEST_DEFINITIONS.values()]
    assert len(set(skill_ids)) == len(skill_ids) == QUEST_COUNT


def test_definitions_day_costs_configured() -> None:
    """Every day_cost is a real non-negative integer, never the -1
    'not configured yet' sentinel."""
    for quest_id in QUEST_IDS:
        day_cost = get_definition(quest_id)["day_cost"]
        assert isinstance(day_cost, int) and not isinstance(day_cost, bool)
        assert day_cost >= 0, "%s: day_cost %r" % (quest_id, day_cost)


def test_definitions_lecture_sheets_resolve() -> None:
    """Every lecture sheet id resolves to real content, in order, and
    belongs to the quest that lists it."""
    for quest_id in QUEST_IDS:
        sheets = get_lecture_sheets(quest_id)
        assert sheets, "%s: no lecture sheets" % quest_id
        for sheet_id in sheets:
            sheet = get_sheet(sheet_id)
            assert sheet is not DEFAULT_SHEET, \
                "%s: %s resolves to nothing" % (quest_id, sheet_id)
            assert sheet["skill_id"] == quest_id
            assert sheet["text"].strip()


def test_definitions_fail_loudly_on_a_bad_entry() -> None:
    """A broken table raises rather than silently skipping the entry."""
    original = SIDE_QUEST_DEFINITIONS[FIRST_QUEST]
    broken = dict(original)
    broken["lecture_sheets"] = ["SQ_NOT_A_REAL_SHEET"]
    SIDE_QUEST_DEFINITIONS[FIRST_QUEST] = broken
    try:
        error = raises(SideQuestDefinitionError, validate)
        assert "resolves to no content" in str(error)
        broken["lecture_sheets"] = original["lecture_sheets"]
        broken["day_cost"] = -1
        error = raises(SideQuestDefinitionError, validate)
        assert "negative" in str(error)
    finally:
        SIDE_QUEST_DEFINITIONS[FIRST_QUEST] = original
    validate()


def test_definitions_accessors_never_raise() -> None:
    """An unknown id is answered, not raised at."""
    assert get_definition("NOPE") is None
    assert get_quest_for_semester(0) is None
    assert get_quest_for_semester(13) is None
    assert get_quest_for_semester("not a number") is None
    assert get_lecture_sheets("") == []
    assert get_definition(FIRST_QUEST.lower()) is not None
    assert get_lecture_sheets(FIRST_QUEST) is not \
        SIDE_QUEST_DEFINITIONS[FIRST_QUEST]["lecture_sheets"]


# ── the four legal transitions ─────────────────────────────────

def test_legal_unoffered_to_unlocked() -> None:
    """The player accepts."""
    machine = QuestStateMachine()
    assert machine.get_state(FIRST_QUEST) == STATE_UNOFFERED
    machine.accept(FIRST_QUEST)
    assert machine.get_state(FIRST_QUEST) == STATE_UNLOCKED
    assert machine.get_unlocked_quests() == [FIRST_QUEST]


def test_legal_unoffered_to_declined() -> None:
    """The player refuses."""
    machine = QuestStateMachine()
    machine.decline(FIRST_QUEST)
    assert machine.get_state(FIRST_QUEST) == STATE_DECLINED
    assert machine.get_unlocked_quests() == []


def test_legal_unoffered_to_missed() -> None:
    """The semester ends without the offer ever being put."""
    machine = QuestStateMachine()
    expired = machine.expire_unoffered_for_semester(get_semester(FIRST_QUEST))
    assert expired == FIRST_QUEST
    assert machine.get_state(FIRST_QUEST) == STATE_MISSED


def test_legal_unlocked_to_completed() -> None:
    """Every lecture sheet read."""
    machine = QuestStateMachine()
    machine.accept(FIRST_QUEST)
    machine.mark_completed(FIRST_QUEST)
    assert machine.get_state(FIRST_QUEST) == STATE_COMPLETED
    assert machine.get_completed_quests() == [FIRST_QUEST]
    assert machine.get_unlocked_quests() == []


def test_legal_transitions_are_exactly_seven() -> None:
    """
    The rulebook itself holds seven pairs and no others.

    TASK 2 added the last three. Declined stopped being terminal: the
    player may walk back and accept, walk back and refuse again, or
    leave it refused until the term ends and it expires like a quest
    that was never put.
    """
    assert LEGAL_TRANSITIONS == frozenset((
        (STATE_UNOFFERED, STATE_UNLOCKED),
        (STATE_UNOFFERED, STATE_DECLINED),
        (STATE_UNOFFERED, STATE_MISSED),
        (STATE_UNLOCKED, STATE_COMPLETED),
        (STATE_DECLINED, STATE_UNLOCKED),
        (STATE_DECLINED, STATE_DECLINED),
        (STATE_DECLINED, STATE_MISSED),
    ))


def test_declined_is_offerable_again(unused=None) -> None:
    """The mechanic itself, at the machine level."""
    definition = get_definition(FIRST_QUEST)
    npc_id, semester = definition["npc_id"], definition["semester"]

    machine = QuestStateMachine()
    machine.decline(FIRST_QUEST)
    assert machine.get_state(FIRST_QUEST) == STATE_DECLINED
    assert machine.can_offer(npc_id, semester), \
        "a declined quest was not re-offered"

    # Refusing again is legal and idempotent.
    machine.decline(FIRST_QUEST)
    assert machine.get_state(FIRST_QUEST) == STATE_DECLINED
    assert machine.can_offer(npc_id, semester)

    # ...and saying yes later is the point of it coming back.
    machine.accept(FIRST_QUEST)
    assert machine.get_state(FIRST_QUEST) == STATE_UNLOCKED
    assert not machine.can_offer(npc_id, semester), \
        "an accepted quest was offered again"


def test_a_declined_quest_expires_when_the_term_ends() -> None:
    """The boundary is the semester, not the answer."""
    machine = QuestStateMachine()
    machine.decline(FIRST_QUEST)
    expired = machine.expire_for_semester(get_semester(FIRST_QUEST))
    assert expired == FIRST_QUEST
    assert machine.get_state(FIRST_QUEST) == STATE_MISSED

    definition = get_definition(FIRST_QUEST)
    assert not machine.can_offer(definition["npc_id"],
                                 definition["semester"]), \
        "a missed quest came back in a later term"


# ── every illegal transition ───────────────────────────────────

def test_illegal_transitions_all_rejected() -> None:
    """
    Every (state, mutator) pair outside the rulebook raises, and leaves
    the quest exactly where it was.

    Five states times three mutators is fifteen combinations. TASK 2
    made two of them legal that were not — Declined -> Unlocked and the
    Declined -> Declined self-move — so five are legal now and ten must
    raise. Accepting an already-Unlocked quest is still an error rather
    than a shrug.
    """
    legal_by_mutator = sum(
        1 for source in QUEST_STATES
        for target, _name, _operation in OPERATIONS
        if (source, target) in LEGAL_TRANSITIONS)
    checked = 0
    for source in QUEST_STATES:
        for target, name, operation in OPERATIONS:
            machine = machine_in(source)
            if (source, target) in LEGAL_TRANSITIONS:
                operation(machine, FIRST_QUEST)
                assert machine.get_state(FIRST_QUEST) == target
                continue
            error = raises(QuestStateError, operation, machine, FIRST_QUEST)
            assert "illegal transition" in str(error)
            assert machine.get_state(FIRST_QUEST) == source, \
                "%s survived %s()" % (source, name)
            checked += 1
    assert legal_by_mutator == 5, \
        "the mutator-reachable rulebook changed: %d" % legal_by_mutator
    assert checked == len(QUEST_STATES) * len(OPERATIONS) - 5 == 10


def test_illegal_terminal_states_are_final() -> None:
    """
    Nothing leaves Missed or Completed.

    TASK 2 removed Declined from this list: it is offerable again for
    the rest of the term, so accept() and decline() are legal from it.
    Missed and Completed are the two genuinely terminal states now —
    Missed is what a Declined quest becomes when the term ends.
    """
    for source in (STATE_MISSED, STATE_COMPLETED):
        for _target, _name, operation in OPERATIONS:
            machine = machine_in(source)
            raises(QuestStateError, operation, machine, FIRST_QUEST)
            assert machine.get_state(FIRST_QUEST) == source


def test_illegal_expire_is_a_no_op_off_unoffered() -> None:
    """
    Ending a semester never overwrites an answer already given.

    This is the one documented exception to 'throw, never no-op': it is
    not a request to move a quest, it is 'this term is over', so a quest
    that was accepted or completed simply keeps its state.

    TASK 2 moved Declined out of this list and into the expiring set —
    declining is no longer an answer that outlives the term, so a quest
    left refused when the term closes is Missed. Covered by
    test_a_declined_quest_expires_when_the_term_ends.
    """
    semester = get_semester(FIRST_QUEST)
    for source in (STATE_MISSED, STATE_UNLOCKED, STATE_COMPLETED):
        machine = machine_in(source)
        assert machine.expire_for_semester(semester) is None
        assert machine.get_state(FIRST_QUEST) == source


def test_illegal_unknown_quest_id_rejected() -> None:
    """A typo'd quest id raises everywhere it can, rather than being
    answered as an Unoffered quest that does not exist."""
    machine = QuestStateMachine()
    for call in (machine.get_state, machine.accept,
                 machine.decline, machine.mark_completed):
        error = raises(QuestStateError, call, "SQ_NOT_A_QUEST")
        assert "unknown side quest id" in str(error)
    raises(QuestStateError, machine.get_state, "")
    raises(QuestStateError, machine.get_state, None)


def test_a_full_run_reaches_every_state() -> None:
    """
    One playthrough, every transition, twelve quests.

    TASK 2 changed the shape of this. A declined quest no longer stays
    Declined once its term is expired — it becomes Missed like one that
    was never put — so the only way a run ends with a Declined quest is
    for its semester to still be running. The last term is therefore
    left unexpired, which is exactly the state a player is in when they
    refuse an offer and keep playing.
    """
    machine = QuestStateMachine()
    for semester in range(SEMESTER_MIN, SEMESTER_MAX + 1):
        quest_id = machine.get_quest_for_semester(semester)
        if semester % 4 == 1:
            machine.accept(quest_id)
            machine.mark_completed(quest_id)
        elif semester % 4 == 2:
            machine.accept(quest_id)
        elif semester % 4 == 3:
            machine.decline(quest_id)
        if semester != SEMESTER_MAX:
            machine.expire_for_semester(semester)

    last = machine.get_quest_for_semester(SEMESTER_MAX)
    machine.decline(last)               # the term the player is still in

    states = machine.get_all_states()
    assert len(states) == QUEST_COUNT
    assert sorted(set(states.values())) == sorted(
        {STATE_COMPLETED, STATE_UNLOCKED, STATE_DECLINED, STATE_MISSED})
    assert list(states) == list(QUEST_IDS)
    assert states[last] == STATE_DECLINED

    # ...and closing that last term takes the declined one with it.
    machine.expire_for_semester(SEMESTER_MAX)
    assert machine.get_state(last) == STATE_MISSED
    assert STATE_DECLINED not in set(machine.get_all_states().values())


# ── can_offer ──────────────────────────────────────────────────

def test_can_offer_matches_the_npc_and_the_semester() -> None:
    """True only for the right NPC in the right term."""
    machine = QuestStateMachine()
    for quest_id in QUEST_IDS:
        definition = get_definition(quest_id)
        npc_id, semester = definition["npc_id"], definition["semester"]
        assert machine.can_offer(npc_id, semester)
        assert not machine.can_offer("someone_else", semester)
        assert not machine.can_offer(npc_id, 0)
        assert not machine.can_offer(npc_id, SEMESTER_MAX + 1)


def test_can_offer_false_once_answered() -> None:
    """
    A quest that was TAKEN or LOST is never put a second time.

    TASK 2: Declined is no longer in this set — it is offerable again
    until the term ends. Accepted, completed and missed still are.
    """
    definition = get_definition(FIRST_QUEST)
    npc_id, semester = definition["npc_id"], definition["semester"]
    for source in (STATE_MISSED, STATE_COMPLETED, STATE_UNLOCKED):
        machine = machine_in(source)
        assert not machine.can_offer(npc_id, semester), \
            "%s was offered again" % source
    assert QuestStateMachine().can_offer(npc_id, semester)
    assert machine_in(STATE_DECLINED).can_offer(npc_id, semester), \
        "a declined quest was not re-offered"


# ── the ending gate ────────────────────────────────────────────

def complete_quests(machine: QuestStateMachine, quest_ids) -> None:
    """Accept and finish each of these."""
    for quest_id in quest_ids:
        machine.accept(quest_id)
        machine.mark_completed(quest_id)


def test_is_highly_skilled_false_at_eleven_of_twelve() -> None:
    """Eleven completed is not enough — and it is not enough whichever
    one is left out."""
    for left_out in QUEST_IDS:
        machine = QuestStateMachine()
        complete_quests(machine,
                        [q for q in QUEST_IDS if q != left_out])
        assert len(machine.get_completed_quests()) == QUEST_COUNT - 1
        assert not machine.is_highly_skilled()


def test_is_highly_skilled_false_when_the_last_one_is_only_unlocked() -> None:
    """Accepted but unread does not count as completed."""
    machine = QuestStateMachine()
    complete_quests(machine, QUEST_IDS[:-1])
    machine.accept(QUEST_IDS[-1])
    assert not machine.is_highly_skilled()


def test_is_highly_skilled_true_at_twelve_of_twelve() -> None:
    """All twelve completed, and only then."""
    machine = QuestStateMachine()
    assert not machine.is_highly_skilled()
    complete_quests(machine, QUEST_IDS)
    assert machine.get_completed_quests() == list(QUEST_IDS)
    assert machine.is_highly_skilled()


# ── persistence ────────────────────────────────────────────────

def mixed_machine() -> QuestStateMachine:
    """One machine with every state represented across the twelve."""
    machine = QuestStateMachine()
    order = (STATE_COMPLETED, STATE_UNLOCKED, STATE_DECLINED,
             STATE_MISSED, STATE_UNOFFERED)
    for index, quest_id in enumerate(QUEST_IDS):
        wanted = order[index % len(order)]
        if wanted == STATE_COMPLETED:
            machine.accept(quest_id)
            machine.mark_completed(quest_id)
        elif wanted == STATE_UNLOCKED:
            machine.accept(quest_id)
        elif wanted == STATE_DECLINED:
            machine.decline(quest_id)
        elif wanted == STATE_MISSED:
            machine.expire_unoffered_for_semester(get_semester(quest_id))
    return machine


def test_round_trip_through_a_real_save_file() -> None:
    """All twelve states survive build_state -> disk -> load -> rebuild,
    through the actual SaveManager, in a throwaway directory."""
    machine = mixed_machine()
    before = machine.get_all_states()
    assert len(set(before.values())) == len(QUEST_STATES)

    workspace = tempfile.mkdtemp(prefix="cse_life_quest_test_")
    try:
        manager = SaveManager(workspace)
        state = build_state(display_name="Nangiba", current_semester=7,
                            quest_states=to_state(_Ctx(machine)))
        assert manager.save(1, state), manager.get_last_error()
        loaded = manager.load(1)
        assert loaded is not None, manager.get_last_error()
        assert loaded["quests"]["states"] == before

        rebuilt = from_state(loaded["quests"]["states"])
        assert rebuilt.get_all_states() == before
        assert rebuilt.get_unlocked_quests() == machine.get_unlocked_quests()
        assert rebuilt.get_completed_quests() == machine.get_completed_quests()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_round_trip_preserves_the_ending_gate() -> None:
    """A finished run reloads as a finished run."""
    machine = QuestStateMachine()
    complete_quests(machine, QUEST_IDS)
    rebuilt = from_state(machine.to_dict())
    assert rebuilt.is_highly_skilled()

    machine = QuestStateMachine()
    complete_quests(machine, QUEST_IDS[:-1])
    rebuilt = from_state(machine.to_dict())
    assert not rebuilt.is_highly_skilled()


def test_pre_phase_12_save_loads_all_unoffered() -> None:
    """
    A save written before this feature has no "quests" block at all. It
    must load cleanly, with twelve Unoffered quests, not crash.

    The file is written by hand rather than by build_state(), because
    build_state() now always emits the block -- an old file genuinely
    does not have the key.
    """
    old_save = build_state(display_name="Old Save", current_semester=5,
                           level_id="campus_main")
    del old_save["quests"]
    assert "quests" not in old_save

    workspace = tempfile.mkdtemp(prefix="cse_life_quest_test_")
    try:
        manager = SaveManager(workspace)
        path = manager.get_slot_path(1)
        os.makedirs(workspace, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(old_save, handle)

        loaded = manager.load(1)
        assert loaded is not None, manager.get_last_error()
        assert "quests" not in loaded

        block = loaded.get("quests") or {}
        machine = from_state(block.get("states"))
        assert machine.get_all_states() == {
            quest_id: STATE_UNOFFERED for quest_id in QUEST_IDS}
        assert not machine.is_highly_skilled()
        assert machine.get_unlocked_quests() == []
        # And it is a working machine, not a frozen one.
        machine.accept(FIRST_QUEST)
        assert machine.get_state(FIRST_QUEST) == STATE_UNLOCKED
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_a_hand_edited_save_never_raises() -> None:
    """Junk in the quest block is dropped, quest by quest, rather than
    refusing to load the playthrough."""
    for junk in (None, "", [], 7, {"SQ_NOT_A_QUEST": STATE_COMPLETED},
                 {FIRST_QUEST: "ascended"}, {FIRST_QUEST: None},
                 {None: None}):
        machine = from_state(junk)
        assert machine.get_all_states() == {
            quest_id: STATE_UNOFFERED for quest_id in QUEST_IDS}

    partial = from_state({FIRST_QUEST.lower(): STATE_COMPLETED.upper(),
                          "SQ_NOT_A_QUEST": STATE_COMPLETED})
    assert partial.get_state(FIRST_QUEST) == STATE_COMPLETED
    assert len(partial.get_completed_quests()) == 1


def test_to_state_survives_a_context_without_a_machine() -> None:
    """capture() runs before restore() has ever been called on a fresh
    boot, so to_state() must answer for a bare context too."""
    assert to_state(_Ctx(None)) == {
        quest_id: STATE_UNOFFERED for quest_id in QUEST_IDS}
    assert to_state(object()) == {
        quest_id: STATE_UNOFFERED for quest_id in QUEST_IDS}


def test_build_state_carries_the_block() -> None:
    """The save payload's canonical shape holds the quest block, and an
    unfilled one is an empty dict rather than a missing key."""
    assert build_state()["quests"] == {"states": {}}
    machine = QuestStateMachine()
    machine.accept(FIRST_QUEST)
    state = build_state(quest_states=machine.to_dict())
    assert state["quests"]["states"][FIRST_QUEST] == STATE_UNLOCKED
    # Still plain JSON types, per save_manager's "dictionary of
    # primitives" contract.
    assert json.loads(json.dumps(state))["quests"] == state["quests"]


class _Ctx:
    """The one attribute engine/quest_state.py::to_state() reads. A stub
    rather than a real AppContext, which would need pygame and a
    window."""

    def __init__(self, machine) -> None:
        self.quest_states = machine


# -------------------------------------------------------------
# RUNNER -- collect every test_* in this module, in the order it is
# written, run it, and report. Exits non-zero if anything failed, so
# this works unchanged as a CI step.
# -------------------------------------------------------------

def main() -> int:
    """Run every test in this module. Returns the process exit code."""
    cases = [(name, function) for name, function in globals().items()
             if name.startswith("test_") and callable(function)]
    cases.sort(key=lambda pair: pair[1].__code__.co_firstlineno)

    failures = []
    for name, function in cases:
        try:
            function()
        except Exception as error:                # noqa: BLE001 - report all
            failures.append((name, error))
            print("FAIL  %s\n        %s: %s"
                  % (name, type(error).__name__, error))
        else:
            print("PASS  %s" % name)

    print("\n%d/%d passed" % (len(cases) - len(failures), len(cases)))
    if failures:
        print("failed: %s" % ", ".join(name for name, _ in failures))
        return 1

    print("\n-- all twelve quests through the public API --")
    machine = mixed_machine()
    print("%-4s %-8s %-24s %s" % ("SEM", "NPC", "QUEST ID", "STATE"))
    for quest_id, state in machine.get_all_states().items():
        definition = get_definition(quest_id)
        print("%-4d %-8s %-24s %s" % (definition["semester"],
                                      definition["npc_id"], quest_id, state))
    return 0


if __name__ == "__main__":
    sys.exit(main())

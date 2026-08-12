"""
tests/test_lecture_reader.py
CSE Life: Compile & Conquer
Phase 15 — coverage for the lecture reader, its day cost and completion

    python -m tests.test_lecture_reader

Headless and self-contained: SDL_VIDEODRIVER=dummy, no window anybody
can see. The only thing written anywhere is a tempfile.mkdtemp()
directory for the one save round-trip case, so `saves/` is never
touched — the rule engine/save_manager.py's own stub already follows.

WHAT IS ACTUALLY DRIVEN. The rule half runs against a context built on
the REAL GameSession, GameClock, Player, Semester and SkillTree rather
than mocks of them, because "the days came off" is a claim about that
pipeline and a fake pool would prove nothing. The last section then
drives the REAL engine/states/side_quest_lecture.py and
engine/states/side_quests.py through a REAL AppContext with real popups
and real pygame KEYDOWN events, because "warns before leaving" and "no
progress is kept" are claims about the screen.

    the flow, in the brief's own order   test_flow_*
    R1, leaving early is retryable       test_r1_*
    R2, what counts as leaving early     test_r2_*
    no per-sheet progress, anywhere      test_nobookmark_*
    refusals                             test_block_*
    the four named edge cases            test_edge_*
    what the popups can hold             test_popup_*
    through the real screens             test_screen_*
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame                                          # noqa: E402

from academic.side_quest_catalog import (              # noqa: E402
    build_side_quest_catalog, get_side_quest_by_id)
from content import side_quest_definitions as defs     # noqa: E402
from content.side_quest_definitions import (           # noqa: E402
    QUEST_IDS, get_day_cost, get_lecture_sheets, get_skill_id)
from content.side_quest_lectures import (              # noqa: E402
    DEFAULT_SHEET, get_sheet)
from engine import (lecture_reader, side_quest_list,   # noqa: E402
                    skill_completion)
from engine.game_clock import GameClock                # noqa: E402
from engine.game_session import GameSession            # noqa: E402
from engine.quest_state import (                       # noqa: E402
    LEGAL_TRANSITIONS, QUEST_STATES, STATE_COMPLETED, STATE_DECLINED,
    STATE_MISSED, STATE_UNLOCKED, STATE_UNOFFERED, QuestStateMachine)
from engine.screen_manager import ScreenState          # noqa: E402
from ui.popup import (                                 # noqa: E402
    BOX_W, MAX_BODY_LINES, RESULT_CANCEL, RESULT_CONFIRM, SIZE_BODY,
    load_font)

SEMESTERS = tuple(range(1, 13))
DAY_COST = 2                    # what all twelve cost today
SKILL_REWARD = 15               # what academic/side_quest_catalog.py grants
SHEETS_PER_QUEST = 3

# The widest a popup body line may render. The card is BOX_W wide with a
# 4px frame; 24px of breathing room each side is what the existing
# messages sit inside.
BODY_MAX_PX = BOX_W - 48


# ── a context, without a window ────────────────────────────────

class _Ctx:
    """
    The five things engine/lecture_reader.py asks a context for, over
    the REAL GameSession, GameClock, Player, Semester and SkillTree.

    Deliberately not mocked. Every claim in this file about days coming
    off, the global career clock moving or a skill going up is a claim
    about that pipeline, and a fake pool would let all three pass while
    the game did nothing.
    """

    def __init__(self, semester: int = 1, days: int = 80) -> None:
        self.session = GameSession()
        while self.session.get_active_player().get_current_semester() \
                < semester:
            self.session.get_active_player().advance_semester()
        from academic.semester import Semester
        self.session.set_active_semester(Semester(semester))
        self.game_clock = GameClock(self.session)
        self.quest_states = QuestStateMachine()
        spend = 80 - int(days)
        if spend > 0:
            self.semester().deduct_time(spend)
            self.player().deduct_time_pool_days(spend)

    def semester(self):
        return self.session.get_active_semester()

    def player(self):
        return self.session.get_active_player()


def unlocked(semester: int = 1, days: int = 80):
    """A context whose quest for `semester` has been accepted."""
    ctx = _Ctx(semester, days)
    ctx.quest_states.accept(ctx.quest_states.get_quest_for_semester(semester))
    return ctx


def quest_of(semester: int) -> str:
    """The quest id offered in a semester."""
    return QuestStateMachine().get_quest_for_semester(semester)


def read_to_the_end(ctx, quest_id) -> int:
    """Open a sitting and page every sheet. Returns the sheets read."""
    assert lecture_reader.start(ctx, quest_id) is None
    seen = 0
    while lecture_reader.is_open():
        seen += 1
        lecture_reader.advance(ctx)
    return seen


def sheet_order(ctx, quest_id) -> list:
    """The sheet ids a sitting shows, in the order it shows them."""
    assert lecture_reader.start(ctx, quest_id) is None
    order = []
    while lecture_reader.is_open():
        order.append(lecture_reader.current_sheet()["title"])
        lecture_reader.advance(ctx)
    return order


class patched_definition:
    """
    Edit one quest's definition for the length of a `with` block.

    The table is module-level data validated at import, so a case that
    needs a broken row has to break it and put it back. Restores the
    whole entry rather than the one key, so a test cannot leak.
    """

    def __init__(self, quest_id: str, **changes) -> None:
        self.__quest_id = quest_id
        self.__changes = changes
        self.__saved = None

    def __enter__(self):
        self.__saved = copy.deepcopy(defs.SIDE_QUEST_DEFINITIONS[
            self.__quest_id])
        defs.SIDE_QUEST_DEFINITIONS[self.__quest_id].update(self.__changes)
        return self

    def __exit__(self, *_) -> bool:
        defs.SIDE_QUEST_DEFINITIONS[self.__quest_id] = self.__saved
        return False


# ── the flow, in the brief's own order ─────────────────────────

def test_flow_the_day_gate_is_rechecked_on_open():
    """
    Step 1: re-check the day rules, and abort with NO side effects if
    they refuse.

    Forced by draining the term after the quest was accepted, which is
    the shape a stale confirmation has.

    UPDATED BY PHASE 17. At one day left BOTH day rules now refuse, and
    the wider one answers first: below the end-of-semester threshold no
    new lecture may be started whatever it costs. What this test is
    about — the re-check happens before a single day moves — is
    unchanged, and the cost rule itself is still covered directly in
    tests/test_side_quest_list.py::test_day_*.
    """
    ctx = unlocked(1, days=80)
    ctx.semester().deduct_time(79)                    # 1 day left, cost 2
    before = ctx.quest_states.get_all_states()
    refused = lecture_reader.start(ctx, quest_of(1))
    assert refused is not None and refused[0] == "TOO LATE IN THE TERM"
    assert not lecture_reader.is_open(), "opened a reader it refused"
    assert ctx.semester().get_time_pool_days() == 1, "spent a day anyway"
    assert ctx.quest_states.get_all_states() == before


def test_flow_the_charge_lands_once_on_open():
    """Step 2: day_cost off the semester, the player AND the global
    career clock, together, through GameClock."""
    ctx = unlocked(1)
    assert lecture_reader.start(ctx, quest_of(1)) is None
    assert ctx.semester().get_time_pool_days() == 80 - DAY_COST
    assert ctx.player().get_time_pool_days() == 80 - DAY_COST
    assert ctx.session.get_global_career_clock_days() == DAY_COST
    lecture_reader.end()


def test_flow_the_charge_is_not_repeated_per_sheet():
    """"ONCE, on open, not per sheet" — the words of the brief."""
    ctx = unlocked(1)
    lecture_reader.start(ctx, quest_of(1))
    after_open = ctx.semester().get_time_pool_days()
    while lecture_reader.is_open():
        lecture_reader.advance(ctx)
        assert ctx.semester().get_time_pool_days() == after_open, \
            "a sheet cost a day"
    assert after_open == 80 - DAY_COST
    lecture_reader.end()


def test_flow_opens_on_the_first_sheet():
    """Step 3, for all twelve."""
    for semester in SEMESTERS:
        ctx = unlocked(semester)
        quest_id = quest_of(semester)
        assert lecture_reader.start(ctx, quest_id) is None
        assert lecture_reader.get_sheet_number() == 1
        first = get_lecture_sheets(quest_id)[0]
        assert lecture_reader.current_sheet() is get_sheet(first)
        lecture_reader.end()


def test_flow_every_sheet_in_order():
    """Step 4: every sheet for that quest, in the order Phase 12 lists
    them. Checked against the definitions table, for all twelve."""
    for semester in SEMESTERS:
        ctx = unlocked(semester)
        quest_id = quest_of(semester)
        assert lecture_reader.start(ctx, quest_id) is None
        seen = []
        while lecture_reader.is_open():
            index = lecture_reader.get_sheet_number() - 1
            seen.append(get_lecture_sheets(quest_id)[index])
            assert lecture_reader.current_sheet() is get_sheet(seen[-1])
            lecture_reader.advance(ctx)
        assert seen == get_lecture_sheets(quest_id)
        assert len(seen) == SHEETS_PER_QUEST
        lecture_reader.end()


def test_flow_the_last_sheet_marks_completed_and_applies_the_skill():
    """Step 5, the acceptance criterion, for all twelve."""
    for semester in SEMESTERS:
        ctx = unlocked(semester)
        quest_id = quest_of(semester)
        skill_id = get_skill_id(quest_id)
        tree = ctx.player().get_skill_tree()
        assert not skill_completion.is_completed(ctx, skill_id)
        assert read_to_the_end(ctx, quest_id) == SHEETS_PER_QUEST
        assert ctx.quest_states.get_state(quest_id) == STATE_COMPLETED
        # TASK 4: was `tree.get_skill_level(skill_id) == SKILL_REWARD`.
        # The skill is binary now and the level never moves — both
        # halves of that are asserted, so a grant creeping back in
        # fails here rather than passing quietly.
        assert skill_completion.is_completed(ctx, skill_id)
        assert tree.get_skill_level(skill_id) == 0
        lecture_reader.end()


def test_flow_nothing_is_applied_before_the_last_sheet():
    """The state and the skill both move on the LAST sheet, not on the
    way in and not on the way through."""
    ctx = unlocked(1)
    quest_id = quest_of(1)
    skill_id = get_skill_id(quest_id)
    lecture_reader.start(ctx, quest_id)
    for _ in range(SHEETS_PER_QUEST - 1):
        assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED
        assert not skill_completion.is_completed(ctx, skill_id)
        lecture_reader.advance(ctx)
    assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED
    lecture_reader.advance(ctx)                        # the last one
    assert ctx.quest_states.get_state(quest_id) == STATE_COMPLETED
    assert skill_completion.is_completed(ctx, skill_id)
    lecture_reader.end()


def test_flow_the_skill_reward_is_the_catalogs_number():
    """
    The EXP is read from academic/side_quest_catalog.py, not declared in
    the reader.

    engine/endgame_manager.py's two ending thresholds are documented as
    lining up with it, so a second copy that drifted would put an ending
    quietly out of reach.
    """
    catalog = build_side_quest_catalog()
    for quest_id in QUEST_IDS:
        quest = get_side_quest_by_id(catalog, quest_id)
        assert quest is not None, "%s is not in the catalog" % quest_id
        assert lecture_reader.skill_reward(quest_id) == quest.get_exp_reward()
        assert lecture_reader.skill_reward(quest_id) == SKILL_REWARD


def test_flow_a_topic_can_only_pay_out_once():
    """Completed is terminal, so a second sitting is refused before it
    can charge a day or grant a second reward."""
    ctx = unlocked(1)
    quest_id = quest_of(1)
    read_to_the_end(ctx, quest_id)
    lecture_reader.end()
    days = ctx.semester().get_time_pool_days()
    level = ctx.player().get_skill_tree().get_skill_level(
        get_skill_id(quest_id))

    refused = lecture_reader.start(ctx, quest_id)
    assert refused is not None and refused[0] == "ALREADY READ"
    assert ctx.semester().get_time_pool_days() == days
    assert ctx.player().get_skill_tree().get_skill_level(
        get_skill_id(quest_id)) == level


def test_flow_the_state_machine_was_not_modified():
    """
    "Do not modify the state machine's transition rules."

    Five states and four transitions, exactly as Phase 12 left them.
    R1 (RETRYABLE) is what makes this possible — a ONE-SHOT rule would
    have needed a sixth state and a fifth transition.
    """
    assert len(QUEST_STATES) == 5
    assert len(LEGAL_TRANSITIONS) == 4
    assert LEGAL_TRANSITIONS == frozenset((
        (STATE_UNOFFERED, STATE_DECLINED),
        (STATE_UNOFFERED, STATE_MISSED),
        (STATE_UNOFFERED, STATE_UNLOCKED),
        (STATE_UNLOCKED, STATE_COMPLETED),
    ))


def test_flow_mark_completed_is_the_only_transition_this_phase_makes():
    """A whole run through the reader moves exactly one quest, one step,
    and touches nothing else."""
    ctx = unlocked(1)
    ctx.quest_states.accept(quest_of(2))
    ctx.quest_states.decline(quest_of(3))
    ctx.quest_states.expire_unoffered_for_semester(4)
    before = ctx.quest_states.get_all_states()
    read_to_the_end(ctx, quest_of(1))
    lecture_reader.end()
    after = ctx.quest_states.get_all_states()
    moved = [q for q in QUEST_IDS if before[q] != after[q]]
    assert moved == [quest_of(1)]
    assert after[quest_of(1)] == STATE_COMPLETED


# ── R1: leaving early is RETRYABLE ─────────────────────────────

def test_r1_leaving_early_leaves_the_quest_unlocked():
    """The quest is exactly where it was. No new state, no transition."""
    ctx = unlocked(1)
    quest_id = quest_of(1)
    lecture_reader.start(ctx, quest_id)
    lecture_reader.advance(ctx)
    assert lecture_reader.abandon() is True
    assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED


def test_r1_days_are_not_refunded():
    """The cost of walking out, stated plainly and actually charged."""
    ctx = unlocked(1)
    lecture_reader.start(ctx, quest_of(1))
    lecture_reader.abandon()
    assert ctx.semester().get_time_pool_days() == 80 - DAY_COST
    assert ctx.player().get_time_pool_days() == 80 - DAY_COST
    assert ctx.session.get_global_career_clock_days() == DAY_COST


def test_r1_the_full_cost_is_payable_again():
    """"The player may pay full cost again" — and the second attempt
    starts at sheet 1, not where they left off."""
    ctx = unlocked(1)
    quest_id = quest_of(1)
    lecture_reader.start(ctx, quest_id)
    lecture_reader.advance(ctx)
    lecture_reader.advance(ctx)
    assert lecture_reader.get_sheet_number() == 3
    lecture_reader.abandon()

    assert lecture_reader.start(ctx, quest_id) is None
    assert lecture_reader.get_sheet_number() == 1, "resumed instead of restarting"
    assert ctx.semester().get_time_pool_days() == 80 - DAY_COST * 2
    lecture_reader.end()


def test_r1_the_day_gate_is_rechecked_on_the_retry():
    """
    "Re-check the day gate on each attempt." A term that can afford one
    sitting but not two refuses the second.

    UPDATED BY PHASE 17. The term is set to threshold + 2 rather than
    cost + 1, because the sitting that puts the term ON the threshold is
    now the last one it will allow — which is exactly the shape this
    test wanted, one attempt granted and the next refused, with the
    end-of-term lockout doing the refusing instead of the cost.
    """
    limit = side_quest_list.threshold(unlocked(1))
    ctx = unlocked(1, days=limit + 2)                  # room for one only
    quest_id = quest_of(1)
    lecture_reader.start(ctx, quest_id)
    lecture_reader.abandon()
    assert ctx.semester().get_time_pool_days() == limit
    refused = lecture_reader.start(ctx, quest_id)
    assert refused is not None and refused[0] == "TOO LATE IN THE TERM"
    assert "%d days" % limit in " ".join(refused[1])
    assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED


def test_r1_no_partial_credit():
    """
    "Finishing sheet 7 of 8 and leaving is worth exactly as much as
    finishing zero."

    Every stopping point short of the end produces the same quest state
    and the same skill level as never opening it at all.
    """
    baseline = _Ctx(1)
    baseline.quest_states.accept(quest_of(1))
    untouched = (baseline.quest_states.get_all_states(),
                 baseline.player().get_skill_tree().get_skill_level(
                     get_skill_id(quest_of(1))))

    for stop_after in range(SHEETS_PER_QUEST):         # 0, 1, 2 sheets
        ctx = unlocked(1)
        lecture_reader.start(ctx, quest_of(1))
        for _ in range(stop_after):
            lecture_reader.advance(ctx)
        lecture_reader.abandon()
        assert (ctx.quest_states.get_all_states(),
                ctx.player().get_skill_tree().get_skill_level(
                    get_skill_id(quest_of(1)))) == untouched, \
            "stopping after %d sheets was worth something" % stop_after


def test_r1_the_warning_says_it_can_be_started_again():
    """R1 is stated to the player, not just implemented."""
    ctx = unlocked(1)
    lecture_reader.start(ctx, quest_of(1))
    _, lines = lecture_reader.exit_warning()
    body = " ".join(lines).lower()
    assert "gone" in body, "does not say the days are lost"
    assert "kept" in body, "does not say no progress is kept"
    assert "sheet 1" in body, "does not say it restarts from the beginning"
    lecture_reader.end()


# ── R2: what counts as leaving early ───────────────────────────

def test_r2_closing_the_panel_ends_the_sitting():
    """The first of the two: abandon() is what the panel's exit calls."""
    ctx = unlocked(1)
    lecture_reader.start(ctx, quest_of(1))
    assert lecture_reader.abandon() is True
    assert not lecture_reader.is_open()
    assert lecture_reader.get_quest_id() is None
    assert lecture_reader.abandon() is False, "abandoning twice"


def test_r2_saving_and_reloading_loses_the_sitting():
    """
    The second of the two, proved on a real file.

    The payload cannot carry a sitting, because nothing writes one:
    capture() taken mid-read is identical to capture() taken without the
    reader ever being opened, apart from the days that were spent.
    """
    from engine import save_bridge
    from engine.save_manager import SaveManager, build_state

    ctx = screen_ctx()
    ctx.quest_states.accept(quest_of(2))
    lecture_reader.start(ctx, quest_of(2))
    lecture_reader.advance(ctx)                        # mid-sitting
    assert lecture_reader.is_open()

    mid_read = save_bridge.capture(ctx)
    blob = json.dumps(mid_read)
    for sheet_id in get_lecture_sheets(quest_of(2)):
        assert sheet_id not in blob, "a sheet id reached the save file"
    assert "sheet" not in blob.lower(), "something sheet-shaped is in the save"
    assert mid_read["quests"]["states"][quest_of(2)] == STATE_UNLOCKED, \
        "a sitting in progress is not a completion"

    folder = tempfile.mkdtemp(prefix="cse_life_reader_")
    try:
        manager = SaveManager(folder)
        assert manager.save(1, mid_read)
        assert save_bridge.restore(ctx, manager.load(1))
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    assert not lecture_reader.is_open(), "a reload resumed a sitting"
    assert ctx.quest_states.get_state(quest_of(2)) == STATE_UNLOCKED
    assert ctx.semester().get_time_pool_days() == 80 - DAY_COST, \
        "the days spent must survive the reload; the reading must not"


def test_r2_restore_drops_a_sitting_left_over_in_the_process():
    """save_bridge.restore() clears the reader, so a loaded game can
    never inherit one from earlier in the same session."""
    from engine import save_bridge
    ctx = screen_ctx()
    ctx.quest_states.accept(quest_of(2))
    lecture_reader.start(ctx, quest_of(2))
    assert lecture_reader.is_open()
    save_bridge.new_game(ctx)
    assert not lecture_reader.is_open()


def test_r2_the_reader_offers_no_route_to_the_pause_menu():
    """
    Structural, and the reason the two named cases are the whole list.

    progression.open_pause() is called from exactly one place —
    engine/states/exploration.py — so SAVE GAME and QUIT TO MENU are
    both unreachable while the reader is open. A save cannot be taken
    mid-sitting at all; the case above covers a payload that was made
    one anyway.
    """
    from engine.states import side_quest_lecture
    source = open(side_quest_lecture.__file__, encoding="utf-8").read()
    for forbidden in ("open_pause", "pause_menu", "resolve_pause",
                      "ScreenState.SAVE_GAME"):
        assert forbidden not in source, \
            "the reader reaches %s" % forbidden


# ── no per-sheet progress, anywhere ────────────────────────────

def test_nobookmark_nothing_survives_the_sitting():
    """There is no resume point to read back, by any public name."""
    ctx = unlocked(1)
    lecture_reader.start(ctx, quest_of(1))
    lecture_reader.advance(ctx)
    lecture_reader.abandon()
    assert lecture_reader.get_quest_id() is None
    assert lecture_reader.get_sheet_number() == 0
    assert lecture_reader.get_sheet_count() == 0
    assert lecture_reader.get_day_cost() == 0
    assert not lecture_reader.is_open() and not lecture_reader.is_finished()


def test_nobookmark_the_quest_state_carries_no_progress():
    """The machine has five states and none of them is "part-read"."""
    ctx = unlocked(1)
    lecture_reader.start(ctx, quest_of(1))
    lecture_reader.advance(ctx)
    lecture_reader.abandon()
    assert ctx.quest_states.get_state(quest_of(1)) in QUEST_STATES
    assert ctx.quest_states.get_state(quest_of(1)) == STATE_UNLOCKED


# ── refusals ───────────────────────────────────────────────────

def test_block_an_unknown_quest_id():
    """A typo is a caller bug and is refused, not invented around."""
    for bad in ("", None, "SQ_NOPE", 7):
        refused = lecture_reader.blocker(unlocked(1), bad)
        assert refused is not None and refused[0] == "LECTURE UNAVAILABLE"


def test_block_a_quest_that_is_not_on_the_pcs_list():
    """Unoffered, Declined and Missed all refuse — the reader can only
    open what the PC could show, and Phase 14 decides that."""
    for state in (STATE_UNOFFERED, STATE_DECLINED, STATE_MISSED):
        ctx = _Ctx(1)
        quest_id = quest_of(1)
        if state == STATE_DECLINED:
            ctx.quest_states.decline(quest_id)
        elif state == STATE_MISSED:
            ctx.quest_states.expire_unoffered_for_semester(1)
        assert ctx.quest_states.get_state(quest_id) == state
        refused = lecture_reader.blocker(ctx, quest_id)
        assert refused is not None, "%s opened a reader" % state


def test_block_the_day_refusal_is_reused_and_names_both_numbers():
    """
    The refusal is Phase 14's, reused rather than rewritten — the point
    of the test, and it is the identity below that proves it.

    UPDATED BY PHASE 17: at one day left the refusal that comes back is
    the end-of-term lockout, which names both of ITS numbers for the
    same reason the cost one names both of its own.
    """
    ctx = unlocked(1, days=1)
    limit = side_quest_list.threshold(ctx)
    refused = lecture_reader.blocker(ctx, quest_of(1))
    assert refused == side_quest_list.refusal(ctx, quest_of(1))
    assert "1 day" in " ".join(refused[1])
    assert "%d days" % limit in " ".join(refused[1])


def test_block_a_refusal_changes_nothing_at_all():
    """Every blocked path leaves the machine, both day pools and the
    global clock exactly as they were."""
    for days in (0, 1):
        ctx = unlocked(1, days=days)
        snapshot = (ctx.quest_states.get_all_states(),
                    ctx.semester().get_time_pool_days(),
                    ctx.player().get_time_pool_days(),
                    ctx.session.get_global_career_clock_days())
        assert lecture_reader.start(ctx, quest_of(1)) is not None
        assert not lecture_reader.is_open()
        assert (ctx.quest_states.get_all_states(),
                ctx.semester().get_time_pool_days(),
                ctx.player().get_time_pool_days(),
                ctx.session.get_global_career_clock_days()) == snapshot


def test_block_can_start_agrees_with_blocker():
    """One rule, one front door."""
    ctx = unlocked(1)
    assert lecture_reader.can_start(ctx, quest_of(1))
    assert not lecture_reader.can_start(ctx, quest_of(2))
    assert not lecture_reader.can_start(_Ctx(1, days=1), quest_of(1))


# ── the four named edge cases ──────────────────────────────────

def test_edge_unconfigured_day_cost_blocks_rather_than_passing_silently():
    """
    EDGE 3, and the acceptance criterion: day_cost -1 blocks with an
    explicit error and is never treated as free.
    """
    quest_id = quest_of(1)
    with patched_definition(quest_id, day_cost=-1):
        ctx = unlocked(1)
        refused = lecture_reader.start(ctx, quest_id)
        assert refused is not None
        assert refused[0] == "LECTURE NOT CONFIGURED"
        assert "day cost" in " ".join(refused[1]).lower()
        assert not lecture_reader.is_open(), "opened an unconfigured topic"
        assert ctx.semester().get_time_pool_days() == 80
        assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED


def test_edge_unconfigured_day_cost_blocks_even_with_days_to_spare():
    """
    The check runs BEFORE the day gate, deliberately.

    -1 satisfies `remaining >= cost` for every pool there is, including
    an empty one, so a day check running first would wave it through as
    free — which is exactly the failure the brief names. Asserted at a
    full term AND at zero days.
    """
    quest_id = quest_of(1)
    with patched_definition(quest_id, day_cost=-1):
        for days in (80, 40, 2, 0):
            ctx = unlocked(1, days=days)
            refused = lecture_reader.start(ctx, quest_id)
            assert refused[0] == "LECTURE NOT CONFIGURED", \
                "at %d days the day gate answered first" % days
            assert ctx.semester().get_time_pool_days() == days


def test_edge_a_non_integer_day_cost_blocks_too():
    """None, a string and True are all "not configured", not zero."""
    quest_id = quest_of(1)
    for bad in (None, "2", 2.0, True):
        with patched_definition(quest_id, day_cost=bad):
            refused = lecture_reader.start(unlocked(1), quest_id)
            assert refused is not None and \
                refused[0] == "LECTURE NOT CONFIGURED", \
                "day_cost %r was accepted" % (bad,)


def test_edge_the_definitions_table_refuses_a_negative_cost_at_import():
    """The first lock, which is why the sentinel cannot ship: Phase 12's
    validate() fails the whole module rather than let -1 load."""
    quest_id = quest_of(1)
    with patched_definition(quest_id, day_cost=-1):
        try:
            defs.validate()
        except defs.SideQuestDefinitionError as error:
            assert "day_cost" in str(error)
        else:
            raise AssertionError("validate() accepted a negative day_cost")


def test_edge_a_sheet_that_fails_to_load_does_not_stop_the_sequence():
    """
    EDGE 4, resolved per R2: a bad sheet id is one unreadable card, not
    a lost sitting.

    get_sheet() hands back DEFAULT_SHEET, the player pages past it, and
    the topic still completes — the fault is the content table's, and
    charging the player two days and a topic for it would not be.
    """
    quest_id = quest_of(1)
    real = get_lecture_sheets(quest_id)
    broken = [real[0], "SQ_DOES_NOT_EXIST", real[2]]
    with patched_definition(quest_id, lecture_sheets=broken):
        ctx = unlocked(1)
        assert lecture_reader.start(ctx, quest_id) is None
        titles = []
        while lecture_reader.is_open():
            titles.append(lecture_reader.current_sheet()["title"])
            lecture_reader.advance(ctx)
        assert len(titles) == 3, "the sequence stopped at the broken sheet"
        assert titles[1] == DEFAULT_SHEET["title"]
        assert ctx.quest_states.get_state(quest_id) == STATE_COMPLETED
        assert skill_completion.is_completed(ctx, get_skill_id(quest_id))
        assert ctx.semester().get_time_pool_days() == 80 - DAY_COST
    lecture_reader.end()


def test_edge_a_quest_with_no_sheets_at_all_blocks():
    """An empty list is different from a broken id: there is nothing to
    read, so nothing is charged."""
    with patched_definition(quest_of(1), lecture_sheets=[]):
        ctx = unlocked(1)
        refused = lecture_reader.start(ctx, quest_of(1))
        assert refused is not None and refused[0] == "NOTHING TO READ"
        assert ctx.semester().get_time_pool_days() == 80


def test_edge_the_last_start_of_the_term_is_one_day_above_the_threshold():
    """
    EDGE 1, first half — REWRITTEN BY PHASE 17.

    It used to open a sitting with the term at exactly `day_cost` and
    assert the pool landing on zero. A lecture can no longer take the
    term anywhere near zero: `threshold + 1` is the last day one may be
    opened at all, so the floor a lecture can leave the term on is
    `threshold + 1 - day_cost` and never lower.

    What the test still proves is the half that matters: the deduction
    resolves in full at the boundary, and the day count does not
    interrupt a reader once it is open — the sitting reads through and
    completes with the term below the threshold the whole way.
    """
    ctx = unlocked(1)
    limit = side_quest_list.threshold(ctx)
    ctx = unlocked(1, days=limit + 1)                 # the last legal day
    assert lecture_reader.start(ctx, quest_of(1)) is None
    assert ctx.semester().get_time_pool_days() == limit + 1 - DAY_COST
    assert ctx.player().get_time_pool_days() == limit + 1 - DAY_COST
    assert side_quest_list.is_locked_out(ctx), \
        "the charge should have taken the term past the threshold"
    assert read_through(ctx) == SHEETS_PER_QUEST, \
        "a locked-out term interrupted a reader that was already open"
    assert ctx.quest_states.get_state(quest_of(1)) == STATE_COMPLETED
    lecture_reader.end()

    # ...and one day earlier is already too late, with nothing spent.
    ctx = unlocked(1, days=limit)
    assert lecture_reader.start(ctx, quest_of(1)) is not None
    assert ctx.semester().get_time_pool_days() == limit


def read_through(ctx) -> int:
    """Page an already-open sitting to the end. Returns sheets read."""
    seen = 0
    while lecture_reader.is_open():
        seen += 1
        lecture_reader.advance(ctx)
    return seen


def test_edge_the_charge_crosses_the_phase_6_threshold():
    """
    EDGE 1, second half: crossing 15 days by opening a lecture is
    indistinguishable from crossing it by sitting an exam, because both
    go through GameClock and Phase 6 reads the counter afterwards.
    """
    from engine import day_warning
    ctx = unlocked(1, days=16)
    assert not day_warning.is_low(ctx)
    assert lecture_reader.start(ctx, quest_of(1)) is None
    assert day_warning.is_low(ctx), "the charge did not cross the rule"
    assert day_warning.hud_days(ctx) == 14
    lecture_reader.end()


def test_edge_a_frozen_run_blocks_rather_than_reading_for_free():
    """
    process_time_consumable() is a no-op on a frozen session, so a
    reader opened there would cost nothing. "Never treat as free"
    applies to the end of the game as much as to an unset cost.
    """
    ctx = unlocked(1)
    ctx.session.freeze_session()
    refused = lecture_reader.start(ctx, quest_of(1))
    assert refused is not None and refused[0] == "NO TIME LEFT"
    assert not lecture_reader.is_open()
    assert ctx.semester().get_time_pool_days() == 80


def test_edge_a_short_player_pool_blocks_rather_than_parting_the_two():
    """
    The two day counters are separate ints. A charge the player's own
    pool cannot cover would take the semester's and not theirs, and the
    two would disagree for the rest of the run.
    """
    ctx = unlocked(1)
    ctx.player().deduct_time_pool_days(79)             # player 1, term 80
    refused = lecture_reader.start(ctx, quest_of(1))
    assert refused is not None and refused[0] == "NOT ENOUGH DAYS"
    assert ctx.semester().get_time_pool_days() == 80
    assert ctx.player().get_time_pool_days() == 1


def test_edge_no_quest_machine_never_raises():
    """The editor, the harnesses and a half-built AppContext all land
    here, and a refusal beats a crash."""
    class _Bare:
        pass
    assert lecture_reader.blocker(_Bare(), quest_of(1)) is not None
    assert not lecture_reader.can_start(_Bare(), quest_of(1))


# ── what the popups can hold ───────────────────────────────────

def every_message(ctx):
    """Every (title, lines) pair this phase can put in a popup."""
    out = []
    for semester in SEMESTERS:
        run = unlocked(semester)
        quest_id = quest_of(semester)
        lecture_reader.start(run, quest_id)
        out.append(lecture_reader.exit_warning())
        while lecture_reader.is_open():
            lecture_reader.advance(run)
        out.append(lecture_reader.completion_notice(run))
        lecture_reader.end()
        out.append(lecture_reader.blocker(run, quest_id))       # ALREADY READ
        out.append(lecture_reader.blocker(_Ctx(1, days=1), quest_of(1)))
        out.append(lecture_reader.blocker(run, "SQ_NOPE"))
    frozen = unlocked(1)
    frozen.session.freeze_session()
    out.append(lecture_reader.blocker(frozen, quest_of(1)))
    with patched_definition(quest_of(1), day_cost=-1):
        out.append(lecture_reader.blocker(unlocked(1), quest_of(1)))
    with patched_definition(quest_of(1), lecture_sheets=[]):
        out.append(lecture_reader.blocker(unlocked(1), quest_of(1)))
    return [message for message in out if message is not None]


def test_popup_every_message_fits_the_three_line_maximum():
    """ui/popup.py drops anything past three body lines, silently."""
    for title, lines in every_message(None):
        assert 0 < len(lines) <= MAX_BODY_LINES, \
            "%s has %d lines" % (title, len(lines))


def test_popup_every_message_fits_the_box_width():
    """
    Measured through the real PressStart2P at the real body size, not
    counted in characters.

    "Object-Oriented Programming (OOP)" is 33 characters and was the
    reason the completion notice puts the title on a line of its own.
    """
    font = load_font(SIZE_BODY)
    for title, lines in every_message(None):
        for line in lines:
            width = font.size(line)[0]
            assert width <= BODY_MAX_PX, \
                "%r is %dpx, over the %dpx the card allows (%s)" \
                % (line, width, BODY_MAX_PX, title)


def test_popup_every_message_is_plain_ascii():
    """The pixel font has no glyph for a stray em dash, and a missing
    glyph renders as a blank box on the one card that explains a loss."""
    for title, lines in every_message(None):
        for text in [title] + list(lines):
            assert text.isascii(), "%r is not ascii" % text


# ── through the real screens ───────────────────────────────────

__ctx = None


def screen_ctx(semester: int = 2, days: int = 80):
    """
    A real AppContext, restored into a hand-made run.

    One AppContext is built for the whole file and re-restored per case,
    the way tests/test_side_quest_list.py does it: building one opens an
    audio device and loads every font, and doing that a dozen times is
    slow for no extra coverage.
    """
    global __ctx
    from engine import save_bridge
    from engine.app_context import AppContext
    from engine.save_manager import build_state

    if __ctx is None:
        pygame.init()
        pygame.display.set_mode((1280, 720))
        __ctx = AppContext()
    save_bridge.restore(__ctx, build_state(current_semester=semester,
                                           time_pool_days=days))
    __ctx.return_state = ScreenState.EXPLORATION
    __ctx.popup.close()
    __ctx.popup.take_result()
    __ctx.message_popup.close()
    __ctx.message_popup.take_result()
    __ctx.screen_mgr.transition_to(ScreenState.SIDE_QUEST_LECTURE)
    lecture_reader.end()
    return __ctx


def opened(semester: int = 2, days: int = 80):
    """A real context sitting in the reader, with the days charged."""
    from engine.states import side_quest_lecture
    ctx = screen_ctx(semester, days)
    ctx.quest_states.accept(quest_of(semester))
    assert lecture_reader.start(ctx, quest_of(semester)) is None
    side_quest_lecture.enter(ctx)
    return ctx


def at_the_pc(semester: int = 2, days: int = 80):
    """
    A real context standing at the PC's list, with the quest accepted.

    Parked on SIDE_QUESTS rather than on the reader, so "did it hand
    over yet?" below is a real question instead of an assertion about
    where the harness left the router.
    """
    from engine import day_warning
    from engine.states import side_quests
    ctx = screen_ctx(semester, days)
    ctx.quest_states.accept(quest_of(semester))
    ctx.screen_mgr.transition_to(ScreenState.SIDE_QUESTS)
    day_warning.forget()
    side_quests.enter(ctx)
    return ctx


def confirm_the_topic(ctx) -> None:
    """START on the highlighted row, then answer its question yes."""
    from engine.states import side_quests
    side_quests.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_RETURN)])
    assert ctx.popup.is_open(), "no confirmation was asked"
    ctx.popup.set_result(RESULT_CONFIRM)
    side_quests.update(ctx, 0.016)


def key(ctx, code) -> None:
    """One KEYDOWN through the real reader state."""
    from engine.states import side_quest_lecture
    side_quest_lecture.handle_events(
        ctx, [pygame.event.Event(pygame.KEYDOWN, key=code)])


def answer(ctx, result) -> None:
    """Answer the open ConfirmPopup the way the router's modal would,
    then give the state its update() frame."""
    from engine.states import side_quest_lecture
    ctx.popup.set_result(result)
    side_quest_lecture.update(ctx, 0.016)


def landed_on(ctx):
    """The state the router would move to next."""
    ctx.screen_mgr.apply_pending_transition()
    return ctx.screen_mgr.get_current_state()


def page_to_the_end(ctx) -> int:
    """SPACE through every sheet of an open reader. Returns presses."""
    presses = 0
    while lecture_reader.is_open() and presses < 200:
        key(ctx, pygame.K_SPACE)
        presses += 1
    return presses


def page_one_sheet(ctx) -> None:
    """
    SPACE until the reader moves off the sheet it is on.

    A sheet is not one press: Phase 11.5 split every paragraph into
    several `lines` sized for ui/dialog_box.py's three-row card, and
    SPACE advances one of those at a time — the same two-stage press
    engine/states/lecture.py uses.
    """
    start = lecture_reader.get_sheet_number()
    for _ in range(40):
        if not lecture_reader.is_open() \
                or lecture_reader.get_sheet_number() != start:
            return
        key(ctx, pygame.K_SPACE)
    raise AssertionError("sheet %d never ended" % start)


def test_screen_reads_a_topic_end_to_end():
    """
    The acceptance criterion, through the real reader: every sheet on
    SPACE, then Completed, the skill applied, and the days gone once.
    """
    ctx = opened(2)
    quest_id = quest_of(2)
    assert ctx.semester().get_time_pool_days() == 80 - DAY_COST
    page_to_the_end(ctx)
    assert ctx.quest_states.get_state(quest_id) == STATE_COMPLETED
    assert skill_completion.is_completed(ctx, get_skill_id(quest_id))
    assert ctx.semester().get_time_pool_days() == 80 - DAY_COST
    assert ctx.message_popup.get_title() == "TOPIC COMPLETE"
    assert landed_on(ctx) is ScreenState.EXPLORATION


def test_screen_escape_asks_before_it_leaves():
    """"Any player-initiated exit must warn first." ESC opens the
    question and leaves the reader exactly where it was."""
    ctx = opened(2)
    page_one_sheet(ctx)                                # onto sheet 2
    assert lecture_reader.get_sheet_number() == 2
    key(ctx, pygame.K_ESCAPE)
    assert ctx.popup.is_open(), "ESC left without asking"
    assert ctx.popup.get_title() == "LEAVE THE LECTURE?"
    assert ctx.popup.get_confirm_label() == "LEAVE"
    assert lecture_reader.is_open(), "the sitting ended before the answer"
    assert landed_on(ctx) is ScreenState.SIDE_QUEST_LECTURE
    lecture_reader.end()


def test_screen_cancelling_the_warning_keeps_reading():
    """CANCEL is the default way out of the question, and it changes
    nothing — same sheet, same days, same state."""
    ctx = opened(2)
    page_one_sheet(ctx)
    days = ctx.semester().get_time_pool_days()
    key(ctx, pygame.K_ESCAPE)
    answer(ctx, RESULT_CANCEL)
    assert lecture_reader.is_open()
    assert lecture_reader.get_sheet_number() == 2, "lost the reader's place"
    assert ctx.semester().get_time_pool_days() == days
    assert landed_on(ctx) is ScreenState.SIDE_QUEST_LECTURE
    lecture_reader.end()


def test_screen_confirming_the_warning_keeps_nothing():
    """The R1 path through the real screen: days spent, nothing kept,
    the quest still Unlocked, back on the map."""
    ctx = opened(2)
    quest_id = quest_of(2)
    page_one_sheet(ctx)
    page_one_sheet(ctx)                                # two of three read
    key(ctx, pygame.K_ESCAPE)
    answer(ctx, RESULT_CONFIRM)
    assert not lecture_reader.is_open()
    assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED
    assert ctx.player().get_skill_tree().get_skill_level(
        get_skill_id(quest_id)) == 0
    assert ctx.semester().get_time_pool_days() == 80 - DAY_COST
    assert landed_on(ctx) is ScreenState.EXPLORATION


def test_screen_enter_does_not_advance_a_sheet():
    """
    ENTER is CONFIRM on every ConfirmPopup in this game. Binding it to
    "next sheet" as well would let a player mashing through a lecture
    answer the leave question by accident, with two days on it.
    """
    ctx = opened(2)
    for code in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
        key(ctx, code)
    assert lecture_reader.get_sheet_number() == 1, "a non-SPACE key advanced"
    lecture_reader.end()


def test_screen_a_click_advances():
    """Click-to-advance, the way lecture.py and dialogue.py both do."""
    from engine.states import side_quest_lecture
    ctx = opened(2)
    for _ in range(60):
        if not lecture_reader.is_open():
            break
        side_quest_lecture.handle_events(ctx, [pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 600))])
    assert ctx.quest_states.get_state(quest_of(2)) == STATE_COMPLETED
    lecture_reader.end()


def test_screen_the_exit_hook_ends_any_sitting():
    """No path off this screen can leave a sitting half-alive."""
    from engine.states import side_quest_lecture
    ctx = opened(2)
    key(ctx, pygame.K_SPACE)
    assert lecture_reader.is_open()
    side_quest_lecture.exit(ctx)
    assert not lecture_reader.is_open()
    assert ctx.quest_states.get_state(quest_of(2)) == STATE_UNLOCKED


def test_screen_routed_to_with_nothing_open_bounces():
    """Nothing paid for it, so there is nothing to read."""
    from engine.states import side_quest_lecture
    ctx = screen_ctx(2)
    side_quest_lecture.enter(ctx)
    assert landed_on(ctx) is ScreenState.EXPLORATION
    side_quest_lecture.render(ctx, pygame.display.get_surface())


def test_screen_does_not_read_a_popup_it_did_not_open():
    """ctx.popup is shared. An update() with no question of ours open
    must not throw away a lecture off somebody else's CONFIRM."""
    from engine.states import side_quest_lecture
    ctx = opened(2)
    ctx.popup.open("SOMEBODY ELSE'S QUESTION", ["not ours"])
    ctx.popup.set_result(RESULT_CONFIRM)
    side_quest_lecture.update(ctx, 0.016)
    assert lecture_reader.is_open(), "answered a question it never asked"
    assert ctx.popup.take_result() == RESULT_CONFIRM, \
        "the other screen's result must still be there for it to read"
    lecture_reader.end()


def test_screen_renders_every_sheet_of_every_topic():
    """Draws, headless, without raising — all twelve topics, all their
    sheets, plus the header the state owns."""
    from engine.states import side_quest_lecture
    surface = pygame.display.get_surface()
    for semester in SEMESTERS:
        ctx = opened(semester)
        while lecture_reader.is_open():
            side_quest_lecture.update(ctx, 0.016)
            side_quest_lecture.render(ctx, surface)
            assert lecture_reader.progress_label().startswith("SHEET ")
            key(ctx, pygame.K_SPACE)
        lecture_reader.end()


# ── the hand-over from the PC's list ───────────────────────────

def test_handover_the_warning_is_answered_before_the_reader_opens():
    """
    EDGE 1: "resolve the time change fully BEFORE the reader opens, and
    do not let time events interrupt an open reader."

    Set up at 16 days, so the charge crosses Phase 6's threshold. The
    card waits with the warning up; only once it is dismissed does the
    router move to the reader.
    """
    from engine import day_warning
    from engine.states import side_quests
    ctx = at_the_pc(2, days=16)
    confirm_the_topic(ctx)

    assert ctx.semester().get_time_pool_days() == 14, "the charge did not land"
    assert ctx.message_popup.is_open(), "Phase 6's warning did not fire"
    assert ctx.message_popup.get_title() == "WARNING"
    assert landed_on(ctx) is ScreenState.SIDE_QUESTS, \
        "handed over with a time event still on screen"

    ctx.message_popup.set_result("ok")
    ctx.message_popup.take_result()
    side_quests.update(ctx, 0.016)
    assert landed_on(ctx) is ScreenState.SIDE_QUEST_LECTURE
    assert lecture_reader.is_open()
    lecture_reader.end()
    day_warning.forget()


def test_handover_no_warning_means_no_wait():
    """A charge that crosses nothing hands over on the same frame."""
    from engine import day_warning
    ctx = at_the_pc(2, days=80)
    confirm_the_topic(ctx)
    assert not ctx.message_popup.is_open()
    assert landed_on(ctx) is ScreenState.SIDE_QUEST_LECTURE
    lecture_reader.end()
    day_warning.forget()


def test_handover_a_stale_confirmation_charges_nothing():
    """The term drained under an open question refuses at the charge as
    well as at the card, and spends nothing either way.

    UPDATED BY PHASE 17: the term drained to zero is now below the
    end-of-term threshold, so the lockout is what refuses. Which of the
    two day rules says no is not what this test is about — that nothing
    is charged and the player is left on the card is."""
    from engine.states import side_quests
    ctx = at_the_pc(2, days=80)
    side_quests.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_RETURN)])
    assert ctx.popup.is_open()
    ctx.semester().deduct_time(ctx.semester().get_time_pool_days())
    ctx.popup.set_result(RESULT_CONFIRM)
    side_quests.update(ctx, 0.016)
    assert not lecture_reader.is_open(), "opened a reader nobody paid for"
    assert ctx.semester().get_time_pool_days() == 0
    assert ctx.message_popup.get_title() == "TOO LATE IN THE TERM"
    assert landed_on(ctx) is ScreenState.SIDE_QUESTS


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
        lecture_reader.end()
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

    print("\n-- one sitting, end to end --")
    run = unlocked(1)
    print("days before      : %d" % run.semester().get_time_pool_days())
    lecture_reader.start(run, quest_of(1))
    print("days after open  : %d"
          % run.semester().get_time_pool_days())
    while lecture_reader.is_open():
        print("  %-12s %s" % (lecture_reader.progress_label(),
                              lecture_reader.topic()))
        lecture_reader.advance(run)
    print("state            : %s" % run.quest_states.get_state(quest_of(1)))
    print("skill            : %s = %d"
          % (lecture_reader.skill_name(),
             run.player().get_skill_tree().get_skill_level(
                 get_skill_id(quest_of(1)))))
    print("days after read  : %d" % run.semester().get_time_pool_days())
    lecture_reader.end()
    return 0


if __name__ == "__main__":
    sys.exit(main())

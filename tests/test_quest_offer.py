"""
tests/test_quest_offer.py
CSE Life: Compile & Conquer
Phase 13 — coverage for the NPC side quest offer

    python -m tests.test_quest_offer

Headless and self-contained: SDL_VIDEODRIVER=dummy, no window anybody
can see, and the only thing written to disk is a throwaway temporary
directory — the real saves/ folder is never touched, exactly the rule
engine/save_manager.py's own stub test follows.

WHAT IS ACTUALLY DRIVEN. Most of this file runs against a REAL
AppContext, the REAL level files, the REAL DialogueManager and the real
engine/states/dialogue.py event loop, with pygame KEYDOWN events pushed
through it. Nothing about the conversation is mocked, because the thing
under test is precisely that the offer appears in the middle of the
real dialogue path and nowhere else.

    the acceptance criterion         test_offer_*, test_accept_*,
                                     test_decline_*, test_second_*
    only the semester's NPC          test_only_*
    edge A: rollover on the day      test_edge_a_*
    edge B: interrupted conversation test_edge_b_*
    edge C: absent / unreachable NPC test_edge_c_*
    the term ending                  test_close_semester_*
    the Phase 9 stores are retired   test_retired_*
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame                                      # noqa: E402

from content.level_registry import get_npc_min_semester   # noqa: E402
from content.npc_quest_offers import SEMESTER_QUEST_OFFERS  # noqa: E402
from content.side_quest_definitions import (       # noqa: E402
    QUEST_IDS,
    get_npc_id,
    get_quest_for_semester,
    get_semester,
)
from content.level_schema import (                # noqa: E402
    level_path, list_level_files, read_level)
from engine import dialogue_flow, npc_availability, quest_offer  # noqa: E402
from engine.app_context import AppContext          # noqa: E402
from engine.level_loader import load_level         # noqa: E402
from engine.quest_state import (                   # noqa: E402
    STATE_DECLINED,
    STATE_MISSED,
    STATE_UNLOCKED,
    STATE_UNOFFERED,
    QuestStateMachine,
)
from engine.save_manager import SaveManager, build_state   # noqa: E402
from engine.states import dialogue, exam           # noqa: E402
from engine import save_bridge                     # noqa: E402

SEMESTERS = tuple(range(1, 13))


# ── the world these tests run in ───────────────────────────────

def level_by_npc() -> dict:
    """
    {npc type id: level id}, read off the level files themselves.

    Scanned rather than written out, so an NPC moved to another map in
    the editor moves this suite with it instead of breaking it.
    """
    found = {}
    for path in list_level_files():
        document = read_level(path)
        for npc in document.get_npcs():
            found.setdefault(npc.get_type_id(), document.get_level_id())
    return found


LEVEL_BY_NPC = level_by_npc()

__ctx = None


def context_at(semester: int) -> AppContext:
    """
    A real AppContext sitting in `semester`, with a fresh quest machine.

    One AppContext is built for the whole run and re-restored per case:
    building it opens an audio device and loads every font, and doing
    that thirty times is slow for no extra coverage. restore() rebuilds
    the session, the clock, the catalog and ctx.quest_states from a save
    payload, which is exactly the reset each case wants.
    """
    global __ctx
    if __ctx is None:
        pygame.init()
        __ctx = AppContext()
    save_bridge.restore(__ctx, build_state(current_semester=semester))
    return __ctx


def npc_for(semester: int):
    """(level, NpcData) for the NPC who offers `semester`'s quest."""
    type_id = get_npc_id(get_quest_for_semester(semester))
    level = load_level(LEVEL_BY_NPC[type_id], semester=semester)
    for npc in level.get_npcs():
        if npc.get_type_id() == type_id:
            return level, npc
    raise AssertionError("%s is not on %s in semester %d"
                         % (type_id, LEVEL_BY_NPC[type_id], semester))


def npc_named(semester: int, type_id: str):
    """(level, NpcData) for any placed NPC, or (None, None) if hidden."""
    level = load_level(LEVEL_BY_NPC[type_id], semester=semester)
    for npc in level.get_npcs():
        if npc.get_type_id() == type_id:
            return level, npc
    return level, None


# ── driving a real conversation ────────────────────────────────

def talk(ctx, level, npc) -> bool:
    """Press E on `npc`, the way exploration.__talk does."""
    ctx.level = level
    ctx.level_id = level.get_level_id()
    started = dialogue_flow.start_talk(ctx, npc)
    if started:
        dialogue.enter(ctx)              # what the router does next
    return started


def press(ctx, key) -> None:
    """One KEYDOWN through the real dialogue state."""
    dialogue.handle_events(ctx, [pygame.event.Event(pygame.KEYDOWN, key=key)])


def run_to_offer(ctx, limit: int = 80) -> bool:
    """
    SPACE through the chain until the offer docks. False if it never
    does — including because the conversation simply ended.

    Asserts on the way that the offer NEVER appears while the chain
    still has lines to give: "after the normal dialogue concludes" is
    half the behaviour under test, so it is checked on every press
    rather than only at the end.
    """
    for _ in range(limit):
        if dialogue_flow.is_offer_open(ctx):
            return True
        if not ctx.dialogue_manager.is_active():
            return False
        shown, total = ctx.dialogue_manager.get_progress()
        assert not dialogue_flow.is_offer_open(ctx), "offer cut the chain off"
        press(ctx, pygame.K_SPACE)
    return dialogue_flow.is_offer_open(ctx)


def answer(ctx, accept: bool) -> None:
    """Pick Accept or Decline on the open reply list."""
    assert dialogue_flow.is_offer_open(ctx), "no offer is open to answer"
    if not accept:
        press(ctx, pygame.K_DOWN)
        assert ctx.choice_box.get_selected() == 1
    press(ctx, pygame.K_RETURN)


def run_out(ctx, limit: int = 40) -> None:
    """SPACE until the conversation is over."""
    for _ in range(limit):
        if not ctx.dialogue_manager.is_active():
            return
        press(ctx, pygame.K_SPACE)
    raise AssertionError("the conversation never ended")


def full_talk(ctx, semester: int, accept: bool) -> None:
    """Walk up, hear them out, answer, walk away."""
    level, npc = npc_for(semester)
    assert talk(ctx, level, npc), "the conversation did not start"
    assert run_to_offer(ctx), "no offer after the dialogue concluded"
    answer(ctx, accept)
    run_out(ctx)


# ══ the acceptance criterion ═══════════════════════════════════

def test_offer_appears_after_the_dialogue_in_every_semester():
    """All twelve: the chain plays out, then Accept / Decline docks."""
    for semester in SEMESTERS:
        ctx = context_at(semester)
        level, npc = npc_for(semester)
        assert talk(ctx, level, npc), "semester %d" % semester
        assert run_to_offer(ctx), "semester %d put no offer" % semester
        assert ctx.choice_options == list(quest_offer.REPLIES), semester
        assert ctx.choice_prompt == quest_offer.PROMPT, semester
        assert ctx.pending_quest_id == get_quest_for_semester(semester)
        # The lines on screen are the authored ones, not invented here.
        offer = SEMESTER_QUEST_OFFERS[semester]
        assert ctx.dialogue_manager.get_current_line() \
            == offer["offer_lines"][0], semester


def test_offer_uses_the_existing_choice_prompt_not_a_new_one():
    """The reply list is ui/choice_box.py, shared with authored
    branches — the constraint against a parallel dialogue path."""
    ctx = context_at(1)
    level, npc = npc_for(1)
    talk(ctx, level, npc)
    run_to_offer(ctx)
    assert ctx.choice_box is not None, "the offer built its own widget"
    assert dialogue_flow.is_choice_open(ctx), "not on the shared hook"
    assert dialogue_flow.is_offer_open(ctx), "not flagged as the offer"
    assert len(ctx.choice_options) == 2


def test_accept_unlocks_the_quest_and_ends_the_conversation():
    """All twelve, through the state machine's own API."""
    for semester in SEMESTERS:
        ctx = context_at(semester)
        quest_id = get_quest_for_semester(semester)
        full_talk(ctx, semester, accept=True)
        assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED, semester
        assert quest_id in ctx.quest_states.get_unlocked_quests()
        assert ctx.dialogue_npc is None and ctx.pending_quest_id is None
        assert not dialogue_flow.is_offer_open(ctx)


def test_accept_starts_nothing_else():
    """The quest does NOT begin: no completion, no days, no skill."""
    ctx = context_at(1)
    days_before = ctx.semester().get_time_pool_days()
    skill_before = ctx.player().get_skill_tree().get_skill_level("git")
    full_talk(ctx, 1, accept=True)
    assert ctx.quest_states.get_completed_quests() == [], "a quest completed"
    assert ctx.semester().get_time_pool_days() == days_before, "days spent"
    assert ctx.player().get_skill_tree().get_skill_level("git") == skill_before
    assert ctx.player().get_accumulated_credits() == 0


def test_decline_declines_the_quest_and_ends_the_conversation():
    """All twelve. Declined is terminal — nothing leaves it."""
    for semester in SEMESTERS:
        ctx = context_at(semester)
        quest_id = get_quest_for_semester(semester)
        full_talk(ctx, semester, accept=False)
        assert ctx.quest_states.get_state(quest_id) == STATE_DECLINED, semester
        assert quest_id not in ctx.quest_states.get_unlocked_quests()
        assert ctx.dialogue_npc is None and ctx.pending_quest_id is None


def test_the_reply_lines_match_the_answer():
    """Accept plays the accept lines, Decline the decline lines."""
    for accept in (True, False):
        ctx = context_at(1)
        level, npc = npc_for(1)
        talk(ctx, level, npc)
        run_to_offer(ctx)
        answer(ctx, accept)
        key = "accept_lines" if accept else "decline_lines"
        assert ctx.dialogue_manager.get_current_line() \
            == SEMESTER_QUEST_OFFERS[1][key][0], key


def test_second_interaction_never_offers_again_after_accepting():
    """Talking again plays unchanged dialogue. No reminder, no nag."""
    for semester in SEMESTERS:
        ctx = context_at(semester)
        quest_id = get_quest_for_semester(semester)
        full_talk(ctx, semester, accept=True)

        level, npc = npc_for(semester)
        assert talk(ctx, level, npc), "the NPC stopped talking"
        first_line = ctx.dialogue_manager.get_current_line()
        assert not run_to_offer(ctx), "offered twice in semester %d" % semester
        assert ctx.pending_quest_id is None
        assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED

        # Unchanged: the same chain, from the same first line, as a
        # player who was never offered anything would have heard.
        fresh = context_at(semester)
        level, npc = npc_for(semester)
        talk(fresh, level, npc)
        assert fresh.dialogue_manager.get_current_line() == first_line


def test_second_interaction_offers_again_after_declining():
    """
    TASK 2, the acceptance criterion: decline, walk away, come back,
    and the same NPC puts the same offer again — in every semester, so
    this is the whole game and not one special-cased NPC.

    This test used to assert the opposite. Declining was terminal until
    the owner's Sprint 5 ruling; it now holds only until the player
    walks back.
    """
    for semester in SEMESTERS:
        ctx = context_at(semester)
        quest_id = get_quest_for_semester(semester)
        full_talk(ctx, semester, accept=False)
        assert ctx.quest_states.get_state(quest_id) == STATE_DECLINED

        level, npc = npc_for(semester)
        assert talk(ctx, level, npc)
        assert run_to_offer(ctx), \
            "the offer did not return in semester %d" % semester
        assert ctx.pending_quest_id == quest_id, \
            "a different quest came back in semester %d" % semester


def test_the_returned_offer_can_be_accepted():
    """Saying no in week one and yes in week six is the point of it."""
    for semester in SEMESTERS:
        ctx = context_at(semester)
        quest_id = get_quest_for_semester(semester)
        full_talk(ctx, semester, accept=False)
        full_talk(ctx, semester, accept=True)
        assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED, \
            "the second answer did not stick in semester %d" % semester


def test_declining_ten_times_keeps_re_offering():
    """Every time, for as long as the semester lasts — not just once."""
    ctx = context_at(1)
    quest_id = get_quest_for_semester(1)
    for attempt in range(10):
        full_talk(ctx, 1, accept=False)
        assert ctx.quest_states.get_state(quest_id) == STATE_DECLINED, \
            "state drifted on attempt %d" % attempt
    # ...and it is still there on the eleventh.
    level, npc = npc_for(1)
    assert talk(ctx, level, npc)
    assert run_to_offer(ctx), "the offer stopped coming back"


def test_an_accepted_quest_is_never_offered_again():
    """
    The half of the old rule that stays.

    Accepting IS permanent — only declining comes back — so ten more
    conversations must stay silent.
    """
    ctx = context_at(1)
    full_talk(ctx, 1, accept=True)
    for attempt in range(10):
        level, npc = npc_for(1)
        assert talk(ctx, level, npc)
        assert not run_to_offer(ctx), "offered on attempt %d" % attempt
        run_out(ctx)


# ══ only the semester's own NPC ════════════════════════════════

def test_only_the_assigned_npc_offers_anything():
    """Every other NPC on the map behaves exactly as it does today."""
    for semester in SEMESTERS:
        ctx = context_at(semester)
        assigned = get_npc_id(get_quest_for_semester(semester))
        for type_id in sorted(LEVEL_BY_NPC):
            if type_id == assigned:
                continue
            level, npc = npc_named(semester, type_id)
            if npc is None:
                continue                 # not around this term (Phase 8)
            assert talk(ctx, level, npc), "%s stopped talking" % type_id
            assert ctx.pending_quest_id is None, \
                "%s armed an offer in semester %d" % (type_id, semester)
            assert not run_to_offer(ctx), \
                "%s offered in semester %d" % (type_id, semester)
        assert ctx.quest_states.get_all_states() \
            == QuestStateMachine().get_all_states(), semester


def test_only_the_right_semester_offers_a_given_quest():
    """The same NPC in a term that is not theirs offers nothing —
    five of the seven offer twice, so this is a real case."""
    for semester in SEMESTERS:
        ctx = context_at(semester)
        for other in SEMESTERS:
            if other == semester:
                continue
            type_id = get_npc_id(get_quest_for_semester(other))
            if get_npc_min_semester(type_id) > semester:
                continue
            if get_npc_id(get_quest_for_semester(semester)) == type_id:
                continue                 # they DO owe one, just not this
            level, npc = npc_named(semester, type_id)
            assert quest_offer.offered_quest_id(ctx, npc) is None, \
                "%s offered semester %d's quest in semester %d" \
                % (type_id, other, semester)


# ══ EDGE A — the day the semester rolls over ═══════════════════

def test_edge_a_answer_then_rollover_keeps_the_answer():
    """
    Answered, and the term closes in the same breath.

    A conversation is ScreenState.DIALOGUE and a rollover happens on
    the exam screen or at the end_semester prop, so the two can never
    interleave — the ordering is total.

    TASK 2 SPLIT THE TWO ANSWERS APART. Accepting is still an answer
    that outlives the term: the quest is Unlocked and the expiry leaves
    it alone. Declining is not — it holds only while the term runs, so
    closing the term takes a still-declined quest to Missed exactly
    like one that was never put. That is the brief's "on semester
    change the quest becomes unavailable regardless".
    """
    ctx = context_at(1)
    full_talk(ctx, 1, accept=True)
    assert quest_offer.expire_semester(ctx) is None, "expiry overrode accept"
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_UNLOCKED

    ctx = context_at(1)
    full_talk(ctx, 1, accept=False)
    assert quest_offer.expire_semester(ctx) == "SQ_GIT_GITHUB", \
        "a declined quest survived the term it was declined in"
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_MISSED


def test_edge_a_rollover_then_talk_offers_nothing():
    """
    The other order: the term closed first.

    The quest is Missed, so can_offer() is False, and the semester has
    moved on to a quest that belongs to somebody else. The NPC plays
    unchanged dialogue.
    """
    ctx = context_at(1)
    assert quest_offer.expire_semester(ctx) == "SQ_GIT_GITHUB"
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_MISSED
    level, npc = npc_for(1)
    assert talk(ctx, level, npc)
    assert ctx.pending_quest_id is None
    assert not run_to_offer(ctx), "offered a missed quest"
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_MISSED


def test_edge_a_a_stale_offer_is_refused_rather_than_written():
    """
    The guard, forced by hand.

    resolve() re-derives the quest from the context instead of trusting
    what was armed, so an answer can only ever land on the term the
    game is actually in. Nothing in the engine can produce this, which
    is why it is produced here.
    """
    ctx = context_at(1)
    level, npc = npc_for(1)
    talk(ctx, level, npc)
    run_to_offer(ctx)
    # The term turns over underneath the open question.
    save_bridge.restore(ctx, build_state(current_semester=2))
    ctx.pending_quest_id = "SQ_GIT_GITHUB"
    assert not quest_offer.is_still_offerable(ctx, "SQ_GIT_GITHUB")
    assert not quest_offer.resolve(ctx, "SQ_GIT_GITHUB", True)
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_UNOFFERED
    assert ctx.quest_states.get_state("SQ_OOP") == STATE_UNOFFERED


def test_edge_a_zero_days_left_still_offers():
    """
    Decision D1: this phase does not gate on days.

    A term drained to nothing still puts the offer, because the 15-day
    threshold and the quest's day_cost are Phase 17's and two places
    deciding whether a side quest may start is one too many.
    """
    ctx = context_at(1)
    ctx.semester().deduct_time(ctx.semester().get_time_pool_days())
    assert ctx.semester().get_time_pool_days() == 0
    full_talk(ctx, 1, accept=True)
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_UNLOCKED


# ══ EDGE B — an interrupted conversation ═══════════════════════

def test_edge_b_escape_before_the_offer_leaves_it_unoffered():
    """ESC on the first line: no offer fired, nothing written."""
    ctx = context_at(1)
    level, npc = npc_for(1)
    talk(ctx, level, npc)
    assert ctx.pending_quest_id == "SQ_GIT_GITHUB", "not armed"
    press(ctx, pygame.K_ESCAPE)
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_UNOFFERED
    assert ctx.pending_quest_id is None, "the arm outlived the talk"
    assert not dialogue_flow.is_offer_open(ctx)


def test_edge_b_escape_on_the_last_line_leaves_it_unoffered():
    """The nastiest moment to walk off: one press from the question."""
    ctx = context_at(1)
    level, npc = npc_for(1)
    talk(ctx, level, npc)
    while True:
        shown, total = ctx.dialogue_manager.get_progress()
        if shown >= total:
            break
        press(ctx, pygame.K_SPACE)
    assert not dialogue_flow.is_offer_open(ctx), "offer opened too early"
    press(ctx, pygame.K_ESCAPE)
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_UNOFFERED
    assert ctx.pending_quest_id is None


def test_edge_b_an_interrupted_talk_is_offered_again():
    """Walking away is not an answer — the question comes back."""
    ctx = context_at(1)
    for _ in range(3):
        level, npc = npc_for(1)
        talk(ctx, level, npc)
        press(ctx, pygame.K_ESCAPE)
        assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_UNOFFERED
    level, npc = npc_for(1)
    talk(ctx, level, npc)
    assert run_to_offer(ctx), "the offer never came back"
    answer(ctx, accept=True)
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_UNLOCKED


def test_edge_b_the_open_offer_cannot_be_escaped():
    """
    Once the question is on screen the reply list owns every event.

    engine/states/dialogue.py swallows ESC while a choice is open, and
    that is deliberate for authored branches; the offer inherits it, so
    the only way past the question is to answer it.
    """
    ctx = context_at(1)
    level, npc = npc_for(1)
    talk(ctx, level, npc)
    run_to_offer(ctx)
    for _ in range(5):
        press(ctx, pygame.K_ESCAPE)
        assert dialogue_flow.is_offer_open(ctx), "ESC skipped the question"
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_UNOFFERED
    answer(ctx, accept=False)
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_DECLINED


def test_edge_b_a_load_mid_offer_leaves_it_unoffered():
    """Loading a save with the question on screen writes nothing."""
    ctx = context_at(1)
    level, npc = npc_for(1)
    talk(ctx, level, npc)
    run_to_offer(ctx)
    assert dialogue_flow.is_offer_open(ctx)
    save_bridge.restore(ctx, build_state(current_semester=1))
    assert not dialogue_flow.is_offer_open(ctx), "the offer survived a load"
    assert ctx.pending_quest_id is None
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_UNOFFERED
    level, npc = npc_for(1)
    talk(ctx, level, npc)
    assert run_to_offer(ctx), "the offer did not come back after loading"


# ══ EDGE C — an absent, unavailable or unreachable NPC ═════════

def test_edge_c_no_offer_is_stranded_behind_the_semester_gate():
    """
    Every offering NPC is already on the map in their offer term.

    content/side_quest_definitions.py::validate() asserts this at
    import, so a table that stranded one would refuse to boot. Checked
    again here against the placements themselves, which validate() does
    not read.
    """
    for quest_id in QUEST_IDS:
        semester = get_semester(quest_id)
        type_id = get_npc_id(quest_id)
        assert get_npc_min_semester(type_id) <= semester, quest_id
        level, npc = npc_named(semester, type_id)
        assert npc is not None, \
            "%s is not on the map in semester %d" % (type_id, semester)
        assert npc.get_effective_min_semester() <= semester, quest_id


def test_edge_c_a_hidden_npc_is_not_on_the_map_at_all():
    """Phase 8's filter, from this phase's side: an NPC whose term has
    not come is absent, so there is nobody to be offered anything by."""
    early = load_level(LEVEL_BY_NPC["hoque"], semester=4)
    assert all(npc.get_type_id() != "hoque" for npc in early.get_npcs())
    ready = load_level(LEVEL_BY_NPC["hoque"], semester=5)
    assert any(npc.get_type_id() == "hoque" for npc in ready.get_npcs())
    document = read_level(level_path(LEVEL_BY_NPC["hoque"]))
    assert "hoque" in [n.get_type_id() for n in document.get_npcs()]
    assert npc_availability.hidden_in(document, 4), "nobody hidden at all"


def test_edge_c_an_unreachable_npc_ends_the_term_missed():
    """
    The ordinary case: the player never walks to that map.

    Nothing special happens and nothing is stuck — the quest was never
    offered, so the term's close marks it Missed and it is gone.
    """
    ctx = context_at(6)
    assert ctx.quest_states.get_state("SQ_LINUX_CLI") == STATE_UNOFFERED
    assert quest_offer.expire_semester(ctx) == "SQ_LINUX_CLI"
    assert ctx.quest_states.get_state("SQ_LINUX_CLI") == STATE_MISSED
    level, npc = npc_for(6)
    assert talk(ctx, level, npc), "the NPC stopped talking"
    assert not run_to_offer(ctx), "a missed quest was offered"


def test_edge_c_an_npc_gated_out_of_their_own_term_is_never_asked():
    """
    The one way absence could become real: an editor gate raising a
    placement's min semester above the roster's. Nothing in the repo
    does it today, so it is built here.

    The offer is simply never put. It expires Missed at term close,
    the same as any other quest nobody got round to.
    """
    ctx = context_at(1)
    level, npc = npc_for(1)
    document = read_level(level_path(LEVEL_BY_NPC["purnno"]))
    placed = next(n for n in document.get_npcs()
                  if n.get_type_id() == "purnno")
    record = placed.to_dict()
    record["gate"] = {"min_semester": 9}
    document.replace_npc(placed.get_uid(), record)
    gated = next(n for n in document.get_npcs()
                 if n.get_type_id() == "purnno")
    assert gated.get_effective_min_semester() == 9
    assert not npc_availability.is_available(gated, 1), "still on the map"
    # Phase 8 would have removed them at load; talking is impossible,
    # so the term simply ends with the quest never offered.
    assert quest_offer.expire_semester(ctx) == "SQ_GIT_GITHUB"
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == STATE_MISSED


def test_edge_c_a_context_with_no_quest_machine_never_raises():
    """The editor, the harnesses, a half-built context."""
    class _Bare:
        pass

    assert quest_offer.offered_quest_id(_Bare(), npc_for(1)[1]) is None
    assert quest_offer.expire_semester(_Bare()) is None
    assert not quest_offer.resolve(_Bare(), "SQ_GIT_GITHUB", True)
    assert quest_offer.machine_of(_Bare()) is None
    assert quest_offer.semester_of(_Bare()) == quest_offer.SEMESTER_NONE


# ══ the term ending ════════════════════════════════════════════

def test_close_semester_expires_the_unoffered_quest():
    """The hook, through the real close_semester()."""
    ctx = context_at(3)
    ctx.semester().register_course(ctx.full_catalog[0])
    exam.close_semester(ctx)
    assert ctx.quest_states.get_state("SQ_DSA") == STATE_MISSED
    assert ctx.semester().get_semester_number() == 4, "the term did not roll"
    assert ctx.quest_states.get_state("SQ_WEB_APP_DEV") == STATE_UNOFFERED


def test_close_semester_leaves_a_taken_quest_alone():
    """
    Accepted and completed quests keep their answer through a rollover.

    TASK 2: declined no longer does. A quest still refused when the term
    closes is Missed — the decline was only ever good for that term —
    so it is asserted here as Missed rather than Declined.
    """
    ctx = context_at(2)
    full_talk(ctx, 2, accept=True)
    exam.close_semester(ctx)
    assert ctx.quest_states.get_state("SQ_OOP") == STATE_UNLOCKED

    ctx = context_at(2)
    full_talk(ctx, 2, accept=False)
    exam.close_semester(ctx)
    assert ctx.quest_states.get_state("SQ_OOP") == STATE_MISSED, \
        "a declined quest survived the term it was declined in"

    ctx = context_at(2)
    full_talk(ctx, 2, accept=True)
    ctx.quest_states.mark_completed("SQ_OOP")
    exam.close_semester(ctx)
    assert ctx.quest_states.get_state("SQ_OOP") == "completed"


def test_close_semester_expires_before_the_freeze_check():
    """
    A run that ends on ENDGAME still closes its books.

    Owner ruling: the expiry sits above the freeze check, so the final
    term's quest is Missed rather than left Unoffered forever where
    Phase 16's ending gate would read it.
    """
    ctx = context_at(12)
    ctx.player().add_credits(140)                  # freezes the session
    ctx.game_clock.check_semester_end_state()
    assert ctx.session.get_is_frozen(), "the session did not freeze"
    exam.close_semester(ctx)
    assert ctx.quest_states.get_state("SQ_PROGRAMMING_LANGUAGE") \
        == STATE_MISSED
    assert ctx.semester().get_semester_number() == 12, "a frozen run rolled"


def test_close_semester_expires_only_the_term_that_ended():
    """Twelve terms in a row, nobody talked to: twelve Missed, in
    order, and never one ahead of itself."""
    ctx = context_at(1)
    for semester in SEMESTERS:
        assert ctx.semester().get_semester_number() == semester
        ahead = [q for q in QUEST_IDS if get_semester(q) > semester]
        exam.close_semester(ctx)
        assert ctx.quest_states.get_state(
            get_quest_for_semester(semester)) == STATE_MISSED, semester
        for quest_id in ahead:
            assert ctx.quest_states.get_state(quest_id) == STATE_UNOFFERED
        if ctx.session.get_is_frozen():
            break
    assert len([q for q in QUEST_IDS
                if ctx.quest_states.get_state(q) == STATE_MISSED]) == 12


# ══ persistence, and the retirement of Phase 9's stores ════════

def test_the_answer_survives_a_save_and_a_load():
    """
    Through a real file on disk, both answers, all twelve.

    TASK 2 changed what "still not offered after the round trip" means
    for a decline: it IS offered again, because the term is still
    running. Accepts stay silent. Both are checked below.
    """
    folder = tempfile.mkdtemp(prefix="cse_life_offer_")
    try:
        saves = SaveManager(save_dir=folder)
        ctx = context_at(1)
        expected = {}
        for semester in SEMESTERS:
            save_bridge.restore(ctx, build_state(current_semester=semester))
            full_talk(ctx, semester, accept=semester % 2 == 1)
            expected[get_quest_for_semester(semester)] = (
                STATE_UNLOCKED if semester % 2 == 1 else STATE_DECLINED)

            assert saves.save(1, save_bridge.capture(ctx))
            reloaded = saves.load(1)
            assert reloaded is not None
            assert save_bridge.restore(ctx, reloaded)
            quest_id = get_quest_for_semester(semester)
            assert ctx.quest_states.get_state(quest_id) \
                == expected[quest_id], quest_id
            # The state survives the round trip, and so does what it
            # means: an accept stays silent, a decline comes back.
            level, npc = npc_for(semester)
            talk(ctx, level, npc)
            offered = run_to_offer(ctx)
            if expected[quest_id] == STATE_UNLOCKED:
                assert not offered, "an accepted quest was offered after load"
            else:
                assert offered, "a declined quest stopped coming back"
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_retired_phase_9_stores_are_gone():
    """
    ctx.unlocked_side_quests and ctx.decided_quest_semesters are
    removed, not shadowed.

    Two stores for one quest is two answers that can disagree, and
    Phase 12's handoff asked for them to go in one change. The machine
    is now the only thing that knows.
    """
    ctx = context_at(1)
    assert not hasattr(ctx, "unlocked_side_quests")
    assert not hasattr(ctx, "decided_quest_semesters")
    assert not hasattr(ctx, "pending_quest_npc")
    assert hasattr(ctx, "quest_states") and hasattr(ctx, "pending_quest_id")

    full_talk(ctx, 1, accept=True)
    assert ctx.quest_states.get_unlocked_quests() == ["SQ_GIT_GITHUB"]


def test_retired_nothing_in_the_repo_still_reads_them():
    """
    A grep, so a re-introduction is caught rather than assumed.

    Attribute access and getattr strings only — the names are still
    spelled out in engine/app_context.py's comment, which is the note
    saying they were retired and is the opposite of a use.
    """
    roots = ("engine", "content", "ui", "academic", "core", "tools")
    stale = ("unlocked_side_quests", "decided_quest_semesters",
             "pending_quest_npc")
    hits = []
    for root in roots:
        for folder, _, files in os.walk(root):
            if "__pycache__" in folder:
                continue
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8") as handle:
                    text = handle.read()
                for word in stale:
                    used = ("." + word in text or '"%s"' % word in text
                            or "'%s'" % word in text)
                    if used:
                        hits.append("%s: %s" % (path, word))
    assert not hits, "retired quest stores are still referenced: %s" % hits


def test_the_offer_is_not_written_into_the_save_payload():
    """An unanswered offer is transient, so the payload gains no key
    and SAVE_SCHEMA_VERSION stays where Phase 12 left it."""
    ctx = context_at(1)
    level, npc = npc_for(1)
    talk(ctx, level, npc)
    run_to_offer(ctx)
    payload = save_bridge.capture(ctx)
    assert payload["schema_version"] == 1
    assert payload["quests"]["states"]["SQ_GIT_GITHUB"] == STATE_UNOFFERED
    assert "pending_quest_id" not in repr(payload)


# ── runner ─────────────────────────────────────────────────────

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

    print("\n-- a whole degree of offers, through the real dialogue --")
    ctx = context_at(1)
    print("%-4s %-8s %-24s %s" % ("SEM", "NPC", "QUEST ID", "STATE"))
    for semester in SEMESTERS:
        save_bridge.restore(ctx, build_state(current_semester=semester))
        machine = ctx.quest_states
        if semester % 3 == 0:
            outcome = "ignored"
            quest_offer.expire_semester(ctx)
        else:
            full_talk(ctx, semester, accept=semester % 3 == 1)
            outcome = ""
        quest_id = get_quest_for_semester(semester)
        print("%-4d %-8s %-24s %s%s"
              % (semester, get_npc_id(quest_id), quest_id,
                 machine.get_state(quest_id),
                 "  (%s)" % outcome if outcome else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

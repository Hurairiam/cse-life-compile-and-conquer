"""
tests/test_day_lockout.py
CSE Life: Compile & Conquer
Phase 17 — coverage for the end-of-semester side quest lockout

    python -m tests.test_day_lockout

Headless and self-contained: SDL_VIDEODRIVER=dummy, no window anybody
can see, and nothing at all is written to disk — this phase adds no save
key and no state of its own, so there is not even a temporary directory
to clean up.

WHAT THIS PHASE CLAIMS, AND WHAT EACH CLAIM IS CHECKED AGAINST
──────────────────────────────────────────────────────────────
    the threshold is Phase 6's, not a second one    test_rule_*
    above it, Phase 15 behaviour is unchanged       test_above_*
    at or below it, no NEW sitting starts, anywhere test_block_*
    a quest already Unlocked is untouched           test_unlocked_*
    D1 (a): the NPC offer is not affected           test_offer_*
    there is no other path to block                 test_paths_*
    through the real PC screen                      test_screen_*

WHAT IS ACTUALLY DRIVEN. The rule half runs against a context built on
the REAL GameSession, GameClock, Player, Semester and SkillTree rather
than mocks of them, because "the term ran out" is a claim about that
pipeline and a fake pool would prove nothing. The last section drives
the REAL engine/states/side_quests.py through a REAL AppContext with
real popups and real pygame KEYDOWN events, because "the player is told
why" is a claim about the screen.

THE NUMBER 15 APPEARS NOWHERE IN THIS FILE ON PURPOSE. Every case reads
the threshold back through `side_quest_list.threshold()`, so lowering or
raising `GameClock.__MIN_MAIN_QUEST_TIME_BORDER` re-aims the whole suite
instead of breaking it — which is itself one of the things being tested.
"""
from __future__ import annotations

import inspect
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame                                          # noqa: E402

from content.side_quest_definitions import (           # noqa: E402
    get_day_cost, get_npc_id)
from engine import (                                   # noqa: E402
    day_warning, dialogue_flow, lecture_reader, quest_offer, side_quest_list)
from engine.game_clock import GameClock                # noqa: E402
from engine.game_session import GameSession            # noqa: E402
from engine.quest_state import (                       # noqa: E402
    LEGAL_TRANSITIONS, STATE_COMPLETED, STATE_UNLOCKED, STATE_UNOFFERED,
    QuestStateMachine)
from engine.screen_manager import ScreenState          # noqa: E402
from ui.popup import (                                 # noqa: E402
    BOX_W, MAX_BODY_LINES, RESULT_CONFIRM, SIZE_BODY, load_font)
from ui.side_quest_screen import CARD_W, SIZE_LABEL    # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The title the lockout refuses under. One string, asserted everywhere,
# so a reworded refusal cannot pass by only being changed in one place.
LOCKOUT_TITLE = "TOO LATE IN THE TERM"

# The widest a popup body line may render, the same figure
# tests/test_lecture_reader.py measures against: the card is BOX_W wide
# with a 4px frame, and 24px of breathing room each side is what the
# existing messages sit inside.
BODY_MAX_PX = BOX_W - 48


# ── a context, without a window ────────────────────────────────

class _Ctx:
    """
    What this phase's rules ask a context for, over the REAL
    GameSession, GameClock, Player, Semester and SkillTree.

    Deliberately not mocked: the threshold is read off the real clock
    and the days off the real semester, which is the whole point — a
    fake pool would let every case below pass while the game did
    nothing.
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
        self.spend(80 - int(days))

    def semester(self):
        return self.session.get_active_semester()

    def player(self):
        return self.session.get_active_player()

    def spend(self, days: int) -> None:
        """Take days off BOTH pools, the way GameClock does."""
        if days > 0:
            self.semester().deduct_time(days)
            self.player().deduct_time_pool_days(days)


class _Npc:
    """The one method engine/quest_offer.py reads off an NpcData."""

    def __init__(self, type_id: str) -> None:
        self.__type_id = type_id

    def get_type_id(self) -> str:
        return self.__type_id


def limit_of(ctx) -> int:
    """The threshold, read back rather than written down."""
    return side_quest_list.threshold(ctx)


def unlocked(semester: int = 1, days: int = 80):
    """A context whose quest for `semester` has been accepted."""
    ctx = _Ctx(semester, days)
    ctx.quest_states.accept(ctx.quest_states.get_quest_for_semester(semester))
    return ctx


def at_threshold(semester: int = 1):
    """A context with its quest Unlocked and the term ON the threshold —
    the first day the lockout applies."""
    ctx = unlocked(semester)
    ctx.spend(80 - limit_of(ctx))
    return ctx


def quest_of(semester: int) -> str:
    """The quest id offered in a semester."""
    return QuestStateMachine().get_quest_for_semester(semester)


def snapshot(ctx):
    """Everything a block is forbidden to move."""
    return (ctx.quest_states.get_all_states(),
            ctx.semester().get_time_pool_days(),
            ctx.player().get_time_pool_days(),
            ctx.session.get_global_career_clock_days())


def source_of(module) -> str:
    """A module's source with its docstring removed.

    The docstrings in this feature discuss the rule at length, and a
    structural check that counted those mentions would be asserting
    prose rather than code.
    """
    text = inspect.getsource(module)
    doc = module.__doc__
    return text.replace(doc, "", 1) if doc else text


# ── the threshold is Phase 6's, not a second one ───────────────

def test_rule_the_threshold_is_the_clocks_own_number():
    """One 15 in the codebase. This phase reads it, never restates it."""
    ctx = _Ctx()
    assert side_quest_list.threshold(ctx) == ctx.game_clock.get_min_border()
    assert side_quest_list.threshold(ctx) == day_warning.threshold(ctx)


def test_rule_the_lockout_is_day_warnings_own_verdict():
    """`is_locked_out` is Phase 6's `is_low` and not a second compare, so
    the popup that warns and the rule that blocks cannot disagree."""
    for days in (80, 41, 16, 15, 14, 1, 0):
        ctx = _Ctx(days=days)
        assert side_quest_list.is_locked_out(ctx) == day_warning.is_low(ctx)


def test_rule_the_lockout_is_the_complement_of_the_firewall():
    """It is the same rule GameClock has owned since Sprint 2, read from
    the other side: eligible for side activities XOR locked out."""
    for days in (80, 16, 15, 0):
        ctx = _Ctx(days=days)
        assert side_quest_list.is_locked_out(ctx) is not \
            ctx.game_clock.is_eligible_for_side_activities()


def test_rule_no_second_number_is_written_down():
    """
    Structural: the two functions that decide the lockout compile with
    no numeric constant at all, and both delegate to day_warning.

    Read off the CODE OBJECT rather than the source text, because the
    docstrings discuss the number at length and a source scan would be
    asserting prose. `co_consts` is exactly the literals the function
    body was compiled with — a `<= 15` written in here would put a 15 in
    it, and nothing else would.

    This is what stops the next person "simplifying" the delegation into
    a hardcoded compare that then drifts from the clock.
    """
    for function in (side_quest_list.threshold,
                     side_quest_list.is_locked_out):
        assert "day_warning" in inspect.getsource(function), function.__name__
        numbers = [value for value in function.__code__.co_consts
                   if isinstance(value, (int, float))
                   and not isinstance(value, bool)]
        assert numbers == [], \
            "%s writes %s down" % (function.__name__, numbers)


def test_rule_the_boundary_is_at_or_below_not_below():
    """The threshold day itself is locked out — `<=`, not `<`."""
    ctx = _Ctx()
    limit = limit_of(ctx)
    assert not side_quest_list.is_locked_out(_Ctx(days=limit + 1))
    assert side_quest_list.is_locked_out(_Ctx(days=limit))
    assert side_quest_list.is_locked_out(_Ctx(days=limit - 1))


def test_rule_no_clock_means_no_lockout():
    """The editor, the harnesses and a half-built context have no
    game_clock. They lock nothing out rather than raising, or locking
    everything out — the same way machine_of() and days_left() go
    quiet."""
    class _Bare:
        def __init__(self):
            self.quest_states = QuestStateMachine()

        def semester(self):
            raise AttributeError("no semester here")

    assert side_quest_list.threshold(object()) == side_quest_list.NO_THRESHOLD
    assert side_quest_list.is_locked_out(object()) is False
    assert side_quest_list.is_locked_out(_Bare()) is False
    assert side_quest_list.threshold(None) == side_quest_list.NO_THRESHOLD


# ── above the threshold, nothing changed ───────────────────────

def test_above_a_sitting_still_opens_and_charges():
    """ACCEPTANCE, first half: with days above the threshold everything
    behaves as it did after Phase 15."""
    ctx = unlocked(1)
    quest_id = quest_of(1)
    assert side_quest_list.is_startable(ctx, quest_id)
    assert side_quest_list.refusal(ctx, quest_id) is None
    assert lecture_reader.start(ctx, quest_id) is None
    assert ctx.semester().get_time_pool_days() == 80 - get_day_cost(quest_id)
    lecture_reader.end()


def test_above_a_sitting_still_completes_the_skill():
    """The whole Phase 15 pipeline, unchanged, above the threshold."""
    from content.side_quest_definitions import get_skill_id
    from engine import skill_completion
    ctx = unlocked(1)
    quest_id = quest_of(1)
    assert lecture_reader.start(ctx, quest_id) is None
    while lecture_reader.is_open():
        lecture_reader.advance(ctx)
    assert ctx.quest_states.get_state(quest_id) == STATE_COMPLETED
    # TASK 4: the sitting used to pay 15 EXP onto the node and this
    # asserted the level moved. Skills are binary now — the assertion
    # is the same claim ("the skill was earned"), read off the flag
    # that replaced the level.
    assert skill_completion.is_completed(ctx, get_skill_id(quest_id))
    lecture_reader.end()


def test_above_the_last_legal_day_is_threshold_plus_one():
    """The boundary from the allowed side: one day above the threshold a
    sitting still opens, and it is the last day one ever will."""
    ctx = unlocked(1)
    limit = limit_of(ctx)
    ctx = unlocked(1, days=limit + 1)
    assert side_quest_list.is_startable(ctx, quest_of(1))
    assert lecture_reader.start(ctx, quest_of(1)) is None
    lecture_reader.end()


def test_above_the_subtitle_still_counts_days():
    """The card says nothing new until the rule applies."""
    from engine.states import side_quests
    subtitle = getattr(side_quests, "__subtitle")
    assert "NO NEW LECTURES" not in subtitle(_Ctx(days=41))
    assert "41" in subtitle(_Ctx(days=41))


# ── at or below the threshold, nothing new starts ──────────────

def test_block_the_list_refuses_every_unlocked_topic():
    """ACCEPTANCE, second half: at the threshold no new side quest can be
    taken on, and the refusal names the rule."""
    ctx = at_threshold(1)
    quest_id = quest_of(1)
    assert side_quest_list.is_locked_out(ctx)
    assert not side_quest_list.is_startable(ctx, quest_id)
    title, lines = side_quest_list.refusal(ctx, quest_id)
    assert title == LOCKOUT_TITLE
    assert lines and len(lines) <= MAX_BODY_LINES


def test_block_the_refusal_names_both_numbers():
    """"Blocking must state a reason." A wall is not a reason: the
    message quotes the days left AND the threshold it is refusing on."""
    ctx = at_threshold(1)
    body = " ".join(side_quest_list.refusal(ctx, quest_of(1))[1])
    assert "%d days" % ctx.semester().get_time_pool_days() in body
    assert "%d days" % limit_of(ctx) in body


def test_block_holds_all_the_way_down_to_zero():
    """Every day from the threshold to an empty term refuses, and always
    for the same reason."""
    limit = limit_of(_Ctx())
    for days in range(limit, -1, -1):
        ctx = unlocked(1, days=days)
        assert not side_quest_list.is_startable(ctx, quest_of(1)), days
        assert side_quest_list.refusal(ctx, quest_of(1))[0] == LOCKOUT_TITLE


def test_block_the_reader_refuses_too():
    """The other end of the same path. lecture_reader.blocker() reuses
    Phase 14's refusal rather than re-deciding, so the lockout reaches
    the charge as well as the card."""
    ctx = at_threshold(1)
    quest_id = quest_of(1)
    assert not lecture_reader.can_start(ctx, quest_id)
    assert lecture_reader.blocker(ctx, quest_id) == \
        side_quest_list.refusal(ctx, quest_id)


def test_block_starting_anyway_changes_nothing():
    """A blocked start is indistinguishable from a start never
    attempted: no day, no state, no global clock, no open reader."""
    ctx = at_threshold(1)
    before = snapshot(ctx)
    refused = lecture_reader.start(ctx, quest_of(1))
    assert refused is not None and refused[0] == LOCKOUT_TITLE
    assert not lecture_reader.is_open(), "opened a reader it refused"
    assert snapshot(ctx) == before


def test_block_a_completed_topic_still_reads_already_read():
    """The lockout sits BELOW the state checks: a term running out is
    not why a finished topic is shut, and saying so would be wrong."""
    ctx = at_threshold(1)
    ctx.quest_states.mark_completed(quest_of(1))
    assert side_quest_list.refusal(ctx, quest_of(1))[0] == "ALREADY READ"


def test_block_every_line_fits_the_popup():
    """The refusal is drawn by ui/popup.py, which neither wraps nor
    truncates: a line wider than the card runs off both sides of it."""
    pygame.init()
    font = load_font(SIZE_BODY)
    ctx = at_threshold(1)
    title, lines = side_quest_list.refusal(ctx, quest_of(1))
    assert len(lines) <= MAX_BODY_LINES
    for line in lines:
        assert font.size(line)[0] <= BODY_MAX_PX, line


def test_block_every_line_is_plain_ascii():
    """The pixel font has no glyph for a stray em dash, and a missing
    glyph renders as a blank box on the card that explains a refusal."""
    from engine.states import side_quests
    ctx = at_threshold(1)
    title, lines = side_quest_list.refusal(ctx, quest_of(1))
    for text in [title] + list(lines):
        assert text.isascii(), "%r is not ascii" % text
    assert getattr(side_quests, "__subtitle")(ctx).isascii()


def test_block_the_card_says_so_before_start_is_pressed():
    """The standing notice, so a muted START is not a mystery."""
    from engine.states import side_quests
    pygame.init()
    subtitle = getattr(side_quests, "__subtitle")(at_threshold(1))
    assert "NO NEW LECTURES" in subtitle
    assert load_font(SIZE_LABEL).size(subtitle)[0] <= CARD_W - 32


# ── a quest already Unlocked is untouched ──────────────────────

def test_unlocked_the_block_moves_no_quest_state():
    """"Blocking must not change any quest state." Every one of the five
    states is left exactly where the block found it."""
    ctx = at_threshold(1)
    ctx.quest_states.accept(quest_of(2))
    ctx.quest_states.decline(quest_of(3))
    ctx.quest_states.expire_unoffered_for_semester(4)
    before = ctx.quest_states.get_all_states()
    for quest_id in (quest_of(1), quest_of(2), quest_of(3), quest_of(4)):
        side_quest_list.is_startable(ctx, quest_id)
        side_quest_list.refusal(ctx, quest_id)
        lecture_reader.blocker(ctx, quest_id)
        lecture_reader.start(ctx, quest_id)
    assert ctx.quest_states.get_all_states() == before


def test_unlocked_the_topic_is_still_listed():
    """The rule blocks starting, not owning. An unlocked topic is still
    on the PC, still named, still counted as a row — hiding it would
    read as having lost it."""
    ctx = at_threshold(1)
    rows = [row["quest_id"] for row in side_quest_list.entries(ctx)]
    assert quest_of(1) in rows
    assert side_quest_list.listed_ids(ctx) == [quest_of(1)]


def test_unlocked_it_starts_again_next_term():
    """
    The block is temporary and the quest survives it: a real semester
    rollover refills the pool and the same topic opens.

    Driven through GameClock.advance_semester(), the one mutator recon
    §7 records for a rollover, rather than by resetting a counter.
    """
    ctx = at_threshold(1)
    quest_id = quest_of(1)
    assert not side_quest_list.is_startable(ctx, quest_id)
    ctx.game_clock.advance_semester()
    assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED, \
        "the rollover moved a quest state"
    assert not side_quest_list.is_locked_out(ctx)
    assert side_quest_list.is_startable(ctx, quest_id)
    assert lecture_reader.start(ctx, quest_id) is None
    lecture_reader.end()


def test_unlocked_a_sitting_already_open_is_not_interrupted():
    """The charge itself may cross the threshold — Phase 6 owns that
    crossing — and the reader that paid for it reads through."""
    ctx = unlocked(1)
    limit = limit_of(ctx)
    ctx = unlocked(1, days=limit + 1)
    assert lecture_reader.start(ctx, quest_of(1)) is None
    assert side_quest_list.is_locked_out(ctx), "the charge did not cross"
    sheets = 0
    while lecture_reader.is_open():
        sheets += 1
        lecture_reader.advance(ctx)
    assert sheets > 0
    assert ctx.quest_states.get_state(quest_of(1)) == STATE_COMPLETED
    lecture_reader.end()


def test_unlocked_the_state_machine_was_not_modified():
    """Out of scope, asserted rather than claimed: five states, four
    transitions, exactly as Phase 12 left them."""
    assert len(LEGAL_TRANSITIONS) == 4
    assert (STATE_UNOFFERED, STATE_UNLOCKED) in LEGAL_TRANSITIONS
    assert (STATE_UNLOCKED, STATE_COMPLETED) in LEGAL_TRANSITIONS


# ── D1 (a): the NPC offer is not affected ──────────────────────

def test_offer_is_still_put_below_the_threshold():
    """Decision D1, answer (a): the offer is still presented, so the NPC
    path is exactly what Phase 13 shipped."""
    ctx = _Ctx(1)
    ctx.spend(80 - limit_of(ctx))
    assert side_quest_list.is_locked_out(ctx)
    npc = _Npc(get_npc_id(quest_of(1)))
    assert quest_offer.offered_quest_id(ctx, npc) == quest_of(1)


def test_offer_can_still_be_accepted_on_an_empty_term():
    """Accept still reaches Unlocked with the term at zero days. What the
    player may not then do is START it — which is the whole of the
    difference between the two paths."""
    ctx = _Ctx(1, days=0)
    quest_id = quest_of(1)
    assert quest_offer.resolve(ctx, quest_id, True)
    assert ctx.quest_states.get_state(quest_id) == STATE_UNLOCKED
    assert not side_quest_list.is_startable(ctx, quest_id)


def test_offer_can_still_be_declined_below_the_threshold():
    """The other answer is unaffected too — the lockout is not a third
    outcome that silently takes the decision away."""
    ctx = _Ctx(2, days=1)
    assert quest_offer.resolve(ctx, quest_of(2), False)
    assert ctx.quest_states.get_state(quest_of(2)) == "declined"


def test_offer_every_semester_still_offers_below_the_threshold():
    """All twelve, not just the first: no term quietly stops offering
    because it ran short."""
    for semester in range(1, 13):
        ctx = _Ctx(semester, days=0)
        quest_id = quest_of(semester)
        npc = _Npc(get_npc_id(quest_id))
        assert quest_offer.offered_quest_id(ctx, npc) == quest_id, semester


def test_offer_the_offer_path_never_reads_a_day_rule():
    """
    Structural, and the real content of D1 (a): neither module on the
    NPC path so much as mentions the threshold, the clock or this
    phase's module. That is what "Phase 13 was not touched" means, and
    it cannot be asserted by reading a diff from inside a test.
    """
    for module in (quest_offer, dialogue_flow):
        body = source_of(module)
        for name in ("day_warning", "side_quest_list", "is_locked_out",
                     "get_min_border", "is_eligible_for_side_activities"):
            assert name not in body, "%s reaches %s" % (module.__name__, name)


# ── there is no other path to block ────────────────────────────

def test_paths_the_dead_side_quest_routes_are_still_dead():
    """
    Step 1's list, made structural.

    `Semester.add_quest()` and `NPC.offer_quest()` are the two
    pre-existing routes recon §12 found, and both are still called by
    nothing — so blocking them would have been blocking dead code. This
    fails the day somebody wires one up, which is exactly when this
    phase needs looking at again.

    Parsed rather than grepped: `engine/npc_manager.py` names
    `NPC.offer_quest()` in its own design notes, explaining why it is
    not used, and a text search cannot tell that paragraph from a call.
    """
    import ast
    callers = []
    for folder in ("engine", "academic", "core", "content", "ui", "tools"):
        for root, _, files in os.walk(os.path.join(PROJECT_ROOT, folder)):
            if "__pycache__" in root:
                continue
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as handle:
                    tree = ast.parse(handle.read(), filename=path)
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    called = getattr(node.func, "attr", None) \
                        or getattr(node.func, "id", None)
                    if called in ("add_quest", "offer_quest"):
                        callers.append((os.path.relpath(path, PROJECT_ROOT),
                                        called, node.lineno))
    assert callers == [], "a dormant side quest route woke up: %s" % callers


def test_paths_only_one_place_decides_whether_a_sitting_may_start():
    """
    `refusal()` is the single gate. `is_startable()` is defined as its
    absence, and the reader defers to it rather than re-deciding — so
    there is no second opinion anywhere for the lockout to have missed.
    """
    body = inspect.getsource(side_quest_list.is_startable)
    assert "refusal(ctx, quest_id) is None" in body
    assert "side_quest_list.refusal" in inspect.getsource(
        lecture_reader.blocker)


def test_paths_the_pc_is_the_only_menu_that_starts_a_quest():
    """
    The PC is reached by a menu id, not a hardcoded prop, so "every
    path" has to include the registry. Exactly one id routes to the
    list, and no level file wires a second screen to it.
    """
    from content.level_registry import MENU_REGISTRY
    routes = [menu_id for menu_id, entry in MENU_REGISTRY.items()
              if entry.get("state") == "SIDE_QUESTS"]
    assert routes == ["side_quests"]


# ── through the real PC screen ─────────────────────────────────

__ctx = None


def screen_ctx(semester: int = 1, days: int = 80):
    """
    A real AppContext, restored into a hand-made run.

    One AppContext is built for the whole file and re-restored per case,
    the way tests/test_side_quest_list.py and tests/test_lecture_reader.py
    both do it: building one opens an audio device and loads every font.
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
    __ctx.screen_mgr.transition_to(ScreenState.SIDE_QUESTS)
    day_warning.forget()
    lecture_reader.end()
    side_quest_list.reset()
    return __ctx


def at_the_pc(semester: int = 1, days: int = 80):
    """A real context standing at the PC, with the term's quest taken."""
    from engine.states import side_quests
    ctx = screen_ctx(semester, days)
    ctx.quest_states.accept(quest_of(semester))
    side_quests.enter(ctx)
    return ctx


def press(ctx, code) -> None:
    """One KEYDOWN through the real PC screen, then its update frame."""
    from engine.states import side_quests
    side_quests.handle_events(
        ctx, [pygame.event.Event(pygame.KEYDOWN, key=code)])
    side_quests.update(ctx, 0.016)


def landed_on(ctx):
    """The state the router would move to next."""
    ctx.screen_mgr.apply_pending_transition()
    return ctx.screen_mgr.get_current_state()


def test_screen_start_is_refused_with_the_reason_on_screen():
    """
    ACCEPTANCE, through the screen the player actually uses: no
    confirmation opens, the notice says why, and nothing has moved.
    """
    ctx = at_the_pc(1, days=1)
    before = (ctx.quest_states.get_all_states(),
              ctx.semester().get_time_pool_days())
    press(ctx, pygame.K_RETURN)
    assert not ctx.popup.is_open(), "a confirmation opened on a block"
    assert ctx.message_popup.is_open(), "the block did not say why"
    assert ctx.message_popup.get_title() == LOCKOUT_TITLE
    assert not lecture_reader.is_open()
    assert side_quest_list.get_last_confirmed() is None
    assert (ctx.quest_states.get_all_states(),
            ctx.semester().get_time_pool_days()) == before
    assert landed_on(ctx) is ScreenState.SIDE_QUESTS, \
        "a refusal leaves the player on the card"


def test_screen_start_is_drawn_muted():
    """START is already muted before it is pressed, so the notice
    confirms what the button was saying rather than surprising."""
    from engine.states import side_quests
    ctx = at_the_pc(1, days=1)
    rows = side_quest_list.entries(ctx)
    assert rows, "nothing on the card to mute"
    assert not side_quest_list.is_startable(ctx, rows[0]["quest_id"])
    side_quests.render(ctx, pygame.display.get_surface())


def test_screen_a_confirmation_taken_over_the_threshold_is_refused():
    """
    The term cannot drain while a modal is up, but an answer that lands
    on a rule that no longer allows it must refuse rather than be
    honoured. Forced here by hand.
    """
    from engine.states import side_quests
    ctx = at_the_pc(1, days=80)
    side_quests.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_RETURN)])
    assert ctx.popup.is_open(), "no question was asked"
    ctx.semester().deduct_time(80 - limit_of(ctx))
    ctx.popup.set_result(RESULT_CONFIRM)
    side_quests.update(ctx, 0.016)
    assert not lecture_reader.is_open(), "opened a reader nobody may open"
    assert ctx.message_popup.get_title() == LOCKOUT_TITLE
    assert side_quest_list.get_last_confirmed() is None
    assert landed_on(ctx) is ScreenState.SIDE_QUESTS


def test_screen_above_the_threshold_it_still_starts():
    """The other half of the acceptance, through the same screen: a
    healthy term still opens the reader exactly as Phase 15 left it."""
    from engine.states import side_quests
    ctx = at_the_pc(1, days=80)
    press(ctx, pygame.K_RETURN)
    assert ctx.popup.is_open(), "the question was not asked"
    # Answered the way the router's modal layer would, then given the
    # update frame that acts on it — SPACE here would be a second START
    # press rather than an answer.
    ctx.popup.set_result(RESULT_CONFIRM)
    side_quests.update(ctx, 0.016)
    assert lecture_reader.is_open(), "the reader did not open"
    assert landed_on(ctx) is ScreenState.SIDE_QUEST_LECTURE
    lecture_reader.end()


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
        day_warning.forget()
        side_quest_list.reset()
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

    # -- the rule, day by day, across the boundary ---------------
    print("\n-- the last days of a term, with one topic unlocked --")
    ruler = unlocked(1)
    limit = limit_of(ruler)
    print("%-6s %-10s %s" % ("DAYS", "LOCKED?", "START?"))
    for days in (limit + 3, limit + 2, limit + 1, limit, limit - 1, 0):
        ctx = unlocked(1, days=days)
        why = side_quest_list.refusal(ctx, quest_of(1))
        print("%-6d %-10s %s"
              % (days, "yes" if side_quest_list.is_locked_out(ctx) else "no",
                 "yes" if why is None else "no  (%s)" % why[0]))
    print("threshold      : %d  (GameClock.get_min_border)" % limit)
    print("the offer      : still put, still acceptable  (Decision D1 a)")
    print("unlocked quests: untouched, and startable again next term")
    return 0


if __name__ == "__main__":
    sys.exit(main())

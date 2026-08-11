"""
tests/test_ending_gate.py
CSE Life: Compile & Conquer
Phase 16 — coverage for the highly-skilled ending gate

    python -m tests.test_ending_gate

Headless and self-contained: SDL_VIDEODRIVER=dummy, no window anybody
can see, and the only thing written to disk is a throwaway temporary
directory — the real saves/ folder is never touched, exactly the rule
engine/save_manager.py's own stub test follows.

WHAT IS ACTUALLY DRIVEN. The wiring half runs against a REAL
AppContext, the REAL GameSession/Player/SkillTree, the REAL
EndgameEvaluationManager and the real engine/states/endgame.py, because
the claim under test is "the ending the game shows changes with the
quest states", and a mock ending would prove nothing.

    ACCEPTANCE: 12 Completed -> highly skilled     test_acceptance_*
    11 Completed + 1 Missed  -> not                test_acceptance_*
    11 Completed + 1 Declined -> not               test_acceptance_*
    the ending decision, all four                  test_title_*
    no alternative route to the outcome            test_no_alternative_*
    the integration point is really wired          test_wiring_*
    the verdict survives a save/load               test_round_trip_*
    the state machine was not modified             test_untouched_*
    the debug command                              test_debug_*
"""
from __future__ import annotations

import inspect
import os
import shutil
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame                                          # noqa: E402

from content.epilogue_text import EPILOGUE_TEXT        # noqa: E402
from content.side_quest_definitions import (           # noqa: E402
    QUEST_COUNT,
    QUEST_IDS,
    SEMESTER_MAX,
    SEMESTER_MIN,
    get_npc_id,
    get_semester,
    get_skill_id,
)
from engine import ending_gate, save_bridge            # noqa: E402
from engine.app_context import AppContext              # noqa: E402
from engine.endgame_manager import EndgameEvaluationManager  # noqa: E402
from engine.quest_state import (                       # noqa: E402
    LEGAL_TRANSITIONS,
    QUEST_STATES,
    STATE_COMPLETED,
    STATE_DECLINED,
    STATE_MISSED,
    STATE_UNLOCKED,
    STATE_UNOFFERED,
    QuestStateMachine,
    from_state,
)
from engine.save_manager import SaveManager, build_state    # noqa: E402
from engine.screen_manager import ScreenState          # noqa: E402
from engine.states import endgame                      # noqa: E402
from ui.endgame_screen import THEMES                   # noqa: E402

SEMESTERS = tuple(range(SEMESTER_MIN, SEMESTER_MAX + 1))

TITLE_TOP = "TOP GRADUATE"
TITLE_AVERAGE = "AVERAGE GRADUATE"
TITLE_STRONG = "DROP OUT Strong Skills"
TITLE_WEAK = "DROP OUT Weak Skills"


# ── helpers ────────────────────────────────────────────────────

def machine(completed=(), declined=(), missed=(), unlocked=()):
    """
    A machine driven into a shape through the PUBLIC API only.

    No reaching into the private dict, so no test can set up a state the
    game itself could not reach — the rule tests/test_quest_state.py's
    machine_in() already set.
    """
    built = QuestStateMachine()
    for semester in completed:
        quest_id = built.get_quest_for_semester(semester)
        built.accept(quest_id)
        built.mark_completed(quest_id)
    for semester in unlocked:
        built.accept(built.get_quest_for_semester(semester))
    for semester in declined:
        built.decline(built.get_quest_for_semester(semester))
    for semester in missed:
        built.expire_unoffered_for_semester(semester)
    return built


def all_but(semester: int):
    """Every semester except one."""
    return tuple(s for s in SEMESTERS if s != semester)


class _Ctx:
    """The smallest thing ending_gate reads: something with a machine."""

    def __init__(self, quest_states=None) -> None:
        self.quest_states = quest_states


class _Player:
    """A stand-in Player for the two getters the manager actually uses.

    Deliberately NOT a real Player for the pure-decision cases: those
    assert what the manager does with a credit total and a boolean, and
    a real Player would drag a GameSession in for no extra coverage.
    The wiring cases below use the real one.
    """

    def __init__(self, credits: int, skills=None) -> None:
        self.__credits = credits
        self.__skills = skills

    def get_accumulated_credits(self) -> int:
        return self.__credits

    def get_wallet_balance(self) -> float:
        return 0.0

    def get_skill_tree(self):
        return self.__skills


class _MaxedTree:
    """A skill tree with every skill far above every retired threshold.

    The point of this class: under the OLD rule this player was highly
    skilled. Under the gate they are not, unless the quests say so.
    """

    def get_skill_level(self, skill_id: str) -> int:
        return 999


__ctx = None


def context() -> AppContext:
    """
    One real AppContext for the whole run, reset per case.

    Building it opens an audio device and loads every font; doing that
    per case is slow for no extra coverage. restore() rebuilds the
    session, the clock, the catalog and ctx.quest_states from a save
    payload, which is exactly the reset each case wants — the pattern
    tests/test_quest_offer.py already uses.
    """
    global __ctx
    if __ctx is None:
        pygame.init()
        __ctx = AppContext()
    save_bridge.restore(__ctx, build_state())
    __ctx.endgame_result = None
    return __ctx


def ending_for(states, credits: int) -> str:
    """
    Drive the REAL engine/states/endgame.py::enter() and read the title
    it put on the context. This is the integration point, end to end:
    ctx.quest_states -> ending_gate -> EndgameEvaluationManager.
    """
    ctx = context()
    ctx.quest_states = states
    ctx.player().add_credits(credits)
    endgame.enter(ctx)
    return str(ctx.endgame_result["epilogue_title"])


# ── ACCEPTANCE: the brief's three scenarios ────────────────────

def test_acceptance_twelve_completed_is_highly_skilled() -> None:
    """Forcing all twelve Completed yields highly skilled."""
    states = machine(completed=SEMESTERS)
    assert len(states.get_completed_quests()) == QUEST_COUNT
    assert ending_gate.is_highly_skilled(states) is True
    assert ending_gate.is_highly_skilled(_Ctx(states)) is True
    assert ending_gate.completed_count(states) == QUEST_COUNT


def test_acceptance_eleven_completed_one_missed_is_not() -> None:
    """Eleven Completed and one Missed does not, whichever one it is."""
    for left_out in SEMESTERS:
        states = machine(completed=all_but(left_out), missed=(left_out,))
        quest_id = states.get_quest_for_semester(left_out)
        assert states.get_state(quest_id) == STATE_MISSED
        assert len(states.get_completed_quests()) == QUEST_COUNT - 1
        assert ending_gate.is_highly_skilled(states) is False, left_out
        assert ending_gate.is_highly_skilled(_Ctx(states)) is False, left_out


def test_acceptance_eleven_completed_one_declined_is_not() -> None:
    """Eleven Completed and one Declined does not, whichever one it is."""
    for left_out in SEMESTERS:
        states = machine(completed=all_but(left_out), declined=(left_out,))
        quest_id = states.get_quest_for_semester(left_out)
        assert states.get_state(quest_id) == STATE_DECLINED
        assert len(states.get_completed_quests()) == QUEST_COUNT - 1
        assert ending_gate.is_highly_skilled(states) is False, left_out
        assert ending_gate.is_highly_skilled(_Ctx(states)) is False, left_out


def test_acceptance_the_other_two_ways_to_fall_short() -> None:
    """Unlocked and Unoffered are not Completed either — eleven is
    eleven however the twelfth got left behind."""
    for left_out in SEMESTERS:
        for states in (machine(completed=all_but(left_out),
                               unlocked=(left_out,)),
                       machine(completed=all_but(left_out))):
            assert ending_gate.is_highly_skilled(states) is False, left_out
    assert ending_gate.is_highly_skilled(QuestStateMachine()) is False


def test_acceptance_no_partial_tier_exists() -> None:
    """Zero through eleven are all the same answer: no. There is no
    count between them that behaves differently."""
    for done in range(0, QUEST_COUNT):
        states = machine(completed=SEMESTERS[:done])
        assert ending_gate.completed_count(states) == done
        assert ending_gate.is_highly_skilled(states) is False, done
    assert ending_gate.is_highly_skilled(machine(completed=SEMESTERS)) is True


# ── the ending decision ────────────────────────────────────────

def test_title_for_is_the_whole_two_by_two() -> None:
    """The four endings, from the two axes and nothing else."""
    manager = EndgameEvaluationManager()
    assert manager.title_for(True, True) == TITLE_TOP
    assert manager.title_for(True, False) == TITLE_AVERAGE
    assert manager.title_for(False, True) == TITLE_STRONG
    assert manager.title_for(False, False) == TITLE_WEAK


def test_title_every_ending_is_a_real_theme_and_epilogue() -> None:
    """Every title the decision can produce is a key in both
    ui/endgame_screen.py::THEMES and content/epilogue_text.py, so no
    reachable ending renders on the fallback theme."""
    manager = EndgameEvaluationManager()
    for graduated in (True, False):
        for skilled in (True, False):
            title = manager.title_for(graduated, skilled)
            assert title in THEMES, title
            assert title in EPILOGUE_TEXT, title
            assert manager.get_epilogue_lines(title) == \
                list(EPILOGUE_TEXT[title])


def test_title_determine_reads_the_credit_threshold() -> None:
    """The academic axis is unchanged: 140 credits, >= not >."""
    manager = EndgameEvaluationManager()
    goal = manager.GRADUATION_CREDIT_THRESHOLD
    assert manager.determine_ending_title(_Player(goal), True) == TITLE_TOP
    assert manager.determine_ending_title(_Player(goal - 1), True) \
        == TITLE_STRONG
    assert manager.determine_ending_title(_Player(goal), False) \
        == TITLE_AVERAGE
    assert manager.determine_ending_title(_Player(goal - 1), False) \
        == TITLE_WEAK


def test_title_evaluate_returns_the_render_contract() -> None:
    """evaluate() still returns exactly the four keys
    ui/endgame_screen.py::render() takes as keyword arguments."""
    manager = EndgameEvaluationManager()
    result = manager.evaluate(_Player(140), True)
    assert set(result) == {"epilogue_title", "epilogue_lines",
                           "final_credits", "final_wallet"}
    assert result["epilogue_title"] == TITLE_TOP
    assert result["epilogue_lines"] == list(EPILOGUE_TEXT[TITLE_TOP])
    assert result["final_credits"] == 140
    assert manager.evaluate(_Player(140), False)["epilogue_title"] \
        == TITLE_AVERAGE


def test_title_the_verdict_has_no_default() -> None:
    """Omitting the verdict raises rather than guessing one.

    This is the structural guarantee that there is no second rule
    hiding behind a default value — a caller that forgets fails at the
    call site instead of shipping a silently wrong ending.
    """
    manager = EndgameEvaluationManager()
    for call in (lambda: manager.determine_ending_title(_Player(140)),
                 lambda: manager.evaluate(_Player(140))):
        try:
            call()
        except TypeError:
            continue
        raise AssertionError("the verdict was defaulted, not required")


# ── no alternative route to the outcome ────────────────────────

def test_no_alternative_route_through_the_skill_tree() -> None:
    """
    A player with every tracked skill at 999 — far past both retired
    thresholds — is NOT highly skilled on eleven quests.

    Under the old rule this player got TOP GRADUATE. This is the whole
    point of the phase.
    """
    manager = EndgameEvaluationManager()
    player = _Player(140, _MaxedTree())
    assert manager.calculate_average_skill_level(_MaxedTree()) == 999.0
    assert manager.calculate_average_skill_level(_MaxedTree()) > \
        manager.TOP_GRADUATE_SKILL_THRESHOLD
    for left_out in SEMESTERS:
        states = machine(completed=all_but(left_out), missed=(left_out,))
        verdict = ending_gate.is_highly_skilled(states)
        assert verdict is False
        assert manager.determine_ending_title(player, verdict) == TITLE_AVERAGE
        assert manager.determine_ending_title(_Player(0, _MaxedTree()),
                                              verdict) == TITLE_WEAK


def test_no_alternative_route_an_empty_skill_tree_still_qualifies() -> None:
    """And the reverse: twelve Completed is highly skilled even with an
    empty skill tree. The average is not consulted in either direction."""
    manager = EndgameEvaluationManager()
    verdict = ending_gate.is_highly_skilled(machine(completed=SEMESTERS))
    assert verdict is True
    assert manager.calculate_average_skill_level(None) == 0.0
    assert manager.determine_ending_title(_Player(140, None), verdict) \
        == TITLE_TOP
    assert manager.determine_ending_title(_Player(0, None), verdict) \
        == TITLE_STRONG


def test_no_alternative_route_the_decision_never_reads_the_average() -> None:
    """
    Structural, on the manager's own source: neither the average nor
    either retired threshold appears in the body of the two functions
    that decide an ending.

    A comment saying "retired" is not proof; this is.
    """
    for function in (EndgameEvaluationManager.determine_ending_title,
                     EndgameEvaluationManager.title_for):
        body = inspect.getsource(function)
        body = body.split('"""')[-1]              # drop the docstring
        for banned in ("calculate_average_skill_level",
                       "TOP_GRADUATE_SKILL_THRESHOLD",
                       "STRONG_SKILLS_DROPOUT_THRESHOLD"):
            assert banned not in body, "%s reads %s" % (function, banned)


def test_no_alternative_route_endgame_state_supplies_the_gate() -> None:
    """Structural, on the state module: the one caller of evaluate()
    fills the verdict from ending_gate and from nothing else."""
    source = inspect.getsource(endgame)
    assert "ending_gate.is_highly_skilled(ctx)" in source
    assert source.count("manager.evaluate(") == 1


# ── the integration point, end to end ──────────────────────────

def test_wiring_twelve_completed_reaches_the_ending_screen() -> None:
    """Through the REAL endgame state, a real AppContext and a real
    Player: twelve Completed produces the highly-skilled ending on both
    sides of the academic axis."""
    assert ending_for(machine(completed=SEMESTERS), 140) == TITLE_TOP
    assert ending_for(machine(completed=SEMESTERS), 0) == TITLE_STRONG


def test_wiring_eleven_completed_does_not() -> None:
    """The same run one quest short, both ways of being short."""
    short = all_but(SEMESTER_MAX)
    for states in (machine(completed=short, missed=(SEMESTER_MAX,)),
                   machine(completed=short, declined=(SEMESTER_MAX,))):
        assert ending_for(states, 140) == TITLE_AVERAGE
        assert ending_for(states, 0) == TITLE_WEAK


def test_wiring_a_fresh_run_is_not_highly_skilled() -> None:
    """A context straight out of restore(): twelve Unoffered, no gate."""
    ctx = context()
    assert ending_gate.completed_count(ctx) == 0
    assert ending_gate.is_highly_skilled(ctx) is False
    endgame.enter(ctx)
    assert ctx.endgame_result["epilogue_title"] == TITLE_WEAK


def test_wiring_the_certificate_reads_the_same_title() -> None:
    """engine/states/certificate.py takes its title off the same
    ctx.endgame_result, so the two final screens cannot disagree."""
    from engine.states import certificate
    ctx = context()
    ctx.quest_states = machine(completed=SEMESTERS)
    ctx.player().add_credits(140)
    endgame.enter(ctx)
    assert ctx.endgame_result["epilogue_title"] == TITLE_TOP
    assert 'result.get("epilogue_title"' in inspect.getsource(certificate)
    certificate.enter(ctx)                    # the real screen, no crash


def test_wiring_the_result_is_computed_once() -> None:
    """enter() is a no-op once ctx.endgame_result is set — the screen is
    re-entered by the router, and a second evaluation on a frozen
    session would be wasted work at best."""
    ctx = context()
    ctx.quest_states = machine(completed=SEMESTERS)
    ctx.player().add_credits(140)
    endgame.enter(ctx)
    first = ctx.endgame_result
    ctx.quest_states = QuestStateMachine()
    endgame.enter(ctx)
    assert ctx.endgame_result is first


def test_wiring_the_session_is_frozen_by_entering() -> None:
    """enter() goes through GameSession.trigger_endgame_evaluation(),
    which freezes the session — unchanged by this phase, asserted so a
    refactor of the seam cannot quietly drop it."""
    ctx = context()
    assert not ctx.session.get_is_frozen()
    endgame.enter(ctx)
    assert ctx.session.get_is_frozen()


def test_wiring_endgame_still_turns_the_page() -> None:
    """The screen's own behaviour is untouched: any key goes to the
    certificate."""
    ctx = context()
    endgame.enter(ctx)
    endgame.handle_events(
        ctx, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)])
    assert ctx.screen_mgr.apply_pending_transition()
    assert ctx.screen_mgr.get_current_state() == ScreenState.CERTIFICATE


# ── the verdict survives a save ────────────────────────────────

def test_round_trip_twelve_completed_through_a_real_save_file() -> None:
    """
    Twelve Completed, written to a real file through SaveManager and
    read back: still highly skilled.

    The gate has no state of its own — it reads the quest machine — so
    what is really asserted here is that the machine's own persistence
    carries the ending. Written into tempfile.mkdtemp(); saves/ is never
    touched.
    """
    folder = tempfile.mkdtemp(prefix="cse_ending_gate_")
    try:
        saves = SaveManager(folder)
        payload = build_state(
            quest_states=machine(completed=SEMESTERS).to_dict())
        assert saves.save(1, payload), saves.get_last_error()
        loaded = saves.load(1)
        assert loaded is not None
        rebuilt = from_state(loaded["quests"]["states"])
        assert ending_gate.is_highly_skilled(rebuilt) is True
        assert ending_gate.completed_count(rebuilt) == QUEST_COUNT
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_round_trip_eleven_completed_stays_short() -> None:
    """And a run one quest short reloads one quest short."""
    folder = tempfile.mkdtemp(prefix="cse_ending_gate_")
    try:
        saves = SaveManager(folder)
        for left_out in SEMESTERS:
            states = machine(completed=all_but(left_out), missed=(left_out,))
            assert saves.save(1, build_state(quest_states=states.to_dict()))
            rebuilt = from_state(saves.load(1)["quests"]["states"])
            assert ending_gate.is_highly_skilled(rebuilt) is False, left_out
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_round_trip_a_pre_quest_save_is_not_highly_skilled() -> None:
    """A save written before the quest system carries no quest block at
    all. It loads as twelve Unoffered — not as a free good ending."""
    payload = build_state()
    payload.pop("quests", None)
    rebuilt = from_state((payload.get("quests") or {}).get("states"))
    assert ending_gate.is_highly_skilled(rebuilt) is False
    ctx = context()
    save_bridge.restore(ctx, payload)
    assert ending_gate.is_highly_skilled(ctx) is False


def test_round_trip_a_hand_edited_save_cannot_forge_the_ending() -> None:
    """An invented state name falls back to Unoffered rather than
    counting as Completed, so a bad twelfth entry cannot open the gate."""
    states = machine(completed=all_but(SEMESTER_MAX)).to_dict()
    last = QUEST_IDS[-1]
    for forged in ("COMPLETED!", "complete", "finished", "", None, 12):
        states[last] = forged
        rebuilt = from_state(states)
        assert rebuilt.get_state(last) == STATE_UNOFFERED, forged
        assert ending_gate.is_highly_skilled(rebuilt) is False, forged


# ── tolerance ──────────────────────────────────────────────────

def test_tolerance_no_machine_is_false_never_an_exception() -> None:
    """Every shape of "there is no quest machine" answers no. False is
    the safe default: the ending it withholds is the good one, and a
    crash on the last screen of the game would lose the run."""
    for source in (None, object(), _Ctx(None), _Ctx("twelve"), _Ctx({}),
                   "", 0, [], {}):
        assert ending_gate.is_highly_skilled(source) is False, source
        assert ending_gate.completed_count(source) == 0, source
        assert ending_gate.machine_of(source) is None, source


def test_tolerance_machine_of_accepts_both_shapes() -> None:
    """A bare machine and a context carrying one both resolve."""
    built = machine(completed=(1,))
    assert ending_gate.machine_of(built) is built
    assert ending_gate.machine_of(_Ctx(built)) is built


def test_tolerance_rows_are_twelve_even_with_no_machine() -> None:
    """The report never shows a short table — a missing machine reads as
    twelve Unoffered, and the count line says which."""
    rows = ending_gate.quest_rows(object())
    assert len(rows) == QUEST_COUNT
    assert all(row["state"] == STATE_UNOFFERED for row in rows)
    assert all(not row["completed"] for row in rows)


# ── the state machine was not modified ─────────────────────────

def test_untouched_five_states_and_four_transitions() -> None:
    """Phase 16 reads the machine and never writes to it."""
    assert set(QUEST_STATES) == {STATE_UNOFFERED, STATE_DECLINED,
                                 STATE_MISSED, STATE_UNLOCKED,
                                 STATE_COMPLETED}
    assert LEGAL_TRANSITIONS == frozenset((
        (STATE_UNOFFERED, STATE_DECLINED),
        (STATE_UNOFFERED, STATE_MISSED),
        (STATE_UNOFFERED, STATE_UNLOCKED),
        (STATE_UNLOCKED, STATE_COMPLETED),
    ))


def test_untouched_the_gate_writes_nothing() -> None:
    """Reading the verdict, the count, the rows and the whole report
    leaves all twelve states exactly where they were."""
    states = machine(completed=(1, 2, 3), unlocked=(4,), declined=(5,),
                     missed=(6,))
    before = states.get_all_states()
    ending_gate.is_highly_skilled(states)
    ending_gate.completed_count(states)
    ending_gate.quest_rows(states)
    ending_gate.report_lines(states)
    assert states.get_all_states() == before


def test_untouched_no_mutator_appears_in_the_module() -> None:
    """Structural: engine/ending_gate.py contains no call to any of the
    four transitions outside its own debug block, which builds throwaway
    machines to demonstrate the scenarios."""
    source = inspect.getsource(ending_gate)
    body = source.split('if __name__ == "__main__":')[0]
    for mutator in ("accept(", "decline(", "mark_completed(",
                    "expire_unoffered_for_semester("):
        assert mutator not in body, mutator


# ── the debug command ──────────────────────────────────────────

def test_debug_report_lists_all_twelve_with_their_states() -> None:
    """Every quest id, its semester, its NPC, its skill and its state
    are on the report, and the data comes from the definitions table
    rather than being written out here."""
    states = machine(completed=(1, 2, 3), unlocked=(4,), declined=(5,),
                     missed=(6,))
    rows = ending_gate.quest_rows(states)
    assert [row["quest_id"] for row in rows] == list(QUEST_IDS)
    assert [row["semester"] for row in rows] == list(SEMESTERS)
    for row in rows:
        quest_id = row["quest_id"]
        assert row["npc_id"] == get_npc_id(quest_id)
        assert row["skill_id"] == get_skill_id(quest_id)
        assert row["semester"] == get_semester(quest_id)
        assert row["state"] == states.get_state(quest_id)
        assert row["completed"] is (row["state"] == STATE_COMPLETED)

    text = "\n".join(ending_gate.report_lines(states))
    for quest_id in QUEST_IDS:
        assert quest_id in text, quest_id
    for state in (STATE_COMPLETED, STATE_UNLOCKED, STATE_DECLINED,
                  STATE_MISSED, STATE_UNOFFERED):
        assert state in text, state


def test_debug_report_states_the_verdict_and_the_endings() -> None:
    """The verdict line, the count, and the ending each side of the
    academic axis — the three things the brief asks it to show."""
    text = "\n".join(ending_gate.report_lines(machine(completed=SEMESTERS)))
    assert "HIGHLY SKILLED         : YES" in text
    assert "completed              : 12/12" in text
    assert TITLE_TOP in text and TITLE_STRONG in text

    text = "\n".join(ending_gate.report_lines(machine(completed=(1,))))
    assert "HIGHLY SKILLED         : NO" in text
    assert "completed              : 1/12" in text
    assert TITLE_AVERAGE in text and TITLE_WEAK in text


def test_debug_report_titles_come_from_the_manager() -> None:
    """The report does not write the four ending strings out a fifth
    time — it asks the manager, so it cannot drift from the game."""
    manager = EndgameEvaluationManager()
    for states, skilled in ((machine(completed=SEMESTERS), True),
                            (QuestStateMachine(), False)):
        text = "\n".join(ending_gate.report_lines(states))
        assert manager.title_for(True, skilled) in text
        assert manager.title_for(False, skilled) in text

    # Structural: none of the four titles is a literal anywhere below
    # the module docstring, where the 2x2 is drawn for the reader.
    body = inspect.getsource(ending_gate).split('"""', 2)[-1]
    for title in (TITLE_TOP, TITLE_AVERAGE, TITLE_STRONG, TITLE_WEAK):
        assert title not in body, title


def test_debug_report_takes_a_live_context() -> None:
    """The same report off a real AppContext, which is what makes it
    usable on a running game rather than only on a fabricated machine."""
    ctx = context()
    ctx.quest_states = machine(completed=SEMESTERS)
    text = "\n".join(ending_gate.report_lines(ctx, "LIVE"))
    assert text.startswith("LIVE\n----")
    assert "HIGHLY SKILLED         : YES" in text


def test_debug_command_runs_clean_and_exits_zero() -> None:
    """`py -3 -m engine.ending_gate` — run for real, in a subprocess, so
    the acceptance scenarios it drives are actually executed."""
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    finished = subprocess.run(
        [sys.executable, "-m", "engine.ending_gate"],
        cwd=root, capture_output=True, text=True)
    assert finished.returncode == 0, finished.stderr
    assert "all scenarios correct" in finished.stdout
    assert "HIGHLY SKILLED         : YES" in finished.stdout
    assert "HIGHLY SKILLED         : NO" in finished.stdout
    for quest_id in QUEST_IDS:
        assert quest_id in finished.stdout, quest_id


def test_debug_output_is_plain_ascii() -> None:
    """A Windows console is cp1252 by default and a stray em dash there
    is a UnicodeEncodeError, not a cosmetic problem."""
    for states in (machine(completed=SEMESTERS), QuestStateMachine()):
        for line in ending_gate.report_lines(states, "TITLE"):
            line.encode("ascii")


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

    print("\n-- the gate, at twelve and at eleven --")
    ending_gate.print_report(machine(completed=SEMESTERS))
    print("")
    ending_gate.print_report(
        machine(completed=all_but(SEMESTER_MAX), missed=(SEMESTER_MAX,)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
tests/test_exam_session.py
CSE Life: Compile & Conquer — phase F9

Guards engine/exam_session.py — the exam state machine.

An exam decides whether a course is passed and how many of the
player's 80 days it burns, so the cases that matter are the ones that
cost them something: a timeout that must score wrong, a clock that
must never run negative or tick while paused, and an answer dict whose
shape must match what MainQuest.attempt_qa_optimization() expects
byte-for-byte.

The suite also pins the opt-in skill rule: with USE_SKILL_IN_PASS_RULE
False (the shipped default) it is provably inert, and with skill_tree
None it stays inert even when the flag is on.

Most tests run against a synthetic Course with a known answer key, so
a catalog edit can never quietly change what they assert. Two tests
run against the real 65-course catalog to prove the wiring is real.
"""

from __future__ import annotations

import pytest

from academic.course import Course
from academic.course_catalog import build_course_catalog
from academic.quest import MainQuest
from core.skill_tree import SkillTree
from engine import exam_session as exam_module
from engine.exam_session import (QUESTION_TIME_LIMIT_SECONDS,
                                 QUESTION_TIME_WARNING_SECONDS,
                                 SKILL_PASS_MIN_AVERAGE_LEVEL,
                                 TIME_COST_OPTIMIZED_DAYS,
                                 TIME_COST_UNOPTIMIZED_DAYS, TIERS,
                                 TIMEOUT_ANSWER, TRACKED_SKILL_IDS,
                                 USE_SKILL_IN_PASS_RULE, ExamResult,
                                 ExamSession, evaluate_pass,
                                 get_average_skill_level)

# The synthetic course's answer key — easy A, medium B, hard C.
KEY = {"easy": "A", "medium": "B", "hard": "C"}


@pytest.fixture
def course():
    """A 3-credit course with a complete, known 3-tier question set."""
    built = Course("CSE9999", "Test Course", 3)
    for tier, correct in KEY.items():
        built.add_question(tier, f"The {tier} question?",
                           ["first", "second", "third", "fourth"], correct)
    return built


@pytest.fixture
def partial_course():
    """A course missing its hard question — check_answers() can never pass."""
    built = Course("CSE9998", "Half Loaded", 3)
    built.add_question("easy", "The easy question?",
                       ["first", "second"], "A")
    return built


def _answer_all(session, answers):
    """Submit one letter per tier, in order."""
    for tier in TIERS:
        session.submit_answer(answers[tier])


# ─────────────────────────────────────────────────────────────
# CONSTANTS AND THE TIER CONTRACT
# ─────────────────────────────────────────────────────────────


def test_tiers_match_course_difficulties():
    """
    TIERS must equal Course.VALID_DIFFICULTIES exactly.

    A divergence would mis-key every dict handed to check_answers(), so
    every answer would silently score wrong.
    """
    assert TIERS == Course.VALID_DIFFICULTIES


def test_time_limit_constants():
    """The countdown resolves to the safer end of the brief's 10-15 s."""
    assert QUESTION_TIME_LIMIT_SECONDS == 15.0
    assert QUESTION_TIME_WARNING_SECONDS == 5.0


def test_time_costs_mirror_main_quest():
    """10 days optimized / 14 otherwise, matching MainQuest."""
    assert TIME_COST_OPTIMIZED_DAYS == 10
    assert TIME_COST_UNOPTIMIZED_DAYS == 14


# ─────────────────────────────────────────────────────────────
# THE HAPPY PATH — ALL CORRECT
# ─────────────────────────────────────────────────────────────


def test_all_correct_is_optimized_and_passes(course):
    """All three right ⇒ optimized ⇒ pass ⇒ 10 days ⇒ credits awarded."""
    session = ExamSession(course)
    session.start()
    _answer_all(session, KEY)

    assert session.is_finished() is True
    result = session.get_result()
    assert result.is_optimized() is True
    assert result.is_passed() is True
    assert result.get_time_cost_days() == 10
    assert result.get_credits_awarded() == 3
    assert result.get_per_tier_outcome() == {"easy": True, "medium": True,
                                             "hard": True}
    assert result.get_timeouts() == []


def test_answers_shape_matches_main_quest(course):
    """
    get_answers() is exactly the dict MainQuest.attempt_qa_optimization()
    expects — this is the whole hand-off, so it is asserted end to end
    against a real MainQuest rather than just by shape.
    """
    session = ExamSession(course)
    session.start()
    _answer_all(session, KEY)

    answers = session.get_answers()
    assert answers == KEY
    assert set(answers.keys()) == set(TIERS)

    quest = MainQuest("quest_1", course)
    assert quest.attempt_qa_optimization(answers) is True
    assert quest.get_is_optimized() is True
    assert quest.evaluate_exam_result() is True
    # The session's day figure must agree with what GameClock will charge.
    assert quest.get_time_cost() == session.get_result().get_time_cost_days()


# ─────────────────────────────────────────────────────────────
# THE FAILING PATH
# ─────────────────────────────────────────────────────────────


def test_any_wrong_answer_fails(course):
    """One wrong answer ⇒ not optimized ⇒ fail ⇒ 14 days ⇒ no credits."""
    session = ExamSession(course)
    session.start()
    _answer_all(session, {"easy": "A", "medium": "D", "hard": "C"})

    result = session.get_result()
    assert result.is_optimized() is False
    assert result.is_passed() is False
    assert result.get_time_cost_days() == 14
    assert result.get_credits_awarded() == 0


def test_per_tier_outcome_isolates_the_wrong_tier(course):
    """
    The result card needs to say WHICH tier went wrong.

    Course never exposes its answer key and check_answers() is
    all-or-nothing, so this is the test that the indirect grading in
    __grade_per_tier() actually works.
    """
    session = ExamSession(course)
    session.start()
    _answer_all(session, {"easy": "A", "medium": "D", "hard": "C"})

    assert session.get_result().get_per_tier_outcome() == {
        "easy": True, "medium": False, "hard": True}


def test_failing_main_quest_agrees_with_session(course):
    """A failed session and a real MainQuest charge the same 14 days."""
    session = ExamSession(course)
    session.start()
    _answer_all(session, {"easy": "B", "medium": "B", "hard": "C"})

    quest = MainQuest("quest_2", course)
    quest.attempt_qa_optimization(session.get_answers())
    assert quest.evaluate_exam_result() is False
    assert quest.get_time_cost() == 14
    assert session.get_result().get_time_cost_days() == 14


# ─────────────────────────────────────────────────────────────
# THE COUNTDOWN
# ─────────────────────────────────────────────────────────────


def test_timer_starts_full(course):
    """A started exam has the whole limit on the clock."""
    session = ExamSession(course)
    session.start()
    assert session.get_time_remaining() == QUESTION_TIME_LIMIT_SECONDS
    assert session.get_time_ratio() == 1.0


def test_tick_decrements_the_clock(course):
    """A tick spends exactly its dt."""
    session = ExamSession(course)
    session.start()
    session.tick(4.0)
    assert session.get_time_remaining() == pytest.approx(11.0)
    assert session.get_time_ratio() == pytest.approx(11.0 / 15.0)


def test_timer_never_goes_negative(course):
    """
    The clock is never negative, however far a tick overshoots.

    Note the shape of this: overshooting mid-exam does NOT leave the
    clock at zero, because the timeout advances to the next tier and
    that tier starts a fresh clock. The invariant under test is only
    that the value is never below zero — asserted after every tick.
    """
    session = ExamSession(course)
    session.start()
    for _ in range(6):
        session.tick(999.0)
        assert session.get_time_remaining() >= 0.0
        assert 0.0 <= session.get_time_ratio() <= 1.0


def test_timer_clamps_to_zero_on_the_final_tier(course):
    """Once the exam ends there is no clock left to run."""
    session = ExamSession(course)
    session.start()
    for _ in TIERS:
        session.tick(QUESTION_TIME_LIMIT_SECONDS + 5.0)

    assert session.is_finished() is True
    assert session.get_time_remaining() == 0.0
    assert session.get_time_ratio() == 0.0


def test_finished_exam_ignores_further_ticks(course):
    """Ticking a finished exam changes nothing."""
    session = ExamSession(course)
    session.start()
    _answer_all(session, KEY)
    assert session.tick(10.0) is False
    assert session.get_time_remaining() == 0.0


def test_timeout_auto_submits_wrong_and_advances(course):
    """
    A timeout records the sentinel answer and moves to the next tier —
    the brief's rule, and what stops a silent player stalling the exam.
    """
    session = ExamSession(course)
    session.start()
    assert session.get_current_tier() == "easy"

    timed_out = session.tick(QUESTION_TIME_LIMIT_SECONDS + 1.0)
    assert timed_out is True
    assert session.get_answers()["easy"] == TIMEOUT_ANSWER
    assert session.get_current_tier() == "medium"
    # The next tier gets a fresh clock.
    assert session.get_time_remaining() == QUESTION_TIME_LIMIT_SECONDS


def test_all_timeouts_finish_the_exam_as_a_fail(course):
    """A player who never answers still reaches a (failed) result."""
    session = ExamSession(course)
    session.start()
    for _ in TIERS:
        session.tick(QUESTION_TIME_LIMIT_SECONDS + 0.1)

    assert session.is_finished() is True
    result = session.get_result()
    assert result.get_timeouts() == list(TIERS)
    assert result.is_passed() is False
    assert result.get_time_cost_days() == 14
    assert result.get_per_tier_outcome() == {"easy": False, "medium": False,
                                             "hard": False}


def test_timeout_answer_can_never_be_a_real_option(course):
    """The sentinel is not a letter any question offers, so it scores wrong."""
    session = ExamSession(course)
    session.start()
    assert TIMEOUT_ANSWER not in session.get_current_option_letters()
    assert course.check_answers({tier: TIMEOUT_ANSWER
                                 for tier in TIERS}) is False


def test_pause_freezes_the_clock(course):
    """pause() stops the countdown; resume() starts it again."""
    session = ExamSession(course)
    session.start()
    session.tick(3.0)
    frozen_at = session.get_time_remaining()

    assert session.pause() is True
    session.tick(5.0)
    assert session.get_time_remaining() == frozen_at
    assert session.is_paused() is True

    assert session.resume() is True
    session.tick(2.0)
    assert session.get_time_remaining() == pytest.approx(frozen_at - 2.0)


def test_tick_before_start_does_nothing(course):
    """The clock does not run before start()."""
    session = ExamSession(course)
    session.tick(5.0)
    assert session.get_time_remaining() == QUESTION_TIME_LIMIT_SECONDS


def test_warning_window(course):
    """is_in_warning() turns on inside the last 5 seconds."""
    session = ExamSession(course)
    session.start()
    session.tick(9.0)                       # 6.0 left
    assert session.is_in_warning() is False
    session.tick(2.0)                       # 4.0 left
    assert session.is_in_warning() is True


# ─────────────────────────────────────────────────────────────
# INPUT SAFETY — NEVER RAISE, NEVER CORRUPT (§0.8)
# ─────────────────────────────────────────────────────────────


def test_invalid_letter_never_burns_a_tier(course):
    """An unoffered letter is refused and the tier stays live."""
    session = ExamSession(course)
    session.start()
    assert session.submit_answer("Z") is False
    assert session.get_current_tier() == "easy"
    assert session.get_answers() == {}


def test_submit_before_start_is_refused(course):
    """Nothing can be answered before start()."""
    session = ExamSession(course)
    assert session.submit_answer("A") is False
    assert session.get_answers() == {}


def test_submit_after_finish_is_refused(course):
    """A finished exam accepts no more answers."""
    session = ExamSession(course)
    session.start()
    _answer_all(session, KEY)
    assert session.submit_answer("A") is False
    assert session.get_answers() == KEY


def test_double_start_does_not_reset_progress(course):
    """A second start() is refused, so a screen transition cannot wipe answers."""
    session = ExamSession(course)
    assert session.start() is True
    session.submit_answer("A")
    assert session.start() is False
    assert session.get_answers() == {"easy": "A"}


def test_answers_and_result_are_defensive_copies(course):
    """Mutating a returned dict cannot corrupt the session or the result."""
    session = ExamSession(course)
    session.start()
    _answer_all(session, KEY)

    session.get_answers()["easy"] = "ZZZ"
    assert session.get_answers()["easy"] == "A"

    result = session.get_result()
    result.get_per_tier_outcome()["easy"] = False
    assert result.get_per_tier_outcome()["easy"] is True


def test_lowercase_answer_is_accepted(course):
    """A lower-case letter is normalised rather than refused."""
    session = ExamSession(course)
    session.start()
    assert session.submit_answer("a") is True
    assert session.get_answers()["easy"] == "A"


# ─────────────────────────────────────────────────────────────
# QUESTION DELEGATION — COURSE OWNS THE DATA
# ─────────────────────────────────────────────────────────────


def test_question_comes_from_the_course_and_hides_the_answer(course):
    """
    get_current_question() delegates to Course and never leaks the key.

    This is the guarantee that lets ui/exam_screen.py be trusted not to
    grade: there is simply no answer in what it receives.
    """
    session = ExamSession(course)
    session.start()
    question = session.get_current_question()
    assert question["question_text"] == "The easy question?"
    assert set(question["options"]) == {"A", "B", "C", "D"}
    assert "correct_option" not in question


def test_question_is_none_when_finished(course):
    """There is no live question once the exam is over."""
    session = ExamSession(course)
    session.start()
    _answer_all(session, KEY)
    assert session.get_current_question() is None
    assert session.get_current_tier() is None


def test_tier_index_advances(course):
    """The index walks 0, 1, 2 and lands on 3 when finished."""
    session = ExamSession(course)
    session.start()
    assert session.get_tier_index() == 0
    session.submit_answer("A")
    assert session.get_tier_index() == 1
    session.submit_answer("B")
    assert session.get_tier_index() == 2
    session.submit_answer("C")
    assert session.get_tier_index() == 3


# ─────────────────────────────────────────────────────────────
# DEGRADING SAFELY ON A HALF-LOADED COURSE
# ─────────────────────────────────────────────────────────────


def test_incomplete_question_set_degrades_to_a_fail(partial_course):
    """
    A course missing a tier cannot be passed, mirroring
    Course.check_answers() returning False for the same reason — and it
    must not raise on the way there.
    """
    assert partial_course.is_question_set_complete() is False
    session = ExamSession(partial_course)
    session.start()
    session.submit_answer("A")              # the one real question
    # The two missing tiers have no options, so they can only time out.
    session.tick(QUESTION_TIME_LIMIT_SECONDS + 0.1)
    session.tick(QUESTION_TIME_LIMIT_SECONDS + 0.1)

    assert session.is_finished() is True
    result = session.get_result()
    assert result.is_optimized() is False
    assert result.is_passed() is False
    assert result.get_credits_awarded() == 0
    assert all(value is False
               for value in result.get_per_tier_outcome().values())


def test_missing_question_yields_no_options(partial_course):
    """A tier with no question offers no letters instead of raising."""
    session = ExamSession(partial_course)
    session.start()
    session.submit_answer("A")
    assert session.get_current_question() is None
    assert session.get_current_option_letters() == []


# ─────────────────────────────────────────────────────────────
# THE PASS RULE AND ITS OPT-IN SKILL FLAG
# ─────────────────────────────────────────────────────────────


def test_flag_ships_off():
    """Owner ruling: Q&A-only for now (IMPLEMENTATION_PLAN §3)."""
    assert USE_SKILL_IN_PASS_RULE is False


def test_evaluate_pass_is_qa_only_while_the_flag_is_off():
    """With the flag off, the skill tree is ignored entirely."""
    empty = SkillTree()
    stocked = SkillTree()
    for skill_id in TRACKED_SKILL_IDS:
        stocked.increment_skill(skill_id, 10)

    assert evaluate_pass(True, None) is True
    assert evaluate_pass(True, empty) is True       # would fail if enabled
    assert evaluate_pass(True, stocked) is True
    assert evaluate_pass(False, stocked) is False


def test_evaluate_pass_changes_behaviour_when_enabled(monkeypatch):
    """
    Flipping the one switch adds the skill component (plan Phase B4).

    A low-skill player who aced the Q&A now fails; a stocked one passes.
    """
    monkeypatch.setattr(exam_module, "USE_SKILL_IN_PASS_RULE", True)

    empty = SkillTree()
    assert exam_module.evaluate_pass(True, empty) is False

    stocked = SkillTree()
    for skill_id in TRACKED_SKILL_IDS:
        stocked.increment_skill(skill_id, int(SKILL_PASS_MIN_AVERAGE_LEVEL) + 1)
    assert exam_module.evaluate_pass(True, stocked) is True


def test_enabled_flag_never_rescues_a_failed_qa(monkeypatch):
    """The skill component can only ever make the exam harder."""
    monkeypatch.setattr(exam_module, "USE_SKILL_IN_PASS_RULE", True)
    stocked = SkillTree()
    for skill_id in TRACKED_SKILL_IDS:
        stocked.increment_skill(skill_id, 20)
    assert exam_module.evaluate_pass(False, stocked) is False


def test_none_skill_tree_is_inert_even_when_enabled(monkeypatch):
    """skill_tree=None always degrades to the plain Q&A result."""
    monkeypatch.setattr(exam_module, "USE_SKILL_IN_PASS_RULE", True)
    assert exam_module.evaluate_pass(True, None) is True
    assert exam_module.evaluate_pass(False, None) is False


def test_session_honours_the_flag(monkeypatch, course):
    """The flag reaches a real session, not just the bare function."""
    monkeypatch.setattr(exam_module, "USE_SKILL_IN_PASS_RULE", True)
    session = ExamSession(course, skill_tree=SkillTree())
    session.start()
    _answer_all(session, KEY)

    result = session.get_result()
    assert result.is_optimized() is True     # the Q&A was perfect
    assert result.is_passed() is False       # but the skills were not there


def test_average_skill_level():
    """The average is taken over all 12 canonical ids, unseen ones as 0."""
    assert len(TRACKED_SKILL_IDS) == 12
    tree = SkillTree()
    assert get_average_skill_level(tree) == 0.0
    for skill_id in TRACKED_SKILL_IDS:
        tree.increment_skill(skill_id, 6)
    assert get_average_skill_level(tree) == pytest.approx(6.0)
    assert get_average_skill_level(None) == 0.0


def test_evaluate_pass_never_mutates_the_tree(monkeypatch):
    """The pass rule only ever READS the skill tree."""
    monkeypatch.setattr(exam_module, "USE_SKILL_IN_PASS_RULE", True)
    tree = SkillTree()
    for skill_id in TRACKED_SKILL_IDS:
        tree.increment_skill(skill_id, 4)
    before = {sid: tree.get_skill_level(sid) for sid in TRACKED_SKILL_IDS}
    exam_module.evaluate_pass(True, tree)
    after = {sid: tree.get_skill_level(sid) for sid in TRACKED_SKILL_IDS}
    assert before == after


# ─────────────────────────────────────────────────────────────
# THE SESSION MUTATES NOTHING
# ─────────────────────────────────────────────────────────────


def test_session_does_not_mutate_the_course(course):
    """
    An exam attempt leaves the Course's lifecycle flags untouched.

    Marking a course completed or backlogged is MainQuest's job, run
    through GameClock — never the session's.
    """
    session = ExamSession(course)
    session.start()
    _answer_all(session, KEY)

    assert course.is_completed() is False
    assert course.is_backlogged() is False


# ─────────────────────────────────────────────────────────────
# AGAINST THE REAL CATALOG
# ─────────────────────────────────────────────────────────────


def test_runs_against_a_real_catalog_course():
    """A real, fully-loaded catalog course plays through to a result."""
    real = build_course_catalog()[0]
    assert real.is_question_set_complete() is True

    session = ExamSession(real)
    session.start()
    for _ in TIERS:
        letters = session.get_current_option_letters()
        assert len(letters) == 4
        session.submit_answer(letters[0])

    result = session.get_result()
    assert isinstance(result, ExamResult)
    assert result.get_course_code() == real.get_course_code()
    assert result.get_time_cost_days() in (10, 14)


def test_every_catalog_course_can_start_an_exam():
    """All 65 courses expose a complete, answerable question set."""
    catalog = build_course_catalog()
    assert len(catalog) == 65
    for real in catalog:
        session = ExamSession(real)
        session.start()
        assert session.get_current_question() is not None
        assert len(session.get_current_option_letters()) >= 2

"""
engine/exam_session.py
CSE Life: Compile & Conquer — phase F9  (Feature 8, the exam state machine)
─────────────────────────────────────────────────────────────
OOP Pillars: Encapsulation + Separation of Concerns

The exam is three MCQs — easy, medium, hard — each under a
countdown. This module runs that ladder: which tier is live, how
long is left, what the player picked, what a timeout does, and
what the whole attempt was worth.

It owns NO question data. `academic/course.py` is the single source
of both the questions and the answer key, so `get_current_question()`
delegates to `course.get_question(tier)` (which never exposes the
answer) and grading delegates to `course.check_answers()`. Nothing
is duplicated here.

It also mutates NOTHING. No `Player`, no `Course`, no
`AcademicHistory` is written to. The session's whole output is
`get_answers()` — shaped exactly `{"easy": "A", "medium": "C",
"hard": "B"}` — which the lead feeds to
`MainQuest.attempt_qa_optimization()` and then runs through
`GameClock.process_time_consumable()`. The hand-off is spelled out
in PHASELOG_F9 §9.

Pure Python, no pygame (Build Plan §0.7): the exam rules must be
unit-testable headlessly, and ui/exam_screen.py draws whatever this
hands it.

THE COUNTDOWN IS A NEW MECHANIC. It appears in no diagram and in no
existing rule; the owner confirmed it is required. The brief's
10-15 s range is resolved to 15 s, the safer end, retunable on one
line. Flagged in PHASELOG_F9 §8.
─────────────────────────────────────────────────────────────
Created by Nangiba Tasnim (Dev 3), branch nangiba-temp-01.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from academic.course import Course
    from core.skill_tree import SkillTree

# ─────────────────────────────────────────────────────────────
# TUNING
# ─────────────────────────────────────────────────────────────
# The per-question countdown. The brief allows 10-15 s; 15 is the
# safer end for a player reading a 147-character question, and both
# numbers are one-line retunable.
QUESTION_TIME_LIMIT_SECONDS: float = 15.0
QUESTION_TIME_WARNING_SECONDS: float = 5.0

# The three tiers, in the order they are asked. Matches
# academic/course.py::Course.VALID_DIFFICULTIES exactly — a divergence
# would silently mis-key every answer dict handed to check_answers().
TIERS = ("easy", "medium", "hard")

# What a timed-out tier records. It can never equal a real option
# letter (Course letters options A, B, C, D...), so check_answers()
# scores it wrong without needing a special case anywhere.
TIMEOUT_ANSWER: str = "-"

# Exam time costs, from IMPLEMENTATION_PLAN §3 and mirrored from
# academic/quest.py::MainQuest — 10 days optimized, 14 otherwise.
TIME_COST_OPTIMIZED_DAYS: int = 10
TIME_COST_UNOPTIMIZED_DAYS: int = 14

# ─────────────────────────────────────────────────────────────
# THE PASS RULE — ONE SWITCH, ONE FUNCTION
# ─────────────────────────────────────────────────────────────
# Owner ruling: Q&A-only for now (IMPLEMENTATION_PLAN §3 rules Q&A-only
# through Phase A5 and defers the SkillTree component to B4), but the
# skill path is built as an opt-in that can be switched on later
# without touching a call site.
USE_SKILL_IN_PASS_RULE: bool = False
SKILL_PASS_MIN_AVERAGE_LEVEL: float = 3.0

# The 12 canonical skill IDs the optional skill component averages over
# (Build Plan §1.4). Imported from the manager that owns them so there
# is one list, not two. NOTE the deliberate, owner-ruled divergence:
# content/level_registry.py::SKILL_IDS is a DIFFERENT, shorter 9-entry
# authoring list used by level gates. Both stay as they are; the lead
# reconciles at integration.
try:                                    # pragma: no cover - trivial guard
    from engine.endgame_manager import EndgameEvaluationManager
    TRACKED_SKILL_IDS = tuple(EndgameEvaluationManager.TRACKED_SKILL_IDS)
except (ImportError, AttributeError):   # pragma: no cover
    TRACKED_SKILL_IDS = ()


def evaluate_pass(qa_all_correct: bool, skill_tree: "SkillTree" = None) -> bool:
    """
    THE single place the exam pass rule lives.

    Q&A-only while USE_SKILL_IN_PASS_RULE is False — matching
    MainQuest.evaluate_exam_result() and IMPLEMENTATION_PLAN §3.
    Flip the flag to add the SkillTree component (plan Phase B4).

    When enabled, passing requires the Q&A pass AND an average level of
    at least SKILL_PASS_MIN_AVERAGE_LEVEL across the 12 canonical skill
    IDs — the skill component can only ever make the exam HARDER, never
    rescue a failed Q&A.

    `skill_tree=None` always degrades to the plain Q&A result, so a
    caller without a skill tree behaves identically whatever the flag
    says. This function only ever READS the tree — never call a
    SkillTree mutator from here.
    """
    if not USE_SKILL_IN_PASS_RULE:
        return bool(qa_all_correct)
    if skill_tree is None:
        return bool(qa_all_correct)
    if not qa_all_correct:
        return False
    return get_average_skill_level(skill_tree) >= SKILL_PASS_MIN_AVERAGE_LEVEL


def get_average_skill_level(skill_tree: "SkillTree") -> float:
    """
    Mean level across the 12 canonical skill IDs, 0.0 when unreadable.

    Read-only. An id the tree has never seen reads as level 0, which is
    what SkillTree.get_skill_level() already returns, so an untouched
    tree averages to 0.0 rather than raising.
    """
    if skill_tree is None or not TRACKED_SKILL_IDS:
        return 0.0
    try:
        total = sum(int(skill_tree.get_skill_level(skill_id))
                    for skill_id in TRACKED_SKILL_IDS)
    except (AttributeError, TypeError, ValueError):
        return 0.0
    return total / float(len(TRACKED_SKILL_IDS))


# ─────────────────────────────────────────────────────────────
# THE RESULT
# ─────────────────────────────────────────────────────────────


class ExamResult:
    """
    What one finished exam attempt was worth.

    An immutable snapshot built by ExamSession when the third tier is
    answered. It reports; it changes nothing. Awarding the credits and
    charging the days is the lead's job, through MainQuest and GameClock.
    """

    def __init__(self, course_code: str, course_name: str,
                 answers: Dict[str, str], is_optimized: bool,
                 is_passed: bool, per_tier: Dict[str, bool],
                 timeouts: List[str], credit_value: int) -> None:
        """Store one decided attempt. Nothing here recomputes or grades."""
        self.__course_code: str = str(course_code)
        self.__course_name: str = str(course_name)
        self.__answers: Dict[str, str] = dict(answers)
        self.__is_optimized: bool = bool(is_optimized)
        self.__is_passed: bool = bool(is_passed)
        self.__per_tier: Dict[str, bool] = dict(per_tier)
        self.__timeouts: List[str] = list(timeouts)
        self.__credit_value: int = int(credit_value)

    def get_course_code(self) -> str:
        """The course this attempt was for."""
        return self.__course_code

    def get_course_name(self) -> str:
        """The course's display name."""
        return self.__course_name

    def is_optimized(self) -> bool:
        """True when all three answers were correct (Q&A optimization)."""
        return self.__is_optimized

    def is_passed(self) -> bool:
        """True when the attempt passed, via evaluate_pass()."""
        return self.__is_passed

    def get_time_cost_days(self) -> int:
        """
        Days this attempt costs: 10 optimized, 14 otherwise.

        Mirrors MainQuest.get_time_cost() so the number the result card
        shows is the number GameClock will actually charge.
        """
        return (TIME_COST_OPTIMIZED_DAYS if self.__is_optimized
                else TIME_COST_UNOPTIMIZED_DAYS)

    def get_credits_awarded(self) -> int:
        """The course's credit value on a pass, 0 on a fail."""
        return self.__credit_value if self.__is_passed else 0

    def get_per_tier_outcome(self) -> Dict[str, bool]:
        """Per-tier correctness, e.g. {"easy": True, "medium": False, ...}."""
        return dict(self.__per_tier)

    def get_timeouts(self) -> List[str]:
        """The tiers whose countdown ran out, in order."""
        return list(self.__timeouts)

    def get_answers(self) -> Dict[str, str]:
        """The submitted answers — the dict MainQuest expects."""
        return dict(self.__answers)


# ─────────────────────────────────────────────────────────────
# THE SESSION
# ─────────────────────────────────────────────────────────────


class ExamSession:
    """
    The three-tier exam state machine with a per-question countdown.

    Lifecycle: build it, `start()`, then each frame `tick(dt)` and, when
    the player picks, `submit_answer(letter)`. Both advance the tier; a
    timeout auto-submits TIMEOUT_ANSWER, which scores wrong. After the
    third tier `is_finished()` is True and `get_result()` returns an
    ExamResult.

    Owns only its OWN state — the tier index, the clock, the answers.
    Question data belongs to Course and is fetched, never copied.
    """

    def __init__(self, course: "Course",
                 skill_tree: "SkillTree" = None) -> None:
        """Bind an exam to a course, optionally with a skill tree to read."""
        self.__course: "Course" = course
        self.__skill_tree: Optional["SkillTree"] = skill_tree
        self.__tier_index: int = 0
        self.__answers: Dict[str, str] = {}
        self.__timeouts: List[str] = []
        self.__remaining: float = QUESTION_TIME_LIMIT_SECONDS
        self.__started: bool = False
        self.__paused: bool = False
        self.__finished: bool = False
        self.__result: Optional[ExamResult] = None

    # ── lifecycle ─────────────────────────────────────────────

    def start(self) -> bool:
        """
        Begin the exam at the easy tier with a full clock.

        Returns False if it has already started, so a double-start from a
        screen transition cannot silently reset a player's progress.
        """
        if self.__started:
            return False
        self.__started = True
        self.__tier_index = 0
        self.__answers = {}
        self.__timeouts = []
        self.__remaining = QUESTION_TIME_LIMIT_SECONDS
        self.__finished = False
        self.__result = None
        return True

    def is_started(self) -> bool:
        """True once start() has been called."""
        return self.__started

    def is_finished(self) -> bool:
        """True once all three tiers have an answer."""
        return self.__finished

    # ── the current question ──────────────────────────────────

    def get_tier_index(self) -> int:
        """0, 1 or 2 while running; 3 once finished."""
        return self.__tier_index

    def get_current_tier(self) -> Optional[str]:
        """The live tier name, or None when the exam is over."""
        if self.__finished or self.__tier_index >= len(TIERS):
            return None
        return TIERS[self.__tier_index]

    def get_current_question(self) -> Optional[Dict[str, object]]:
        """
        The live question, straight from the Course.

        Delegates to course.get_question(tier), which returns
        {"question_text": str, "options": {"A": str, ...}} and NEVER the
        correct option. The session stores no copy: Course owns the
        question bank, and duplicating it here is how the two drift apart.
        Returns None when the exam is over or the tier has no question.
        """
        tier = self.get_current_tier()
        if tier is None:
            return None
        try:
            return self.__course.get_question(tier)
        except (AttributeError, TypeError):
            return None

    # ── the countdown ─────────────────────────────────────────

    def tick(self, dt_seconds: float) -> bool:
        """
        Advance the countdown by `dt_seconds`.

        Returns True if this tick timed the question out. A timeout
        auto-submits TIMEOUT_ANSWER and advances the tier — the brief's
        rule — so a player who never answers still reaches a result.
        The clock never runs while paused, before start(), or after the
        exam is finished, and never goes negative.
        """
        if (not self.__started or self.__finished or self.__paused
                or dt_seconds <= 0):
            return False
        self.__remaining -= float(dt_seconds)
        if self.__remaining > 0.0:
            return False
        self.__remaining = 0.0
        tier = self.get_current_tier()
        if tier is not None:
            self.__timeouts.append(tier)
            self.__record(tier, TIMEOUT_ANSWER)
        return True

    def get_time_remaining(self) -> float:
        """Seconds left on the live question, never below 0."""
        return max(0.0, self.__remaining)

    def get_time_ratio(self) -> float:
        """Fraction of the question's time left, 0.0-1.0 — the bar fill."""
        if QUESTION_TIME_LIMIT_SECONDS <= 0:
            return 0.0
        return max(0.0, min(1.0,
                            self.__remaining / QUESTION_TIME_LIMIT_SECONDS))

    def is_in_warning(self) -> bool:
        """True inside the last QUESTION_TIME_WARNING_SECONDS — drives the blink."""
        return (self.__started and not self.__finished
                and self.get_time_remaining() <= QUESTION_TIME_WARNING_SECONDS)

    def pause(self) -> bool:
        """Freeze the countdown (a popup opened). False if already paused."""
        if self.__paused or not self.__started or self.__finished:
            return False
        self.__paused = True
        return True

    def resume(self) -> bool:
        """Unfreeze the countdown. False if it was not paused."""
        if not self.__paused:
            return False
        self.__paused = False
        return True

    def is_paused(self) -> bool:
        """True while the countdown is frozen."""
        return self.__paused

    # ── answering ─────────────────────────────────────────────

    def submit_answer(self, letter: str) -> bool:
        """
        Record the player's pick for the live tier and advance.

        Returns False — changing nothing — for a submission before
        start(), after the exam ended, or for a letter that is not one of
        the live question's options. An invalid key press must never
        burn a tier (Build Plan §0.8: never raise, never corrupt).
        """
        if not self.__started or self.__finished:
            return False
        tier = self.get_current_tier()
        if tier is None:
            return False
        choice = str(letter).strip().upper()
        if choice not in self.get_current_option_letters():
            return False
        self.__record(tier, choice)
        return True

    def get_current_option_letters(self) -> List[str]:
        """The letters the live question actually offers, e.g. [A, B, C, D]."""
        question = self.get_current_question()
        if not question:
            return []
        options = question.get("options") or {}
        return [str(key).upper() for key in options.keys()]

    def get_answers(self) -> Dict[str, str]:
        """
        The answers so far, shaped exactly as MainQuest expects:
        `{"easy": "A", "medium": "C", "hard": "B"}`.

        This dict IS the session's product. The lead passes it straight to
        MainQuest.attempt_qa_optimization(), then runs the quest through
        GameClock.process_time_consumable(). A timed-out tier carries
        TIMEOUT_ANSWER, which check_answers() scores wrong.
        """
        return dict(self.__answers)

    def get_result(self) -> Optional[ExamResult]:
        """The finished attempt's ExamResult, or None while still running."""
        return self.__result

    # ── private ───────────────────────────────────────────────

    def __record(self, tier: str, answer: str) -> None:
        """Store one tier's answer, advance, and finish after the third."""
        self.__answers[tier] = answer
        self.__tier_index += 1
        if self.__tier_index >= len(TIERS):
            self.__finish()
        else:
            self.__remaining = QUESTION_TIME_LIMIT_SECONDS

    def __finish(self) -> None:
        """Grade the attempt and build the immutable ExamResult."""
        self.__finished = True
        self.__paused = False
        self.__remaining = 0.0

        # Course is the ONE validator (academic/course.py). An incomplete
        # question set makes this False, exactly as check_answers()
        # documents, so a half-loaded course degrades to a fail instead
        # of crashing.
        try:
            optimized = bool(self.__course.check_answers(self.__answers))
        except (AttributeError, TypeError):
            optimized = False

        passed = evaluate_pass(optimized, self.__skill_tree)

        try:
            credit_value = int(self.__course.get_credit_value())
            code = str(self.__course.get_course_code())
            name = str(self.__course.get_course_name())
        except (AttributeError, TypeError, ValueError):
            credit_value, code, name = 0, "", ""

        self.__result = ExamResult(
            course_code=code, course_name=name, answers=self.__answers,
            is_optimized=optimized, is_passed=passed,
            per_tier=self.__grade_per_tier(optimized), timeouts=self.__timeouts,
            credit_value=credit_value)

    def __grade_per_tier(self, optimized: bool) -> Dict[str, bool]:
        """
        Work out which individual tiers were right, for the result card.

        WHY THIS IS INDIRECT. Course deliberately never exposes a correct
        option (get_question() and get_all_questions() both strip it), and
        check_answers() is all-or-nothing — so "which one did I get
        wrong?" cannot be asked directly. Rather than duplicating the
        answer key into this module (which would put it one attribute away
        from the UI and break Course's single-source rule), the key is
        RE-DERIVED at grading time through the public validator: try each
        combination of the offered letters until check_answers() accepts
        one. That is at most 4x4x4 = 64 dict comparisons, once, on a
        screen the player has already left.

        The derived key is a LOCAL: it is never stored on the session or
        the result, and no getter can reach it. All that survives is three
        booleans. A timed-out tier is known wrong without any of this.

        If no combination validates — an incomplete or unanswerable
        question set — every tier that is not a timeout is reported False,
        matching check_answers() returning False for the same reason.
        """
        if optimized:
            return {tier: True for tier in TIERS}

        key = self.__derive_answer_key()
        outcome: Dict[str, bool] = {}
        for tier in TIERS:
            given = self.__answers.get(tier, TIMEOUT_ANSWER)
            if given == TIMEOUT_ANSWER or key is None:
                outcome[tier] = False
            else:
                outcome[tier] = (given == key.get(tier))
        return outcome

    def __derive_answer_key(self) -> Optional[Dict[str, str]]:
        """
        Recover the correct letters using only course.check_answers().

        Returns None when no combination validates. See __grade_per_tier
        for why this exists and why the result is never retained.
        """
        letters: Dict[str, List[str]] = {}
        for tier in TIERS:
            try:
                question = self.__course.get_question(tier)
            except (AttributeError, TypeError):
                return None
            if not question:
                return None
            letters[tier] = [str(k).upper()
                             for k in (question.get("options") or {})]
            if not letters[tier]:
                return None

        for easy in letters["easy"]:
            for medium in letters["medium"]:
                for hard in letters["hard"]:
                    probe = {"easy": easy, "medium": medium, "hard": hard}
                    try:
                        if self.__course.check_answers(probe):
                            return probe
                    except (AttributeError, TypeError):
                        return None
        return None


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to exercise the machine.
# Abu Huraira removes this block when he plugs in the real game.
#   (no window: pure logic, so the stub plays two headless exams --
#    one answered perfectly, one left to time out -- and prints what
#    each attempt was worth)
# -------------------------------------------------------------
if __name__ == "__main__":
    from academic.course_catalog import build_course_catalog

    catalog = build_course_catalog()
    course = catalog[0]

    print(f"=== {course.get_course_code()} - {course.get_course_name()} ===")
    print(f"question set complete: {course.is_question_set_complete()}")
    print(f"time limit: {QUESTION_TIME_LIMIT_SECONDS:.0f}s per question, "
          f"warning at {QUESTION_TIME_WARNING_SECONDS:.0f}s")
    print(f"skill rule enabled: {USE_SKILL_IN_PASS_RULE}")

    # --- attempt 1: answer every tier correctly ------------------
    # To play a PERFECT run the stub has to know the right letters. It
    # finds them the same way the grader does -- through the public
    # validator, never by reading a private field.
    def _correct_letters(target) -> dict:
        """Recover the answer key using only the public check_answers()."""
        options = {tier: list(target.get_question(tier)["options"])
                   for tier in TIERS}
        for easy in options["easy"]:
            for medium in options["medium"]:
                for hard in options["hard"]:
                    probe = {"easy": easy, "medium": medium, "hard": hard}
                    if target.check_answers(probe):
                        return probe
        return {}

    print("\n--- attempt 1: perfect run ---")
    key = _correct_letters(course)
    session = ExamSession(course)
    session.start()
    while not session.is_finished():
        tier = session.get_current_tier()
        question = session.get_current_question()
        print(f"  [{tier}] {question['question_text'][:60]}...")
        session.submit_answer(key[tier])
    perfect = session.get_result()
    print(f"  answers:   {session.get_answers()}")
    print(f"  optimized: {perfect.is_optimized()}  "
          f"passed: {perfect.is_passed()}")
    print(f"  time cost: {perfect.get_time_cost_days()} days   "
          f"credits: +{perfect.get_credits_awarded()}")
    print(f"  per tier:  {perfect.get_per_tier_outcome()}")

    # --- attempt 2: let every question time out ------------------
    print("\n--- attempt 2: never answers ---")
    timeout_session = ExamSession(course)
    timeout_session.start()
    while not timeout_session.is_finished():
        timeout_session.tick(QUESTION_TIME_LIMIT_SECONDS + 0.1)
    result = timeout_session.get_result()
    print(f"  answers:   {timeout_session.get_answers()}")
    print(f"  timeouts:  {result.get_timeouts()}")
    print(f"  optimized: {result.is_optimized()}  passed: {result.is_passed()}")
    print(f"  time cost: {result.get_time_cost_days()} days   "
          f"credits: +{result.get_credits_awarded()}")
    print(f"  per tier:  {result.get_per_tier_outcome()}")

"""
course.py

CSE Life: Compile & Conquer
Academic Package — Course Entity
─────────────────────────────────────────────────────────────
Encapsulates all metadata for a single university course: its identity,
credit value, prerequisite chain, category tag, and the 3-question
(Easy/Medium/Hard) MCQ ladder used by the exam simulation to determine:

    1. Pass/Fail status of the course
    2. The time-cost optimization of the linked MainQuest's exam action

EXAM FORMAT (confirmed): Each course has exactly 3 MCQ questions
(easy/medium/hard), each with multiple lettered options (A/B/C/D...).
A course is passed only if the player answers ALL 3 correctly.

STATUS: Question/Answer content is intentionally left EMPTY in this
version. All methods needed to store, retrieve, and validate MCQ
questions are implemented and ready — actual question data will be
loaded later via add_question() calls from a separate catalog/content
file (course_catalog.py).

Design notes
────────────
• Course is a PERSISTENT, single-instance entity (per project spec —
  no duplicate Course objects are created for a re-attempted/backlogged
  course; the same instance is simply re-registered into a new semester
  catalog by AcademicHistory).

• Prerequisites are stored as a list of prerequisite *codes* (strings).
  Two kinds of codes are supported:
      - Real course codes    e.g. "CSE1102"
      - Category/tier tags   e.g. "GED_CORE_1", "MANDATORY_CSE"
  Course itself does NOT know *how* a prerequisite is satisfied — only
  *what* is required. That resolution logic belongs to AcademicHistory,
  keeping the two classes cleanly decoupled (Single Responsibility).

• category is a free-text label (e.g. "GED Core 1", "Major Elective",
  "Mandatory for CSE / GED Tier 2"). It does NOT drive any logic by
  itself — it's descriptive metadata for catalog display / grouping.
  Plain major/departmental courses can leave this as None.

• Encapsulation: all state is private (name-mangled) and only exposed
  through validated getters/mutators — no external code can silently
  corrupt a Course's credit value, questions, or lifecycle state.
"""

from typing import Dict, List, Optional


class Course:
    """Represents a single, persistent university course entity."""

    VALID_DIFFICULTIES = ("easy", "medium", "hard")

    def __init__(
        self,
        course_code: str,
        course_name: str,
        credit_value: int,
        prerequisites: Optional[List[str]] = None,
        is_lab_component: bool = False,
        category: Optional[str] = None,
    ) -> None:
        if not course_code or not isinstance(course_code, str):
            raise ValueError("course_code must be a non-empty string")
        if not course_name or not isinstance(course_name, str):
            raise ValueError("course_name must be a non-empty string")
        if not isinstance(credit_value, (int, float)) or credit_value < 0:
            raise ValueError("credit_value must be a non-negative number")

        self.__course_code: str = course_code.strip().upper()
        self.__course_name: str = course_name.strip()
        self.__credit_value: int = int(credit_value)
        self.__prerequisites: List[str] = (
            [p.strip().upper() for p in prerequisites] if prerequisites else []
        )
        self.__is_lab_component: bool = is_lab_component
        self.__category: Optional[str] = category.strip() if category else None

        # 3-question MCQ ladder → {"easy": {...}, "medium": {...}, "hard": {...}}
        # Each entry: {"question_text": str, "options": {"A": str, "B": str, ...},
        #              "correct_option": "A"}
        # Intentionally EMPTY for now — filled later via add_question().
        self.__questions: Dict[str, Dict[str, object]] = {}

        # Persistent lifecycle state (mutated by MainQuest / AcademicHistory)
        self.__is_completed: bool = False
        self.__is_backlogged: bool = False

    # ── Identity & Metadata Getters ─────────────────────────────────
    def get_course_code(self) -> str:
        return self.__course_code

    def get_course_name(self) -> str:
        return self.__course_name

    def get_credit_value(self) -> int:
        return self.__credit_value

    def is_lab_component(self) -> bool:
        return self.__is_lab_component

    def get_category(self) -> Optional[str]:
        return self.__category

    def set_category(self, category: Optional[str]) -> None:
        """Allows the catalog loader to tag/re-tag a course after creation."""
        self.__category = category.strip() if category else None

    def get_prerequisites(self) -> List[str]:
        # Return a defensive copy so callers cannot mutate internal state
        return list(self.__prerequisites)

    def has_prerequisites(self) -> bool:
        return len(self.__prerequisites) > 0

    def add_prerequisite(self, prerequisite_code: str) -> None:
        """
        Register another course/category code as a prerequisite.
        Used by the catalog-loading code when the curriculum tree
        is built. Duplicate codes are ignored.
        """
        if not prerequisite_code:
            return
        code = prerequisite_code.strip().upper()
        if code not in self.__prerequisites:
            self.__prerequisites.append(code)

    # ── MCQ Ladder Management (structure ready, content empty) ──────

    def add_question(
        self,
        difficulty: str,
        question_text: str,
        options: List[str],
        correct_option: str,
    ) -> bool:
        """
        Register one MCQ for this course under a difficulty tier.

        difficulty:      must be one of 'easy', 'medium', 'hard'.
        question_text:   the question prompt shown to the player.
        options:         list of option texts, e.g.
                         ["A stack", "A queue", "A tree", "A graph"]
                         — automatically lettered A, B, C, ... in order.
        correct_option:  the letter of the correct option, e.g. "A".
                         Case-insensitive; must correspond to a real
                         lettered option.

        Returns True on success, False if:
          - difficulty is not a valid tier, or
          - question_text is empty, or
          - fewer than 2 options are given, or
          - correct_option doesn't match any generated letter.

        NOTE: Not called anywhere yet — question content will be
        supplied later via course_catalog.py.
        """
        difficulty = difficulty.strip().lower()
        if difficulty not in self.VALID_DIFFICULTIES:
            return False
        if not question_text:
            return False
        if not options or len(options) < 2:
            return False

        # Letter each option in order: A, B, C, D, ...
        lettered_options: Dict[str, str] = {
            chr(ord("A") + i): opt.strip() for i, opt in enumerate(options)
        }

        correct_option = correct_option.strip().upper()
        if correct_option not in lettered_options:
            return False

        self.__questions[difficulty] = {
            "question_text": question_text.strip(),
            "options": lettered_options,
            "correct_option": correct_option,
        }
        return True

    def is_question_set_complete(self) -> bool:
        """True only when all 3 difficulty tiers have a registered MCQ."""
        return all(tier in self.__questions for tier in self.VALID_DIFFICULTIES)

    def get_question(self, difficulty: str) -> Optional[Dict[str, object]]:
        """
        Returns {'question_text': ..., 'options': {'A': ..., 'B': ...}}
        for one tier — the correct_option is never exposed here.
        """
        difficulty = difficulty.strip().lower()
        data = self.__questions.get(difficulty)
        if not data:
            return None
        return {
            "question_text": data["question_text"],
            "options": dict(data["options"]),
        }

    def get_all_questions(self) -> Dict[str, Dict[str, object]]:
        """Returns question_text + options only, per tier — never the answer."""
        return {
            tier: {
                "question_text": data["question_text"],
                "options": dict(data["options"]),
            }
            for tier, data in self.__questions.items()
        }

    def check_answers(self, submitted_answers: Dict[str, str]) -> bool:
        """
        Validates a full exam attempt against all 3 MCQ tiers.

        submitted_answers: {"easy": "A", "medium": "C", "hard": "B"}
        (the option letter the player picked for each tier)

        Returns True only if:
          - The question set is complete (all 3 tiers registered), AND
          - All 3 submitted option letters match the correct_option
            for their tier (case-insensitive)

        This single boolean result feeds BOTH downstream outcomes:
          - Course Pass/Fail (confirmed rule: all 3 MCQs correct = pass)
          - MainQuest exam time-cost optimization (10 vs 14 days)

        NOTE: Will always return False right now since no questions are
        loaded yet (is_question_set_complete() gates this). That's expected.
        """
        if not self.is_question_set_complete():
            return False
        for tier in self.VALID_DIFFICULTIES:
            expected = self.__questions[tier]["correct_option"]
            given = str(submitted_answers.get(tier, "")).strip().upper()
            if expected != given:
                return False
        return True

    # ── Lifecycle State (mutated externally by MainQuest/AcademicHistory) ──
    def mark_completed(self) -> None:
        self.__is_completed = True
        self.__is_backlogged = False

    def mark_backlogged(self) -> None:
        self.__is_completed = False
        self.__is_backlogged = True

    def is_completed(self) -> bool:
        return self.__is_completed

    def is_backlogged(self) -> bool:
        return self.__is_backlogged

    # ── Dunder helpers ───────────────────────────────────────────────
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Course):
            return NotImplemented
        return self.__course_code == other.get_course_code()

    def __hash__(self) -> int:
        return hash(self.__course_code)

    def __repr__(self) -> str:
        return (
            f"Course({self.__course_code!r}, credits={self.__credit_value}, "
            f"completed={self.__is_completed}, backlogged={self.__is_backlogged})"
        )
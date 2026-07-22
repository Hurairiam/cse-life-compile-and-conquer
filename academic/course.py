"""
course.py
 
CSE Life: Compile & Conquer
Academic Package — Course Entity
─────────────────────────────────────────────────────────────
Encapsulates all metadata for a single university course: its identity,
credit value, prerequisite chain, and the 3-question (Easy/Medium/Hard)
Q&A ladder used by the exam simulation to determine BOTH:
 
    1. Pass/Fail status of the course
    2. The time-cost optimization of the linked MainQuest's exam action
 
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
 
        # 3-question Q&A ladder → {"easy": {...}, "medium": {...}, "hard": {...}}
        self.__questions: Dict[str, Dict[str, str]] = {}
 
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
 
    def get_prerequisites(self) -> List[str]:
        # Return a defensive copy so callers cannot mutate internal state
        return list(self.__prerequisites)
 
    def has_prerequisites(self) -> bool:
        return len(self.__prerequisites) > 0
 
    # ── Q&A Ladder Management ───────────────────────────────────────
    def add_question(self, difficulty: str, question_text: str, correct_answer: str) -> bool:
        """
        Registers one question for this course under a difficulty tier.
        difficulty must be one of: 'easy', 'medium', 'hard'.
        Returns True on success, False if the difficulty label is invalid.
        """
        if not question_text or not correct_answer:
            return False
        difficulty = difficulty.strip().lower()
        if difficulty not in self.VALID_DIFFICULTIES:
            return False
        self.__questions[difficulty] = {
            "question_text": question_text.strip(),
            "correct_answer": correct_answer.strip(),
        }
        return True
 
    def is_question_set_complete(self) -> bool:
        """True only when all 3 difficulty tiers have a registered question."""
        return all(tier in self.__questions for tier in self.VALID_DIFFICULTIES)
 
    def get_question(self, difficulty: str) -> Optional[Dict[str, str]]:
        """Returns {'question_text': ...} for one tier — never the answer."""
        difficulty = difficulty.strip().lower()
        data = self.__questions.get(difficulty)
        return {"question_text": data["question_text"]} if data else None
 
    def get_all_questions(self) -> Dict[str, Dict[str, str]]:
        """Returns question_text only, per tier — correct_answer is never exposed."""
        return {
            tier: {"question_text": data["question_text"]}
            for tier, data in self.__questions.items()
        }
 
    def check_answers(self, submitted_answers: Dict[str, str]) -> bool:
        """
        Validates a full exam attempt against all 3 tiers.
 
        submitted_answers: {"easy": "...", "medium": "...", "hard": "..."}
 
        Returns True only if:
          - The question set is complete (all 3 tiers registered), AND
          - All 3 submitted answers match (case-insensitive, trimmed)
 
        This single boolean result feeds BOTH downstream outcomes:
          - Course Pass/Fail
          - MainQuest exam time-cost optimization (10 vs 14 days)
        """
        if not self.is_question_set_complete():
            return False
        for tier in self.VALID_DIFFICULTIES:
            expected = self.__questions[tier]["correct_answer"].strip().lower()
            given = str(submitted_answers.get(tier, "")).strip().lower()
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
        return f"Course({self.__course_code!r}, credits={self.__credit_value})"
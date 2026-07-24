"""
quest.py

CSE Life: Compile & Conquer
Academic Package — Quest Hierarchy
─────────────────────────────────────────────────────────────
OOP Pillars: Abstraction + Inheritance + Polymorphism
Abstract Quest defines shared quest identity (ID, time cost,
completion state). MainQuest and SideQuest specialise it.
Both implement TimeConsumable so GameClock can process them
through one unified pipeline — this is polymorphism in action.

DESIGN NOTE (important divergence from the original skeleton):
In this version, Course itself owns the 3-question (easy/medium/
hard) Q&A ladder and the check_answers() validation logic — NOT
MainQuest. So MainQuest does NOT keep its own qa_question_pool;
it simply delegates to self.__linked_course.check_answers() during
attempt_qa_optimization(). This avoids duplicating question data
in two places.

EXAM RULE (confirmed for this iteration): a course is passed
if and only if the Q&A optimization succeeds (all 3 answers
correct). There is no separate SkillTree threshold check yet —
evaluate_exam_result() simply returns the optimization result.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

from core.interfaces import TimeConsumable

if TYPE_CHECKING:
    from core.character.player import Player
    from academic.course import Course


# ══════════════════════════════════════════════════════════════════
# ABSTRACT BASE
# ══════════════════════════════════════════════════════════════════

class Quest(ABC):
    """
    Abstract base for all quest types in the game.
    Defines the shared identity contract: every quest has an ID,
    a time cost, and a completion flag.

    Cannot be instantiated directly.
    OOP: Abstraction — shared state without shared behaviour.
    """

    def __init__(self, quest_id: str, time_cost: int) -> None:
        self._quest_id: str = quest_id
        self._time_cost: int = time_cost
        self._is_completed: bool = False

    def get_quest_id(self) -> str:
        """Return the unique quest identifier."""
        return self._quest_id

    def get_time_cost(self) -> int:
        """Return base time cost in days."""
        return self._time_cost

    def get_is_completed(self) -> bool:
        """Return whether this quest has been completed."""
        return self._is_completed

    @abstractmethod
    def execute_action(self, player: Player) -> None:
        """
        Every quest subclass MUST define how it executes.
        This abstract method forces concrete subclasses to provide
        their own implementation — enforcing the TimeConsumable
        contract at the Quest hierarchy level as well.
        [Implemented by MainQuest and SideQuest]
        """
        pass


# ══════════════════════════════════════════════════════════════════
# MAIN QUEST
# ══════════════════════════════════════════════════════════════════

class MainQuest(Quest, TimeConsumable):
    """
    Represents a course examination event.

    Key mechanics:
    - Q&A optimization: answering the linked Course's 3-question
      ladder (easy/medium/hard) correctly sets isOptimized = True,
      reducing the exam's time cost from 14 -> 10 days.
    - Exam result: passing = isOptimized being True (see module
      docstring for the confirmed rule). Failure means the Course
      is marked backlogged via AcademicHistory.

    OOP: Inheritance — extends Quest.
         Polymorphism — implements TimeConsumable.execute_action().
    """

    def __init__(self, quest_id: str, linked_course: Course) -> None:
        super().__init__(quest_id=quest_id, time_cost=14)
        self.__linked_course: Course = linked_course
        self.__is_optimized: bool = False

    def get_linked_course(self) -> Course:
        """Return the Course this exam is testing."""
        return self.__linked_course

    def get_is_optimized(self) -> bool:
        """Return whether Q&A optimization was successful."""
        return self.__is_optimized

    def attempt_qa_optimization(self, submitted_answers: Dict[str, str]) -> bool:
        """
        Run the pre-exam Q&A optimization.

        submitted_answers must be shaped like:
            {"easy": "...", "medium": "...", "hard": "..."}

        Delegates the actual checking to the linked Course's own
        check_answers() — question/answer data lives in ONE place
        only (Course), so this method never duplicates it.

        If all 3 answers are correct: sets isOptimized = True,
        which later reduces execute_action()'s time cost to 10 days.
        If the Course's question set isn't loaded yet, check_answers()
        safely returns False (see course.py), so this degrades
        gracefully rather than crashing.
        """
        self.__is_optimized = self.__linked_course.check_answers(submitted_answers)
        return self.__is_optimized

    def evaluate_exam_result(self) -> bool:
        """
        Determine whether the exam is passed or failed.

        Confirmed rule for this iteration: pass if and only if the
        Q&A optimization succeeded. No separate SkillTree threshold
        is applied here — this is intentionally simple for now and
        can be extended later without changing the public contract.
        """
        return self.__is_optimized

    def execute_action(self, player: Player) -> None:
        """
        Execute the exam attempt:
        1. Deduct 10 days (optimized) or 14 days (unoptimized) from
           the player's time pool. If the player doesn't have enough
           days left, the attempt is aborted with no side effects —
           the GameClock/15-day firewall is expected to prevent this
           situation from happening in the first place.
        2. Evaluate the result via evaluate_exam_result().
        3. On PASS: record completion in AcademicHistory (which also
           syncs the Course's own is_completed flag) and award credits
           to the player.
        4. On FAIL: mark the course incomplete/backlogged via
           AcademicHistory so it re-enters next semester's catalog.
        Called by GameClock via the TimeConsumable contract.
        """
        time_cost = 10 if self.__is_optimized else 14

        if not player.deduct_time_pool_days(time_cost):
            return

        passed = self.evaluate_exam_result()
        self._is_completed = True

        history = player.get_academic_history()

        if passed:
            history.record_completion(self.__linked_course)
            player.add_credits(self.__linked_course.get_credit_value())
        else:
            history.mark_course_incomplete(self.__linked_course)
            history.add_backlog(self.__linked_course)


# ══════════════════════════════════════════════════════════════════
# SIDE QUEST
# ══════════════════════════════════════════════════════════════════

class SideQuest(Quest, TimeConsumable):
    """
    Represents an extracurricular activity (skill sprint, NPC task).
    Only available when the semester time pool is above the 15-day
    borderline threshold — enforced by GameClock, not by this class.

    Earns EXP which feeds into the SkillTree.

    OOP: Inheritance — extends Quest.
         Polymorphism — implements TimeConsumable.execute_action().

    Note: In the full scope diagram, SideQuest is further
    specialised into SkillSprint and CertificationQuest (Sprint 3).
    For this iteration, SideQuest is concrete and generic.
    """

    def __init__(self, quest_id: str, time_cost: int) -> None:
        super().__init__(quest_id=quest_id, time_cost=time_cost)
        self.__exp_reward: int = 10
        self.__academic_gate_dependency_flag: str = ""

    def get_exp_reward(self) -> int:
        """Return the EXP awarded on completion."""
        return self.__exp_reward

    def set_exp_reward(self, amount: int) -> None:
        """Allow content-loading code to customise the EXP payout."""
        if amount >= 0:
            self.__exp_reward = amount

    def get_academic_gate_dependency_flag(self) -> str:
        """
        Return the skill ID this side quest feeds into (empty string
        if none set yet).
        """
        return self.__academic_gate_dependency_flag

    def set_academic_gate_dependency_flag(self, skill_id: str) -> None:
        """
        Set which SkillTree skill node this side quest contributes
        EXP to when completed. Called by the content-loading code
        when the side quest is created (e.g. "python", "networking").
        """
        self.__academic_gate_dependency_flag = skill_id or ""

    def execute_action(self, player: Player) -> None:
        """
        Execute the side quest:
        1. Deduct this quest's time cost from the player's time pool.
           If the player doesn't have enough days, the attempt is
           aborted with no side effects.
        2. Award EXP to the player's SkillTree, under the configured
           skill ID (falls back to "general" if none was set).
        3. Mark the quest as completed.
        Only reachable if GameClock confirms timePoolDays > 15
        (the 15-Day Borderline Firewall) — this class does not
        re-check that threshold itself.
        """
        if not player.deduct_time_pool_days(self._time_cost):
            return

        skill_tree = player.get_skill_tree()
        if skill_tree is not None:
            skill_id = self.__academic_gate_dependency_flag or "general"
            skill_tree.increment_skill(skill_id, self.__exp_reward)

        self._is_completed = True
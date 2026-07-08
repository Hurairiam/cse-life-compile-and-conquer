"""
quest.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillars: Abstraction + Inheritance + Polymorphism
Abstract Quest defines shared quest identity (ID, time cost,
completion state). MainQuest and SideQuest specialise it.
Both implement TimeConsumable so GameClock can process them
through one unified pipeline — this is polymorphism in action.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from core.interfaces import TimeConsumable

if TYPE_CHECKING:
    from core.character import Player
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
    - No automatic pass: evaluateExamResult() combines SkillTree
      level with Q&A performance to determine outcome.
    - Q&A optimization: 3 questions answered correctly sets
      isOptimized = True, reducing time cost from 14 → 10 days.
    - Failure means isPassed = False and the Course is backlogged.

    OOP: Inheritance — extends Quest.
         Polymorphism — implements TimeConsumable.executeAction().
    """

    def __init__(self, quest_id: str, linked_course: Course) -> None:
        super().__init__(quest_id=quest_id, time_cost=14)
        self.__linked_course: Course = linked_course
        self.__is_optimized: bool = False
        self.__qa_question_pool: list[str] = []

    def get_linked_course(self) -> Course:
        """Return the Course this exam is testing."""
        return self.__linked_course

    def get_is_optimized(self) -> bool:
        """Return whether Q&A optimization was successful."""
        return self.__is_optimized

    def attempt_qa_optimization(self, answers: list[str]) -> bool:
        """
        Run the 3-question Q&A pre-exam optimization.
        If passed, sets isOptimized = True which reduces the
        time cost of executeAction() from 14 days to 10 days.
        Does NOT determine exam pass/fail — only affects cost.
        [Sprint 3 — Q&A logic and question pool implementation]
        """
        pass

    def evaluate_exam_result(self) -> bool:
        """
        Combine SkillTree level with Q&A performance to determine
        whether the exam is passed or failed.
        Sets Course.isPassed and Course.isCompleted accordingly.
        [Sprint 3 — SkillTree integration and threshold logic]
        """
        pass

    def execute_action(self, player: Player) -> None:
        """
        Execute the exam attempt:
        1. Deduct 10 days (optimized) or 14 days (unoptimized).
        2. Call evaluateExamResult().
        3. If passed: award credits, record completion.
        4. If failed: mark course incomplete, push to backlog.
        Called by GameClock via TimeConsumable contract.
        [Sprint 3 — full implementation]
        """
        pass


# ══════════════════════════════════════════════════════════════════
# SIDE QUEST
# ══════════════════════════════════════════════════════════════════

class SideQuest(Quest, TimeConsumable):
    """
    Represents an extracurricular activity (skill sprint, NPC task).
    Only available when semester time pool is above the 15-day
    borderline threshold — enforced by GameClock, not by this class.

    Earns EXP which feeds into the SkillTree.

    OOP: Inheritance — extends Quest.
         Polymorphism — implements TimeConsumable.executeAction().

    Note: In the full scope diagram, SideQuest is further
    specialised into SkillSprint and CertificationQuest (Sprint 3).
    For iteration 1 (Phase 1 scope), SideQuest is concrete.
    """

    def __init__(self, quest_id: str, time_cost: int) -> None:
        super().__init__(quest_id=quest_id, time_cost=time_cost)
        self.__exp_reward: int = 10
        self.__academic_gate_dependency_flag: str = ""

    def get_exp_reward(self) -> int:
        """Return the EXP awarded on completion."""
        return self.__exp_reward

    def execute_action(self, player: Player) -> None:
        """
        Execute the side quest:
        1. Deduct time cost from player's time pool.
        2. Award EXP to player's SkillTree.
        3. Mark quest as completed.
        Only reachable if GameClock confirms timePoolDays > 15.
        [Sprint 2 — full implementation]
        """
        pass

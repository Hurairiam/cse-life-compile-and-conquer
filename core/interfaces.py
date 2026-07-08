"""
interfaces.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Polymorphism
Defines the TimeConsumable interface — a pure contract.
Any class that costs in-game time MUST implement executeAction().
This allows GameClock to process MainQuest, SideQuest, and
future career actions through ONE unified pipeline without
knowing anything about their internal behaviour.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.character import Player


class TimeConsumable(ABC):
    """
    Interface contract for every action that consumes semester time.

    Implemented by: MainQuest, SideQuest, (Sprint 3) JobShift,
    SkillSprint, CertificationQuest, UndergraduateInternship.

    GameClock calls executeAction() on any TimeConsumable without
    needing to know which concrete type it is — this IS polymorphism.
    """

    @abstractmethod
    def execute_action(self, player: Player) -> None:
        """
        Execute this time-consuming action and apply its effects
        to the player's state (time pool, wallet, credits, skills).
        [Sprint 1 — implemented by concrete subclasses]
        """
        pass

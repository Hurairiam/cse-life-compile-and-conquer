"""
core/character/base.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Abstraction
Abstract base class for all living entities in the game.
Defines shared identity fields (ID, name, location) and
enforces move_to_location() on every concrete subclass.
Cannot be instantiated directly.
─────────────────────────────────────────────────────────────
Sprint 2 — Refactored by Abu Huraira (dev1-hurairiam-core)
"""

from __future__ import annotations
from abc import ABC, abstractmethod


class Character(ABC):
    """
    Abstract base for all game entities with identity and location.
    Player and NPC inherit from this — nothing else should.

    OOP: Abstraction — shared identity contract without shared behaviour.
         Encapsulation — identity fields are private, read-only externally.
    """

    def __init__(
        self,
        character_id: str,
        display_name: str,
        current_location_id: str
    ) -> None:
        self.__character_id: str = character_id
        self.__display_name: str = display_name
        self.__current_location_id: str = current_location_id

    def get_character_id(self) -> str:
        """Return the unique identifier for this character."""
        return self.__character_id

    def get_display_name(self) -> str:
        """Return the display name shown in-game."""
        return self.__display_name

    def get_current_location_id(self) -> str:
        """Return the ID of the location this character is currently in."""
        return self.__current_location_id

    @abstractmethod
    def move_to_location(self, location_id: str) -> None:
        """
        Move this character to a new location node.
        Subclasses define whether movement is gated by time,
        availability, or any other game-state condition.
        [Sprint 2 — implemented by Player and NPC]
        """
        pass

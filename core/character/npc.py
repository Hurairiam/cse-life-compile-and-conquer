"""
core/character/npc.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillars: Inheritance + Encapsulation
NPC is a non-player character that offers quests and dialogue.
Uses a temporal fractional availability window — only accessible
during the first 25% of a semester (ratio 0.75 to 1.00).
─────────────────────────────────────────────────────────────
Sprint 2 — Refactored by Abu Huraira (dev1-hurairiam-core)
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from core.character.base import Character

if TYPE_CHECKING:
    from core.character.player import Player
    from academic.quest import Quest


class NPC(Character):
    """
    Non-player character with dialogue, quest offering, and
    a temporal availability window tied to the semester pool.

    OOP: Inheritance — extends Character.
         Encapsulation — dialogue and quest arrays are private.
    """

    def __init__(
        self,
        character_id: str,
        display_name: str,
        location_id: str,
        semester_bound_expiry: int
    ) -> None:
        super().__init__(character_id, display_name, location_id)
        self.__dialogue_nodes: list[str] = []
        self.__quest_pointer_array: list[Quest] = []
        self.__is_accessible: bool = True
        self.__semester_bound_expiry: int = semester_bound_expiry
        self.__availability_ratio_min: float = 0.75
        self.__availability_ratio_max: float = 1.00

    # ── Dialogue ──────────────────────────────────────────────

    def get_dialogue_node(self, index: int) -> str:
        """Return the dialogue string at the given index, or empty."""
        if 0 <= index < len(self.__dialogue_nodes):
            return self.__dialogue_nodes[index]
        return ""

    def load_dialogue(self, nodes: list[str]) -> None:
        """
        Load a list of dialogue strings into this NPC.
        Called during scene initialisation from content/dialogues.py.
        """
        self.__dialogue_nodes = nodes

    # ── Availability ──────────────────────────────────────────

    def is_within_availability_window(self, player: Player) -> bool:
        """
        Returns True if the player's remaining time ratio falls within
        this NPC's availability window (0.75 to 1.00 of the semester pool).
        An NPC is only accessible in the first 20 days of an 80-day semester.
        Called by the game engine before showing the NPC on screen.
        """
        if not self.__is_accessible:
            return False
        ratio: float = player.get_time_pool_days() / 80.0
        return self.__availability_ratio_min <= ratio <= self.__availability_ratio_max

    def expire_for_semester(self) -> None:
        """
        Mark this NPC as inaccessible for the rest of the semester.
        Called by GameClock when the exploration phase ends.
        [Sprint 2 — implemented by Ayesha's layer]
        """
        pass

    def get_is_accessible(self) -> bool:
        """Return whether this NPC is currently accessible."""
        return self.__is_accessible

    # ── Quest Offering ────────────────────────────────────────

    def offer_quest(self) -> Optional[Quest]:
        """
        Return the first uncompleted quest from this NPC's pool.
        Returns None if all quests are done or pool is empty.
        [Sprint 2 — implemented by Ayesha's layer]
        """
        pass

    def interact(self) -> None:
        """
        Signal that the player has initiated NPC interaction.
        DialogueManager takes over rendering from the screen manager.
        [Sprint 2 — implemented by Ayesha's layer]
        """
        pass

    # ── Movement ──────────────────────────────────────────────

    def move_to_location(self, location_id: str) -> None:
        """
        NPCs are statically placed in Phase 1 — no movement.
        [Sprint 3 — may extend for roaming NPCs]
        """
        pass

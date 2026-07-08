"""
character.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillars: Abstraction + Encapsulation + Inheritance
Abstract class Character defines shared identity fields for
every living entity in the game. Player and NPC inherit and
specialise this base without duplicating identity logic.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from academic.academic_history import AcademicHistory
    from core.skill_tree import SkillTree
    from academic.quest import Quest


class Character(ABC):
    """
    Abstract base for all game entities with an identity and location.
    Cannot be instantiated directly — only Player and NPC are concrete.

    OOP: Abstraction — hides identity management from subclasses.
         Encapsulation — characterID and displayName are private.
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

    # ── Getters ───────────────────────────────────────────────────

    def get_character_id(self) -> str:
        """Return the unique identifier for this character."""
        return self.__character_id

    def get_display_name(self) -> str:
        """Return the display name shown in-game."""
        return self.__display_name

    def get_current_location_id(self) -> str:
        """Return the ID of the location this character is in."""
        return self.__current_location_id

    # ── Abstract Methods ─────────────────────────────────────────

    @abstractmethod
    def move_to_location(self, location_id: str) -> None:
        """
        Move this character to a new location.
        Subclasses define whether movement is gated by time,
        availability, or game-state conditions.
        [Sprint 2 — implemented by Player and NPC]
        """
        pass


# ══════════════════════════════════════════════════════════════════
# PLAYER
# ══════════════════════════════════════════════════════════════════

class Player(Character):
    """
    The human-controlled student entity.
    Owns the core resource state: time pool, wallet, credits.

    OOP: Inheritance — extends Character for identity fields.
         Encapsulation — all resource fields strictly private,
         mutated only through validated public methods.
    """

    def __init__(self) -> None:
        super().__init__(
            character_id="player_01",
            display_name="CSE Student",
            current_location_id="campus_main"
        )
        # ── Core Resources (private — mutate via methods only) ──
        self.__time_pool_days: int = 80
        self.__wallet_balance: float = 0.00
        self.__current_semester: int = 1
        self.__accumulated_credits: int = 0
        self.__has_graduated: bool = False

        # ── Permanent Profiles (aggregated — survive semester resets) ──
        self.__academic_history: AcademicHistory = None   # [Sprint 1 init]
        self.__skill_tree: SkillTree = None               # [Sprint 1 init]

    # ── Time Pool ─────────────────────────────────────────────────

    def get_time_pool_days(self) -> int:
        """Return remaining days in the current semester pool."""
        return self.__time_pool_days

    def deduct_time_pool_days(self, days: int) -> bool:
        """
        Deduct days from the semester time pool.
        Returns False and makes no change if insufficient days remain.
        This validation pipeline enforces the resource scarcity mechanic.
        """
        if days < 0:
            return False
        if self.__time_pool_days >= days:
            self.__time_pool_days -= days
            return True
        return False

    # ── Wallet ────────────────────────────────────────────────────

    def get_wallet_balance(self) -> float:
        """Return current BDT wallet balance."""
        return self.__wallet_balance

    def deposit_funds(self, amount: float) -> None:
        """
        Add funds to the wallet (stipend, salary, etc.).
        Negative deposits are silently ignored.
        """
        if amount > 0:
            self.__wallet_balance += amount

    def withdraw_funds(self, amount: float) -> bool:
        """
        Deduct funds from the wallet.
        Returns False and makes no change if insufficient balance.
        """
        if amount < 0:
            return False
        if self.__wallet_balance >= amount:
            self.__wallet_balance -= amount
            return True
        return False

    # ── Academic Progress ─────────────────────────────────────────

    def get_current_semester(self) -> int:
        """Return the current semester number."""
        return self.__current_semester

    def advance_semester(self) -> None:
        """
        Increment semester counter and reset the time pool to 80 days.
        Called by GameClock at the end of each semester cycle.
        """
        self.__current_semester += 1
        self.__time_pool_days = 80

    def get_accumulated_credits(self) -> int:
        """Return total credits earned across all semesters."""
        return self.__accumulated_credits

    def add_credits(self, credits: int) -> None:
        """
        Add earned credits after a successful exam.
        Negative values are ignored.
        """
        if credits > 0:
            self.__accumulated_credits += credits

    def get_has_graduated(self) -> bool:
        """Return graduation status."""
        return self.__has_graduated

    def check_graduation_eligibility(self) -> bool:
        """
        Check whether the player has reached 140 accumulated credits.
        Sets hasGraduated = True if the threshold is met.
        [Sprint 3 — full implementation with GameSession integration]
        """
        pass

    # ── Profile Access ────────────────────────────────────────────

    def get_academic_history(self) -> AcademicHistory:
        """Return the player's permanent academic history object."""
        return self.__academic_history

    def get_skill_tree(self) -> SkillTree:
        """Return the player's permanent skill tree object."""
        return self.__skill_tree

    # ── Movement (inherited contract) ─────────────────────────────

    def move_to_location(self, location_id: str) -> None:
        """
        Move the player to an unlocked map location.
        [Sprint 2 — map system and location unlock logic]
        """
        pass


# ══════════════════════════════════════════════════════════════════
# NPC
# ══════════════════════════════════════════════════════════════════

class NPC(Character):
    """
    A non-player character that offers quests and dialogue.
    Uses a temporal fractional availability window — NPCs are only
    accessible during a specific ratio of the semester time pool.

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

    # ── Dialogue ──────────────────────────────────────────────────

    def get_dialogue_node(self, index: int) -> str:
        """Return the dialogue string at the given index."""
        if 0 <= index < len(self.__dialogue_nodes):
            return self.__dialogue_nodes[index]
        return ""

    # ── Availability ──────────────────────────────────────────────

    def is_within_availability_window(self, player: Player) -> bool:
        """
        Returns True if the player's remaining time ratio falls within
        this NPC's availability window (0.75–1.00 of the semester pool).
        Prevents NPCs from appearing too late in the semester.
        [Sprint 2 — full implementation]
        """
        pass

    def expire_for_semester(self) -> None:
        """
        Mark this NPC as inaccessible for the remainder of the semester.
        [Sprint 2 — implementation]
        """
        pass

    # ── Quest Offering ────────────────────────────────────────────

    def offer_quest(self) -> Optional[Quest]:
        """
        Return the next available quest from this NPC's pool.
        Returns None if no quests remain.
        [Sprint 2 — implementation]
        """
        pass

    def interact(self) -> None:
        """
        Trigger the interaction sequence: play dialogue, offer quest.
        [Sprint 2 — implementation]
        """
        pass

    # ── Movement ──────────────────────────────────────────────────

    def move_to_location(self, location_id: str) -> None:
        """
        NPCs do not move in Phase 1 — they are statically placed.
        [Sprint 2 — may be extended for roaming NPCs]
        """
        pass

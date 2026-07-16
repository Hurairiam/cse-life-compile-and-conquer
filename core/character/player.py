"""
core/character/player.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillars: Inheritance + Encapsulation
Player is the human-controlled student entity.
Inherits identity from Character.
Owns the three core resource pools: time, wallet, credits.
All resource fields are strictly private — mutations only
through validated public methods.
─────────────────────────────────────────────────────────────
Sprint 2 — Refactored by Abu Huraira (dev1-hurairiam-core)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from core.character.base import Character

if TYPE_CHECKING:
    from academic.academic_history import AcademicHistory
    from core.skill_tree import SkillTree


class Player(Character):
    """
    The human-controlled student entity.
    Aggregates AcademicHistory and SkillTree — both survive
    semester resets because they are aggregated, not composed.

    OOP: Inheritance — extends Character for identity fields.
         Encapsulation — all resource fields double-underscore private.
    """

    def __init__(self) -> None:
        super().__init__(
            character_id="player_01",
            display_name="CSE Student",
            current_location_id="campus_main"
        )
        # ── Core Resources ────────────────────────────────────
        self.__time_pool_days: int = 80
        self.__wallet_balance: float = 0.00
        self.__current_semester: int = 1
        self.__accumulated_credits: int = 0
        self.__has_graduated: bool = False

        # ── Permanent Profiles (aggregated) ───────────────────
        self.__academic_history: AcademicHistory = None
        self.__skill_tree: SkillTree = None

    # ── Time Pool ─────────────────────────────────────────────

    def get_time_pool_days(self) -> int:
        """Return remaining days in the current semester pool."""
        return self.__time_pool_days

    def deduct_time_pool_days(self, days: int) -> bool:
        """
        Deduct days from the semester time pool.
        Returns False without changing state if days < 0
        or if the pool has insufficient days remaining.
        """
        if days < 0:
            return False
        if self.__time_pool_days >= days:
            self.__time_pool_days -= days
            return True
        return False

    def reset_time_pool(self) -> None:
        """
        Reset time pool to 80 days for a new semester.
        Called by advance_semester() — not directly by GameClock.
        """
        self.__time_pool_days = 80

    # ── Wallet ────────────────────────────────────────────────

    def get_wallet_balance(self) -> float:
        """Return current BDT wallet balance."""
        return self.__wallet_balance

    def deposit_funds(self, amount: float) -> None:
        """
        Credit funds to the wallet.
        Negative amounts are silently ignored.
        """
        if amount > 0:
            self.__wallet_balance += amount

    def withdraw_funds(self, amount: float) -> bool:
        """
        Debit funds from the wallet.
        Returns False without changing state if amount < 0
        or if the wallet has insufficient balance.
        """
        if amount < 0:
            return False
        if self.__wallet_balance >= amount:
            self.__wallet_balance -= amount
            return True
        return False

    # ── Academic Progress ─────────────────────────────────────

    def get_current_semester(self) -> int:
        """Return the current semester number."""
        return self.__current_semester

    def advance_semester(self) -> None:
        """
        Increment semester counter and reset the 80-day time pool.
        Called by GameClock at the end of each semester cycle.
        """
        self.__current_semester += 1
        self.__time_pool_days = 80

    def get_accumulated_credits(self) -> int:
        """Return total credits earned across all semesters."""
        return self.__accumulated_credits

    def add_credits(self, credits: int) -> None:
        """
        Add earned credits after a passed exam.
        Negative values are silently ignored.
        """
        if credits > 0:
            self.__accumulated_credits += credits

    def get_has_graduated(self) -> bool:
        """Return graduation status."""
        return self.__has_graduated

    def check_graduation_eligibility(self) -> bool:
        """
        Check whether the player has reached 140 accumulated credits.
        Sets __has_graduated = True and returns True if threshold met.
        [Sprint 3 — GameSession integration]
        """
        pass

    # ── Profile Access ────────────────────────────────────────

    def get_academic_history(self) -> AcademicHistory:
        """Return the player's permanent academic history object."""
        return self.__academic_history

    def set_academic_history(self, history: AcademicHistory) -> None:
        """
        Inject the AcademicHistory instance.
        Called once during GameSession initialisation.
        """
        self.__academic_history = history

    def get_skill_tree(self) -> SkillTree:
        """Return the player's permanent skill tree object."""
        return self.__skill_tree

    def set_skill_tree(self, skill_tree: SkillTree) -> None:
        """
        Inject the SkillTree instance.
        Called once during GameSession initialisation.
        """
        self.__skill_tree = skill_tree

    # ── Movement ──────────────────────────────────────────────

    def move_to_location(self, location_id: str) -> None:
        """
        Move the player to an unlocked map location node.
        [Sprint 2 — map system and unlock logic]
        """
        pass

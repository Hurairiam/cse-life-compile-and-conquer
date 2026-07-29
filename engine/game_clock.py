"""
engine/game_clock.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Separation of Concerns
GameClock is the central engine that drives the semester loop.
It is the ONLY class that calls execute_action() on
TimeConsumable objects. It enforces the 15-day Borderline
Firewall via is_eligible_for_side_activities().

No Pygame code lives here — GameClock is pure logic.
─────────────────────────────────────────────────────────────
Sprint 2 — Created by Abu Huraira (dev1-hurairiam-core)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from core.interfaces import TimeConsumable
from core.character.player import Player
from academic.semester import Semester
from academic.academic_history import AcademicHistory

if TYPE_CHECKING:
    from engine.game_session import GameSession


class GameClock:
    """
    Drives the semester lifecycle loop. Owns the 15-day Borderline
    Firewall constant and enforces it every gameplay iteration.

    Key responsibilities:
    - Process TimeConsumable actions through one unified pipeline
    - Enforce the 15-day firewall (locks side activities)
    - Advance semesters and carry over incomplete courses
    - Check semester end state and route to endgame if needed

    Holds a reference to GameSession for clock increment and cap
    checks — does NOT own GameSession (association, not composition).
    """

    __MIN_MAIN_QUEST_TIME_BORDER: int = 15

    def __init__(self, session: GameSession) -> None:
        self.__session: GameSession = session
        self.__current_semester: Semester = session.get_active_semester()

    # ── Core Pipeline ─────────────────────────────────────────

    def process_time_consumable(self, action: TimeConsumable) -> None:
        """
        Execute a TimeConsumable action against the active player.
        This is the single entry point for ALL time-costing actions
        in the game — MainQuest, SideQuest, and future career actions
        all go through here, none call execute_action() directly.

        Order of operations:
        1. Guard: do nothing if session is frozen
        2. Read the time cost before execution (for clock increment)
        3. Call execute_action() on the action — deducts time, awards
           credits or EXP, marks quest complete etc.
        4. Increment the GlobalCareerClock by the same day cost
        """
        if self.__session.get_is_frozen():
            return

        player: Player = self.__session.get_active_player()
        days_cost: int = action.get_time_cost()
        action.execute_action(player)
        self.__session.increment_global_clock(days_cost)

    # ── Firewall ──────────────────────────────────────────────

    def is_eligible_for_side_activities(self) -> bool:
        """
        Return True if the player is allowed to do side activities.
        Returns False when remaining semester days <= 15.

        This is the 15-day Borderline Firewall. When it activates,
        the main loop must route the player directly to the exam
        phase — no NPC interactions, no skill sprints, no drops.

        Called at the start of every gameplay loop iteration before
        presenting any action choices to the player.
        """
        remaining: int = self.__current_semester.get_time_pool_days()
        return remaining > self.__MIN_MAIN_QUEST_TIME_BORDER

    # ── Semester Lifecycle ────────────────────────────────────

    def advance_semester(self) -> None:
        """
        Close the current semester and open the next one.

        Order of operations:
        1. Terminate the current semester (clears its quest pool)
        2. Call player.advance_semester() which increments the
           semester counter AND resets the 80-day time pool
        3. Instantiate a fresh Semester with the new number
        4. Set it as active on GameSession
        5. Update local reference
        """
        player: Player = self.__session.get_active_player()

        self.__current_semester.terminate()
        player.advance_semester()

        new_number: int = player.get_current_semester()
        new_semester: Semester = Semester(new_number)

        self.__session.set_active_semester(new_semester)
        self.__current_semester = new_semester

    def check_semester_end_state(self) -> None:
        """
        Called after all registered courses have been attempted
        or the time pool hits zero.

        Order of operations:
        1. Carry incomplete courses to backlog (only if history exists)
        2. Check graduation — 140+ credits (takes priority over cap)
        3. Check GlobalCareerClock cap — freeze and trigger endgame
        """
        player: Player = self.__session.get_active_player()
        history: AcademicHistory = player.get_academic_history()

        # Carry incomplete courses to backlog only if history is wired
        if history is not None:
            for course in self.__current_semester.get_registered_courses():
                if not course.get_is_completed():
                    history.add_backlog(course)

        # Graduation takes priority — check first
        if player.get_accumulated_credits() >= 140:
            self.__session.freeze_session()
            return

        # Year cap check
        if self.__session.has_reached_year_cap():
            self.__session.freeze_session()
            return

    # ── Getters ───────────────────────────────────────────────

    def get_current_semester(self) -> Semester:
        """Return the current active Semester."""
        return self.__current_semester

    def get_min_border(self) -> int:
        """Return the 15-day firewall threshold constant."""
        return self.__MIN_MAIN_QUEST_TIME_BORDER

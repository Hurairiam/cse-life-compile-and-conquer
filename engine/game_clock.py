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
        This is the single entry point for ALL time-costing actions.
        Increments the GlobalCareerClock after the action completes.
        Does nothing if the session is frozen.
        [Sprint 2 — stub]
        """
        pass

    # ── Firewall ──────────────────────────────────────────────

    def is_eligible_for_side_activities(self) -> bool:
        """
        Return True if the player is allowed to do side activities.
        Returns False when timePoolDays <= 15 (firewall active).
        Called at the start of every gameplay loop iteration.
        [Sprint 2 — stub]
        """
        pass

    # ── Semester Lifecycle ────────────────────────────────────

    def advance_semester(self) -> None:
        """
        Close the current semester and open the next one.
        Calls player.advance_semester() which resets the time pool.
        Creates a new Semester instance and sets it on GameSession.
        Does NOT carry over backlog — that is check_semester_end_state().
        [Sprint 2 — stub]
        """
        pass

    def check_semester_end_state(self) -> None:
        """
        Called after all registered courses have been attempted
        or the time pool hits zero. Carries any incomplete courses
        to backlog via AcademicHistory. Then checks cap and graduation.
        [Sprint 2 — stub]
        """
        pass

    # ── Getters ───────────────────────────────────────────────

    def get_current_semester(self) -> Semester:
        """Return the current active Semester."""
        return self.__current_semester

    def get_min_border(self) -> int:
        """Return the 15-day firewall threshold constant."""
        return self.__MIN_MAIN_QUEST_TIME_BORDER

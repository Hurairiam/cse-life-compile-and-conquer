"""
engine/game_session.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation + Composition
GameSession is the top-level owner of all persistent game
state. It owns the active Player, the active Semester, and
the GlobalCareerClock. Nothing else should hold references
to these — all access goes through GameSession.
─────────────────────────────────────────────────────────────
Sprint 2 — Created by Abu Huraira (dev1-hurairiam-core)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.endgame_manager import EndgameEvaluationManager

from core.character import Player
from academic.semester import Semester


class GameSession:
    """
    Top-level game container. Instantiated once at game start.
    Owns the Player profile, the active Semester, and the
    GlobalCareerClock that tracks the 7-year hard cap.

    Composition relationships:
        GameSession 1 *-- 1 Player
        GameSession 1 *-- 1 Semester (active at any given time)
    """

    # Short scope: 4 years x 4 semesters x ~60 days average = ~960 days
    __GLOBAL_YEAR_CAP_DAYS: int = 960

    def __init__(self) -> None:
        self.__global_career_clock_days: int = 0
        self.__is_frozen: bool = False
        self.__active_player: Player = Player()
        self.__active_semester: Semester = Semester(1)

    # ── GlobalCareerClock ─────────────────────────────────────

    def get_global_career_clock_days(self) -> int:
        """Return total days elapsed across the entire playthrough."""
        return self.__global_career_clock_days

    def increment_global_clock(self, days: int) -> None:
        """
        Increment the global career clock by the given number of days.
        Called by GameClock after every TimeConsumable action.
        Does nothing if the session is already frozen.
        [Sprint 2 — stub]
        """
        pass

    def has_reached_year_cap(self) -> bool:
        """
        Return True if the global clock has hit or exceeded the cap.
        Checked every semester end — triggers freeze and endgame.
        [Sprint 2 — stub]
        """
        pass

    def freeze_session(self) -> None:
        """
        Lock all further progression. Called when the year cap is hit
        or graduation is confirmed. Endgame evaluation runs after this.
        [Sprint 2 — stub]
        """
        pass

    def get_is_frozen(self) -> bool:
        """Return whether the session has been frozen."""
        return self.__is_frozen

    # ── Active Objects ────────────────────────────────────────

    def get_active_player(self) -> Player:
        """Return the active Player instance."""
        return self.__active_player

    def get_active_semester(self) -> Semester:
        """Return the currently active Semester instance."""
        return self.__active_semester

    def set_active_semester(self, semester: Semester) -> None:
        """
        Replace the active Semester with a new instance.
        Called by GameClock when advancing to a new semester.
        [Sprint 2 — stub]
        """
        pass

    # ── Endgame ───────────────────────────────────────────────

    def trigger_endgame_evaluation(self) -> EndgameEvaluationManager:
        """
        Freeze the session and spawn the EndgameEvaluationManager.
        Returns the manager so the caller can run evaluations.
        [Sprint 3 — stub until EndgameEvaluationManager exists]
        """
        pass

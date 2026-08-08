"""
engine/screen_manager.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation + Separation of Concerns
ScreenManager owns the current screen state and handles
transitions between screens. main.py queries it each frame
to decide what to render and what events to handle.

No game logic lives here — only routing decisions.
─────────────────────────────────────────────────────────────
Sprint 3 — Created by Abu Huraira (dev1-hurairiam-core)
"""

from __future__ import annotations
from enum import Enum, auto


class ScreenState(Enum):
    """
    Enum representing every possible screen in the game.
    One value per distinct view the player can be on.
    """
    MAIN_MENU = auto()
    REGISTRATION = auto()
    EXPLORATION = auto()
    EXAM = auto()
    DIALOGUE = auto()
    ENDGAME = auto()
    MONOLOGUE = auto()
    SETTINGS = auto()
    LOAD_GAME = auto()
    SKILL_TREE = auto()
    STATS = auto()
    EXAM_RESULT = auto()
    CERTIFICATE = auto()
    LECTURE = auto()
    # The exam / lecture / cancel card a classroom prop opens. Appended
    # rather than inserted: auto() numbers by position, and moving an
    # existing member would renumber the ones after it.
    ACTIVITY = auto()
    CUTSCENE = auto()
    # Name entry, between START GAME and the opening monologue.
    # Appended for the same reason ACTIVITY was.
    NAME_ENTRY = auto()
    # The slot picker the pause menu's SAVE GAME opens. Appended for the
    # same reason ACTIVITY was.
    SAVE_GAME = auto()
    # The "Where to go?" destination list a teleport prop opens.
    # Appended for the same reason ACTIVITY was.
    TELEPORT = auto()
    # The "end the semester now?" question an end_semester prop opens,
    # so a player who finished the exams with days to spare can close
    # the term when they are done roaming. Appended for the same reason
    # ACTIVITY was.
    END_SEMESTER = auto()


class ScreenManager:
    """
    Owns and manages the current screen state.
    Tracks previous state for back-navigation where applicable.
    All screen transitions go through this class — nothing
    sets the state directly from outside.
    """

    def __init__(self) -> None:
        self.__current_state: ScreenState = ScreenState.MAIN_MENU
        self.__previous_state: ScreenState | None = None
        self.__pending_transition: ScreenState | None = None

    # ── State Access ──────────────────────────────────────────

    def get_current_state(self) -> ScreenState:
        """Return the currently active screen state."""
        return self.__current_state

    def get_previous_state(self) -> ScreenState | None:
        """Return the previously active screen state."""
        return self.__previous_state

    def is_state(self, state: ScreenState) -> bool:
        """Return True if the given state is currently active."""
        return self.__current_state == state

    # ── Transitions ───────────────────────────────────────────

    def transition_to(self, new_state: ScreenState) -> None:
        """
        Immediately transition to a new screen state.
        Stores the current state as previous for back-navigation.
        """
        self.__previous_state = self.__current_state
        self.__current_state = new_state
        self.__pending_transition = None

    def queue_transition(self, new_state: ScreenState) -> None:
        """
        Queue a transition to happen at the end of the current
        frame. Prevents state changes mid-render cycle.
        Call apply_pending_transition() at the start of each frame.
        """
        self.__pending_transition = new_state

    def apply_pending_transition(self) -> bool:
        """
        Apply any queued transition. Returns True if a transition
        was applied, False if nothing was pending.
        Call at the very start of the main loop before event handling.
        """
        if self.__pending_transition is not None:
            self.transition_to(self.__pending_transition)
            return True
        return False

    def go_back(self) -> bool:
        """
        Return to the previous state if one exists.
        Returns True if navigation occurred, False if no history.
        """
        if self.__previous_state is not None:
            self.__current_state = self.__previous_state
            self.__previous_state = None
            return True
        return False

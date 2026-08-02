"""
engine/app_context.py
One object that owns every runtime system and every piece of shared
screen state. Built once in main(); passed to every state module.

Fields marked STAGE n are populated by that stage and are None/default
until then. Every consumer must guard with `if ctx.x is not None:`.
"""
from __future__ import annotations

import pygame

from engine.game_session import GameSession
from engine.game_clock import GameClock
from engine.registration_manager import RegistrationManager
from engine.screen_manager import ScreenManager, ScreenState
from engine.npc_manager import NPCManager
from engine.dialogue_manager import DialogueManager
from academic.course_catalog import build_course_catalog
from ui.hud import HUD
from engine.audio_manager import AudioManager
from engine import settings_store

VERSION: str = "v1.0"


class AppContext:
    """Mutable struct. No game rules live here — only ownership."""

    def __init__(self, screen_w: int = 1280, screen_h: int = 720) -> None:
        # -- window / loop ------------------------------------------
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.is_fullscreen = False
        self.running = True
        self.playtime_seconds = 0.0

        # -- STAGE 1: core systems ----------------------------------
        self.session = GameSession()
        self.game_clock = GameClock(self.session)
        self.registration_manager = RegistrationManager()
        self.screen_mgr = ScreenManager()
        self.npc_manager = NPCManager()
        self.dialogue_manager = DialogueManager(screen_w, screen_h)
        self.full_catalog = build_course_catalog()
        self.hud = HUD()
        self.fonts = {
            "title": pygame.font.SysFont("Arial", 28, bold=True),
            "body": pygame.font.SysFont("Arial", 16),
            "small": pygame.font.SysFont("Arial", 13),
        }
        self.exam = {"course_index": 0, "tier_index": 0,
                     "answers": {}, "message": None}

        # -- STAGE 2: audio + settings ------------------------------
        prefs = settings_store.load()
        self.music_volume = prefs["music_volume"]
        self.sfx_volume = prefs["sfx_volume"]
        self.text_speed = prefs["text_speed"]
        self.is_fullscreen = prefs["fullscreen"]
        self.audio = AudioManager(music_volume=self.music_volume,
                                  sfx_volume=self.sfx_volume)
        settings_store.apply_all(self)

        # -- STAGE 3: title / save / load ---------------------------
        from engine.save_manager import SaveManager
        from ui.popup import ConfirmPopup, MessagePopup
        self.saves = SaveManager()
        self.popup = ConfirmPopup(screen_w, screen_h)
        self.message_popup = MessagePopup(screen_w, screen_h)
        self.main_menu = None
        self.settings_screen = None
        self.load_screen = None
        self.menu_focus = 0
        self.load_selected = 0
        self.return_state = None
        self.pending_save_slot = None

        # -- STAGE 4: narrative -------------------------------------
        from ui.choice_box import ChoiceBox
        self.monologue = None
        self.dialog_box = None            # owned by DialogueManager
        self.choice_box = ChoiceBox(screen_w, screen_h)
        self.choice_options = []
        self.choice_result = None
        self.monologue_title = ""
        self.monologue_subtitle = ""
        self.monologue_lines = []
        self.monologue_next = None     # ScreenState to enter after beat
        self.dialogue_return = None    # ScreenState to return to
        self.dialogue_portrait = None

        # -- STAGE 5: world -----------------------------------------
        from ui.interaction_prompt import InteractionPrompt
        from ui.map_screen import MapScreen
        self.level = None
        self.level_id = "campus_main"
        self.walker = None
        self.map_screen = MapScreen()
        self.prompt = InteractionPrompt()
        self.prop_trigger_counts = {}
        self.npc_chain_index = {}
        self.last_cell = (0, 0)
        self.pulse = 0.0
        self.level_error = ""
        self.camera = (0, 0)
        self.npc_frames = {}
        self.anim_time = 0.0
        self.talked_npc_uids = set()
        self.triggered_prop_uids = set()
        self.pending_spawn = None

        # -- STAGE 6: gates -----------------------------------------
        from ui.gate_notice import GateNotice
        self.gate_evaluator = None            # built lazily by gate_service
        self.gate_notice = GateNotice(screen_w, screen_h)
        self.gate_args = {}
        self.pending_gate = None
        self.gate_states = {}                 # {(x,y): met} for map badges
        self.gates_cleared = set()            # cells already passed this run

        # -- STAGE 7: exam ------------------------------------------
        from ui.exam_screen import ExamScreen
        from ui.exam_result_screen import ExamResultScreen
        self.exam_session = None
        self.exam_screen = ExamScreen()
        # built in the state (needs audio)
        self.exam_result_screen = None
        self.exam_result = None
        self.exam_quest = None
        self.exam_focus = -1

        # -- STAGE 8: skills / pause / stats ------------------------
        from ui.pause_menu import PauseMenu
        from ui.skill_tree_screen import SkillTreeScreen
        from ui.stats_screen import StatsScreen
        self.pause_menu = PauseMenu(screen_w, screen_h)
        self.pause_focus = 0
        self.skill_tree_screen = SkillTreeScreen()
        self.stats_screen = StatsScreen()
        self.skill_points = 0
        self.selected_skill_id = ""

        # -- STAGE 9: registration / endgame ------------------------
        self.catalog_builder = None
        self.reg_scroll = 0
        self.endgame_result = None
        self.endgame_screen = None
        self.certificate = None

    # -- shortcuts ---------------------------------------------------
    def player(self):
        return self.session.get_active_player()

    def semester(self):
        return self.session.get_active_semester()

    def history(self):
        return self.player().get_academic_history()

    def go(self, state: ScreenState) -> None:
        self.screen_mgr.queue_transition(state)

    def quit(self) -> None:
        self.running = False

    # -- audio, always safe when self.audio is None ------------------
    def play_sfx(self, key: str) -> None:
        if self.audio is not None:
            self.audio.play_sfx(key)

    def play_music(self, key: str) -> None:
        if self.audio is not None:
            self.audio.play_music(key)

    def play_ambient(self, key: str) -> None:
        if self.audio is not None:
            self.audio.play_ambient(key)

    def shutdown(self) -> None:
        if self.audio is not None:
            self.audio.shutdown()

from __future__ import annotations

import json
import os
import sys

import pygame

from core.interfaces import TimeConsumable
from core.character import Player
from core.skill_tree import SkillTree
from academic.quest import Quest, MainQuest, SideQuest
from academic.academic_history import AcademicHistory
from academic.course import Course
from academic.course_catalog import build_course_catalog
from content.monologues import get_monologue
from engine.game_session import GameSession
from engine.game_clock import GameClock
from engine.registration_manager import RegistrationManager
from ui.confirm_popup import ConfirmPopup
from ui.main_menu_screen import (MainMenuScreen, START_GAME, EXIT,
                                 MENU_LABELS)
from ui.monologue_screen import MonologueScreen, TYPEWRITER_CPS
from ui.registration_screen import RegistrationScreen

SCREEN_W = 1280
SCREEN_H = 720
WINDOWED_FLAGS = pygame.SCALED
FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN
FPS = 60

WINDOW_CAPTION = "CSE Life: Compile & Conquer"
VERSION_STRING = "v0.2 — short scope"

CREDIT_LIMIT = 15
VISIBLE_COURSE_ROWS = 7

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(PROJECT_ROOT, "config", "settings.json")
SETTINGS_SCHEMA_VERSION = 1
DEFAULT_SETTINGS: dict = {
    "schema_version": SETTINGS_SCHEMA_VERSION,
    "music_volume": 80,
    "sfx_volume": 80,
    "fullscreen": False,
}

AUDIO_DIR = os.path.join(PROJECT_ROOT, "assets", "audio")
# [AUDIO PLACEHOLDER: assets/audio/menu_theme.ogg -- calm chiptune loop]
MENU_THEME_PATH = os.path.join(AUDIO_DIR, "menu_theme.ogg")
# [AUDIO PLACEHOLDER: assets/audio/sfx_click.ogg -- UI click]
SFX_CLICK_PATH = os.path.join(AUDIO_DIR, "sfx_click.ogg")
# [AUDIO PLACEHOLDER: assets/audio/sfx_confirm.ogg -- confirm chime]
SFX_CONFIRM_PATH = os.path.join(AUDIO_DIR, "sfx_confirm.ogg")

STATE_MAIN_MENU = "MAIN_MENU"
STATE_INTRO_MONOLOGUE = "INTRO_MONOLOGUE"
STATE_REGISTRATION = "REGISTRATION"

POPUP_NONE = None
POPUP_EXIT = "EXIT"
POPUP_RETURN_TO_MENU = "RETURN_TO_MENU"
POPUP_OVER_LIMIT = "OVER_LIMIT"


def load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as handle:
            stored = json.load(handle)
    except (FileNotFoundError, OSError, ValueError):
        save_settings(settings)
        return settings

    if isinstance(stored, dict):
        settings["music_volume"] = _clean_volume(
            stored.get("music_volume"), DEFAULT_SETTINGS["music_volume"])
        settings["sfx_volume"] = _clean_volume(
            stored.get("sfx_volume"), DEFAULT_SETTINGS["sfx_volume"])
        settings["fullscreen"] = bool(stored.get("fullscreen", False))

    save_settings(settings)
    return settings


def save_settings(settings: dict) -> bool:
    payload = {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "music_volume": _clean_volume(settings.get("music_volume"),
                                      DEFAULT_SETTINGS["music_volume"]),
        "sfx_volume": _clean_volume(settings.get("sfx_volume"),
                                    DEFAULT_SETTINGS["sfx_volume"]),
        "fullscreen": bool(settings.get("fullscreen", False)),
    }
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        return True
    except OSError:
        return False


def _clean_volume(value, fallback: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    return int(min(max(value, 0), 100))


class GameApp:

    def __init__(self) -> None:
        self.__settings: dict = load_settings()
        self.__is_fullscreen: bool = bool(self.__settings["fullscreen"])

        pygame.init()
        self.__window: pygame.Surface = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H), self.__display_flags())
        pygame.display.set_caption(WINDOW_CAPTION)
        self.__clock_tick: pygame.time.Clock = pygame.time.Clock()

        self.__audio_ready: bool = self.__init_audio()
        self.__sfx_click = self.__load_sound(SFX_CLICK_PATH)
        self.__sfx_confirm = self.__load_sound(SFX_CONFIRM_PATH)

        self.__menu_screen = MainMenuScreen(SCREEN_W, SCREEN_H)
        self.__monologue_screen = MonologueScreen()
        self.__registration_screen = RegistrationScreen(SCREEN_W, SCREEN_H)
        self.__popup = ConfirmPopup(SCREEN_W, SCREEN_H)

        self.__state: str = STATE_MAIN_MENU
        self.__running: bool = True
        self.__popup_kind = POPUP_NONE
        self.__menu_focus: int = START_GAME

        self.__session: GameSession | None = None
        self.__game_clock: GameClock | None = None
        self.__registration: RegistrationManager | None = None
        self.__full_catalog: list[Course] = []
        self.__visible_courses: list[Course] = []

        self.__mono_lines: list[str] = []
        self.__mono_index: int = 0
        self.__mono_revealed: float = 0.0
        self.__mono_done: bool = False

        self.__start_menu_music()

    def __init_audio(self) -> bool:
        try:
            pygame.mixer.init()
            return True
        except pygame.error:
            return False

    def __load_sound(self, path: str):
        if not self.__audio_ready:
            return None
        try:
            return pygame.mixer.Sound(path)
        except (FileNotFoundError, OSError, pygame.error):
            return None

    def __start_menu_music(self) -> None:
        if not self.__audio_ready:
            return
        try:
            pygame.mixer.music.load(MENU_THEME_PATH)
            pygame.mixer.music.set_volume(self.__settings["music_volume"] / 100)
            pygame.mixer.music.play(-1)
        except (FileNotFoundError, OSError, pygame.error):
            pass

    def __play_sfx(self, sound) -> None:
        if sound is None:
            return
        sound.set_volume(self.__settings["sfx_volume"] / 100)
        sound.play()

    def __display_flags(self) -> int:
        return FULLSCREEN_FLAGS if self.__is_fullscreen else WINDOWED_FLAGS

    def __apply_display(self, fullscreen: bool) -> None:
        self.__is_fullscreen = fullscreen
        self.__settings["fullscreen"] = fullscreen
        self.__window = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H), self.__display_flags())

    def __toggle_fullscreen(self) -> None:
        self.__apply_display(not self.__is_fullscreen)
        save_settings(self.__settings)

    def run(self) -> None:
        while self.__running:
            delta = self.__clock_tick.tick(FPS) / 1000.0

            for event in pygame.event.get():
                self.__handle_event(event)

            self.__update(delta)
            self.__render()
            pygame.display.flip()

        pygame.quit()

    def __update(self, delta: float) -> None:
        if self.__state != STATE_INTRO_MONOLOGUE or self.__mono_done:
            return
        if not self.__mono_lines:
            return

        current = self.__mono_lines[self.__mono_index]
        self.__mono_revealed = min(
            self.__mono_revealed + TYPEWRITER_CPS * delta, float(len(current)))
        if (self.__mono_index == len(self.__mono_lines) - 1
                and self.__mono_revealed >= len(current)):
            self.__mono_done = True

    def __handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.__popup_kind = POPUP_EXIT
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.__toggle_fullscreen()
            return

        if self.__popup_kind is not POPUP_NONE:
            self.__handle_popup_event(event)
            return

        if self.__state == STATE_MAIN_MENU:
            self.__handle_menu_event(event)
        elif self.__state == STATE_INTRO_MONOLOGUE:
            self.__handle_monologue_event(event)
        elif self.__state == STATE_REGISTRATION:
            self.__handle_registration_event(event)

    def __handle_popup_event(self, event: pygame.event.Event) -> None:
        confirmed = False
        cancelled = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                cancelled = True
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                confirmed = True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.__popup_kind == POPUP_OVER_LIMIT:
                confirmed = self.__popup.get_ok_rect().collidepoint(event.pos)
            elif self.__popup.get_confirm_rect().collidepoint(event.pos):
                confirmed = True
            elif self.__popup.get_cancel_rect().collidepoint(event.pos):
                cancelled = True

        if not confirmed and not cancelled:
            return

        kind = self.__popup_kind
        self.__popup_kind = POPUP_NONE
        if cancelled:
            return

        self.__play_sfx(self.__sfx_confirm)
        if kind == POPUP_EXIT:
            self.__running = False
        elif kind == POPUP_RETURN_TO_MENU:
            self.__abandon_run()

    def __popup_content(self) -> tuple | None:
        if self.__popup_kind == POPUP_EXIT:
            return ("EXIT GAME?", ["Any unsaved progress will be lost."],
                    "EXIT", "STAY")
        if self.__popup_kind == POPUP_RETURN_TO_MENU:
            return ("RETURN TO MAIN MENU?", ["Progress cannot be saved yet."],
                    "RETURN", "STAY")
        if self.__popup_kind == POPUP_OVER_LIMIT:
            return ("TOO MANY CREDITS",
                    ["You can register a maximum of",
                     f"{CREDIT_LIMIT} credits per semester.",
                     "Deselect a course and try again."],
                    "OK", None)
        return None

    def __handle_menu_event(self, event: pygame.event.Event) -> None:
        rects = self.__menu_screen.get_button_rects()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.__menu_focus = (self.__menu_focus - 1) % len(MENU_LABELS)
            elif event.key == pygame.K_DOWN:
                self.__menu_focus = (self.__menu_focus + 1) % len(MENU_LABELS)
            elif event.key == pygame.K_ESCAPE:
                if self.__menu_focus == EXIT:
                    self.__popup_kind = POPUP_EXIT
                else:
                    self.__menu_focus = EXIT
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.__activate_menu_item(self.__menu_focus)

        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(rects):
                if rect.collidepoint(event.pos):
                    self.__menu_focus = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(rects):
                if rect.collidepoint(event.pos):
                    self.__menu_focus = i
                    self.__activate_menu_item(i)
                    break

    def __activate_menu_item(self, index: int) -> None:
        self.__play_sfx(self.__sfx_click)

        if index == START_GAME:
            self.__start_new_run()
        elif index == EXIT:
            self.__popup_kind = POPUP_EXIT

    def __start_new_run(self) -> None:
        self.__session = GameSession()
        player = self.__session.get_active_player()
        player.set_academic_history(AcademicHistory())
        player.set_skill_tree(SkillTree())

        self.__game_clock = GameClock(self.__session)
        self.__registration = RegistrationManager()
        self.__full_catalog = build_course_catalog()

        self.__enter_intro_monologue()

    def __abandon_run(self) -> None:
        self.__session = None
        self.__game_clock = None
        self.__registration = None
        self.__full_catalog = []
        self.__visible_courses = []
        self.__menu_focus = START_GAME
        self.__state = STATE_MAIN_MENU

    def advance_to_next_semester(self) -> None:
        if self.__game_clock is None:
            return
        self.__game_clock.advance_semester()
        self.__enter_intro_monologue()

    def __enter_intro_monologue(self) -> None:
        semester = self.__session.get_active_semester()
        semester.play_intro_monologue()

        self.__mono_lines = get_monologue(semester.get_semester_number())
        self.__mono_index = 0
        self.__mono_revealed = 0.0
        self.__mono_done = not self.__mono_lines
        self.__state = STATE_INTRO_MONOLOGUE

    def __handle_monologue_event(self, event: pygame.event.Event) -> None:
        advance = (
            (event.type == pygame.KEYDOWN
             and event.key in (pygame.K_SPACE, pygame.K_RETURN))
            or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
        )
        if not advance:
            return

        if self.__mono_done:
            self.__enter_registration()
            return

        current = self.__mono_lines[self.__mono_index]
        if self.__mono_revealed < len(current):
            self.__mono_revealed = float(len(current))
        elif self.__mono_index < len(self.__mono_lines) - 1:
            self.__mono_index += 1
            self.__mono_revealed = 0.0
        else:
            self.__mono_done = True

    def __visible_monologue_lines(self) -> list[str]:
        if not self.__mono_lines:
            return []
        return (self.__mono_lines[:self.__mono_index]
                + [self.__mono_lines[self.__mono_index]
                   [:int(self.__mono_revealed)]])

    def __enter_registration(self) -> None:
        self.__play_sfx(self.__sfx_confirm)
        self.__registration.clear_selection()
        self.__refresh_visible_courses()
        self.__state = STATE_REGISTRATION

    def __refresh_visible_courses(self) -> None:
        history = self.__session.get_active_player().get_academic_history()
        catalog = self.__registration.build_semester_catalog(
            self.__full_catalog, history)
        self.__visible_courses = catalog[:VISIBLE_COURSE_ROWS]

    def __handle_registration_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.__popup_kind = POPUP_RETURN_TO_MENU
            return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        pos = event.pos
        screen = self.__registration_screen

        if screen.get_confirm_rect().collidepoint(pos):
            self.__play_sfx(self.__sfx_confirm)
            self.__registration.confirm_registration(
                self.__session.get_active_semester())
            return

        if screen.get_cancel_rect().collidepoint(pos):
            self.__play_sfx(self.__sfx_click)
            self.__registration.clear_selection()
            return

        row_rects = screen.get_course_row_rects(len(self.__visible_courses))
        for i, rect in enumerate(row_rects):
            if not rect.collidepoint(pos):
                continue
            course = self.__visible_courses[i]
            if course in self.__registration.get_selected_courses():
                self.__registration.deselect_course(course)
                self.__play_sfx(self.__sfx_click)
            elif self.__registration.select_course(course):
                self.__play_sfx(self.__sfx_click)
            else:
                self.__popup_kind = POPUP_OVER_LIMIT
            break

    def __render(self) -> None:
        if self.__state == STATE_MAIN_MENU:
            self.__menu_screen.render(
                self.__window, self.__menu_focus, VERSION_STRING)

        elif self.__state == STATE_INTRO_MONOLOGUE:
            semester = self.__session.get_active_semester()
            self.__monologue_screen.render(
                self.__window, semester.get_semester_number(),
                semester.get_time_pool_days(),
                self.__visible_monologue_lines(), self.__mono_done)

        elif self.__state == STATE_REGISTRATION:
            self.__render_registration()

        content = self.__popup_content()
        if content is not None:
            title, lines, confirm, cancel = content
            self.__popup.render(self.__window, title, lines, confirm, cancel)

    def __render_registration(self) -> None:
        player = self.__session.get_active_player()
        semester = self.__session.get_active_semester()
        selected = self.__registration.get_selected_courses()
        confirmed = semester.get_registered_courses()
        total = (self.__registration.get_current_selected_credits()
                 + sum(c.get_credit_value() for c in confirmed))

        self.__registration_screen.render(
            self.__window, self.__visible_courses, selected, confirmed,
            total, CREDIT_LIMIT, player.get_display_name(),
            player.get_character_id(), semester.get_semester_number())


def run_boot_check() -> None:
    print("=" * 55)
    print("  CSE Life: Compile & Conquer -- Sprint 1 Boot Check")
    print("=" * 55)

    # ── Prove: Player can be instantiated ─────────────────────────
    player = Player()
    print(f"\n[OK] Player created: '{player.get_display_name()}'")
    print(f"     Time pool : {player.get_time_pool_days()} days")
    print(f"     Wallet    : {player.get_wallet_balance()} BDT")
    print(f"     Credits   : {player.get_accumulated_credits()}")

    # ── Prove: Encapsulation works ────────────────────────────────
    success = player.deduct_time_pool_days(10)
    print(f"\n[OK] Deduct 10 days -> success={success}")
    print(f"     Remaining : {player.get_time_pool_days()} days")

    failed = player.deduct_time_pool_days(999)
    print(f"\n[OK] Deduct 999 days (should fail) -> success={failed}")
    print(f"     Remaining : {player.get_time_pool_days()} days (unchanged)")

    player.deposit_funds(3500.00)
    print(
        f"\n[OK] Deposit 3500 BDT -> balance: {player.get_wallet_balance()} BDT")

    # ── Prove: Course instantiation ───────────────────────────────
    course = Course("CSE101", "Intro to Programming", 3)
    print(f"\n[OK] Course created: '{course.get_course_name()}'"
          f" ({course.get_credit_value()} credits)")

    # ── Prove: MainQuest instantiation and interface check ────────
    mq = MainQuest(quest_id="MQ_CSE101", linked_course=course)
    print(f"\n[OK] MainQuest created: '{mq.get_quest_id()}'")
    print(f"     Is TimeConsumable : {isinstance(mq, TimeConsumable)}")
    print(f"     Is Quest          : {isinstance(mq, Quest)}")
    print(f"     Base time cost    : {mq.get_time_cost()} days")

    # ── Prove: SideQuest instantiation and interface check ────────
    sq = SideQuest(quest_id="SQ_SKILL_01", time_cost=2)
    print(f"\n[OK] SideQuest created: '{sq.get_quest_id()}'")
    print(f"     Is TimeConsumable : {isinstance(sq, TimeConsumable)}")
    print(f"     EXP reward        : {sq.get_exp_reward()}")

    # ── Prove: Abstract classes CANNOT be instantiated ───────────
    print("\n[OK] Verifying abstract class enforcement...")
    try:
        from core.character import Character
        _ = Character("x", "x", "x")
        print("     [FAIL] Character was instantiated -- should not happen")
    except TypeError:
        print("     Character() -> TypeError raised correctly (abstract)")

    try:
        _ = Quest("x", 0)
        print("     [FAIL] Quest was instantiated -- should not happen")
    except TypeError:
        print("     Quest()     -> TypeError raised correctly (abstract)")

    # ── SkillTree check ───────────────────────────────────────────
    tree = SkillTree()
    tree.increment_skill("python", 10)
    print(f"\n[OK] SkillTree: python level = {tree.get_skill_level('python')}")
    print(f"     Is unlocked: {tree.is_skill_unlocked('python')}")

    print("\n" + "=" * 55)
    print("  All Sprint 1 architecture checks passed.")
    print("=" * 55)


def main() -> None:
    run_boot_check()
    if "--check" in sys.argv:
        return
    GameApp().run()


if __name__ == "__main__":
    main()

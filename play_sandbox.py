"""
CSE Life: Compile & Conquer
play_sandbox.py  —  the walk-around testing ground (phase F7)

Run this to actually PLAY a level:

    python play_sandbox.py               # levels/campus_main.json
    python play_sandbox.py campus_lab    # any level id in levels/

It is a testing ground, not the game. It exists so Feature 4 and the
runtime half of Feature 5 can be proven end to end — tiles, collision,
smooth movement, speed-modifier easing, portals, prop rewards, NPC
conversations with real portraits, the real HUD — without touching
main.py, without a Player, and without a save file.

WHAT LIVES WHERE (Build Plan §0.7, Style Guide §6.1)

    engine/level_loader.py   the level and its collision grid
    ui/map_screen.py         draws the level; makes no decisions
    ui/interaction_prompt.py draws the [E] chip; makes no decisions
    engine/dialogue_manager.py + ui/dialog_box.py   the conversation
    ui/popup.py              the reward / notice modal
    engine/gate_evaluator.py weighs a locked door against the player (F8)
    ui/gate_notice.py        the requirement table + entry confirmation (F8)
    engine/game_clock.py     charges a paid entry through the ONE pipeline
    ui/hud.py                the real HUD, imported and never edited
    THIS FILE                the decisions: where the player may step,
                             which cell they face, what E does there,
                             what a reward is worth, and which gate applies

Movement and the fake player state sit here on purpose. A ui/ class
may not decide anything, and the sandbox must not construct real game
state, so the walking rules live in the runner where Abu Huraira can
lift PlayerWalker straight out at integration.

Created by Nangiba Tasnim (Dev 3), branch nangiba-temp-01.
"""
from __future__ import annotations

import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from content.level_registry import (          # noqa: E402  (after sys.path)
    BASE_PLAYER_SPEED_PX_S,
    FACINGS,
    SPEED_MODIFIER_BASE,
    SPEED_SMOOTH_RATE,
    TILE_SIZE_PX,
    get_menu_display_name,
    get_npc_display_name,
    get_npc_portrait_path,
)
from content.skill_tree_layout import build_view_model   # noqa: E402
from ui.skill_tree_screen import SkillTreeScreen         # noqa: E402
from ui.stats_screen import StatsScreen                  # noqa: E402
from content.level_schema import GateData               # noqa: E402
from engine.dialogue_manager import DialogueManager      # noqa: E402
from engine.game_clock import GameClock                  # noqa: E402
from engine.gate_evaluator import (                      # noqa: E402
    GateEntryAction,
    GateEvaluator,
)
from engine.level_loader import (                        # noqa: E402
    NPC_SEMESTER_EXPIRY_DAY,
    Level,
    LevelLoadError,
    load_level,
)
from ui.gate_notice import MODE_CONFIRM, MODE_LOCKED, GateNotice  # noqa: E402
from ui.hud import HUD                                   # noqa: E402
from ui.interaction_prompt import (                      # noqa: E402
    LABEL_ENTER,
    LABEL_EXAMINE,
    LABEL_LOCKED,
    LABEL_TALK,
    InteractionPrompt,
)
from ui.map_screen import MapScreen                      # noqa: E402
from ui.popup import (                                   # noqa: E402
    RESULT_CONFIRM,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    MessagePopup,
)

# -- palette --------------------------------------------------
# The runner draws only debug chrome, so it needs three colours from
# UI_STYLE_GUIDE.md §2. Declared here rather than imported from a
# screen (Build Plan §0.5).
PANEL_TAN = (231, 214, 189)
HEADER_TAN = (214, 196, 168)    # the boxed-footer fill behind dev text
BORDER_BROWN = (169, 130, 94)
TEXT_COFFEE = (74, 53, 39)
STAT_BROWN = (140, 110, 85)

# -------------------------------------------------------------
# LAYOUT + TUNING  (all in pixels / seconds)
# -------------------------------------------------------------
SCREEN_SIZE: Tuple[int, int] = (1280, 720)
WINDOWED_FLAGS = pygame.SCALED
FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN
FPS_CAP = 60

CELL = TILE_SIZE_PX             # 48 px, the grid contract

# The player collides as a 30 px box around their feet, not as a whole
# 48 px sprite: a full-cell hitbox makes a 1-cell gap impassable and
# feels like walking in armour. Four corners are tested, so a diagonal
# can never squeeze through a wall join.
HITBOX_PX = 30

WALK_FPS = 8.0                  # frames per second of the 4-frame cycle
WALK_FRAMES = 4
FOOTSTEP_PERIOD = 0.34          # seconds between footstep SFX while moving

DEFAULT_LEVEL_ID = "indoor_lecturehall"

# The fake player's starting figures — plausible mid-degree numbers so
# the HUD shows something other than zeroes. Every one is nudgeable
# from the debug keys.
START_SEMESTER = 3
START_CREDITS = 42
START_DAYS = 46
START_WALLET = 4500.0

SEMESTER_MIN, SEMESTER_MAX = 1, 12
CREDITS_MAX = 140
CREDITS_STEP = 3
DAYS_MAX = 80
WALLET_STEP = 500.0

DEBUG_LINE_PITCH = 18
PLATE_PAD = 8                   # padding inside a dev-text plate
PLATE_BORDER_W = 2

# The sandbox seeds two demo gates onto campus_main so a tester can cross
# every F8 branch with the debug keys, WITHOUT hand-editing the fixture
# (levels/campus_main.json must stay byte-identical — Build Plan §0.1).
# They live only in this runner, exactly like FakePlayerState; a real
# gate authored in the level editor drives the identical code path. Both
# sit on the open corridor at spawn row y=12 (verified walkable x=1..39).
DEMO_GATE_LEVEL = "campus_main"
DEMO_GATE_FREE_CELL = (12, 12)   # requirements only, no toll
DEMO_GATE_COST_CELL = (18, 12)   # requirements + a days/money toll


# ─────────────────────────────────────────────────────────────
# THE TEST DOUBLE
# ─────────────────────────────────────────────────────────────


class FakeSkillTree:
    """
    Stands in for `core.skill_tree.SkillTree`.

    Only the one method the gate evaluator reads is implemented, and
    levels are plain ints — this is a stub for exercising a UI, not a
    second skill system.
    """

    def __init__(self) -> None:
        self.__levels: Dict[str, int] = {}

    def get_skill_level(self, skill_id: str) -> int:
        """The level of one skill, 0 when it has never been raised."""
        return int(self.__levels.get(str(skill_id), 0))

    def increment_skill(self, skill_id: str, amount: int = 1) -> bool:
        """Raise a skill. Returns False for a non-positive amount."""
        if amount <= 0:
            return False
        key = str(skill_id)
        self.__levels[key] = self.__levels.get(key, 0) + int(amount)
        return True

    def get_all_levels(self) -> Dict[str, int]:
        """Copy of every skill this run has touched."""
        return dict(self.__levels)


class FakeAcademicHistory:
    """Stands in for `academic.academic_history.AcademicHistory`."""

    def __init__(self, completed: Optional[List[str]] = None) -> None:
        self.__completed: List[str] = list(completed or [])

    def get_completed_course_codes(self) -> List[str]:
        """Course codes this fake player has passed."""
        return list(self.__completed)


class FakePlayerState:
    """
    The sandbox's stand-in for `core.character.Player`.

    It implements exactly the seven read methods engine/gate_evaluator.py
    (F8) needs, and nothing else:

        get_current_semester()      get_accumulated_credits()
        get_wallet_balance()        get_time_pool_days()
        get_has_graduated()         get_skill_tree()
        get_academic_history()

    A REAL Player already satisfies the same seven, so F8's evaluator
    can be pointed at either without an adapter. Deliberately NOT a
    Player: constructing real game state in a level-testing harness
    would couple this runner to registration, the clock and the save
    format, and the point of the sandbox is that it couples to nothing.

    The mutators exist only for the debug keys.
    """

    def __init__(self) -> None:
        self.__semester: int = START_SEMESTER
        self.__credits: int = START_CREDITS
        self.__days: int = START_DAYS
        self.__wallet: float = START_WALLET
        self.__graduated: bool = False
        self.__skills: FakeSkillTree = FakeSkillTree()
        self.__history: FakeAcademicHistory = FakeAcademicHistory(
            ["CSE110", "CSE111", "MAT110"])

    # -- the seven the gate evaluator reads -------------------
    def get_current_semester(self) -> int:
        """Which of the 12 semesters this fake player is in."""
        return self.__semester

    def get_accumulated_credits(self) -> int:
        """Credits earned so far, out of the 140 needed to graduate."""
        return self.__credits

    def get_wallet_balance(self) -> float:
        """Money in BDT."""
        return self.__wallet

    def get_time_pool_days(self) -> int:
        """Days left in the 80-day semester pool."""
        return self.__days

    def get_has_graduated(self) -> bool:
        """Whether the degree is finished."""
        return self.__graduated

    def get_skill_tree(self) -> FakeSkillTree:
        """The skill store, for `get_skill_level(id)`."""
        return self.__skills

    def get_academic_history(self) -> FakeAcademicHistory:
        """The transcript, for `get_completed_course_codes()`."""
        return self.__history

    # -- the two the paid-entry action writes -----------------
    # These mirror core.character.Player.withdraw_funds() /
    # deduct_time_pool_days() byte-for-byte, so GateEntryAction charges
    # the fake exactly as it will charge a real Player at integration.
    def withdraw_funds(self, amount: float) -> bool:
        """Debit the wallet. False, unchanged, if short or negative."""
        if amount < 0:
            return False
        if self.__wallet >= amount:
            self.__wallet -= amount
            return True
        return False

    def deduct_time_pool_days(self, days: int) -> bool:
        """Debit the day pool. False, unchanged, if short or negative."""
        if days < 0:
            return False
        if self.__days >= days:
            self.__days -= days
            return True
        return False

    # -- debug mutators (sandbox only) ------------------------
    def nudge_semester(self, delta: int) -> None:
        """Step the semester, clamped to 1-12."""
        self.__semester = max(SEMESTER_MIN,
                              min(SEMESTER_MAX, self.__semester + delta))

    def nudge_credits(self, delta: int) -> None:
        """Step credits by whole courses, clamped to 0-140."""
        self.__credits = max(0, min(CREDITS_MAX, self.__credits + delta))

    def nudge_days(self, delta: int) -> None:
        """Step the day pool, clamped to 0-80."""
        self.__days = max(0, min(DAYS_MAX, self.__days + delta))

    def nudge_wallet(self, delta: float) -> None:
        """Step the wallet, never below zero."""
        self.__wallet = max(0.0, self.__wallet + delta)

    def add_money(self, amount: float) -> None:
        """Credit a prop reward."""
        self.__wallet = max(0.0, self.__wallet + float(amount))

    def add_skill(self, skill_id: str, amount: int) -> None:
        """Apply a prop's skill reward."""
        self.__skills.increment_skill(skill_id, amount)


class FakeSemester:
    """
    Stands in for `academic.semester.Semester`, for GameClock's day sync.

    GameClock deducts the day cost from BOTH the player and the active
    semester (the Iteration-14 fix in game_clock.py). The sandbox only
    shows the player's pool on the HUD, so this counter exists purely so
    the real GameClock has the second object it expects to touch.
    """

    def __init__(self, days: int = 80) -> None:
        self.__days: int = int(days)

    def deduct_time(self, days: int) -> None:
        """Debit the semester's own day pool, never below zero."""
        self.__days = max(0, self.__days - max(0, int(days)))

    def get_time_pool_days(self) -> int:
        """Days left in the semester pool."""
        return self.__days


class FakeGameSession:
    """
    The minimal stand-in for `engine.game_session.GameSession` that lets a
    REAL `engine.game_clock.GameClock` run a GateEntryAction through its
    single pipeline in the sandbox.

    F8 requires a paid entry to be charged through
    GameClock.process_time_consumable() and nowhere else
    (IMPLEMENTATION_PLAN §2.2). GameClock only ever calls interface
    methods on its session, so these four doubles are enough to exercise
    the real pipeline end to end without the sandbox constructing a real
    Player, Semester or save file — the same test-double philosophy as
    FakePlayerState.
    """

    def __init__(self, player: FakePlayerState,
                 semester: FakeSemester) -> None:
        self.__player: FakePlayerState = player
        self.__semester: FakeSemester = semester
        self.__global_days: int = 0
        self.__frozen: bool = False

    def get_active_player(self) -> FakePlayerState:
        """The player GameClock charges."""
        return self.__player

    def get_active_semester(self) -> FakeSemester:
        """The semester GameClock keeps in sync."""
        return self.__semester

    def get_is_frozen(self) -> bool:
        """Never frozen in the sandbox — there is no year cap to hit here."""
        return self.__frozen

    def increment_global_clock(self, days: int) -> None:
        """Advance the global career clock, matching GameSession's guard."""
        if not self.__frozen and days > 0:
            self.__global_days += int(days)

    def get_global_career_clock_days(self) -> int:
        """Total days charged this run — shown in the F1 debug overlay."""
        return self.__global_days


# ─────────────────────────────────────────────────────────────
# MOVEMENT
# ─────────────────────────────────────────────────────────────


class PlayerWalker:
    """
    Smooth pixel movement across the level's collision grid.

    Not grid-stepping: the position is a pair of floats, so the sprite
    rides between cells and stops flush against a wall instead of
    snapping to it. Three rules make it feel right:

      * the two axes are moved SEPARATELY, so walking into a wall at an
        angle slides along it rather than stopping dead
      * the destination is tested BEFORE it is committed, using four
        corners of a 30 px hitbox — collision is never resolved after
        the fact, so the player can never end up inside a rock
      * the per-cell speed modifier is EASED toward its target at
        SPEED_SMOOTH_RATE per second (Spec §5.2), so stepping onto mud
        slows you over about a third of a second instead of snapping

    Pure Python except for the Level it queries. Abu Huraira can lift
    this class straight into engine/ at integration.
    """

    def __init__(self, cell: Tuple[int, int]) -> None:
        """Stand the player in the centre of `cell`, facing down."""
        self.__x: float = cell[0] * CELL + CELL / 2.0
        self.__y: float = cell[1] * CELL + CELL / 2.0
        self.__facing: str = FACINGS[0]
        self.__factor: float = SPEED_MODIFIER_BASE
        self.__anim_time: float = 0.0
        self.__frame: int = 0
        self.__is_moving: bool = False

    # -- state getters ----------------------------------------
    def get_position(self) -> Tuple[float, float]:
        """The player's centre in world pixels."""
        return (self.__x, self.__y)

    def get_cell(self) -> Tuple[int, int]:
        """The cell the player's centre is standing in."""
        return (int(self.__x // CELL), int(self.__y // CELL))

    def get_facing(self) -> str:
        """One of FACINGS — down / left / right / up."""
        return self.__facing

    def get_frame(self) -> int:
        """The walk-cycle frame index, 0 while standing still."""
        return self.__frame

    def get_speed_factor(self) -> float:
        """The eased speed multiplier currently in effect."""
        return self.__factor

    def is_moving(self) -> bool:
        """True on any frame the player actually travelled."""
        return self.__is_moving

    def get_facing_cell(self) -> Tuple[int, int]:
        """
        The cell directly in front of the player — what E acts on.

        Interacting with the cell you FACE rather than the one you
        stand on is what lets an NPC be talked to without standing
        inside them, which the collision grid forbids anyway.
        """
        x, y = self.get_cell()
        step = {"down": (0, 1), "up": (0, -1),
                "left": (-1, 0), "right": (1, 0)}[self.__facing]
        return (x + step[0], y + step[1])

    # -- mutators ---------------------------------------------
    def place(self, cell: Tuple[int, int]) -> None:
        """Teleport to a cell — used on spawn and on portal arrival."""
        self.__x = cell[0] * CELL + CELL / 2.0
        self.__y = cell[1] * CELL + CELL / 2.0
        self.__factor = SPEED_MODIFIER_BASE
        self.__anim_time = 0.0
        self.__frame = 0
        self.__is_moving = False

    def update(self, dt: float, dx: float, dy: float, level: Level) -> None:
        """
        Advance one frame.

        dt : seconds since the last frame
        dx : -1 / 0 / +1 horizontal input
        dy : -1 / 0 / +1 vertical input
        """
        if dt <= 0.0:
            return

        length = math.hypot(dx, dy)
        if length > 0.0:
            dx, dy = dx / length, dy / length      # no diagonal speed bonus
            self.__facing = self.__facing_for(dx, dy)

        target = level.get_speed_modifier_at(*self.get_cell())
        self.__factor += (target - self.__factor) * \
            min(1.0, SPEED_SMOOTH_RATE * dt)

        speed = BASE_PLAYER_SPEED_PX_S * self.__factor * dt
        before = (self.__x, self.__y)
        if dx:
            step_x = self.__x + dx * speed
            if self.__can_stand(level, step_x, self.__y):
                self.__x = step_x
        if dy:
            step_y = self.__y + dy * speed
            if self.__can_stand(level, self.__x, step_y):
                self.__y = step_y

        self.__is_moving = (self.__x, self.__y) != before
        if self.__is_moving:
            self.__anim_time += dt
            self.__frame = int(self.__anim_time * WALK_FPS) % WALK_FRAMES
        else:
            self.__anim_time = 0.0
            self.__frame = 0

    # -- private helpers --------------------------------------
    @staticmethod
    def __facing_for(dx: float, dy: float) -> str:
        """Which way the sprite should look for this input vector."""
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        return "down" if dy > 0 else "up"

    @staticmethod
    def __can_stand(level: Level, cx: float, cy: float) -> bool:
        """
        Whether the hitbox centred on (cx, cy) fits on walkable cells.

        Off-grid never walks, so the level edge holds the player in
        without an author having to paint a wall around every map.
        """
        half = HITBOX_PX / 2.0
        for px, py in ((cx - half, cy - half), (cx + half, cy - half),
                       (cx - half, cy + half), (cx + half, cy + half)):
            if not level.is_walkable(int(px // CELL), int(py // CELL)):
                return False
        return True


# ─────────────────────────────────────────────────────────────
# THE SANDBOX
# ─────────────────────────────────────────────────────────────


class Sandbox:
    """
    The runner: owns the window, the level, the player and every
    decision the ui/ classes refuse to make.

    Conversation state (which chain each NPC is on) and prop trigger
    counts are keyed by (level_id, uid) so walking through a portal and
    back does not reset a conversation — the same bookkeeping the real
    save file will carry in `world.triggered_prop_uids` /
    `world.talked_npc_uids`.
    """

    def __init__(self, level_id: str = DEFAULT_LEVEL_ID) -> None:
        """Open the window, load the level, build every screen."""
        pygame.init()
        self.__is_fullscreen: bool = False
        self.__window: pygame.Surface = pygame.display.set_mode(
            SCREEN_SIZE, WINDOWED_FLAGS)
        pygame.display.set_caption("CSE Life — level sandbox")
        self.__clock: pygame.time.Clock = pygame.time.Clock()

        self.__map: MapScreen = MapScreen()
        self.__prompt: InteractionPrompt = InteractionPrompt()
        self.__hud: HUD = HUD()
        self.__popup: MessagePopup = MessagePopup(*SCREEN_SIZE)
        self.__gate_notice: GateNotice = GateNotice(*SCREEN_SIZE)
        self.__dialogue: DialogueManager = DialogueManager(*SCREEN_SIZE)
        self.__audio: Optional[Any] = self.__start_audio()

        self.__state: FakePlayerState = FakePlayerState()
        self.__level: Level = load_level(level_id)
        self.__walker: PlayerWalker = PlayerWalker(self.__level.get_spawn())
        self.__camera: Tuple[int, int] = (0, 0)

        # F8: the evaluator weighs a gate, and a real GameClock (over fake
        # session/semester doubles) charges a paid entry through the ONE
        # action pipeline — never by deducting days directly.
        self.__evaluator: GateEvaluator = GateEvaluator()
        self.__session: FakeGameSession = FakeGameSession(
            self.__state, FakeSemester())
        self.__game_clock: GameClock = GameClock(self.__session)
        self.__demo_gates: Dict[Tuple[str, Tuple[int, int]], GateData] = \
            self.__build_demo_gates()
        self.__gate_cleared: set = set()
        self.__pending_gate: Optional[Tuple[Tuple[int, int], GateData]] = None
        self.__gate_view: Dict[str, Any] = {}

        self.__chain_index: Dict[Tuple[str, str], int] = {}
        self.__trigger_count: Dict[Tuple[str, str], int] = {}
        self.__talking: Optional[Tuple[str, str]] = None
        self.__talking_chain: int = 0

        # Menu props (Feature: prop -> screen). Built once and reused:
        # both are pure renderers that take their data as arguments
        # (Style Guide §6.1), so keeping them alive costs one card of
        # geometry and no state.
        self.__menu_open: str = ""
        self.__skill_tree_screen: SkillTreeScreen = SkillTreeScreen()
        self.__stats_screen: StatsScreen = StatsScreen()

        self.__show_debug: bool = False
        self.__pulse: float = 0.0
        self.__footstep_timer: float = 0.0
        self.__last_cell: Tuple[int, int] = self.__walker.get_cell()
        self.__running: bool = True
        # The runner's own debug chrome is plain Courier, never the pixel
        # font: it is developer text, not part of the game's look, and
        # keeping it visually distinct stops it being mistaken for UI.
        self.__debug_font: pygame.font.Font = pygame.font.SysFont(
            "Courier", 13)
        self.__announce_level()

    # -- setup helpers ----------------------------------------
    def __start_audio(self) -> Optional[Any]:
        """
        Build an AudioManager if one can be built.

        Entirely optional (Build Plan §F1): assets/audio/ does not exist
        yet and the manager degrades to a no-op, so this is wrapped once
        here and every call site stays a plain `if self.__audio:`.
        """
        try:
            from engine.audio_manager import AudioManager
            return AudioManager()
        except (ImportError, OSError, pygame.error):
            return None

    def __announce_level(self) -> None:
        """Start the level's music, if there is any and audio exists."""
        if not self.__audio:
            return
        track = self.__level.get_level_id()
        if track in self.__audio.get_music_keys():
            self.__audio.play_music(track)

    # -- the loop ---------------------------------------------
    def run(self) -> None:
        """Run until the window closes, then report the missing art."""
        while self.__running:
            dt = self.__clock.tick(FPS_CAP) / 1000.0
            self.__pulse += dt
            self.__handle_events()
            self.__update(dt)
            self.__draw(dt)
            pygame.display.flip()
        self.__report_missing()
        pygame.quit()

    def __handle_events(self) -> None:
        """Route every event to exactly one owner, popup first (§4.7)."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.__running = False
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.__toggle_fullscreen()
                continue
            if self.__gate_notice.consumes_input():
                if self.__gate_notice.handle_event(event):
                    result = self.__gate_notice.take_result()
                    if result is not None:
                        self.__on_gate_result(result)
                continue
            if self.__popup.consumes_input():
                self.__popup.handle_event(event)
                continue
            if event.type != pygame.KEYDOWN:
                continue
            # An open menu owns the keyboard: ESC (or E) backs out of
            # it rather than quitting the sandbox, which is what every
            # other modal here already does.
            if self.__menu_open:
                if event.key in (pygame.K_ESCAPE, pygame.K_e):
                    self.__close_menu()
                continue
            if self.__dialogue.is_active():
                self.__handle_dialogue_key(event.key)
                continue
            self.__handle_world_key(event.key)

    def __handle_dialogue_key(self, key: int) -> None:
        """
        While talking: one key finishes the line, the next moves on.

        ESC leaves the conversation without consuming the rest of the
        chain, which is what a player expects from a skip button.
        """
        if key == pygame.K_ESCAPE:
            self.__end_conversation(finished=False)
            return
        if key not in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN,
                       pygame.K_KP_ENTER):
            return
        if self.__dialogue.skip_reveal():
            return
        if not self.__dialogue.advance():
            self.__end_conversation(finished=True)

    def __handle_world_key(self, key: int) -> None:
        """Keys that act on the world: interact, debug, quit."""
        if key == pygame.K_ESCAPE:
            self.__running = False
        elif key == pygame.K_e:
            self.__interact()
        elif key == pygame.K_F1:
            self.__show_debug = not self.__show_debug
        elif key == pygame.K_LEFTBRACKET:
            self.__state.nudge_semester(-1)
        elif key == pygame.K_RIGHTBRACKET:
            self.__state.nudge_semester(1)
        elif key == pygame.K_MINUS:
            self.__state.nudge_credits(-CREDITS_STEP)
        elif key == pygame.K_EQUALS:
            self.__state.nudge_credits(CREDITS_STEP)
        elif key == pygame.K_COMMA:
            self.__state.nudge_days(-1)
        elif key == pygame.K_PERIOD:
            self.__state.nudge_days(1)
        elif key == pygame.K_9:
            self.__state.nudge_wallet(-WALLET_STEP)
        elif key == pygame.K_0:
            self.__state.nudge_wallet(WALLET_STEP)

    def __toggle_fullscreen(self) -> None:
        """F11 — windowed <-> fullscreen, both SCALED (§4.1)."""
        self.__is_fullscreen = not self.__is_fullscreen
        self.__window = pygame.display.set_mode(
            SCREEN_SIZE,
            FULLSCREEN_FLAGS if self.__is_fullscreen else WINDOWED_FLAGS)

    def __update(self, dt: float) -> None:
        """Advance movement, the typewriter and the camera."""
        self.__dialogue.update(dt)
        if (self.__popup.consumes_input()
                or self.__gate_notice.consumes_input()
                or self.__dialogue.is_active()
                or self.__menu_open):
            self.__walker.update(dt, 0.0, 0.0, self.__level)
        else:
            dx, dy = self.__read_movement_input()
            self.__walker.update(dt, dx, dy, self.__level)
            self.__step_footsteps(dt)
            self.__check_cell_transition()
        self.__camera = self.__map.compute_camera(
            self.__level, self.__walker.get_position(), self.__window)

    @staticmethod
    def __read_movement_input() -> Tuple[float, float]:
        """WASD or the arrow keys, as a -1/0/+1 pair."""
        held = pygame.key.get_pressed()
        dx = float(held[pygame.K_RIGHT] or held[pygame.K_d]) - \
            float(held[pygame.K_LEFT] or held[pygame.K_a])
        dy = float(held[pygame.K_DOWN] or held[pygame.K_s]) - \
            float(held[pygame.K_UP] or held[pygame.K_w])
        return (dx, dy)

    def __step_footsteps(self, dt: float) -> None:
        """Fire the footstep SFX on a fixed cadence while walking."""
        if not self.__audio or not self.__walker.is_moving():
            self.__footstep_timer = 0.0
            return
        self.__footstep_timer += dt
        if self.__footstep_timer >= FOOTSTEP_PERIOD:
            self.__footstep_timer = 0.0
            self.__audio.play_sfx("footstep")

    # -- interaction ------------------------------------------
    def __interact(self) -> None:
        """
        E on the facing cell. Precedence: gate, NPC, portal, prop.

        The gate comes first because a locked door is a locked door
        whatever is behind it — F8 replaced the old "read the authored
        text" stub with the real evaluator + ui/gate_notice.py, which
        weighs the gate against the player and can let them through.
        """
        cell = self.__walker.get_facing_cell()
        gate = self.__gate_at(*cell)
        if gate is not None and not self.__gate_cleared_at(cell):
            self.__resolve_gate(cell, gate)
            return
        npc = self.__level.get_npc_at(*cell)
        if npc is not None and npc.get_interactable():
            self.__start_conversation(npc)
            return
        portal = self.__level.get_portal_at(*cell)
        if portal is not None:
            self.__travel(portal)
            return
        prop = self.__level.get_interactable_at(*cell)
        if prop is not None:
            self.__trigger_prop(prop)

    # -- gates (F8) -------------------------------------------
    def __build_demo_gates(self) -> Dict[Tuple[str, Tuple[int, int]], GateData]:
        """
        Two authored-in-code gates on campus_main, so every branch is
        reachable with the debug keys (Build Plan §F8).

        FREE gate: reach semester 4 and 45 credits and it opens with no
        toll — the "straight through" branch.  COST gate: reach semester 5
        and it opens but charges 10 days + 1,000 BDT, routed through
        GameClock — the confirmation branch.  Neither touches the fixture
        on disk; a gate authored in the editor drives the same code.
        """
        free_gate = GateData()
        free_gate.set_min_semester(4)
        free_gate.set_min_credits(45)
        free_gate.set_locked_title("LAB WING SEALED")
        free_gate.set_locked_lines([
            "The second-year lab wing stays shut for first-years.",
            "Earn your credits and come back."])

        cost_gate = GateData()
        cost_gate.set_min_semester(5)
        cost_gate.set_cost_days(10)
        cost_gate.set_cost_money(1000.0)
        cost_gate.set_locked_title("DEAN'S OFFICE")
        cost_gate.set_locked_lines([
            "The dean sees final-year students by appointment.",
            "An appointment is neither quick nor free."])

        return {
            (DEMO_GATE_LEVEL, DEMO_GATE_FREE_CELL): free_gate,
            (DEMO_GATE_LEVEL, DEMO_GATE_COST_CELL): cost_gate,
        }

    def __gate_at(self, x: int, y: int) -> Optional[GateData]:
        """
        The gate guarding a cell: the level's first, then a demo gate.

        A real level gate always wins, so authoring one in the editor
        overrides the sandbox scaffolding on the same cell.
        """
        level_gate = self.__level.get_gate_at(x, y)
        if level_gate is not None:
            return level_gate
        return self.__demo_gates.get(
            (self.__level.get_level_id(), (x, y)))

    def __gate_cleared_at(self, cell: Tuple[int, int]) -> bool:
        """True once the player has passed this cell's gate this run."""
        return (self.__level.get_level_id(), cell) in self.__gate_cleared

    def __resolve_gate(self, cell: Tuple[int, int], gate: GateData) -> bool:
        """
        Run the evaluator on a gate and act on the verdict.

        Returns True when the player must be held back (locked, or a paid
        door awaiting confirmation) and False when the door is open and
        free so the caller may let them pass. This is the single decision
        point both stepping onto a gate and pressing E route through.
        """
        result = self.__evaluator.evaluate(gate, self.__state)

        if not result.is_open():
            self.__open_gate_notice(gate, result, MODE_LOCKED)
            self.__play("gate_locked")
            return True

        if result.has_cost():
            if self.__evaluator.can_afford_costs(gate, self.__state):
                self.__pending_gate = (cell, gate)
                self.__open_gate_notice(gate, result, MODE_CONFIRM)
                return True
            # Requirements met, but the wallet or the day pool is short:
            # show it as a locked door naming the toll it cannot pay.
            self.__open_gate_notice(gate, result, MODE_LOCKED,
                                    unaffordable=True)
            self.__play("gate_locked")
            return True

        # Open and free — straight through.
        self.__gate_cleared.add((self.__level.get_level_id(), cell))
        self.__play("confirm")
        return False

    def __open_gate_notice(self, gate: GateData, result: Any, mode: str,
                           unaffordable: bool = False) -> None:
        """Stash the notice's drawn values (§6.1) and open it in `mode`."""
        flavour = list(gate.get_locked_lines())
        if unaffordable:
            days, money = result.get_costs()
            flavour = [f"You cannot pay the toll: {days} days, "
                       f"{money:,.0f} BDT."] + flavour
        self.__gate_view = {
            "title": gate.get_locked_title(),
            "rows": result.get_rows(),
            "flavour": flavour,
            "costs": result.get_costs(),
            "mode": mode,
        }
        self.__gate_notice.open(mode)

    def __on_gate_result(self, result: str) -> None:
        """
        Act on the button the gate notice reported.

        CONFIRM on a paid door charges the toll through
        GameClock.process_time_consumable() — the one pipeline — then
        marks the gate cleared and steps the player onto it. CANCEL (or a
        closed locked notice) simply drops any pending entry.
        """
        pending = self.__pending_gate
        self.__pending_gate = None
        if result != RESULT_CONFIRM or pending is None:
            return
        cell, gate = pending
        action = GateEntryAction.for_gate(gate)
        if action is not None:
            self.__game_clock.process_time_consumable(action)
        self.__gate_cleared.add((self.__level.get_level_id(), cell))
        self.__walker.place(cell)
        self.__last_cell = self.__walker.get_cell()
        self.__play("confirm")

    def __play(self, key: str) -> None:
        """Fire one SFX if audio is available — a guarded no-op otherwise."""
        if self.__audio:
            self.__audio.play_sfx(key)

    def __start_conversation(self, npc: Any) -> None:
        """
        Load the NPC's next dialog chain into the dialogue manager.

        The chain's emotion picks the 96x96 portrait through the level
        registry, which is the whole point of tagging chains with an
        emotion in the editor. A missing portrait is normal and draws
        the dialog box's placeholder block.
        """
        chains = npc.get_chains()
        if not chains:
            return
        key = (self.__level.get_level_id(), npc.get_uid())
        index = self.__chain_index.get(key, 0)
        if index >= len(chains):
            mode = npc.get_on_complete()
            if mode == "silent":
                return
            index = 0 if mode == "loop_all" else len(chains) - 1

        chain = chains[index]
        portrait = get_npc_portrait_path(npc.get_type_id(),
                                         chain.get_emotion())
        self.__dialogue.load_dialogue(list(chain.get_lines()), portrait)
        self.__dialogue.set_speaker(get_npc_display_name(npc.get_type_id()))
        self.__talking = key
        self.__talking_chain = index

    def __end_conversation(self, finished: bool) -> None:
        """
        Close the conversation, remembering the chain only if it ran to
        the end — a skipped chain replays next time, which is kinder
        than silently burning it.
        """
        if finished and self.__talking is not None:
            self.__chain_index[self.__talking] = self.__talking_chain + 1
        self.__talking = None
        self.__dialogue.load_dialogue([])
        self.__dialogue.advance()               # deactivates cleanly

    def __trigger_prop(self, prop: Any) -> None:
        """
        Pay out an interactable prop, respecting triggers_per_semester.

        The cap is the editor's per-prop limit; the engine's global
        per-semester cap (MAX_PROP_MONEY_PER_SEMESTER) is a separate
        rule and is not the sandbox's to enforce.

        A "menu" prop is checked FIRST and never counted: it is a door
        to a screen, not a payout, so spending a trigger on it would
        mean a registration desk you could only use once a term.
        """
        kind = prop.get_interaction_kind()
        if kind == "menu":
            self.__open_menu(prop.get_menu_id())
            return

        key = (self.__level.get_level_id(), prop.get_uid())
        used = self.__trigger_count.get(key, 0)
        allowed = prop.get_triggers_per_semester()
        if used >= allowed:
            self.__popup.open(
                "NOTHING LEFT",
                [f"You have used this {allowed} time(s) this semester.",
                 "It refreshes when the next term begins."], SEVERITY_INFO)
            if self.__audio:
                self.__audio.play_sfx("error")
            return

        self.__trigger_count[key] = used + 1
        amount = prop.get_amount()
        if kind == "money":
            self.__state.add_money(amount)
            body = [f"You found {amount:,.0f} BDT.",
                    f"Wallet: {self.__state.get_wallet_balance():,.0f} BDT",
                    f"Uses left: {allowed - used - 1}"]
        elif kind == "skill":
            skill_id = prop.get_skill_id() or "general"
            self.__state.add_skill(skill_id, int(amount))
            level = self.__state.get_skill_tree().get_skill_level(skill_id)
            body = [f"{skill_id.replace('_', ' ')} +{int(amount)}",
                    f"Now at level {level}.",
                    f"Uses left: {allowed - used - 1}"]
        else:
            body = ["There is nothing here to take."]
        self.__popup.open("FOUND SOMETHING", body, SEVERITY_INFO)
        if self.__audio:
            self.__audio.play_sfx("confirm")

    # -- menu props -------------------------------------------

    # Screens this sandbox can genuinely drive. Both are pure
    # renderers fed from FakePlayerState, so opening them here proves
    # the prop -> screen path end to end.
    #
    # The rest of MENU_REGISTRY needs real game state — a Player, a
    # catalog, a RegistrationManager, a save file — which this file is
    # forbidden to construct (see the module docstring). Those report
    # the binding instead of faking it, and get their real screen when
    # main.py's router adopts this dispatch.
    PLAYABLE_MENUS: tuple = ("skill_tree", "stats")

    def __open_menu(self, menu_id: str) -> None:
        """
        Open the screen a menu prop points at.

        An unset or unknown id is an authoring mistake, not a crash:
        the player is told, exactly as a portal with no target is.
        """
        if not menu_id:
            self.__popup.open("NOTHING HAPPENS",
                              ["This prop opens a menu,",
                               "but no menu was chosen for it."],
                              SEVERITY_INFO)
            return

        name = get_menu_display_name(menu_id)
        if menu_id in self.PLAYABLE_MENUS:
            self.__menu_open = menu_id
            if self.__audio:
                self.__audio.play_sfx("page_turn")
            return

        self.__popup.open(
            "MENU PROP",
            [f"This opens: {name}",
             f"(menu_id '{menu_id}')",
             "Needs real game state — wired at integration."],
            SEVERITY_INFO)
        if self.__audio:
            self.__audio.play_sfx("confirm")

    def __close_menu(self) -> None:
        """Leave the open menu and hand control back to the map."""
        self.__menu_open = ""
        if self.__audio:
            self.__audio.play_sfx("page_turn")

    def __render_menu(self) -> None:
        """Draw whichever menu is open, full-screen over the map."""
        if self.__menu_open == "skill_tree":
            self.__skill_tree_screen.render(
                self.__window,
                build_view_model(self.__state.get_skill_tree()))
        elif self.__menu_open == "stats":
            completed = self.__state.get_academic_history() \
                .get_completed_course_codes()
            self.__stats_screen.render(
                self.__window,
                display_name="Sandbox Student",
                semester=self.__state.get_current_semester(),
                days_remaining=self.__state.get_time_pool_days(),
                credits_earned=self.__state.get_accumulated_credits(),
                wallet=self.__state.get_wallet_balance(),
                # The SCREEN wants a {skill_id: level} map, not the tree
                # object — handing it the tree renders nothing and
                # raises on iteration.
                skills=self.__state.get_skill_tree().get_all_levels(),
                completed_count=len(completed))

    def __check_cell_transition(self) -> None:
        """
        React the frame the player steps into a NEW cell: a portal, or a
        gate.

        A portal travels (the classic RPG rule). A gate that is not open
        holds the player back — they are bounced to the cell they came
        from and shown the notice, so a locked door genuinely blocks the
        way instead of only talking about it. An open, free gate is
        cleared and walked through. Only on entry, never every frame, so a
        held-back player does not re-fire the notice while standing still.
        """
        cell = self.__walker.get_cell()
        if cell == self.__last_cell:
            return
        previous = self.__last_cell

        portal = self.__level.get_portal_at(*cell)
        if portal is not None:
            self.__last_cell = cell
            self.__travel(portal)
            return

        gate = self.__gate_at(*cell)
        if gate is not None and not self.__gate_cleared_at(cell):
            if self.__resolve_gate(cell, gate):     # held back
                self.__walker.place(previous)
                self.__last_cell = previous
                return

        self.__last_cell = cell

    def __travel(self, portal: Any) -> None:
        """
        Load the portal's target level and respawn at its target cell.

        A broken target is a level-authoring mistake, not a crash: the
        player is told and left exactly where they were.
        """
        target_id = portal.get_target_level_id()
        if not target_id:
            self.__popup.open("NOWHERE TO GO",
                              ["This doorway has no destination set.",
                               "Give it a target in the level editor."],
                              SEVERITY_WARNING)
            return
        try:
            level = load_level(target_id)
        except LevelLoadError as error:
            self.__popup.open("LEVEL NOT FOUND",
                              [f"Could not open '{target_id}'.",
                               str(error)[:48]], SEVERITY_WARNING)
            return

        self.__level = level
        spawn = portal.get_target_spawn() or level.get_spawn()
        if not level.is_walkable(*spawn):
            spawn = level.get_spawn()
        self.__walker.place(spawn)
        self.__last_cell = self.__walker.get_cell()
        self.__announce_level()
        if self.__audio:
            self.__audio.play_sfx("page_turn")

    # -- drawing ----------------------------------------------
    def __draw(self, dt: float) -> None:
        """One frame: map, prompt, HUD, dialogue, popup, debug."""
        self.__window.fill(PANEL_TAN)
        # A menu prop's screen replaces the world rather than sitting
        # over it: these are full-card screens with their own
        # background, and the HUD would collide with their titles.
        if self.__menu_open:
            self.__render_menu()
            self.__draw_hint()
            return
        self.__map.render(self.__window, self.__level, self.__camera,
                          self.__walker.get_position(),
                          self.__walker.get_facing(),
                          self.__walker.get_frame(), dt=dt)
        if (not self.__dialogue.is_active() and not self.__popup.is_open()
                and not self.__gate_notice.is_open()):
            self.__draw_prompt()
        self.__hud.render(self.__window,
                          time_pool=self.__state.get_time_pool_days(),
                          wallet=self.__state.get_wallet_balance(),
                          semester=self.__state.get_current_semester(),
                          credits=self.__state.get_accumulated_credits(),
                          location=self.__level.get_level_name())
        self.__dialogue.render(self.__window)
        self.__popup.render(self.__window)
        if self.__gate_notice.is_open():
            self.__gate_notice.render(
                self.__window, self.__gate_view.get("title", ""),
                self.__gate_view.get("rows", ()),
                self.__gate_view.get("flavour", ()),
                self.__gate_view.get("costs", (0, 0.0)),
                self.__gate_view.get("mode", MODE_LOCKED))
        if self.__show_debug:
            self.__draw_debug()
        self.__draw_hint()

    def __draw_prompt(self) -> None:
        """Float the [E] chip over whatever the player is facing."""
        cell = self.__walker.get_facing_cell()
        label, locked = self.__verb_for(cell)
        if not label:
            return
        self.__prompt.render(
            self.__window, label,
            self.__map.get_screen_rect_for_cell(*cell, self.__camera),
            self.__pulse, is_locked=locked,
            clamp_to=self.__map.get_viewport_rect(self.__window))

    def __verb_for(self, cell: Tuple[int, int]) -> Tuple[str, bool]:
        """
        (label, is_locked) for a cell — the same precedence __interact()
        uses, so the chip never promises something E will not do.
        """
        if (self.__gate_at(*cell) is not None
                and not self.__gate_cleared_at(cell)):
            return (LABEL_LOCKED, True)
        npc = self.__level.get_npc_at(*cell)
        if npc is not None and npc.get_interactable():
            return (LABEL_TALK, False)
        if self.__level.get_portal_at(*cell) is not None:
            return (LABEL_ENTER, False)
        if self.__level.get_interactable_at(*cell) is not None:
            return (LABEL_EXAMINE, False)
        return ("", False)

    def __draw_debug(self) -> None:
        """
        F1 overlay: everything needed to diagnose a level without a
        debugger — what is under the cursor, where the camera is, and
        what the eased speed factor has settled on.
        """
        cursor = self.__map.get_cell_for_screen_point(pygame.mouse.get_pos(),
                                                      self.__camera)
        prop = self.__level.get_prop_at(*cursor)
        npc = self.__level.get_npc_at(*cursor)
        zone = self.__level.get_zone_at(*cursor)
        cell = self.__walker.get_cell()
        lines = [
            f"level      {self.__level.get_level_id()}  "
            f"{self.__level.get_grid_size()}  "
            f"ambient {self.__level.get_ambient()}",
            f"player     cell {cell}  px "
            f"({self.__walker.get_position()[0]:.1f}, "
            f"{self.__walker.get_position()[1]:.1f})  "
            f"facing {self.__walker.get_facing()}",
            f"speed      x{self.__walker.get_speed_factor():.2f}  "
            f"target x{self.__level.get_speed_modifier_at(*cell):.2f}",
            f"camera     {self.__camera}",
            f"cursor     cell {cursor}  "
            f"walkable {self.__level.is_walkable(*cursor)}",
            f"under      prop {prop.get_uid() if prop else '-'}  "
            f"npc {npc.get_uid() if npc else '-'}  "
            f"zone {zone.get_uid() if zone else '-'}  "
            f"gate {'yes' if self.__gate_at(*cursor) else 'no'}",
            f"npc vis    {self.__npc_visibility(npc)}  "
            f"career +{self.__session.get_global_career_clock_days()}d "
            f"charged",
            f"fps        {self.__clock.get_fps():.0f}",
        ]
        self.__draw_plate(lines, (12, 54), TEXT_COFFEE)

    def __npc_visibility(self, npc_data: Any) -> str:
        """
        The three-way NPC visibility for the NPC under the cursor, or '-'.

        Reuses core.character.npc.NPC's 0.75-1.00 availability rule rather
        than reimplementing it (Build Plan §F8): a throwaway NPC answers
        the window question, and gate_evaluator folds that together with
        the effective min-semester into visible / semester_locked /
        window_closed.
        """
        if npc_data is None:
            return "-"
        from core.character.npc import NPC       # local: debug-only cost
        probe = NPC("probe", "", self.__level.get_level_id(),
                    NPC_SEMESTER_EXPIRY_DAY)
        ratio_ok = probe.is_within_availability_window(self.__state)
        return self.__evaluator.evaluate_npc_visibility(
            npc_data, self.__state, ratio_ok)

    def __draw_hint(self) -> None:
        """The muted bottom-right key hint every stub screen carries."""
        if self.__menu_open:
            text = (f"{get_menu_display_name(self.__menu_open).upper()}"
                    f"  |  ESC / E to close  |  F11")
        else:
            text = ("WASD move  |  E interact  |  F1 debug  |  [ ] sem  "
                    "- = cr  , . days  9 0 BDT  |  F11  |  ESC")
        width = self.__debug_font.size(text)[0] + PLATE_PAD * 2
        height = self.__debug_font.get_height() + PLATE_PAD * 2
        self.__draw_plate(
            [text],
            (self.__window.get_width() - width - 10,
             self.__window.get_height() - height - 6), STAT_BROWN)

    def __draw_plate(self, lines: List[str], topleft: Tuple[int, int],
                     colour: Tuple[int, int, int]) -> None:
        """
        Draw dev text on a flat tan plate with a 2 px border.

        Muted brown on a tile map is unreadable — grass and dirt are the
        same value as the text. A boxed footer fill (§2.1) is the pattern
        the style guide already uses for exactly this, so the debug text
        gets one rather than a drop shadow or an outline, neither of
        which §7 permits.
        """
        if not lines:
            return
        width = max(self.__debug_font.size(line)[0] for line in lines)
        height = DEBUG_LINE_PITCH * (len(lines) - 1) + \
            self.__debug_font.get_height()
        plate = pygame.Rect(topleft[0], topleft[1],
                            width + PLATE_PAD * 2, height + PLATE_PAD * 2)
        pygame.draw.rect(self.__window, HEADER_TAN, plate)
        pygame.draw.rect(self.__window, BORDER_BROWN, plate, PLATE_BORDER_W)
        for index, line in enumerate(lines):
            self.__window.blit(
                self.__debug_font.render(line, True, colour),
                (plate.x + PLATE_PAD,
                 plate.y + PLATE_PAD + index * DEBUG_LINE_PITCH))

    def __report_missing(self) -> None:
        """Print the artist's work queue on the way out (§5.2 step 4)."""
        missing = list(self.__map.get_missing_paths())
        if self.__audio:
            missing.extend(self.__audio.get_missing_paths())
        if not missing:
            return
        print("missing art / audio (Style Guide §5.2 queue):")
        for path in sorted(set(missing)):
            print(f"  {path}")


# -------------------------------------------------------------
# STUB TEST -- this file IS the testing ground; running it walks a
# real level. Abu Huraira deletes the whole runner when the real
# state manager takes over.
#   WASD / arrows -> walk (smooth pixels, eased speed modifiers)
#   E             -> interact with the cell you are facing
#   SPACE / ENTER -> advance dialogue (first press finishes the line)
#   [ / ]         -> semester down / up      - / =  -> credits
#   , / .         -> days                     9 / 0 -> wallet
#   F1            -> debug overlay
#   F11           -> toggle windowed / fullscreen
#   ESC           -> leave a conversation, close a notice, or quit
#
#   F8 gates (campus_main): walk right along the spawn row. The LAB WING
#   door at (12,12) refuses a first-year and opens at semester 4 / 45 cr;
#   the DEAN'S OFFICE at (18,12) opens at semester 5 and charges 10 days
#   + 1,000 BDT through GameClock. Nudge state with [ ] - = , . 9 0 to
#   cross every branch.
# -------------------------------------------------------------
if __name__ == "__main__":
    requested = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LEVEL_ID
    try:
        Sandbox(requested).run()
    except LevelLoadError as failure:
        print(f"could not open level '{requested}': {failure}")
        report = failure.get_report()
        if report is not None:
            for issue in report.get_blockers():
                print(f"  {issue.get_code()}: {issue.get_message()}")
        sys.exit(1)

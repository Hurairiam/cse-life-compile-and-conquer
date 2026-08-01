"""
engine/audio_manager.py
CSE Life: Compile & Conquer — Audio system, phase F1
─────────────────────────────────────────────────────────────
Feature 10. One class, AudioManager, owning music, the ambient
bed, sound effects and both volume levels.

LAYER NOTE (Build Plan §0.7). engine/ is a pygame-free layer
with exactly two owner-granted exceptions: the pre-existing
dialogue_manager.py, and this file. The owner ruled the audio
manager belongs with the other managers rather than in ui/,
because it is a system, not a screen. tests/test_layer_purity.py
whitelists both.

THIS FILE MAKES NO GAME DECISIONS. It never decides *when* to
play anything — callers do. It has no reference to the player,
the clock or any screen, and it holds no game state.

DEGRADES SILENTLY, ALWAYS. If the mixer will not initialise
(no sound device, a CI box, a locked audio server) every method
becomes a no-op and is_available() returns False. If a file is
missing, the load returns None and the key is recorded in
get_missing_paths(). The game never crashes, never blocks and
never waits on audio.

Created by: Nangiba Tasnim (Dev 3).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import pygame

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────
# Anchored to this file, never to the working directory — the same
# pattern content/level_registry.py uses. The game must find the same
# audio whether it was launched from the repo root, from an IDE or
# from the feature showcase.
# ─────────────────────────────────────────────────────────────

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUDIO_DIR: str = "assets/audio"
AUDIO_EXTENSIONS: Tuple[str, ...] = (".mp3", ".ogg", ".wav")


def resolve_asset(relative_path: str) -> str:
    """
    Turn a repo-relative asset path into an absolute one.

    Absolute paths and empty strings are handed back untouched.
    """
    if not relative_path or os.path.isabs(relative_path):
        return relative_path
    return os.path.join(PROJECT_ROOT, relative_path)


# ─────────────────────────────────────────────────────────────
# MIXER SETTINGS
# ─────────────────────────────────────────────────────────────

MIXER_FREQUENCY: int = 44100
MIXER_SIZE: int = -16
MIXER_CHANNELS: int = 2
MIXER_BUFFER: int = 512      # small buffer: UI clicks must feel immediate

AMBIENT_CHANNEL_ID: int = 0  # reserved so an SFX burst never steals the bed
RESERVED_CHANNELS: int = 1

VOLUME_MIN: int = 0          # matches settings_screen.py's VOLUME_MIN/MAX/STEP
VOLUME_MAX: int = 100
DEFAULT_MUSIC_VOLUME: int = 70
DEFAULT_SFX_VOLUME: int = 80

MUSIC_FADE_IN_MS: int = 600
MUSIC_FADE_OUT_MS: int = 400

# ─────────────────────────────────────────────────────────────
# REGISTRIES
# ─────────────────────────────────────────────────────────────
# The explicit fallback tables. Every path here is repo-relative and
# may not exist yet — see the placeholder queue in PHASELOG_F1.
# _discover_audio_files() below overrides and extends these at import
# time, so real files bind themselves the moment they land without
# anyone editing this module.
# ─────────────────────────────────────────────────────────────

MUSIC_TRACKS: Dict[str, str] = {
    "main_menu": "assets/audio/main_menu.mp3",
    "campus": "assets/audio/campus.mp3",
    "exam": "assets/audio/exam.mp3",
    "dialogue": "assets/audio/dialogue.mp3",
    "endgame": "assets/audio/endgame.mp3",
}

# Ambient beds layer *under* the music on a reserved channel. The keys
# mirror content/level_registry.py::AMBIENT_PRESETS so a level's declared
# ambient maps straight onto a bed with no translation table.
AMBIENT_BEDS: Dict[str, str] = {
    "morning": "assets/audio/ambient_morning.ogg",
    "day": "assets/audio/ambient_day.ogg",
    "evening": "assets/audio/ambient_evening.ogg",
    "night": "assets/audio/ambient_night.ogg",
}

SFX_FILES: Dict[str, str] = {
    "click": "assets/audio/click.wav",
    "confirm": "assets/audio/confirm.wav",
    "cancel": "assets/audio/cancel.wav",
    "page_turn": "assets/audio/page_turn.wav",
    "pass": "assets/audio/pass.wav",
    "fail": "assets/audio/fail.wav",
    "error": "assets/audio/error.wav",
    "select": "assets/audio/select.wav",
    "dialogue_blip": "assets/audio/dialogue_blip.wav",
    "gate_locked": "assets/audio/gate_locked.wav",
    "level_up": "assets/audio/level_up.wav",
    "footstep": "assets/audio/footstep.wav",
}

# What each key should sound like. Feeds the PHASELOG placeholder queue
# so the artist gets a brief, not just a list of filenames.
AUDIO_DESCRIPTIONS: Dict[str, str] = {
    "main_menu": "warm looping title theme, unhurried, pixel-era chiptune",
    "campus": "light exploration loop, daytime campus, low-key",
    "exam": "tense low pulse under the countdown, no melody",
    "dialogue": "soft sparse bed for conversation scenes",
    "endgame": "ceremonial closing theme, resolves rather than loops",
    "morning": "birds and distant footsteps, thin and bright",
    "day": "campus murmur, wind, occasional far-off chatter",
    "evening": "crickets starting, quieter murmur, warmer",
    "night": "still air, crickets, very low hum",
    "click": "short dry UI tick",
    "confirm": "rising two-note affirmative blip",
    "cancel": "falling two-note dismissive blip",
    "page_turn": "paper flick for advancing dialogue",
    "pass": "bright ascending arpeggio, exam passed",
    "fail": "flat descending pair, exam failed, not comedic",
    "error": "short buzz for a blocked action",
    "select": "soft tick for moving keyboard focus",
    "dialogue_blip": "very short blip per few revealed characters",
    "gate_locked": "dull thud plus a lock click",
    "level_up": "skill increase chime, brighter than confirm",
    "footstep": "single muted step on grass or road",
}


def _discover_audio_files() -> Dict[str, Dict[str, str]]:
    """
    Scan `assets/audio/` once at import and sort what is there into
    music, ambient and SFX.

    Naming rules, in order:
        `music_<name>` / `ambient_<name>` / `sfx_<name>`  -> that table
        a stem already in SFX_FILES or AMBIENT_BEDS       -> that table
        anything else                                     -> music

    A discovered file overrides the fallback path for a key it matches,
    so `campus.ogg` binds to the `campus` key even though the table
    names `campus.mp3`. Unknown stems auto-register, which is how the
    owner's five tracks will bind themselves with no code edit.

    A missing directory is normal, not an error: it returns three empty
    tables and every registry keeps its declared fallback paths.
    """
    found: Dict[str, Dict[str, str]] = {"music": {}, "ambient": {}, "sfx": {}}
    directory = resolve_asset(AUDIO_DIR)
    try:
        entries = sorted(os.listdir(directory))
    except (FileNotFoundError, NotADirectoryError, OSError):
        return found

    for entry in entries:
        stem, extension = os.path.splitext(entry)
        if extension.lower() not in AUDIO_EXTENSIONS:
            continue
        key = stem.lower()
        relative = f"{AUDIO_DIR}/{entry}"
        if key.startswith("music_"):
            found["music"][key[6:]] = relative
        elif key.startswith("ambient_"):
            found["ambient"][key[8:]] = relative
        elif key.startswith("sfx_"):
            found["sfx"][key[4:]] = relative
        elif key in SFX_FILES:
            found["sfx"][key] = relative
        elif key in AMBIENT_BEDS:
            found["ambient"][key] = relative
        else:
            found["music"][key] = relative
    return found


DISCOVERED_AUDIO: Dict[str, Dict[str, str]] = _discover_audio_files()
MUSIC_TRACKS.update(DISCOVERED_AUDIO["music"])
AMBIENT_BEDS.update(DISCOVERED_AUDIO["ambient"])
SFX_FILES.update(DISCOVERED_AUDIO["sfx"])


def describe(key: str) -> str:
    """What a track or effect should sound like, for the artist's queue."""
    return AUDIO_DESCRIPTIONS.get(key, "unspecified")


class AudioManager:
    """
    Music, ambient bed, sound effects and volume, behind one object.

    Every public method is safe to call at any time, in any order, on
    any machine. Nothing here raises: a dead mixer, an unknown key and
    a missing file are all ordinary states that return False or None.
    That is what lets every screen take an optional
    `audio: AudioManager | None = None` and guard one attribute rather
    than wrapping calls in try/except.
    """

    def __init__(self, music_volume: int = DEFAULT_MUSIC_VOLUME,
                 sfx_volume: int = DEFAULT_SFX_VOLUME) -> None:
        """
        Bring up the mixer and set the starting volumes (0-100).

        A mixer that will not start is not an error — the manager comes
        up unavailable and every later call becomes a no-op.
        """
        self.__available: bool = False
        self.__music_volume: int = self.__clamp(music_volume)
        self.__sfx_volume: int = self.__clamp(sfx_volume)
        self.__muted: bool = False
        self.__pre_mute: Tuple[int, int] = (self.__music_volume,
                                            self.__sfx_volume)
        self.__current_track: Optional[str] = None
        self.__current_ambient: Optional[str] = None
        self.__music_paused: bool = False
        self.__sfx_cache: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.__ambient_cache: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.__ambient_channel: Optional[pygame.mixer.Channel] = None
        self.__missing: List[str] = []

        self.__available = self.__start_mixer()
        if self.__available:
            self.__apply_music_volume()

    # ── mixer bring-up ───────────────────────────────────────
    def __start_mixer(self) -> bool:
        """
        Initialise the mixer, reserving one channel for the ambient bed.

        Returns False on any failure. pre_init() only takes effect
        before init(), so the two are always called together here.
        """
        try:
            pygame.mixer.pre_init(MIXER_FREQUENCY, MIXER_SIZE,
                                  MIXER_CHANNELS, MIXER_BUFFER)
            pygame.mixer.init()
            if pygame.mixer.get_init() is None:
                return False
            pygame.mixer.set_reserved(RESERVED_CHANNELS)
            self.__ambient_channel = pygame.mixer.Channel(AMBIENT_CHANNEL_ID)
            return True
        except (pygame.error, AttributeError, OSError):
            return False

    def is_available(self) -> bool:
        """True when the mixer came up and audio can actually play."""
        return self.__available

    # ── volume ───────────────────────────────────────────────
    def __clamp(self, value: int) -> int:
        """Force any input into 0-100. Never raises, never rejects."""
        try:
            number = int(value)
        except (TypeError, ValueError):
            return VOLUME_MIN
        return max(VOLUME_MIN, min(VOLUME_MAX, number))

    def get_music_volume(self) -> int:
        """Current music volume, 0-100."""
        return self.__music_volume

    def get_sfx_volume(self) -> int:
        """Current effects volume, 0-100."""
        return self.__sfx_volume

    def set_music_volume(self, value: int) -> bool:
        """
        Set the music volume (0-100) and apply it immediately.

        Returns True when the stored level changed. Out-of-range input
        is clamped rather than refused — this is driven by a slider.
        """
        clamped = self.__clamp(value)
        changed = clamped != self.__music_volume
        self.__music_volume = clamped
        self.__muted = False
        self.__apply_music_volume()
        return changed

    def set_sfx_volume(self, value: int) -> bool:
        """
        Set the effects volume (0-100) and apply it immediately to every
        cached Sound and to the ambient bed.
        """
        clamped = self.__clamp(value)
        changed = clamped != self.__sfx_volume
        self.__sfx_volume = clamped
        self.__muted = False
        self.__apply_sfx_volume()
        return changed

    def __apply_music_volume(self) -> None:
        """Push the music level at the mixer."""
        if not self.__available:
            return
        try:
            pygame.mixer.music.set_volume(self.__music_volume / VOLUME_MAX)
        except (pygame.error, AttributeError):
            pass

    def __apply_sfx_volume(self) -> None:
        """Push the effects level at every cached Sound and the bed."""
        if not self.__available:
            return
        level = self.__sfx_volume / VOLUME_MAX
        for sound in self.__sfx_cache.values():
            if sound is not None:
                try:
                    sound.set_volume(level)
                except (pygame.error, AttributeError):
                    pass
        for sound in self.__ambient_cache.values():
            if sound is not None:
                try:
                    sound.set_volume(level)
                except (pygame.error, AttributeError):
                    pass

    def mute_all(self) -> bool:
        """
        Silence music and effects, remembering the levels to restore.

        Muting twice does not overwrite the remembered levels with
        zeroes, which is the bug this guard exists to prevent.
        """
        if self.__muted:
            return False
        self.__pre_mute = (self.__music_volume, self.__sfx_volume)
        self.__music_volume = VOLUME_MIN
        self.__sfx_volume = VOLUME_MIN
        self.__muted = True
        self.__apply_music_volume()
        self.__apply_sfx_volume()
        return True

    def unmute_all(self) -> bool:
        """Restore the volumes captured by the last mute_all()."""
        if not self.__muted:
            return False
        self.__music_volume, self.__sfx_volume = self.__pre_mute
        self.__muted = False
        self.__apply_music_volume()
        self.__apply_sfx_volume()
        return True

    def is_muted(self) -> bool:
        """True while mute_all() is in effect."""
        return self.__muted

    # ── music ────────────────────────────────────────────────
    def play_music(self, key: str, loop: bool = True,
                   fade_ms: int = MUSIC_FADE_IN_MS) -> bool:
        """
        Stream the track registered under `key`.

        Re-requesting the track already playing is a deliberate no-op
        returning False, so moving between screens that share a track
        never restarts the loop mid-bar.
        """
        if not self.__available or key not in MUSIC_TRACKS:
            return False
        if key == self.__current_track and not self.__music_paused:
            return False
        path = resolve_asset(MUSIC_TRACKS[key])
        try:
            # [AUDIO PLACEHOLDER: assets/audio/<key>.mp3 — see
            #  AUDIO_DESCRIPTIONS[key] for what this track should sound
            #  like. A missing file is not an error: the manager simply
            #  reports it through get_missing_paths().]
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.__music_volume / VOLUME_MAX)
            pygame.mixer.music.play(-1 if loop else 0, fade_ms=max(0, fade_ms))
        except (FileNotFoundError, OSError, pygame.error):
            self.__record_missing(MUSIC_TRACKS[key])
            self.__current_track = None
            return False
        self.__current_track = key
        self.__music_paused = False
        return True

    def stop_music(self, fade_ms: int = MUSIC_FADE_OUT_MS) -> bool:
        """Fade the music out and forget the current track."""
        if not self.__available:
            return False
        try:
            if fade_ms > 0:
                pygame.mixer.music.fadeout(fade_ms)
            else:
                pygame.mixer.music.stop()
        except (pygame.error, AttributeError):
            return False
        self.__current_track = None
        self.__music_paused = False
        return True

    def pause_music(self) -> bool:
        """Pause the music where it is, keeping the track loaded."""
        if not self.__available or self.__current_track is None \
                or self.__music_paused:
            return False
        try:
            pygame.mixer.music.pause()
        except (pygame.error, AttributeError):
            return False
        self.__music_paused = True
        return True

    def resume_music(self) -> bool:
        """Resume a paused track."""
        if not self.__available or not self.__music_paused:
            return False
        try:
            pygame.mixer.music.unpause()
        except (pygame.error, AttributeError):
            return False
        self.__music_paused = False
        return True

    def get_current_track(self) -> Optional[str]:
        """The music key currently loaded, or None."""
        return self.__current_track

    def is_music_paused(self) -> bool:
        """True while the music is paused rather than stopped."""
        return self.__music_paused

    # ── ambient bed ──────────────────────────────────────────
    def play_ambient(self, key: str, loop: bool = True) -> bool:
        """
        Start an ambient bed on the reserved channel, under the music.

        Re-requesting the bed already playing is a no-op, for the same
        reason play_music() no-ops: crossing a level boundary into the
        same ambient must not restart it.
        """
        if not self.__available or key not in AMBIENT_BEDS:
            return False
        if key == self.__current_ambient:
            return False
        sound = self.__load_ambient(key)
        if sound is None or self.__ambient_channel is None:
            return False
        try:
            self.__ambient_channel.play(sound, loops=-1 if loop else 0)
        except (pygame.error, AttributeError):
            return False
        self.__current_ambient = key
        return True

    def stop_ambient(self) -> bool:
        """Stop the ambient bed and free the reserved channel."""
        if not self.__available or self.__ambient_channel is None:
            return False
        try:
            self.__ambient_channel.stop()
        except (pygame.error, AttributeError):
            return False
        self.__current_ambient = None
        return True

    def get_current_ambient(self) -> Optional[str]:
        """The ambient key currently playing, or None."""
        return self.__current_ambient

    # ── sound effects ────────────────────────────────────────
    def play_sfx(self, key: str) -> bool:
        """
        Fire a one-shot effect.

        Returns False for an unknown key, a missing file or a dead
        mixer. Callers never branch on the result — they call and move
        on, which is what keeps audio optional everywhere.
        """
        if not self.__available or key not in SFX_FILES:
            return False
        sound = self.__load_sfx(key)
        if sound is None:
            return False
        try:
            sound.play()
        except (pygame.error, AttributeError):
            return False
        return True

    def stop_all_sfx(self) -> bool:
        """Cut every non-reserved channel — used when a screen tears down."""
        if not self.__available:
            return False
        try:
            for index in range(RESERVED_CHANNELS, pygame.mixer.get_num_channels()):
                pygame.mixer.Channel(index).stop()
        except (pygame.error, AttributeError):
            return False
        return True

    # ── loading ──────────────────────────────────────────────
    def __load_sfx(self, key: str) -> Optional[pygame.mixer.Sound]:
        """
        Load and cache one effect, or cache None when it is missing.

        Caching the failure matters: a footstep fires many times a
        second, and re-probing a missing file on every step would hit
        the filesystem hundreds of times a minute for nothing.
        """
        if key in self.__sfx_cache:
            return self.__sfx_cache[key]
        relative = SFX_FILES[key]
        try:
            # [AUDIO PLACEHOLDER: assets/audio/<key>.wav — see
            #  AUDIO_DESCRIPTIONS[key]. Missing files degrade to silence
            #  and are listed by get_missing_paths().]
            sound: Optional[pygame.mixer.Sound] = pygame.mixer.Sound(
                resolve_asset(relative))
            if sound is not None:
                sound.set_volume(self.__sfx_volume / VOLUME_MAX)
        except (FileNotFoundError, OSError, pygame.error):
            self.__record_missing(relative)
            sound = None
        self.__sfx_cache[key] = sound
        return sound

    def __load_ambient(self, key: str) -> Optional[pygame.mixer.Sound]:
        """Load and cache one ambient bed, or cache None when missing."""
        if key in self.__ambient_cache:
            return self.__ambient_cache[key]
        relative = AMBIENT_BEDS[key]
        try:
            # [AUDIO PLACEHOLDER: assets/audio/ambient_<key>.ogg — see
            #  AUDIO_DESCRIPTIONS[key]. Missing beds degrade to silence.]
            sound: Optional[pygame.mixer.Sound] = pygame.mixer.Sound(
                resolve_asset(relative))
            if sound is not None:
                sound.set_volume(self.__sfx_volume / VOLUME_MAX)
        except (FileNotFoundError, OSError, pygame.error):
            self.__record_missing(relative)
            sound = None
        self.__ambient_cache[key] = sound
        return sound

    def __record_missing(self, relative_path: str) -> None:
        """Remember a path that failed to load, once."""
        if relative_path not in self.__missing:
            self.__missing.append(relative_path)

    # ── reporting ────────────────────────────────────────────
    def get_missing_paths(self) -> List[str]:
        """
        Every registered path that is not on disk.

        Probed with os.path.isfile rather than by loading, so this is
        accurate before anything has played and works with no mixer at
        all. Union'd with whatever actually failed to load at runtime.
        """
        missing: List[str] = []
        for table in (MUSIC_TRACKS, AMBIENT_BEDS, SFX_FILES):
            for relative in table.values():
                if not os.path.isfile(resolve_asset(relative)) \
                        and relative not in missing:
                    missing.append(relative)
        for relative in self.__missing:
            if relative not in missing:
                missing.append(relative)
        return missing

    def is_loaded(self, key: str) -> bool:
        """True when the file registered under `key` exists on disk."""
        for table in (MUSIC_TRACKS, AMBIENT_BEDS, SFX_FILES):
            if key in table:
                return os.path.isfile(resolve_asset(table[key]))
        return False

    def get_path(self, key: str) -> Optional[str]:
        """The repo-relative path registered under `key`, or None."""
        for table in (MUSIC_TRACKS, AMBIENT_BEDS, SFX_FILES):
            if key in table:
                return table[key]
        return None

    def get_music_keys(self) -> List[str]:
        """Every registered music key, in a stable order."""
        return sorted(MUSIC_TRACKS)

    def get_ambient_keys(self) -> List[str]:
        """Every registered ambient key, in a stable order."""
        return sorted(AMBIENT_BEDS)

    def get_sfx_keys(self) -> List[str]:
        """Every registered effect key, in a stable order."""
        return sorted(SFX_FILES)

    def shutdown(self) -> None:
        """Stop everything and release the mixer. Safe to call twice."""
        if not self.__available:
            return
        self.stop_music(0)
        self.stop_ambient()
        try:
            pygame.mixer.quit()
        except (pygame.error, AttributeError):
            pass
        self.__available = False


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   1-9, 0     -> fire the numbered sound effect
#   M          -> start / stop the highlighted music track
#   [ / ]      -> previous / next music track
#   A          -> start / stop the highlighted ambient bed
#   ; / '      -> previous / next ambient bed
#   LEFT/RIGHT -> music volume down / up (step 5)
#   UP/DOWN    -> sfx volume up / down (step 5)
#   N          -> mute / unmute everything
#   F11        -> toggle windowed / fullscreen
#   ESC        -> quit
#
# The palette below is declared HERE rather than at module top on
# purpose: engine/ must not carry UI constants, and importing ui/
# from engine/ would invert the layering. This block is a demo
# runner, not library code.
# -------------------------------------------------------------
if __name__ == "__main__":
    # -- palette (stub test only; UI_STYLE_GUIDE §2, verbatim) --
    PANEL_TAN = (231, 214, 189)
    CARD_TAN = (240, 228, 208)
    HEADER_TAN = (214, 196, 168)
    BORDER_BROWN = (169, 130, 94)
    TEXT_COFFEE = (74, 53, 39)
    TITLE_SLATE = (45, 58, 71)
    CREDIT_HL = (155, 110, 70)
    STAT_BROWN = (140, 110, 85)
    BAR_TRACK = (214, 196, 168)
    ROW_WHITE = (247, 243, 236)
    ROW_BLUE = (120, 150, 190)
    ROW_GREEN = (150, 180, 125)
    BAR_RED = (199, 123, 107)
    PLACEHOLDER = (196, 178, 150)
    HINT_BROWN = (150, 125, 100)

    # LAYOUT (stub test only)
    CARD_MARGIN = 24
    CARD_PAD = 14
    CORNER_LEN = 22
    ROW_H = 38
    ROW_PITCH = 44
    BAR_W = 420
    BAR_H = 16

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Audio manager test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    def _font(size: int) -> pygame.font.Font:
        """The same font safety net every screen uses (§3)."""
        try:
            return pygame.font.Font(
                resolve_asset("assets/ui/PressStart2P.ttf"), size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    font_title = _font(26)
    font_body = _font(12)
    font_label = _font(10)

    audio = AudioManager()
    music_keys = audio.get_music_keys()
    ambient_keys = audio.get_ambient_keys()
    sfx_keys = audio.get_sfx_keys()
    music_index = 0
    ambient_index = 0
    log_line = "READY"

    CARD = pygame.Rect(CARD_MARGIN, CARD_MARGIN, SIZE[0] - CARD_MARGIN * 2,
                       SIZE[1] - CARD_MARGIN * 2)
    INNER = CARD.inflate(-CARD_PAD * 2, -CARD_PAD * 2)

    SFX_HOTKEYS = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                   pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8,
                   pygame.K_9, pygame.K_0]

    def draw_card(surface: pygame.Surface) -> None:
        """The signature framed card with corner bracket marks (§4.2)."""
        pygame.draw.rect(surface, CARD_TAN, CARD)
        pygame.draw.rect(surface, BORDER_BROWN, CARD, 3)
        pygame.draw.rect(surface, BORDER_BROWN, INNER, 1)
        n = CORNER_LEN
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((INNER.left, INNER.top), (n, 0), (0, n)),
                ((INNER.right, INNER.top), (-n, 0), (0, n)),
                ((INNER.left, INNER.bottom), (n, 0), (0, -n)),
                ((INNER.right, INNER.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(surface, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(surface, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 3)

    def draw_status_row(surface: pygame.Surface, rect: pygame.Rect, key: str,
                        prefix: str, highlighted: bool, playing: bool) -> None:
        """
        One registry row: key, load status, and the mandatory
        PLACEHOLDER square where the file is missing (§5.2).
        """
        loaded = audio.is_loaded(key)
        if playing:
            fill = ROW_GREEN
        elif highlighted:
            fill = ROW_BLUE
        else:
            fill = ROW_WHITE
        pygame.draw.rect(surface, fill, rect)
        pygame.draw.rect(surface, BORDER_BROWN, rect, 2)

        swatch = pygame.Rect(rect.x + 8, rect.centery - 11, 22, 22)
        if loaded:
            pygame.draw.rect(surface, ROW_GREEN, swatch)
        else:
            pygame.draw.rect(surface, PLACEHOLDER, swatch)
        pygame.draw.rect(surface, BORDER_BROWN, swatch, 1)

        colour = ROW_WHITE if (playing or highlighted) else TEXT_COFFEE
        label = font_label.render(f"{prefix}{key.upper()}", True, colour)
        surface.blit(label, (rect.x + 40,
                             rect.centery - label.get_height() // 2))
        status = "LOADED" if loaded else "MISSING"
        # On a blue/green row the red MISSING would be unreadable, so the
        # row colour carries the emphasis instead of the text colour.
        if playing or highlighted:
            status_colour = ROW_WHITE
        else:
            status_colour = TEXT_COFFEE if loaded else BAR_RED
        rendered = font_label.render(status, True, status_colour)
        surface.blit(rendered, (rect.right - rendered.get_width() - 10,
                                rect.centery - rendered.get_height() // 2))

    def draw_bar(surface: pygame.Surface, x: int, y: int, label: str,
                 value: int) -> None:
        """A labelled 0-100 volume bar in the house style (§4.5)."""
        surface.blit(font_label.render(label, True, CREDIT_HL), (x, y))
        track = pygame.Rect(x, y + 18, BAR_W, BAR_H)
        pygame.draw.rect(surface, BAR_TRACK, track)
        filled = int(BAR_W * value / VOLUME_MAX)
        if filled > 0:
            pygame.draw.rect(surface, ROW_BLUE,
                             pygame.Rect(track.x, track.y, filled, BAR_H))
        pygame.draw.rect(surface, BORDER_BROWN, track, 2)
        rendered = font_body.render(f"{value}", True, TEXT_COFFEE)
        surface.blit(rendered, (track.right + 12, track.y))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    flags = (FULLSCREEN_FLAGS if is_fullscreen
                             else WINDOWED_FLAGS)
                    window = pygame.display.set_mode(SIZE, flags)
                elif event.key in SFX_HOTKEYS:
                    index = SFX_HOTKEYS.index(event.key)
                    if index < len(sfx_keys):
                        key = sfx_keys[index]
                        ok = audio.play_sfx(key)
                        log_line = f"SFX {key.upper()} -> " \
                                   f"{'PLAYED' if ok else 'SILENT'}"
                elif event.key == pygame.K_LEFTBRACKET and music_keys:
                    music_index = (music_index - 1) % len(music_keys)
                elif event.key == pygame.K_RIGHTBRACKET and music_keys:
                    music_index = (music_index + 1) % len(music_keys)
                elif event.key == pygame.K_m and music_keys:
                    key = music_keys[music_index]
                    if audio.get_current_track() == key:
                        audio.stop_music()
                        log_line = f"MUSIC {key.upper()} -> STOPPED"
                    else:
                        ok = audio.play_music(key)
                        log_line = f"MUSIC {key.upper()} -> " \
                                   f"{'PLAYING' if ok else 'SILENT'}"
                elif event.key == pygame.K_SEMICOLON and ambient_keys:
                    ambient_index = (ambient_index - 1) % len(ambient_keys)
                elif event.key == pygame.K_QUOTE and ambient_keys:
                    ambient_index = (ambient_index + 1) % len(ambient_keys)
                elif event.key == pygame.K_a and ambient_keys:
                    key = ambient_keys[ambient_index]
                    if audio.get_current_ambient() == key:
                        audio.stop_ambient()
                        log_line = f"AMBIENT {key.upper()} -> STOPPED"
                    else:
                        ok = audio.play_ambient(key)
                        log_line = f"AMBIENT {key.upper()} -> " \
                                   f"{'PLAYING' if ok else 'SILENT'}"
                elif event.key == pygame.K_LEFT:
                    audio.set_music_volume(audio.get_music_volume() - 5)
                elif event.key == pygame.K_RIGHT:
                    audio.set_music_volume(audio.get_music_volume() + 5)
                elif event.key == pygame.K_UP:
                    audio.set_sfx_volume(audio.get_sfx_volume() + 5)
                elif event.key == pygame.K_DOWN:
                    audio.set_sfx_volume(audio.get_sfx_volume() - 5)
                elif event.key == pygame.K_n:
                    if audio.is_muted():
                        audio.unmute_all()
                        log_line = "UNMUTED"
                    else:
                        audio.mute_all()
                        log_line = "MUTED"

        window.fill(PANEL_TAN)
        draw_card(window)

        window.blit(font_title.render("AUDIO MANAGER", True, TITLE_SLATE),
                    (60, 56))
        state = "MIXER READY" if audio.is_available() else "MIXER UNAVAILABLE"
        window.blit(font_body.render(state, True,
                                     TEXT_COFFEE if audio.is_available()
                                     else BAR_RED), (60, 100))
        missing = audio.get_missing_paths()
        window.blit(font_label.render(
            f"{len(missing)} REGISTERED FILES MISSING FROM assets/audio/",
            True, STAT_BROWN), (60, 126))

        # Discovery can register any number of tracks, so the list is a
        # window that follows the selection rather than a fixed slice.
        MUSIC_ROWS = 5
        first = max(0, min(music_index - MUSIC_ROWS // 2,
                           len(music_keys) - MUSIC_ROWS))
        window.blit(font_label.render(
            f"MUSIC  [ / ]  M PLAY-STOP     "
            f"{music_index + 1} / {len(music_keys)}", True,
            CREDIT_HL), (60, 158))
        for i, key in enumerate(music_keys[first:first + MUSIC_ROWS]):
            draw_status_row(window, pygame.Rect(60, 178 + i * ROW_PITCH,
                                                380, ROW_H), key, "",
                            first + i == music_index,
                            audio.get_current_track() == key)

        window.blit(font_label.render("AMBIENT  ; / '  A PLAY-STOP", True,
                                      CREDIT_HL), (60, 410))
        for i, key in enumerate(ambient_keys[:4]):
            draw_status_row(window, pygame.Rect(60, 430 + i * ROW_PITCH,
                                                380, ROW_H), key, "",
                            i == ambient_index,
                            audio.get_current_ambient() == key)

        window.blit(font_label.render("SOUND EFFECTS  (NUMBER KEYS)", True,
                                      CREDIT_HL), (480, 158))
        for i, key in enumerate(sfx_keys[:12]):
            column = i // 6
            row = i % 6
            draw_status_row(window,
                            pygame.Rect(480 + column * 366,
                                        178 + row * ROW_PITCH, 350, ROW_H),
                            key, f"{i + 1}. " if i < 10 else "   ",
                            False, False)

        draw_bar(window, 480, 456, "MUSIC VOLUME  (LEFT / RIGHT)",
                 audio.get_music_volume())
        draw_bar(window, 480, 516, "SFX VOLUME  (UP / DOWN)",
                 audio.get_sfx_volume())
        window.blit(font_body.render(
            f"MUTED: {'YES' if audio.is_muted() else 'NO'}   (N)", True,
            TEXT_COFFEE), (480, 576))
        window.blit(font_body.render(log_line, True, CREDIT_HL), (480, 606))

        hint = hint_font.render(
            "Numbers = SFX  |  M music  |  A ambient  |  arrows volume"
            "  |  N mute  |  F11  |  ESC", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        pygame.display.flip()
        clock.tick(60)

    audio.shutdown()
    pygame.quit()

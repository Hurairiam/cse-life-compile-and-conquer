"""
engine/settings_store.py
Player preferences (volumes, display mode, text speed) in one JSON file
at the project root. NOT a save slot — this survives across playthroughs
and is per-installation, so it is deliberately outside saves/ and is
gitignored alongside it.

Every setting here must be BOTH persisted and re-applied at launch, and
the two are separate jobs. load() only fills ctx; the systems that
consume a setting are pushed by apply_all() (audio, text speed) and
apply_display() (the window). AppContext STAGE 2 calls both, before the
first frame — a preference that is loaded but never applied looks
exactly like a preference that was never saved.

Text speed is applied by rebinding the module constant TYPEWRITER_CPS in
BOTH ui.dialog_box and engine.dialogue_manager. dialogue_manager does
`from ui.dialog_box import TYPEWRITER_CPS`, which copies the value into
its own namespace, so patching one of the two is not enough.
"""
from __future__ import annotations

import json
import os

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH: str = os.path.join(PROJECT_ROOT, "settings.json")
TMP_SUFFIX: str = ".tmp"

DEFAULTS = {
    "music_volume": 70,
    "sfx_volume": 80,
    "fullscreen": False,
    "text_speed": "NORMAL",
}

VALID_SPEEDS = ("SLOW", "NORMAL", "FAST")

VOLUME_MIN = 0
VOLUME_MAX = 100


def __clamp_volume(value, fallback: int) -> int:
    """
    Force a stored volume into 0-100, or fall back.

    The fallback is passed in rather than hardcoded so an unreadable
    sfx_volume lands on the sfx default and an unreadable music_volume
    lands on the music one. DEFAULTS is the only place those numbers
    are written down.
    """
    try:
        return max(VOLUME_MIN, min(VOLUME_MAX, int(value)))
    except (TypeError, ValueError):
        return fallback


def load() -> dict:
    """
    Read settings.json. Any failure returns a full DEFAULTS copy.

    Missing file, truncated file, hand-edited JSON, wrong encoding and a
    payload that is not an object all land on the defaults rather than
    raising — a bad preferences file must never stop the game starting.
    Each key is also read independently, so one unusable value does not
    discard the other three.
    """
    data = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError, UnicodeDecodeError):
        return data
    if not isinstance(raw, dict):
        return data
    data["music_volume"] = __clamp_volume(raw.get("music_volume"),
                                          DEFAULTS["music_volume"])
    data["sfx_volume"] = __clamp_volume(raw.get("sfx_volume"),
                                        DEFAULTS["sfx_volume"])
    data["fullscreen"] = bool(raw.get("fullscreen", DEFAULTS["fullscreen"]))
    speed = raw.get("text_speed", DEFAULTS["text_speed"])
    data["text_speed"] = (speed if speed in VALID_SPEEDS
                          else DEFAULTS["text_speed"])
    return data


def save(data: dict) -> bool:
    """
    Write settings.json atomically. Returns False instead of raising.

    Same three-step write engine/save_manager.py uses, and for the same
    reason: serialise to a string FIRST so an unserialisable value fails
    before any file is touched, write a temp file with flush + fsync,
    then os.replace() — atomic on Windows and POSIX. Writing the real
    file in place would mean a crash mid-write leaves a truncated
    settings.json, which load() can only read as "defaults", silently
    discarding every preference the player had set.
    """
    try:
        text = json.dumps({k: data.get(k, DEFAULTS[k]) for k in DEFAULTS},
                          indent=2)
    except (TypeError, ValueError):
        return False

    tmp_path = SETTINGS_PATH + TMP_SUFFIX
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, SETTINGS_PATH)
    except OSError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False
    return True


def apply_text_speed(label: str) -> int:
    """Push the chosen speed into both typewriter modules. Returns the cps."""
    from ui.settings_screen import cps_for_speed
    cps = cps_for_speed(label)
    try:
        import ui.dialog_box as dialog_box
        import engine.dialogue_manager as dialogue_manager
        dialog_box.TYPEWRITER_CPS = cps
        dialogue_manager.TYPEWRITER_CPS = cps
    except (ImportError, AttributeError):
        pass
    return cps


def apply_display(ctx) -> None:
    """
    Re-open the window in the mode ctx.is_fullscreen asks for.

    Deliberately NOT folded into apply_all(): the settings screen's BACK
    button reverts through apply_all(), and re-opening the window on
    every cancel would flash the display for a mode that was never
    committed. The two callers that do want it — APPLY, and AppContext
    STAGE 2 at launch — ask for it by name.

    A no-op when no display surface exists yet, so importing or building
    an AppContext headlessly cannot conjure a window out of nothing.
    """
    import pygame
    if pygame.display.get_surface() is None:
        return
    flags = pygame.FULLSCREEN if ctx.is_fullscreen else 0
    try:
        pygame.display.set_mode((ctx.screen_w, ctx.screen_h), flags)
    except pygame.error:
        pass


def apply_all(ctx) -> None:
    """
    Push every ctx setting into the systems that consume it.

    Audio and text speed only — the window is apply_display()'s job, for
    the reason given there.
    """
    if ctx.audio is not None:
        ctx.audio.set_music_volume(ctx.music_volume)
        ctx.audio.set_sfx_volume(ctx.sfx_volume)
    apply_text_speed(ctx.text_speed)


def capture(ctx) -> dict:
    return {
        "music_volume": ctx.music_volume,
        "sfx_volume": ctx.sfx_volume,
        "fullscreen": ctx.is_fullscreen,
        "text_speed": ctx.text_speed,
    }

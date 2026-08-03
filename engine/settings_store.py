"""
engine/settings_store.py
Player preferences (volumes, display mode, text speed) in one JSON file
at the project root. NOT a save slot — this survives across playthroughs.

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

DEFAULTS = {
    "music_volume": 70,
    "sfx_volume": 80,
    "fullscreen": False,
    "text_speed": "NORMAL",
}

VALID_SPEEDS = ("SLOW", "NORMAL", "FAST")


def __clamp_volume(value) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 70


def load() -> dict:
    """Read settings.json. Any failure returns a full DEFAULTS copy."""
    data = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        return data
    if not isinstance(raw, dict):
        return data
    data["music_volume"] = __clamp_volume(raw.get("music_volume", 70))
    data["sfx_volume"] = __clamp_volume(raw.get("sfx_volume", 80))
    data["fullscreen"] = bool(raw.get("fullscreen", False))
    speed = raw.get("text_speed", "NORMAL")
    data["text_speed"] = speed if speed in VALID_SPEEDS else "NORMAL"
    return data


def save(data: dict) -> bool:
    """Write settings.json. Returns False instead of raising."""
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as handle:
            json.dump({k: data.get(k, DEFAULTS[k]) for k in DEFAULTS},
                      handle, indent=2)
        return True
    except (OSError, TypeError, ValueError):
        return False


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
    """Re-open the window in the mode ctx.is_fullscreen asks for."""
    import pygame
    flags = pygame.FULLSCREEN if ctx.is_fullscreen else 0
    try:
        pygame.display.set_mode((ctx.screen_w, ctx.screen_h), flags)
    except pygame.error:
        pass


def apply_all(ctx) -> None:
    """Push every ctx setting into the systems that consume it."""
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

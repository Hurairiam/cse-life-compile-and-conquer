"""
engine/soundtrack.py
CSE Life: Compile & Conquer — what plays where
─────────────────────────────────────────────────────────────
The single place that decides which track is playing. Three rules,
owner-specified:

    "exploration"  the ten outdoor/indoor campus levels
    "menu"         player_room AND every menu or screen
    (silence)      the exam, and any level not on the list

WHY THIS IS ITS OWN FILE
────────────────────────
The alternative was a `play_music` line in each of the thirteen
`engine/states/*.py` modules, all of which belong to the Sprint 4 state
refactor and are shared. Routing every decision through one module the
router calls once per screen change means those files stay untouched
and the rules can be read in one sitting.

WHERE THE LEVEL RULE ACTUALLY LIVES
───────────────────────────────────
Not here. A level's track is `meta.music` in its own JSON, which the
level editor already exposes as the MUSIC TRACK field — so an author
retunes a level without opening Python. LEVEL_TRACKS below is only the
seed used to stamp those files, kept so the intended mapping stays
readable and so a level whose meta was never set still does the right
thing. A level with no music is SILENT by design: the owner's rule is
that exploration music plays nowhere except the listed levels.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from engine.screen_manager import ScreenState

EXPLORATION_TRACK: str = "exploration"
MENU_TRACK: str = "menu"
CLICK_SFX: str = "click"

# player_room is the player's own room, so it carries the menu track
# rather than the exploration one. Every OTHER level explores.
MENU_LEVELS: frozenset = frozenset({"player_room"})

# Only the exceptions are listed. A new level made in the editor gets
# the exploration track for free, which is the right default for a
# game whose levels are all campus locations.
LEVEL_TRACKS: Dict[str, str] = {
    level_id: MENU_TRACK for level_id in MENU_LEVELS
}

# The one screen that must be quiet. The countdown carries the tension
# on its own; a bed under it fights the timer.
SILENT_STATES: frozenset = frozenset({ScreenState.EXAM})


def track_for_level(level_id: str) -> str:
    """
    The track a level id should play.

    Exploration is the default: every level is a campus location the
    player walks around, so listing them all would be a list that goes
    stale the moment somebody adds a map. Only the exceptions are named.
    """
    return LEVEL_TRACKS.get(str(level_id), EXPLORATION_TRACK)


def apply_for_state(ctx: Any, state: Optional[ScreenState]) -> None:
    """
    Set the music for a screen. Called once per screen change.

    EXPLORATION is deliberately skipped: its track depends on which map
    is loaded, so exploration.py sets it from enter() and again after
    portal travel. Handling it here too would fire the same decision
    twice per screen change.
    """
    if state is None or state is ScreenState.EXPLORATION:
        return
    if state in SILENT_STATES:
        silence(ctx)
        return
    play(ctx, MENU_TRACK)


def apply_for_level(ctx: Any) -> None:
    """
    Set the music for whatever level is loaded.

    The level's own `meta.music` wins; LEVEL_TRACKS is the fallback for
    a level whose meta was never stamped. Re-requesting the track
    already playing is a no-op inside AudioManager, so walking a portal
    between two exploration levels does not restart the loop mid-bar.
    """
    level = getattr(ctx, "level", None)
    declared = ""
    if level is not None:
        try:
            declared = (level.get_music() or "").strip()
        except AttributeError:
            declared = ""
    track = declared or track_for_level(getattr(ctx, "level_id", ""))
    play(ctx, track) if track else silence(ctx)


def play(ctx: Any, track: str) -> None:
    """Start a track, or fall silent when the key is empty/unknown."""
    if not track:
        silence(ctx)
        return
    ctx.play_music(track)


def silence(ctx: Any) -> None:
    """
    Stop the music outright.

    ctx.play_music("") would be a no-op rather than a stop -- an
    unknown key is ignored by AudioManager -- so silence has to reach
    the manager directly. Guarded because ctx.audio is None whenever
    the mixer failed to start, which is a supported way to run.
    """
    audio = getattr(ctx, "audio", None)
    if audio is not None:
        audio.stop_music()


# ─────────────────────────────────────────────────────────────
# THE CLICK SOUND
# ─────────────────────────────────────────────────────────────
# Owner rule: it fires when something is ACTUALLY HIT, by mouse or by
# keyboard. That rules out watching raw events -- a MOUSEBUTTONDOWN on
# empty canvas is not a hit, and a keypress that moves the player is
# not either.
#
# It needs no new detection, because the game already tells us. Roughly
# fifty play_sfx() calls sit at exactly the moments a control responds:
# a button pressed, a row selected, a chip toggled, an action refused.
# They fire the same way whether the input was a click or a key, which
# is precisely the rule. Those keys have had no sound file since the
# old audio was removed, so audio_manager points them at the click file
# and the behaviour falls out.
#
# See INTERACTION_SFX_KEYS in engine/audio_manager.py for the list, and
# for the two keys deliberately left out (footstep, dialogue_blip) --
# those repeat continuously and would turn into a rattle.
# ─────────────────────────────────────────────────────────────



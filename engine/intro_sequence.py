"""
engine/intro_sequence.py
The intro's brain: which beat is running, what comes next, where it sits.

Phase 18 §4. NO PYGAME IMPORT — this is the piece the tests drive
headless and the piece engine/states/registration.py calls, so it stays
cheap to import.

WHY A NEW MODULE
────────────────
`origin/main` carries the Sprint 4 state refactor, and engine/states/*,
state_router.py, app_context.py and screen_manager.py are shared with
three other developers. So the logic lives here and the shared files
carry call sites instead of branches — the pattern
engine/dialogue_flow.py and engine/menu_prop.py already document. A new
module cannot produce a merge conflict.

STATE LIVES ON ctx, NOT IN app_context.py
─────────────────────────────────────────
    ctx.intro_beat : str | None
        The beat currently on screen, or None when the intro is not
        running.

Read defensively with getattr(), the way ctx.dialogue_choices already
is. app_context.py is shared and one more field there is one more
conflict surface for nothing.

NEVER SAVED. `engine/save_bridge.py::capture()` does not read
`intro_beat` and must not: a save written mid-intro would reload into a
tutorial the player has already sat through, and the intro is a
first-run event, not a game state.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from engine.screen_manager import ScreenState

# The three beat ids. Duplicated from content/intro_script.py's contract
# (§3) rather than imported, because that file is Ayesha's and may not
# have landed yet — this module must import cleanly without it. The
# guarded import that DOES read her file is in engine/states/intro.py.
BEAT_BRIEFING: str = "briefing"
BEAT_ROOM_TOUR: str = "room_tour"
BEAT_CAMPUS_TOUR: str = "campus_tour"

BEAT_IDS: tuple = (BEAT_BRIEFING, BEAT_ROOM_TOUR, BEAT_CAMPUS_TOUR)

# §4's staging table — the ONLY place the three beats' physical setup is
# written down. The two cells were checked against the live level files:
#
#   player_room   10x10, spawn (4, 5), Roya (4, 3) — walkable, no prop,
#                 no NPC. The bed is at (2, 3) and the vase at (4, 2) is
#                 solid, so she must not move up.
#   lecture_hall  19x16, spawn (9, 14), Roya col 9 / row 8 — walkable,
#                 no prop, no NPC, no portal, no gate, and nothing
#                 overhanging from the row above. Prof. Rahman stands at
#                 (8, 4), four rows further up, and is visible in
#                 semester 1.
#
# CELLS ARE (x, y) — (column, row).
#
# WHERE SHE STANDS IN THE LECTURE HALL, AND WHY THAT CELL (owner ruling:
# fully in frame, centred, no prop under her, clear of the dialogue
# card). Three constraints, and the hall only satisfies all three in one
# column:
#
#   ROW. Rows 6, 7, 9, 10 and 12 are the desk rows — a prop sits on
#   every even column. Rows 5, 8 and 11 are the clear aisles. Row 11 is
#   behind the dialogue card and row 5 is most of the way up the hall,
#   so row 8 is the aisle that is both empty and in shot.
#
#   COLUMN. The spawn is column 9 and the camera centres on the player,
#   so column 9 is dead centre of the screen — 0px off. It is also the
#   central aisle, which is why it is free on every row.
#
#   THE CARD. The lecture hall spawn is on the bottom row, so the camera
#   clamps and everything is drawn low. Her 72px sprite hangs 24px above
#   its own cell, and the dialogue card is Rect(46, 524, 1188, 168) —
#   she is drawn at Rect(604, 404, 72, 72), which clears the top of the
#   card by 48px. She was at (9, 12) originally and was rendered
#   ENTIRELY behind the card; nobody ever saw her.
#
# If she is moved again: each row is 48px, her sprite bottom must stay
# above y=524, and an odd column will put her inside a desk.
STAGES: Dict[str, Dict[str, Any]] = {
    BEAT_BRIEFING: {
        "level_id": None,          # None = the black stage, no map loaded
        "npc_cell": None,
        "facing": "down",
        "fade_out": False,
    },
    BEAT_ROOM_TOUR: {
        "level_id": "player_room",
        "npc_cell": (4, 3),
        "facing": "down",
        "fade_out": False,
    },
    BEAT_CAMPUS_TOUR: {
        "level_id": "lecture_hall",
        "npc_cell": (9, 8),           # (x, y) = column 9, row 8
        "facing": "down",
        "fade_out": True,          # the only beat that fades on the way out
    },
}

# The NPC whose art the cutscenes stage. NPC_REGISTRY type id.
STAGE_NPC_TYPE: str = "roya"

# BEATS THE PLAYER HAS TO WALK INTO. beat id -> the level whose doorway
# starts it.
#
# Beat 2 used to hand straight to beat 3, which meant the tutorial moved
# the player from their room to the lecture hall for them. It does not
# any more: after_room_tour() arms beat 3 and returns EXPLORATION, so
# the player leaves their room, crosses the campus and finds the lecture
# hall on their own, and beat 3 starts the moment they set foot in it.
#
# A table rather than an `if`, for the same reason STAGES is one: a
# second walk-in beat is a row here and no new code anywhere.
WALK_IN_TRIGGERS: Dict[str, str] = {
    BEAT_CAMPUS_TOUR: "lecture_hall",
}


# ── arming ─────────────────────────────────────────────────────

def arm(ctx: Any) -> None:
    """
    Start the intro at beat 1.

    Called by START GAME, AFTER save_bridge.new_game() — that rebuilds
    the session and would drop anything set before it.
    """
    ctx.intro_beat = BEAT_BRIEFING


def finish(ctx: Any) -> None:
    """
    The intro is over, or was abandoned.

    Called at the end of beat 3 and from main_menu.enter(). That second
    caller is the leak guard (§4): start a new game, back out of name
    entry to the title, then load a save, and `intro_beat` would still
    be armed — registration would route into a dead intro. Every route
    back to the title clears it.
    """
    ctx.intro_beat = None


def is_running(ctx: Any) -> bool:
    """True while a beat is armed."""
    return getattr(ctx, "intro_beat", None) is not None


def current_beat(ctx: Any) -> Optional[str]:
    """The armed beat id, or None."""
    return getattr(ctx, "intro_beat", None)


def set_beat(ctx: Any, beat_id: Optional[str]) -> None:
    """Arm a specific beat."""
    ctx.intro_beat = beat_id


def stage_for(beat_id: Any) -> Dict[str, Any]:
    """
    The staging row for a beat.

    An unknown id gets the black stage rather than a KeyError: a beat
    the script grew that this table has not, drawn on black with its
    lines, is a far better failure than a crash on the title screen.
    """
    return dict(STAGES.get(str(beat_id or ""), STAGES[BEAT_BRIEFING]))


# ── routing ────────────────────────────────────────────────────

def after_briefing(ctx: Any) -> ScreenState:
    """Beat 1 ends at the name card."""
    return ScreenState.NAME_ENTRY


def after_name_entry(ctx: Any) -> ScreenState:
    """
    The name card hands to registration.

    Registration is not optional — semester 1 cannot start without
    registered courses — and it lands here because its own __confirm()
    already forces ctx.level_id = "player_room", which is exactly where
    beat 2 needs the player to be.
    """
    return ScreenState.REGISTRATION


def after_registration(ctx: Any) -> ScreenState:
    """
    Where registration goes when the player confirms their courses.

    THE ONE BEHAVIOUR-PRESERVING EDIT (§4). While the intro is armed
    this arms beat 2 and returns INTRO. Otherwise it does exactly what
    engine/states/registration.py did before this phase — that tail is
    moved here verbatim, which is what keeps semesters 2-12 identical:
    the final exam routes to REGISTRATION through MONOLOGUE, the intro
    is not armed on those runs, and this falls through.

    It is also what suppresses the semester-1 entry in CUTSCENES during
    the first run without deleting it — that dict is
    content/dialogues.py, which is on main and is Ayesha's.
    """
    if is_running(ctx):
        set_beat(ctx, BEAT_ROOM_TOUR)
        return ScreenState.INTRO
    from content.dialogues import has_cutscene
    if has_cutscene(ctx.semester().get_semester_number()):
        return ScreenState.CUTSCENE
    return ScreenState.EXPLORATION


def after_room_tour(ctx: Any) -> ScreenState:
    """
    Beat 2 arms beat 3 and HANDS THE PLAYER BACK THEIR LEGS.

    This used to return INTRO, which played beat 3 back-to-back on a
    lecture hall the tutorial had teleported the player into. Beat 3 is
    now a walk-in beat (WALK_IN_TRIGGERS): the player leaves their room
    under their own control and beat 3 starts when they enter the
    lecture hall. check_level_trigger() is what notices, and
    engine/states/exploration.py::update() is where it is asked.

    Beat 3 stays ARMED the whole time they are walking, so nothing else
    about the intro changes — is_running() is still True, the semester-1
    cutscene is still suppressed, and the title screen still disarms it.
    """
    set_beat(ctx, BEAT_CAMPUS_TOUR)
    return ScreenState.EXPLORATION


# ── the walk-in trigger ────────────────────────────────────────

def pending_trigger_level(ctx: Any) -> Optional[str]:
    """The level the armed beat is waiting for the player to walk into."""
    if not is_running(ctx):
        return None
    return WALK_IN_TRIGGERS.get(str(current_beat(ctx) or ""))


def check_level_trigger(ctx: Any) -> bool:
    """
    Start the armed beat if the player is standing in its level.

    True means the game has been routed to INTRO and the caller should
    stop what it was doing this frame. False — the overwhelmingly common
    answer, since this is asked once a frame while walking — means
    nothing happened and costs one dict lookup.

    Asked per frame rather than hooked onto the portal, because a player
    can reach the lecture hall by loading into it, by a teleport rug, or
    by any doorway a level editor grows next week; where they came from
    is not the question, only where they are.
    """
    level_id = pending_trigger_level(ctx)
    if not level_id or getattr(ctx, "level_id", None) != level_id:
        return False
    ctx.go(ScreenState.INTRO)
    return True


def after_campus_tour(ctx: Any) -> ScreenState:
    """Beat 3 hands off to free roam. The caller calls finish() too."""
    return ScreenState.EXPLORATION


# The router a beat uses when it ends, by beat id. Kept as a table so
# engine/states/intro.py has no if/elif chain over beat ids.
AFTER: Dict[str, Any] = {
    BEAT_BRIEFING: after_briefing,
    BEAT_ROOM_TOUR: after_room_tour,
    BEAT_CAMPUS_TOUR: after_campus_tour,
}


def after(ctx: Any, beat_id: Any) -> ScreenState:
    """Where `beat_id` goes when its last line is dismissed."""
    router = AFTER.get(str(beat_id or ""))
    if router is None:
        return ScreenState.EXPLORATION
    return router(ctx)


# -------------------------------------------------------------
# STUB TEST — the repo's convention. Headless, no pygame.
#     py -m engine.intro_sequence
# The full routing suite is tests/test_intro_sequence.py.
# -------------------------------------------------------------
if __name__ == "__main__":
    class _Ctx:
        pass

    ctx = _Ctx()
    assert not is_running(ctx), "an untouched context read as armed"
    assert current_beat(ctx) is None

    arm(ctx)
    assert is_running(ctx) and current_beat(ctx) == BEAT_BRIEFING
    assert after(ctx, BEAT_BRIEFING) is ScreenState.NAME_ENTRY
    assert after_name_entry(ctx) is ScreenState.REGISTRATION

    assert after_registration(ctx) is ScreenState.INTRO
    assert current_beat(ctx) == BEAT_ROOM_TOUR, "registration armed the wrong beat"

    # Beat 2 gives the player back the controls; beat 3 waits for them.
    assert after(ctx, BEAT_ROOM_TOUR) is ScreenState.EXPLORATION
    assert current_beat(ctx) == BEAT_CAMPUS_TOUR
    assert after(ctx, BEAT_CAMPUS_TOUR) is ScreenState.EXPLORATION

    finish(ctx)
    assert not is_running(ctx)

    # -- the walk-in trigger ---------------------------------------
    class _Go:
        def __init__(self, level_id):
            self.level_id = level_id
            self.went_to = None

        def go(self, state):
            self.went_to = state

    walking = _Go("campus_main")
    arm(walking)
    set_beat(walking, BEAT_CAMPUS_TOUR)
    assert pending_trigger_level(walking) == "lecture_hall"
    assert not check_level_trigger(walking), "beat 3 fired on the wrong level"
    assert walking.went_to is None

    walking.level_id = "lecture_hall"
    assert check_level_trigger(walking), "beat 3 did not fire on arrival"
    assert walking.went_to is ScreenState.INTRO

    # An unarmed context never triggers, whatever level it is standing in.
    finish(walking)
    walking.went_to = None
    assert pending_trigger_level(walking) is None
    assert not check_level_trigger(walking), "a finished intro fired again"
    assert walking.went_to is None

    # Beat 2 is not a walk-in beat — it plays where the player already is.
    staged = _Go("player_room")
    arm(staged)
    set_beat(staged, BEAT_ROOM_TOUR)
    assert pending_trigger_level(staged) is None
    assert not check_level_trigger(staged)

    # -- the staging table -----------------------------------------
    assert stage_for(BEAT_BRIEFING)["level_id"] is None
    assert stage_for(BEAT_ROOM_TOUR)["npc_cell"] == (4, 3)
    assert stage_for(BEAT_CAMPUS_TOUR)["npc_cell"] == (9, 8)
    assert stage_for(BEAT_CAMPUS_TOUR)["fade_out"] is True
    assert sum(1 for b in BEAT_IDS if stage_for(b)["fade_out"]) == 1, \
        "more than one beat fades out"
    assert stage_for("nonsense")["level_id"] is None, "unknown id raised"
    stage_for(BEAT_ROOM_TOUR)["npc_cell"] = (0, 0)
    assert STAGES[BEAT_ROOM_TOUR]["npc_cell"] == (4, 3), \
        "stage_for() handed out the live table"

    print("intro_sequence: all checks passed")

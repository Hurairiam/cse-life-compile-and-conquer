"""
The three-beat opening tutorial: Roya's briefing, the room, the campus.

Phase 18 §5. One ScreenState module playing all three beats and owning
the fade. Follows the house shape of every other module in
engine/states/: module-level __-prefixed privates, a lazily built UI
object, and the five router hooks. The router resolves this from the
enum name — ScreenState.INTRO -> engine.states.intro — so
engine/state_router.py needs no dispatch edit.

WHERE THE LINES COME FROM
─────────────────────────
content/intro_script.py, which is Ayesha's file on dev4-aysha-narrative.
It is NOT on this branch yet, so the import is guarded (§7) and a
missing script shows one obvious placeholder line per beat. That
placeholder is a BUILD SCAFFOLD, NOT CONTENT — it is deleted the moment
the two branches meet and must never survive into a demo. Nothing in
this file writes dialogue (G2).

BEAT 3 IS WALKED INTO, NOT HANDED TO
────────────────────────────────────
Beat 2 used to hand straight to beat 3, which meant the tutorial moved
the player from their room to the lecture hall for them. It does not any
more (owner ruling): beat 2 ends on EXPLORATION with beat 3 still armed,
the player crosses the campus themselves, and
engine/intro_sequence.py::check_level_trigger() starts beat 3 the frame
they enter the lecture hall. enter() therefore must NOT re-stage a level
the player is already standing in — see __already_standing_in().

The INTRO -> INTRO guard in __end_beat() is kept even though nothing
reaches it today. The router only fires enter() when the state CHANGES,
so any future beat that routes INTRO from INTRO would silently play the
previous beat's lines over the previous beat's level; the guard costs
two lines and that failure costs an afternoon.
"""
import pygame

from engine import day_warning, intro_sequence
from engine.screen_manager import ScreenState
from ui import cutscene_stage

# §7 — build against the contract before Ayesha's file lands.
try:
    from content import intro_script
except ImportError:                                  # pragma: no cover
    intro_script = None

from content.level_registry import get_npc_portrait_path

# ── phases (§5) ────────────────────────────────────────────────
PHASE_TALK = "talk"
PHASE_FADE_OUT = "fade_out"
PHASE_HOLD = "hold"
PHASE_FADE_IN = "fade_in"

FADE_OUT_SECONDS = 0.7
HOLD_SECONDS = 0.25
FADE_IN_SECONDS = 0.7

SPEAKER_FALLBACK = "Ms. Roya"

# ROYA IS A STILL, NOT AN ANIMATION (owner ruling). The cutscenes draw
# ONE frame of her idle sheet and never cycle it: column 0 of row 0 of
# assets/npcs/npc_roya_idle.png. ui/cutscene_stage.py::frame_for() is
# what used to pick a frame from a clock and is now simply not called
# from here — it is still the drawing module's public API and a placed
# NPC on the map still animates exactly as it did.
STAGE_FRAME = 0

# Module-level, the way engine/states/save_game.py, pass_days.py and
# side_quest_lecture.py all keep theirs. app_context.py is shared and
# worth not touching for three floats.
__phase = PHASE_TALK
__fade_clock = 0.0
__draw_npc = True
__stage = None


# ── the script, guarded ────────────────────────────────────────

def __lines(ctx, beat):
    """
    The beat's lines with {name} filled in, or the scaffold placeholder.

    An empty beat is treated the same as a missing one by the caller —
    §7 says a beat whose lines list is empty should skip straight to the
    next rather than showing an empty card.
    """
    raw = []
    if intro_script is not None:
        try:
            raw = list(intro_script.get_lines(beat) or [])
        except (AttributeError, TypeError, ValueError):
            raw = []
    if not raw:
        return []
    return [__substitute(ctx, line) for line in raw]


def __substitute(ctx, line):
    """Fill the {name} token. replace(), never format() — see §3."""
    try:
        name = ctx.player().get_display_name()
    except AttributeError:
        name = ""
    return str(line).replace("{name}", str(name))


def __placeholder(beat):
    """The §7 build scaffold. Deleted when the two branches meet."""
    return ["[intro_script.py not merged yet - beat: %s]" % beat]


def __emotion(beat):
    if intro_script is None:
        return "neutral"
    try:
        return str(intro_script.get_emotion(beat) or "neutral")
    except (AttributeError, TypeError, ValueError):
        return "neutral"


def __speaker(beat):
    if intro_script is None:
        return SPEAKER_FALLBACK
    try:
        return str(intro_script.get_speaker(beat) or SPEAKER_FALLBACK)
    except (AttributeError, TypeError, ValueError):
        return SPEAKER_FALLBACK


# ── router hooks ───────────────────────────────────────────────

def enter(ctx):
    """
    Stage the armed beat and put its first line up.

    Called by the router on every entry — including the one
    engine/intro_sequence.py::check_level_trigger() causes when the
    player walks into the lecture hall carrying an armed beat 3.
    """
    global __phase, __fade_clock, __draw_npc, __stage
    beat = intro_sequence.current_beat(ctx)
    if beat is None:
        # Defensive: this state should never be entered unarmed.
        ctx.go(ScreenState.EXPLORATION)
        return

    __stage = intro_sequence.stage_for(beat)
    __phase = PHASE_TALK
    __fade_clock = 0.0
    __draw_npc = True

    level_id = __stage.get("level_id")
    if level_id and not __already_standing_in(ctx, level_id):
        # The same call engine/states/cutscene.py already makes. It
        # builds ctx.walker at the level's spawn, so the player is
        # standing in shot without this file placing anybody.
        from engine.states import exploration
        ctx.level_id = level_id
        ctx.level = None
        ctx.pending_spawn = None
        exploration.ensure_level(ctx)

    lines = __lines(ctx, beat)
    if not lines:
        if intro_script is None:
            lines = __placeholder(beat)
        else:
            # A merged-but-empty beat: skip straight to the next one
            # rather than showing an empty card (§7).
            __end_beat(ctx)
            return

    portrait = get_npc_portrait_path(intro_sequence.STAGE_NPC_TYPE,
                                     __emotion(beat))
    ctx.dialogue_manager.set_typewriter_enabled(True)
    ctx.dialogue_manager.load_dialogue(lines, portrait)
    ctx.dialogue_manager.set_speaker(__speaker(beat))


def __already_standing_in(ctx, level_id):
    """
    True when the player is ALREADY in the level this beat stages.

    A walk-in beat (intro_sequence.WALK_IN_TRIGGERS) fires because the
    player walked through the door themselves, so re-staging the level
    would reload it and snap them back to its spawn — the tutorial
    yanking them two cells the moment they arrive. Beat 2 is unaffected:
    registration leaves the player in campus_main, so player_room does
    not match and it stages exactly as it always did.
    """
    return (getattr(ctx, "level_id", None) == level_id
            and getattr(ctx, "level", None) is not None
            and getattr(ctx, "walker", None) is not None)


def exit(ctx):
    """Leave no veil or half-run beat behind a state change."""
    global __phase, __fade_clock, __draw_npc
    __phase = PHASE_TALK
    __fade_clock = 0.0
    __draw_npc = True


def handle_events(ctx, events):
    """
    Only during PHASE_TALK; the fade swallows input.

    ESC skips THIS BEAT, not the whole intro (§5 ruling): a player who
    does not want the tutorial presses it three times, and a player who
    pressed it by accident does not lose the other two.
    """
    if __phase != PHASE_TALK:
        return
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                __end_beat(ctx)
                return
            if event.key in (pygame.K_SPACE, pygame.K_RETURN,
                             pygame.K_KP_ENTER):
                __advance(ctx)
                return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            __advance(ctx)
            return


def __advance(ctx):
    """Finish the line first, then move on — the house two-stage press."""
    if ctx.dialogue_manager.skip_reveal():
        return
    ctx.play_sfx("page_turn")
    if ctx.dialogue_manager.advance():
        return
    __end_beat(ctx)


def __end_beat(ctx):
    """
    The beat is over: fade, or route onward.

    Beat 2 now leaves on EXPLORATION with beat 3 armed, so the player
    walks to the lecture hall themselves. The INTRO -> INTRO branch
    below is therefore unreached today and deliberately kept: the router
    does not re-enter a state it is already in, so a beat that ever
    routes INTRO from INTRO would play the previous beat's lines over
    the previous beat's level without it.
    """
    global __phase, __fade_clock
    if __stage is not None and __stage.get("fade_out"):
        __phase = PHASE_FADE_OUT
        __fade_clock = 0.0
        return

    here = ctx.screen_mgr.get_current_state()
    target = intro_sequence.after(ctx, intro_sequence.current_beat(ctx))
    if target is ScreenState.INTRO and here is ScreenState.INTRO:
        enter(ctx)
        return
    ctx.go(target)


def update(ctx, dt):
    """Tick the typewriter and the fade. Roya does not move — STAGE_FRAME."""
    global __phase, __fade_clock, __draw_npc
    try:
        step = max(0.0, float(dt))
    except (TypeError, ValueError):
        step = 0.0

    if __phase == PHASE_TALK:
        ctx.dialogue_manager.update(step)
        return

    __fade_clock += step
    if __phase == PHASE_FADE_OUT and __fade_clock >= FADE_OUT_SECONDS:
        __phase = PHASE_HOLD
        __fade_clock = 0.0
        # The frame she disappears, hidden behind full black.
        __draw_npc = False
    elif __phase == PHASE_HOLD and __fade_clock >= HOLD_SECONDS:
        __phase = PHASE_FADE_IN
        __fade_clock = 0.0
    elif __phase == PHASE_FADE_IN and __fade_clock >= FADE_IN_SECONDS:
        __phase = PHASE_TALK
        __fade_clock = 0.0
        intro_sequence.finish(ctx)
        ctx.go(ScreenState.EXPLORATION)


def __veil_alpha():
    """0-255 for the phase the beat is in."""
    if __phase == PHASE_FADE_OUT:
        return int(255 * min(1.0, __fade_clock / FADE_OUT_SECONDS))
    if __phase == PHASE_HOLD:
        return 255
    if __phase == PHASE_FADE_IN:
        return int(255 * max(0.0, 1.0 - __fade_clock / FADE_IN_SECONDS))
    return 0


def render(ctx, screen):
    """
    Map, then Roya, then the HUD, then the card, then the veil.

    The order matters and the veil must be LAST — otherwise the fade
    leaves the dialogue card floating on black.
    """
    stage = __stage if __stage is not None else \
        intro_sequence.stage_for(intro_sequence.current_beat(ctx))
    frame = STAGE_FRAME

    if stage.get("level_id") is None:
        cutscene_stage.draw_black_stage(
            screen, intro_sequence.STAGE_NPC_TYPE, frame)
    elif getattr(ctx, "level", None) is not None and ctx.walker is not None:
        ctx.camera = ctx.map_screen.compute_camera(
            ctx.level, ctx.walker.get_position(), screen)
        ctx.map_screen.render(screen, ctx.level, ctx.camera,
                              ctx.walker.get_position(),
                              ctx.walker.get_facing(), ctx.walker.get_frame(),
                              dt=0.0)
        if __draw_npc:
            cutscene_stage.draw_standing_npc(
                screen, ctx.map_screen, stage.get("npc_cell"), ctx.camera,
                intro_sequence.STAGE_NPC_TYPE, frame)
        __draw_hud(ctx, screen)

    ctx.dialogue_manager.render(screen)
    alpha = __veil_alpha()
    if alpha > 0:
        cutscene_stage.draw_fade(screen, alpha)


def __draw_hud(ctx, screen):
    """
    The HUD strip, on the two beats that have a map behind them.

    ScreenState.INTRO is in state_router.HUD_HIDDEN because beat 1 is a
    black stage with no semester to report; beats 2 and 3 draw it here
    instead, so Roya can point at a real day counter while she explains
    the 80-day pool. Same six keyword arguments as
    state_router.render_overlays().
    """
    if getattr(ctx, "hud", None) is None:
        return
    try:
        semester = ctx.semester()
        ctx.hud.render(
            screen,
            time_pool=semester.get_time_pool_days(),
            wallet=ctx.player().get_wallet_balance(),
            semester=semester.get_semester_number(),
            credits=ctx.player().get_accumulated_credits(),
            location=(ctx.level.get_level_name()
                      if ctx.level is not None else ""),
            low_days=day_warning.hud_days(ctx),
        )
    except (AttributeError, TypeError, ValueError):
        # A nicety, not a requirement (§5). A context that cannot
        # report a semester simply gets no strip.
        return

"""
tests/test_intro_sequence.py
Phase 18 — the intro's routing table, arming, and the regressions.

The routing half is headless and needs no pygame at all; the staging
half drives the real state module against real levels, which does.

The tests that matter most are the REGRESSIONS. "Nothing conflicts with
main" means semesters 2-12 must route exactly as they did, and the one
shared file whose behaviour actually changed is
engine/states/registration.py. Its §12 checks are asserted here rather
than left to a playthrough.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame                                            # noqa: E402
import pytest                                            # noqa: E402

from content.dialogues import has_cutscene               # noqa: E402
from engine import intro_sequence, save_bridge           # noqa: E402
from engine.app_context import AppContext                # noqa: E402
from engine.intro_sequence import (BEAT_BRIEFING,        # noqa: E402
                                   BEAT_CAMPUS_TOUR, BEAT_IDS,
                                   BEAT_ROOM_TOUR, STAGES)
from engine.screen_manager import ScreenState            # noqa: E402
from engine.states import intro, main_menu               # noqa: E402

pygame.init()
pygame.display.set_mode((1280, 720))


class Bare:
    """The bare context intro_sequence is allowed to run against."""


@pytest.fixture
def ctx():
    context = AppContext()
    save_bridge.new_game(context)
    return context


def landed_on(context):
    context.screen_mgr.apply_pending_transition()
    return context.screen_mgr.get_current_state()


# ── arming and the leak guard ──────────────────────────────────

def test_a_fresh_context_is_not_armed():
    assert not intro_sequence.is_running(Bare())
    assert intro_sequence.current_beat(Bare()) is None


def test_arm_starts_at_the_briefing():
    bare = Bare()
    intro_sequence.arm(bare)
    assert intro_sequence.is_running(bare)
    assert intro_sequence.current_beat(bare) is BEAT_BRIEFING


def test_finish_disarms():
    bare = Bare()
    intro_sequence.arm(bare)
    intro_sequence.finish(bare)
    assert not intro_sequence.is_running(bare)


def test_the_title_screen_disarms_the_intro(ctx):
    """
    §4's leak guard: new game, back out to the title, load a save. The
    flag must not survive, or registration routes into a dead intro.
    """
    intro_sequence.arm(ctx)
    main_menu.enter(ctx)
    assert not intro_sequence.is_running(ctx)


# ── the routing table ──────────────────────────────────────────

def test_the_whole_chain_in_order(ctx):
    intro_sequence.arm(ctx)
    assert intro_sequence.after(ctx, BEAT_BRIEFING) is ScreenState.NAME_ENTRY
    assert intro_sequence.after_name_entry(ctx) is ScreenState.REGISTRATION

    assert intro_sequence.after_registration(ctx) is ScreenState.INTRO
    assert intro_sequence.current_beat(ctx) is BEAT_ROOM_TOUR

    # Beat 2 hands the controls back with beat 3 still armed: the player
    # walks to the lecture hall and beat 3 starts when they arrive.
    assert intro_sequence.after(ctx, BEAT_ROOM_TOUR) is ScreenState.EXPLORATION
    assert intro_sequence.current_beat(ctx) is BEAT_CAMPUS_TOUR
    assert intro_sequence.is_running(ctx), "beat 3 was disarmed while walking"

    assert intro_sequence.after(ctx, BEAT_CAMPUS_TOUR) is ScreenState.EXPLORATION


def test_an_unknown_beat_routes_somewhere_survivable():
    assert intro_sequence.after(Bare(), "nonsense") is ScreenState.EXPLORATION


# ── the staging table ──────────────────────────────────────────

def test_every_beat_has_a_stage():
    assert set(STAGES) == set(BEAT_IDS)
    for beat in BEAT_IDS:
        stage = intro_sequence.stage_for(beat)
        assert set(stage) == {"level_id", "npc_cell", "facing", "fade_out"}


def test_the_cells_are_the_ones_measured_against_the_levels():
    assert intro_sequence.stage_for(BEAT_BRIEFING)["level_id"] is None
    assert intro_sequence.stage_for(BEAT_ROOM_TOUR)["level_id"] == "player_room"
    assert intro_sequence.stage_for(BEAT_ROOM_TOUR)["npc_cell"] == (4, 3)
    assert intro_sequence.stage_for(
        BEAT_CAMPUS_TOUR)["level_id"] == "lecture_hall"
    # (x, y) = column 9, row 8 — the central aisle, dead centre of the
    # screen, and the only row that is both empty and clear of the card.
    assert intro_sequence.stage_for(BEAT_CAMPUS_TOUR)["npc_cell"] == (9, 8)


def test_only_the_last_beat_fades_out():
    fading = [b for b in BEAT_IDS if intro_sequence.stage_for(b)["fade_out"]]
    assert fading == [BEAT_CAMPUS_TOUR]


def test_stage_for_hands_out_a_copy():
    """A caller mutating its stage must not rewrite the table."""
    intro_sequence.stage_for(BEAT_ROOM_TOUR)["npc_cell"] = (0, 0)
    assert STAGES[BEAT_ROOM_TOUR]["npc_cell"] == (4, 3)


def test_roya_stands_on_a_walkable_cell_with_nothing_on_it(ctx):
    """
    The two cells were claimed to be checked against the live level
    files. This checks them again, every run.

    get_prop_at() rather than get_interactable_at(): a desk's rear row
    is walk-behind and NOT interactable, so the interactable check alone
    reported a clear cell and Roya was stood inside a lecture desk.
    """
    from engine.level_loader import load_level
    for beat in (BEAT_ROOM_TOUR, BEAT_CAMPUS_TOUR):
        stage = intro_sequence.stage_for(beat)
        level = load_level(stage["level_id"], semester=1)
        assert level is not None, "could not load %s" % stage["level_id"]
        cell = stage["npc_cell"]
        assert level.is_walkable(cell[0], cell[1]), \
            "%s: Roya stands on a blocked cell %r" % (beat, cell)
        assert level.get_prop_at(cell[0], cell[1]) is None, \
            "%s: Roya stands inside a prop at %r" % (beat, cell)
        for npc in level.get_npcs():
            assert tuple(npc.get_position()) != tuple(cell), \
                "%s: Roya shares a cell with %s" % (beat, npc.get_type_id())


def test_roya_is_fully_in_frame_and_clear_of_the_dialogue_card(ctx):
    """
    Owner ruling: she must be SEEN. Her sprite has to sit wholly inside
    the viewport and wholly above the dialogue card, framed by the
    camera the player's own spawn produces.

    This is the check nothing had: at her original cell she rendered
    100% behind the card for the entire beat and the cutscene looked
    like Roya had not turned up.
    """
    from content.level_registry import (TILE_SIZE_PX, npc_blit_offset,
                                        npc_sprite_px)
    from engine.level_loader import load_level

    screen = pygame.display.get_surface()
    card = ctx.dialogue_manager.get_box_rect() \
        if hasattr(ctx.dialogue_manager, "get_box_rect") else \
        pygame.Rect(46, screen.get_height() - 28 - 168,
                    screen.get_width() - 92, 168)

    stage = intro_sequence.stage_for(BEAT_CAMPUS_TOUR)
    level = load_level(stage["level_id"], semester=1)
    cell_above = (stage["npc_cell"][0], stage["npc_cell"][1] - 1)
    # She is drawn OVER the map, so a prop above her is not hidden by
    # her — her head is drawn across it. Harmless in the player's room,
    # where the vase has always sat above her, but a lecture desk is a
    # metre of furniture through her shoulders. Column 9 is the central
    # aisle and is free on the desk rows either side of her.
    assert level.get_prop_at(*cell_above) is None, \
        "a desk sits directly behind Roya's head at %r" % (cell_above,)

    spawn = level.get_spawn()
    camera = ctx.map_screen.compute_camera(
        level, (float(spawn[0]), float(spawn[1])), screen)

    cell = stage["npc_cell"]
    cell_rect = ctx.map_screen.get_screen_rect_for_cell(
        cell[0], cell[1], camera)
    dx, dy = npc_blit_offset(TILE_SIZE_PX)
    size = npc_sprite_px(TILE_SIZE_PX)
    sprite = pygame.Rect(cell_rect.x + dx, cell_rect.y + dy, size, size)

    viewport = ctx.map_screen.get_viewport_rect(screen)
    assert viewport.contains(sprite), \
        "Roya is off the edge of the viewport: %r" % (tuple(sprite),)
    assert not sprite.colliderect(card), \
        "Roya is drawn behind the dialogue card: %r vs %r" % (
            tuple(sprite), tuple(card))


# ── the regressions §12 names ──────────────────────────────────

def test_semesters_2_to_12_route_exactly_as_before(ctx):
    """
    THE regression. The intro is not armed on those runs, so
    after_registration() must fall through to what registration.py did
    before this phase: CUTSCENE when the semester has one, else
    EXPLORATION.
    """
    assert not intro_sequence.is_running(ctx)
    for semester in range(1, 13):
        while ctx.player().get_current_semester() < semester:
            ctx.player().advance_semester()
        from academic.semester import Semester
        ctx.session.set_active_semester(Semester(semester))

        expected = (ScreenState.CUTSCENE if has_cutscene(semester)
                    else ScreenState.EXPLORATION)
        assert intro_sequence.after_registration(ctx) is expected, \
            "semester %d routed to the wrong screen" % semester


def test_semester_1_cutscene_is_suppressed_only_while_armed(ctx):
    """
    §4: the first run skips CUTSCENES[1] without deleting it from
    content/dialogues.py, which is on main and is Ayesha's.
    """
    assert has_cutscene(1), "the fixture assumes semester 1 has a cutscene"

    intro_sequence.arm(ctx)
    assert intro_sequence.after_registration(ctx) is ScreenState.INTRO

    intro_sequence.finish(ctx)
    assert intro_sequence.after_registration(ctx) is ScreenState.CUTSCENE


def test_start_game_arms_the_intro_and_routes_to_it(ctx):
    """main_menu's edit, end to end."""
    ctx.screen_mgr.transition_to(ScreenState.MAIN_MENU)
    ctx.menu_focus = 0
    main_menu.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN})])
    assert intro_sequence.is_running(ctx)
    assert intro_sequence.current_beat(ctx) is BEAT_BRIEFING
    assert landed_on(ctx) is ScreenState.INTRO


# ── the state module ───────────────────────────────────────────

def test_beat_1_needs_no_level(ctx):
    intro_sequence.arm(ctx)
    intro.enter(ctx)
    assert ctx.dialogue_manager.is_active(), "beat 1 put no lines up"


def test_beat_2_loads_the_room_and_stands_the_player_in_it(ctx):
    intro_sequence.arm(ctx)
    intro_sequence.set_beat(ctx, BEAT_ROOM_TOUR)
    intro.enter(ctx)
    assert ctx.level_id == "player_room"
    assert ctx.level is not None, "the room was not loaded"
    assert ctx.walker is not None, "the player is not in shot"


def test_beat_2_gives_the_player_back_the_controls(ctx):
    """
    Beat 2 must NOT drag the player to the lecture hall any more.

    It ends on EXPLORATION, in the room it was played in, with beat 3
    still armed — that armed-while-walking state is the whole mechanism
    the walk-in trigger below depends on.
    """
    intro_sequence.arm(ctx)
    intro_sequence.set_beat(ctx, BEAT_ROOM_TOUR)
    ctx.screen_mgr.transition_to(ScreenState.INTRO)
    intro.enter(ctx)
    assert ctx.level_id == "player_room"

    # Page to the end of beat 2.
    intro.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_ESCAPE})])

    assert intro_sequence.current_beat(ctx) is BEAT_CAMPUS_TOUR, \
        "beat 2 did not arm beat 3"
    assert intro_sequence.is_running(ctx), "beat 3 was disarmed on the way out"
    assert landed_on(ctx) is ScreenState.EXPLORATION, \
        "beat 2 did not hand control back to the player"
    assert ctx.level_id == "player_room", \
        "beat 2 teleported the player instead of letting them walk"


def test_beat_3_starts_when_the_player_walks_into_the_lecture_hall(ctx):
    """
    The walk-in trigger, through the shared file's one call site.

    exploration.update() is what asks, so this drives that rather than
    intro_sequence.check_level_trigger() directly — the point of the
    test is that the call site is wired, not that the helper works.
    """
    from engine.states import exploration

    intro_sequence.arm(ctx)
    intro_sequence.set_beat(ctx, BEAT_CAMPUS_TOUR)
    ctx.screen_mgr.transition_to(ScreenState.EXPLORATION)

    # Somewhere else on campus: nothing fires, the player keeps walking.
    ctx.level_id = "campus_main"
    ctx.level = None
    ctx.pending_spawn = None
    exploration.ensure_level(ctx)
    exploration.update(ctx, 0.016)
    assert landed_on(ctx) is ScreenState.EXPLORATION, \
        "beat 3 fired outside the lecture hall"

    # Through the door.
    ctx.level_id = "lecture_hall"
    ctx.level = None
    ctx.pending_spawn = None
    exploration.ensure_level(ctx)
    exploration.update(ctx, 0.016)
    assert landed_on(ctx) is ScreenState.INTRO, \
        "walking into the lecture hall did not start beat 3"


def test_beat_3_does_not_snap_the_player_back_to_the_spawn(ctx):
    """
    The player walked in, so enter() must not reload the level under
    them — that would move them to the lecture hall's spawn cell the
    instant the cutscene starts.
    """
    from engine.states import exploration

    intro_sequence.arm(ctx)
    intro_sequence.set_beat(ctx, BEAT_CAMPUS_TOUR)
    ctx.level_id = "lecture_hall"
    ctx.level = None
    ctx.pending_spawn = None
    exploration.ensure_level(ctx)

    walked_to = (9, 11)
    assert ctx.level.is_walkable(*walked_to), "the fixture cell is blocked"
    ctx.walker.place(walked_to)

    level_before = ctx.level
    ctx.screen_mgr.transition_to(ScreenState.INTRO)
    intro.enter(ctx)

    assert ctx.walker.get_cell() == walked_to, \
        "beat 3 moved the player who had just walked in"
    assert ctx.level is level_before, "beat 3 reloaded the level under them"


def test_roya_is_a_still_in_the_cutscenes():
    """
    Owner ruling: one frame of npc_roya_idle.png, never a cycle. Frame 0
    is the first column of row 0.
    """
    assert intro.STAGE_FRAME == 0
    assert not hasattr(intro, "__anim_clock"), \
        "the idle clock is back — Roya is meant to be static"


def test_escape_skips_one_beat_not_the_whole_intro(ctx):
    """§5's deliberate ruling."""
    intro_sequence.arm(ctx)
    ctx.screen_mgr.transition_to(ScreenState.INTRO)
    intro.enter(ctx)
    intro.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_ESCAPE})])
    assert landed_on(ctx) is ScreenState.NAME_ENTRY, \
        "ESC on beat 1 did not go to the name card"
    assert intro_sequence.is_running(ctx), "ESC abandoned the whole intro"


def test_beat_3_fades_out_then_hands_off(ctx):
    """The only beat with a tail: fade out, drop Roya, fade back in."""
    intro_sequence.arm(ctx)
    intro_sequence.set_beat(ctx, BEAT_CAMPUS_TOUR)
    ctx.screen_mgr.transition_to(ScreenState.INTRO)
    intro.enter(ctx)

    intro.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_ESCAPE})])
    # Still on INTRO: the fade has to run first.
    assert landed_on(ctx) is ScreenState.INTRO, "beat 3 skipped its fade"

    for _ in range(400):
        intro.update(ctx, 0.05)
        if not intro_sequence.is_running(ctx):
            break

    assert not intro_sequence.is_running(ctx), "the intro never finished"
    assert landed_on(ctx) is ScreenState.EXPLORATION


def test_entering_unarmed_bails_to_exploration(ctx):
    intro_sequence.finish(ctx)
    intro.enter(ctx)
    assert landed_on(ctx) is ScreenState.EXPLORATION


def test_the_name_token_is_replaced_not_formatted(ctx):
    """
    §3: substitution is str.replace, never str.format.

    A stray brace in authored prose must not crash the game, and
    str.format would raise KeyError on "{oops}" or ValueError on a
    lone "{". Reached through the module attribute because the helper
    is a module-level private — the same way the other state modules'
    internals are exercised.
    """
    substitute = getattr(intro, "__substitute", None) \
        or getattr(intro, "_substitute", None)
    assert substitute is not None, "the substitution helper was renamed"

    ctx.player().set_display_name("Nangiba")
    assert substitute(ctx, "hi {name}") == "hi Nangiba"
    assert substitute(ctx, "hi {name} {oops}") == "hi Nangiba {oops}"
    assert substitute(ctx, "100% sure {") == "100% sure {"
    assert substitute(ctx, "no token here") == "no token here"


def test_beat_1_never_needs_the_name(ctx):
    """
    §3: beat 1 must never use {name} — the player has not typed one yet.

    Asserted against Ayesha's file when it is present, and skipped when
    it is not, so this starts guarding the moment the branches meet.
    """
    try:
        from content import intro_script
    except ImportError:
        pytest.skip("content/intro_script.py has not merged yet")
    for line in intro_script.get_lines(BEAT_BRIEFING):
        assert "{name}" not in str(line), \
            "beat 1 uses {name} before the player has typed one"

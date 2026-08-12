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

    assert intro_sequence.after(ctx, BEAT_ROOM_TOUR) is ScreenState.INTRO
    assert intro_sequence.current_beat(ctx) is BEAT_CAMPUS_TOUR

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
    assert intro_sequence.stage_for(BEAT_CAMPUS_TOUR)["npc_cell"] == (9, 12)


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
    """
    from engine.level_loader import load_level
    for beat in (BEAT_ROOM_TOUR, BEAT_CAMPUS_TOUR):
        stage = intro_sequence.stage_for(beat)
        level = load_level(stage["level_id"], semester=1)
        assert level is not None, "could not load %s" % stage["level_id"]
        cell = stage["npc_cell"]
        assert level.is_walkable(cell[0], cell[1]), \
            "%s: Roya stands on a blocked cell %r" % (beat, cell)
        for npc in level.get_npcs():
            assert tuple(npc.get_position()) != tuple(cell), \
                "%s: Roya shares a cell with %s" % (beat, npc.get_type_id())


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


def test_beat_2_hands_to_beat_3_without_the_router(ctx):
    """
    §5's trap. The router does not re-enter a state it is already in,
    so INTRO -> INTRO must be handled inside the module — otherwise
    beat 3 shows beat 2's lines over beat 2's level.
    """
    intro_sequence.arm(ctx)
    intro_sequence.set_beat(ctx, BEAT_ROOM_TOUR)
    ctx.screen_mgr.transition_to(ScreenState.INTRO)
    intro.enter(ctx)
    assert ctx.level_id == "player_room"

    # Page to the end of beat 2.
    for _ in range(200):
        if not ctx.dialogue_manager.is_active():
            break
        intro.handle_events(ctx, [pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_ESCAPE})])
        break

    assert intro_sequence.current_beat(ctx) is BEAT_CAMPUS_TOUR, \
        "beat 2 did not arm beat 3"
    assert ctx.level_id == "lecture_hall", \
        "beat 3 was left staged on beat 2's level"


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

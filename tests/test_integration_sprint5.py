"""
tests/test_integration_sprint5.py
Phase 11 — the five cross-task checks, run as tests rather than by hand.

Each phase proved itself in isolation. These prove the seams: a skip
button feeding a stats label, a bed popup feeding an autosave feeding a
mid-session load, a re-offered quest feeding a completion flag.

Nothing is written to saves/ — every context gets a SaveManager pointed
at a temp directory.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame                                            # noqa: E402
import pytest                                            # noqa: E402

from content.side_quest_definitions import get_skill_id  # noqa: E402
from engine import (exam_days, intro_sequence,           # noqa: E402
                    lecture_reader, save_bridge, skill_completion)
from engine.app_context import AppContext                # noqa: E402
from engine.quest_state import STATE_COMPLETED           # noqa: E402
from engine.save_manager import AUTOSAVE_SLOT_ID, SaveManager  # noqa: E402
from engine.screen_manager import ScreenState            # noqa: E402
from engine.states import end_semester, load_game        # noqa: E402
from engine.states import side_quest_lecture             # noqa: E402
from ui import skip_button                               # noqa: E402
from ui.bed_popup import BedPopup                        # noqa: E402
from ui.pause_menu import ACTIONS, ACTION_LOAD_GAME      # noqa: E402

pygame.init()
pygame.display.set_mode((1280, 720))

SCREEN_W = 1280


@pytest.fixture
def ctx():
    folder = tempfile.mkdtemp(prefix="cse_life_integration_")
    context = AppContext()
    context.saves = SaveManager(folder)
    save_bridge.new_game(context)
    context.screen_w = SCREEN_W
    try:
        yield context
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def landed_on(context):
    context.screen_mgr.apply_pending_transition()
    return context.screen_mgr.get_current_state()


def key(code):
    return pygame.event.Event(pygame.KEYDOWN, {"key": code, "unicode": ""})


def typed(char):
    return pygame.event.Event(pygame.KEYDOWN,
                              {"key": ord(char), "unicode": char})


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                              {"button": 1, "pos": pos})


def register(context, count=3):
    from academic.course_catalog import get_course_by_code
    for course in list(context.full_catalog)[:count]:
        real = get_course_by_code(context.full_catalog,
                                  course.get_course_code())
        if real is not None:
            context.semester().register_course(real)


# ── 1. skip button -> completed flag -> stats label ────────────

def test_skipping_a_lecture_shows_completed_on_the_stats_screen(ctx):
    """P4 x P1 x P2, the whole way through."""
    quest = ctx.quest_states.get_quest_for_semester(1)
    skill = get_skill_id(quest)
    ctx.quest_states.accept(quest)

    rows = {label: (ratio, status)
            for label, ratio, status in skill_completion.stats_rows(ctx)}
    assert rows[skill] == (0.5, "NOT COMPLETED"), \
        "an accepted-but-unread skill did not read as half progress"

    assert lecture_reader.start(ctx, quest) is None
    side_quest_lecture.enter(ctx)
    side_quest_lecture.handle_events(
        ctx, [click(skip_button.get_rect(ctx.screen_w).center)])

    assert ctx.quest_states.get_state(quest) == STATE_COMPLETED
    assert skill_completion.is_completed(ctx, skill)

    rows = {label: (ratio, status)
            for label, ratio, status in skill_completion.stats_rows(ctx)}
    assert rows[skill] == (1.0, "COMPLETED"), \
        "the stats screen did not follow the skip button"

    # ...and no numeric level moved anywhere doing it.
    tree = ctx.player().get_skill_tree()
    assert tree.get_skill_level(skill) == 0, "a level was granted"


# ── 2. bed advance -> autosave -> ESC load ─────────────────────

def test_advancing_autosaves_and_load_game_restores_it(ctx):
    """P6 x P7 x P5."""
    register(ctx, 3)
    ctx.exam = {"course_index": 3, "tier_index": 0,
                "answers": {}, "message": None}
    assert exam_days.can_advance(ctx)

    end_semester.enter(ctx)
    end_semester.handle_events(ctx, [click(
        BedPopup(ctx.screen_w, ctx.screen_h).get_option_rects()[0].center)])
    end_semester.update(ctx, 0.016)
    assert ctx.semester().get_semester_number() == 2, "the term did not close"

    payload = ctx.saves.load(AUTOSAVE_SLOT_ID)
    assert payload is not None, "advancing wrote no autosave"
    assert payload["player"]["current_semester"] == 2

    # Diverge, then load the autosave back through the pause menu.
    ctx.level_id = "campus_main"
    ctx.screen_mgr.transition_to(ScreenState.EXPLORATION)
    ctx.return_state = ScreenState.EXPLORATION
    load_game.enter(ctx)
    ctx.load_selected = [s.get_slot_id()
                         for s in ctx.saves.list_slots()].index(
                             AUTOSAVE_SLOT_ID)
    load_game.handle_events(ctx, [key(pygame.K_RETURN)])

    assert landed_on(ctx) is ScreenState.EXPLORATION
    assert ctx.semester().get_semester_number() == 2, \
        "the load did not restore the post-transition semester"


# ── 3. portraits per line, and the single-portrait beats ───────

def test_a_conversation_tracks_emotions_and_a_beat_does_not(ctx):
    """P3 x P9."""
    manager = ctx.dialogue_manager
    portraits = ["assets/portraits/npc_purnno_%s.png" % emotion
                 for emotion in ("neutral", "happy", "encouraging")]
    manager.load_dialogue(["one", "two", "three"], None, portraits)
    faces = [manager.get_current_portrait()]
    while manager.advance():
        faces.append(manager.get_current_portrait())
    assert all(face is not None for face in faces)
    assert len({id(face) for face in faces}) == 3, \
        "a mixed-emotion conversation did not change portrait"

    # An INTRO beat loads ONE portrait and must hold it, unchanged.
    from engine.states import intro
    intro_sequence.arm(ctx)
    intro.enter(ctx)
    assert not manager.has_line_portraits(), \
        "an intro beat built a per-line portrait list"
    first = manager.get_current_portrait()
    while manager.advance():
        assert manager.get_current_portrait() is first, \
            "an intro beat changed face mid-beat"


# ── 4. decline -> re-offer -> accept -> complete ───────────────

def test_a_declined_quest_can_still_be_completed(ctx):
    """P8 x P1, and no level moves anywhere along the way."""
    quest = ctx.quest_states.get_quest_for_semester(1)
    skill = get_skill_id(quest)
    tree = ctx.player().get_skill_tree()

    ctx.quest_states.decline(quest)
    assert not skill_completion.is_completed(ctx, skill)

    npc_id = __import__("content.side_quest_definitions",
                        fromlist=["get_npc_id"]).get_npc_id(quest)
    assert ctx.quest_states.can_offer(npc_id, 1), \
        "the declined quest was not re-offered"

    ctx.quest_states.accept(quest)
    assert lecture_reader.start(ctx, quest) is None
    lecture_reader.skip_to_end(ctx)
    lecture_reader.end()

    assert skill_completion.is_completed(ctx, skill)
    assert tree.get_skill_level(skill) == 0, \
        "completing a re-offered quest granted a level"


# ── 5. old saves and new saves both load ───────────────────────

def test_a_pre_change_save_loads(ctx):
    """
    A save carrying numeric levels and no quest block — what every
    file written before this sprint looks like.
    """
    from engine.save_manager import build_state
    old = build_state(current_semester=3,
                      skills={"git": 15, "oop": 15},
                      completed_course_codes=[])
    old.pop("quests", None)                 # written before Phase 12

    fresh = AppContext()
    assert save_bridge.restore(fresh, old), "a pre-change save failed to load"
    # The levels are carried and simply not read; the flag says not done.
    assert skill_completion.completed_count(fresh) == 0
    assert fresh.player().get_skill_tree().get_skill_level("git") == 15


def test_a_post_change_save_round_trips(ctx):
    """Written after every phase in this sprint, read back clean."""
    quest = ctx.quest_states.get_quest_for_semester(1)
    ctx.quest_states.accept(quest)
    ctx.quest_states.mark_completed(quest)
    assert ctx.saves.save(1, save_bridge.capture(ctx))

    payload = ctx.saves.load(1)
    fresh = AppContext()
    assert save_bridge.restore(fresh, payload)
    assert skill_completion.is_completed(fresh, get_skill_id(quest))


def test_the_intro_flag_is_never_written_to_a_save(ctx):
    """§4: ctx.intro_beat is not game state and must not be captured."""
    intro_sequence.arm(ctx)
    payload = save_bridge.capture(ctx)
    assert "intro_beat" not in json.dumps(payload), \
        "the intro flag leaked into the save payload"


def test_the_pause_menu_load_entry_is_wired(ctx):
    """A cheap guard that Phase 5's entry survived every later phase."""
    assert ACTION_LOAD_GAME in ACTIONS

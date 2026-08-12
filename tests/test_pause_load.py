"""
tests/test_pause_load.py
Task 8 — LOAD GAME in the pause menu, and what a mid-session load leaves.

Two things worth proving. That the entry exists next to SAVE GAME and
routes to the SAME picker the title screen uses (no second load path,
G6). And that loading from inside a run replaces the run — the failure
mode here is not a crash, it is a loaded game quietly wearing a piece of
the abandoned one.

NOTHING IS WRITTEN TO saves/. Every context here gets its own
SaveManager pointed at a tempfile.mkdtemp() directory, so the real
slots — slot_3 in particular, which is the demo save — are never
touched.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame                                            # noqa: E402
import pytest                                            # noqa: E402

from engine import progression, save_bridge, skill_completion  # noqa: E402
from engine.app_context import AppContext                # noqa: E402
from engine.save_manager import SaveManager              # noqa: E402
from engine.screen_manager import ScreenState            # noqa: E402
from engine.states import load_game                      # noqa: E402
from ui import pause_menu                                # noqa: E402
from ui.pause_menu import (ACTIONS, ACTION_LOAD_GAME,    # noqa: E402
                           ACTION_SAVE_GAME, FILLS, LABELS, PauseMenu)

pygame.init()
pygame.display.set_mode((1280, 720))


@pytest.fixture
def ctx():
    """A started run whose saves go to a throwaway directory."""
    folder = tempfile.mkdtemp(prefix="cse_life_pause_")
    context = AppContext()
    context.saves = SaveManager(folder)
    save_bridge.new_game(context)
    try:
        yield context
    finally:
        shutil.rmtree(folder, ignore_errors=True)


# ── the menu entry ─────────────────────────────────────────────

def test_load_game_sits_next_to_save_game():
    """The brief's placement, asserted rather than eyeballed."""
    assert ACTION_LOAD_GAME in ACTIONS
    assert (ACTIONS.index(ACTION_LOAD_GAME)
            == ACTIONS.index(ACTION_SAVE_GAME) + 1)
    assert LABELS[ACTIONS.index(ACTION_LOAD_GAME)] == "LOAD GAME"


def test_the_three_parallel_tuples_stayed_in_step():
    """ACTIONS/LABELS/FILLS are index-matched; a short one draws wrong."""
    assert len(ACTIONS) == len(LABELS) == len(FILLS) == 7
    assert len(set(ACTIONS)) == len(ACTIONS), "a duplicate action id"


def test_every_button_fits_inside_the_card():
    """CARD_H had to grow for a seventh row — check it actually did."""
    menu = PauseMenu()
    card = menu.get_card_rect()
    rects = menu.get_button_rects()
    assert len(rects) == len(ACTIONS)
    for rect in rects:
        assert card.contains(rect), \
            "a button escaped the card: %r not inside %r" % (rect, card)
    assert rects[0].top - card.top == card.bottom - rects[-1].bottom, \
        "the button block is no longer vertically centred"


def test_the_menu_still_resolves_a_click_to_the_right_action():
    """Inserting mid-tuple must not shift what a row does."""
    menu = PauseMenu()
    menu.open()
    rects = menu.get_button_rects()
    index = ACTIONS.index(ACTION_LOAD_GAME)
    menu.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": rects[index].center}))
    assert menu.take_result() == ACTION_LOAD_GAME


# ── the routing ────────────────────────────────────────────────

def landed_on(context):
    """The state the router would move to next. ctx.go() only queues."""
    context.screen_mgr.apply_pending_transition()
    return context.screen_mgr.get_current_state()


def choose(context, action):
    """Open the pause menu and pick one action, as the player would."""
    progression.open_pause(context)
    menu = context.pause_menu
    index = ACTIONS.index(action)
    menu.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos":
                                 menu.get_button_rects()[index].center}))
    progression.resolve_pause(context)


def test_choosing_load_game_opens_the_shared_picker(ctx):
    ctx.screen_mgr.transition_to(ScreenState.EXPLORATION)
    choose(ctx, ACTION_LOAD_GAME)
    assert landed_on(ctx) is ScreenState.LOAD_GAME, \
        "LOAD GAME did not route to the save-slot picker"


def test_the_pause_overlay_is_torn_down_by_the_choice(ctx):
    """It must not survive on top of the picker, or the loaded run."""
    ctx.screen_mgr.transition_to(ScreenState.EXPLORATION)
    choose(ctx, ACTION_LOAD_GAME)
    assert not ctx.pause_menu.is_open(), "the pause overlay survived"
    assert not ctx.pause_menu.consumes_input(), "the overlay still eats input"


def test_backing_out_returns_to_the_map_not_the_title(ctx):
    """
    return_state is why this is safe from mid-session.

    load_game.py falls back to MAIN_MENU, which is right from the title
    screen and wrong from a run.
    """
    ctx.screen_mgr.transition_to(ScreenState.EXPLORATION)
    choose(ctx, ACTION_LOAD_GAME)
    assert ctx.return_state is ScreenState.EXPLORATION

    load_game.enter(ctx)
    load_game.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_ESCAPE})])
    assert landed_on(ctx) is ScreenState.EXPLORATION


# ── the load itself ────────────────────────────────────────────

def test_loading_mid_session_replaces_the_run(ctx):
    """
    Save a state, diverge from it, load it back from the pause menu, and
    check the divergence is gone rather than half-gone.
    """
    git = skill_completion.quest_for_skill("git")
    oop = skill_completion.quest_for_skill("oop")

    # -- the state we will come back to -------------------------
    ctx.quest_states.accept(git)
    ctx.quest_states.mark_completed(git)
    ctx.level_id = "player_room"
    assert ctx.saves.save(1, save_bridge.capture(ctx)), "the save failed"

    # -- diverge from it ----------------------------------------
    ctx.quest_states.accept(oop)
    ctx.quest_states.mark_completed(oop)
    ctx.level_id = "campus_main"
    ctx.dialogue_npc = object()
    ctx.quest_offer_open = True
    ctx.pending_quest_id = oop
    assert skill_completion.is_completed(ctx, "oop")

    # -- load it back through the pause menu --------------------
    ctx.screen_mgr.transition_to(ScreenState.EXPLORATION)
    choose(ctx, ACTION_LOAD_GAME)
    load_game.enter(ctx)
    ctx.load_selected = 0
    load_game.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN})])

    assert landed_on(ctx) is ScreenState.EXPLORATION, \
        "the load did not hand back the map"
    assert skill_completion.is_completed(ctx, "git"), "the save was not restored"
    assert not skill_completion.is_completed(ctx, "oop"), \
        "progress made after the save survived the load"
    assert ctx.level_id == "player_room", "the abandoned level survived"


def test_no_transient_screen_state_survives_the_load(ctx):
    """The specific staleness Task 8 asks to audit for."""
    assert ctx.saves.save(1, save_bridge.capture(ctx))

    ctx.dialogue_npc = object()
    ctx.dialogue_chain = object()
    ctx.choice_options = ["a", "b"]
    ctx.choice_prompt = "pick"
    ctx.quest_offer_open = True
    ctx.pending_quest_id = "SQ_OOP"
    ctx.endgame_result = "TOP GRADUATE"

    ctx.screen_mgr.transition_to(ScreenState.EXPLORATION)
    choose(ctx, ACTION_LOAD_GAME)
    load_game.enter(ctx)
    ctx.load_selected = 0
    load_game.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN})])

    assert ctx.dialogue_npc is None
    assert ctx.dialogue_chain is None
    assert ctx.choice_options == []
    assert ctx.choice_prompt == ""
    assert ctx.quest_offer_open is False
    assert ctx.pending_quest_id is None
    assert ctx.endgame_result is None
    assert ctx.level is None, "the old level document was kept"
    assert not ctx.pause_menu.is_open()


def test_the_load_uses_the_same_routine_as_the_title_screen(ctx):
    """
    G6: one load path, not two.

    engine/progression.py must not import or call save_bridge.restore()
    itself — its whole contribution is a ScreenState and a return_state.
    """
    import ast
    import inspect
    source = inspect.getsource(progression)
    # Parsed, not grepped: the branch's own comment names
    # save_bridge.restore() to explain why it does NOT call it, and a
    # substring check would read that comment as the offence.
    called = {node.func.attr
              for node in ast.walk(ast.parse(source))
              if isinstance(node, ast.Call)
              and isinstance(node.func, ast.Attribute)}
    assert "restore" not in called, "progression.py grew its own load path"
    assert "ScreenState.LOAD_GAME" in source

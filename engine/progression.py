"""
engine/progression.py
Where skill points come from, and the pause-menu action router.

POINTS ARE DERIVED, NOT STORED. A player has
    completed_courses * POINTS_PER_COURSE
points to spend, minus every level already invested. Nothing new goes in
the save file, and loading an old save computes the same number. Tune the
economy by changing POINTS_PER_COURSE and nothing else.
"""
from __future__ import annotations

from content.skill_tree_layout import SKILL_NODES
from engine.screen_manager import ScreenState
from ui.pause_menu import (
    ACTION_QUIT_TO_MENU, ACTION_RESUME, ACTION_SAVE_GAME, ACTION_SETTINGS,
    ACTION_SKILL_TREE, ACTION_STATS)
from ui.popup import SEVERITY_DANGER

POINTS_PER_COURSE: int = 2
CAREER_CAP_DAYS: int = 960          # GameSession.__GLOBAL_YEAR_CAP_DAYS
CREDIT_GOAL: int = 140              # EndgameEvaluationManager threshold


def total_invested(ctx) -> int:
    tree = ctx.player().get_skill_tree()
    if tree is None:
        return 0
    return sum(tree.get_skill_level(skill_id) for skill_id in SKILL_NODES)


def available_points(ctx) -> int:
    earned = len(ctx.history().get_completed_course_codes()) * \
        POINTS_PER_COURSE
    return max(0, earned - total_invested(ctx))


# TASK 4 — invest() IS DELETED.
#
# It spent one derived point to raise one skill node by one level, and
# was the game's only manual-investment path. Skills are binary now:
# `engine/skill_completion.py` answers "completed?" off the side quest's
# own state, and nothing raises a level any more.
#
# Its three callers all went with it — the ENTER/SPACE binding and the
# INVEST click in engine/states/skill_tree.py, and the button in
# ui/skill_tree_screen.py. Deleted rather than left retired (the
# treatment engine/ending_gate.py gave the average-skill helpers)
# because those were a teammate's public API in a file otherwise
# identical to main, and this is neither: progression.py is this
# branch's own file, and a live mutator left importable is a second
# entry point waiting to be called.
#
# `available_points()` above is KEPT. It reads nothing that changed, it
# is the honest answer to "how many course-derived points exist", and
# `total_invested()` still reports what old saves carry.


def skill_levels(ctx) -> dict:
    tree = ctx.player().get_skill_tree()
    if tree is None:
        return {}
    return {skill_id: tree.get_skill_level(skill_id)
            for skill_id in SKILL_NODES}


# ── pause menu ─────────────────────────────────────────────────

def open_pause(ctx) -> None:
    ctx.pause_menu.open()
    ctx.pause_focus = ctx.pause_menu.get_focused_index()
    ctx.play_sfx("click")


def resolve_pause(ctx) -> None:
    """
    Consume the pause menu's button. Call every frame from any state
    that can be paused. `ctx.return_state` is set so SETTINGS comes back
    to the state the player paused from.
    """
    if ctx.pause_menu is None:
        return
    ctx.pause_focus = ctx.pause_menu.get_focused_index()
    action = ctx.pause_menu.take_result()
    if action is None:
        return
    ctx.pause_menu.close()
    here = ctx.screen_mgr.get_current_state()

    if action == ACTION_RESUME:
        ctx.play_sfx("cancel")
    elif action == ACTION_SKILL_TREE:
        ctx.return_state = here
        ctx.go(ScreenState.SKILL_TREE)
    elif action == ACTION_STATS:
        ctx.return_state = here
        ctx.go(ScreenState.STATS)
    elif action == ACTION_SETTINGS:
        ctx.return_state = here
        ctx.go(ScreenState.SETTINGS)
    elif action == ACTION_SAVE_GAME:
        # The player picks the slot now. This used to write the autosave
        # here and say so in a popup, which gave the player one file they
        # never chose and could not keep.
        ctx.return_state = here
        ctx.go(ScreenState.SAVE_GAME)
    elif action == ACTION_QUIT_TO_MENU:
        __autosave(ctx)
        ctx.go(ScreenState.MAIN_MENU)


def __autosave(ctx) -> None:
    """
    Write the autosave slot on the way out of a run.

    Silent when it works: the player asked to quit, not to be told
    about a file, and the notice would land on top of the title screen
    they are already looking at. A failure still speaks up -- that is
    the one case where quitting has lost something.
    [Sprint 4 — manual save slots]
    """
    from engine import save_bridge
    if ctx.saves.autosave(save_bridge.capture(ctx)):
        return
    ctx.play_sfx("error")
    ctx.message_popup.open(
        "SAVE FAILED",
        [ctx.saves.get_last_error()[:48] or "Could not write."],
        SEVERITY_DANGER)

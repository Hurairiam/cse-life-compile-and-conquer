"""
engine/save_bridge.py
Turns the live game into a save dict and back again.

Restore builds a FRESH GameSession, GameClock, RegistrationManager and
course catalog, then replays the saved facts onto them with public
mutators only. A fresh catalog matters: Course objects carry completed/
backlogged flags and are reused across the whole run, so loading into
the old catalog would inherit the previous playthrough's marks.
"""
from __future__ import annotations

from academic.course_catalog import build_course_catalog, get_course_by_code
from academic.semester import Semester
from engine.game_clock import GameClock
from engine.game_session import GameSession
from engine.registration_manager import RegistrationManager
from engine.save_manager import build_state

TRACKED_SKILL_IDS = (
    "programming_language", "dsa", "git", "linux_cli", "databases_sql",
    "networking", "web_app_dev", "docker", "ai_tools", "debugging_testing",
    "oop", "technical_communication",
)

GRADUATION_CREDITS = 140


def skills_of(player) -> dict:
    """{skill_id: level} over the twelve tracked skills, zeros included."""
    tree = player.get_skill_tree()
    if tree is None:
        return {}
    return {sid: tree.get_skill_level(sid) for sid in TRACKED_SKILL_IDS}


def capture(ctx) -> dict:
    """Snapshot the live game as a save-state dict."""
    player = ctx.player()
    semester = ctx.semester()
    history = ctx.history()
    spawn = (0, 0)
    if ctx.walker is not None:
        spawn = ctx.walker.get_cell()
    return build_state(
        display_name=player.get_display_name(),
        character_id=player.get_character_id(),
        wallet_balance=player.get_wallet_balance(),
        accumulated_credits=player.get_accumulated_credits(),
        current_semester=semester.get_semester_number(),
        has_graduated=player.get_accumulated_credits() >= GRADUATION_CREDITS,
        skills=skills_of(player),
        time_pool_days=semester.get_time_pool_days(),
        registered_course_codes=[c.get_course_code()
                                 for c in semester.get_registered_courses()],
        completed_course_codes=list(history.get_completed_course_codes()),
        backlog_course_codes=list(history.get_backlog_courses()),
        level_id=ctx.level_id or "campus_main",
        spawn_x=spawn[0], spawn_y=spawn[1],
        triggered_prop_uids=sorted(ctx.triggered_prop_uids),
        talked_npc_uids=sorted(ctx.talked_npc_uids),
        global_career_clock_days=ctx.session.get_global_career_clock_days(),
        playtime_seconds=int(ctx.playtime_seconds),
    )


def restore(ctx, state: dict) -> bool:
    """Rebuild the whole game from a save dict. False if the dict is junk."""
    if not isinstance(state, dict):
        return False
    p = state.get("player") or {}
    s = state.get("semester") or {}
    a = state.get("academic") or {}
    w = state.get("world") or {}
    c = state.get("clock") or {}

    # -- fresh systems ------------------------------------------
    ctx.full_catalog = build_course_catalog()
    ctx.session = GameSession()
    ctx.game_clock = GameClock(ctx.session)
    ctx.registration_manager = RegistrationManager()
    player = ctx.session.get_active_player()

    # -- semester number (advance_semester is the only mutator) --
    target = max(1, int(p.get("current_semester", 1) or 1))
    while player.get_current_semester() < target:
        player.advance_semester()
    semester = Semester(target)
    ctx.session.set_active_semester(semester)

    # -- wallet: adjust from whatever the fresh Player starts at -
    wanted = float(p.get("wallet_balance", 0.0) or 0.0)
    delta = wanted - player.get_wallet_balance()
    if delta > 0:
        player.deposit_funds(delta)
    elif delta < 0:
        player.withdraw_funds(-delta)

    player.add_credits(int(p.get("accumulated_credits", 0) or 0))

    tree = player.get_skill_tree()
    for skill_id, level in (p.get("skills") or {}).items():
        try:
            tree.increment_skill(str(skill_id), int(level))
        except (TypeError, ValueError):
            continue

    # -- academic history; flags live on the Course objects ------
    history = player.get_academic_history()
    for code in a.get("completed_course_codes") or []:
        course = get_course_by_code(ctx.full_catalog, code)
        if course is not None:
            course.mark_completed()
            history.record_completion(course)
    for code in a.get("backlog_course_codes") or []:
        course = get_course_by_code(ctx.full_catalog, code)
        if course is not None:
            course.mark_backlogged()
            history.add_backlog(course)

    for code in s.get("registered_course_codes") or []:
        course = get_course_by_code(ctx.full_catalog, code)
        if course is not None:
            semester.register_course(course)

    spent = semester.get_max_time_pool_days() - int(s.get("time_pool_days", 80))
    if spent > 0:
        semester.deduct_time(spent)

    ctx.session.increment_global_clock(
        int(c.get("global_career_clock_days", 0) or 0))

    # -- world bookkeeping (consumed by STAGE 5) -----------------
    ctx.level_id = w.get("level_id") or "campus_main"
    ctx.pending_spawn = (int(w.get("spawn_x", 0) or 0),
                         int(w.get("spawn_y", 0) or 0))
    ctx.triggered_prop_uids = set(w.get("triggered_prop_uids") or [])
    ctx.talked_npc_uids = set(w.get("talked_npc_uids") or [])
    ctx.level = None                 # STAGE 5 reloads from ctx.level_id

    # -- reset transient screen state ---------------------------
    ctx.playtime_seconds = float(state.get("playtime_seconds", 0) or 0)
    ctx.exam = {"course_index": 0, "tier_index": 0,
                "answers": {}, "message": None}
    ctx.endgame_result = None
    ctx.reg_scroll = 0
    return True


def new_game(ctx) -> None:
    """Reset everything to a first-boot state without restarting the app."""
    restore(ctx, build_state())
    ctx.level_id = "campus_main"
    ctx.pending_spawn = None

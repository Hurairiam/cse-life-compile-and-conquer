"""
The graduation certificate / record of attendance — the artefact the run
leaves behind. Last screen of the game; ESC or the continue hint returns
to the title screen so a new run can start without restarting the app.
"""
import pygame

from engine import progression
from engine.screen_manager import ScreenState

CREDIT_GOAL = 140
DAY_CAP = 960            # GameSession.__GLOBAL_YEAR_CAP_DAYS


def __title(ctx):
    result = ctx.endgame_result or {}
    return str(result.get("epilogue_title", ""))


def enter(ctx):
    ctx.certificate.reset()
    ctx.certificate.enter(__title(ctx))


def handle_events(ctx, events):
    for event in events:
        if event.type == pygame.KEYDOWN or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            __restart(ctx)
            return


def __restart(ctx):
    from engine import save_bridge
    ctx.play_sfx("confirm")
    save_bridge.new_game(ctx)
    ctx.menu_focus = 0
    ctx.go(ScreenState.MAIN_MENU)


def render(ctx, screen):
    player = ctx.player()
    credits = player.get_accumulated_credits()
    ctx.certificate.render(
        screen,
        ending_title=__title(ctx),
        player_name=player.get_display_name(),
        student_id=player.get_character_id(),
        credits=credits,
        credit_goal=CREDIT_GOAL,
        days_used=ctx.session.get_global_career_clock_days(),
        day_cap=DAY_CAP,
        wallet=player.get_wallet_balance(),
        skills=progression.skill_levels(ctx),
        is_graduated=credits >= CREDIT_GOAL,
    )

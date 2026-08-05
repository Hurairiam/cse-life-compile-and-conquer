"""Player profile / transcript. Read-only; every value is a parameter."""
import pygame

from engine import progression
from engine.screen_manager import ScreenState


def __leave(ctx):
    ctx.play_sfx("cancel")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def handle_events(ctx, events):
    for event in events:
        if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_TAB, pygame.K_RETURN):
            __leave(ctx)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if ctx.stats_screen.get_back_rect().collidepoint(event.pos):
                __leave(ctx)
                return


def render(ctx, screen):
    player = ctx.player()
    semester = ctx.semester()
    history = ctx.history()
    ctx.stats_screen.render(
        screen,
        display_name=player.get_display_name(),
        student_id=player.get_character_id(),
        semester=semester.get_semester_number(),
        days_remaining=semester.get_time_pool_days(),
        day_pool=semester.get_max_time_pool_days(),
        credits_earned=player.get_accumulated_credits(),
        credit_goal=progression.CREDIT_GOAL,
        career_days=ctx.session.get_global_career_clock_days(),
        career_cap=progression.CAREER_CAP_DAYS,
        wallet=player.get_wallet_balance(),
        skills=progression.skill_levels(ctx),
        completed_count=len(history.get_completed_course_codes()),
        backlog_courses=list(history.get_backlog_courses()),
    )

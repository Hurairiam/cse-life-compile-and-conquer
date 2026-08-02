"""
The PASS / FAIL card shown after each course's exam. Any key or a click
inside the card moves to the next course (or back to the map).
"""
import pygame

from engine.screen_manager import ScreenState
from ui.exam_result_screen import (
    ExamResultScreen, TITLE_FAILED, TITLE_PASSED)

BG = (231, 214, 189)

FLAVOUR_PASS = ("The course is signed off.",
                "Credits are on your transcript.")
FLAVOUR_FAIL = ("The course carries over.",
                "It will be waiting next term.")


def __ui(ctx):
    if ctx.exam_result_screen is None:
        ctx.exam_result_screen = ExamResultScreen(audio=ctx.audio)
    return ctx.exam_result_screen


def __title(ctx):
    result = ctx.exam_result
    if result is not None and result.is_passed():
        return TITLE_PASSED
    return TITLE_FAILED


def enter(ctx):
    __ui(ctx).reset()
    __ui(ctx).enter(__title(ctx))
    ctx.play_sfx("pass" if __title(ctx) == TITLE_PASSED else "fail")


def handle_events(ctx, events):
    for event in events:
        if event.type == pygame.KEYDOWN or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            __advance(ctx)
            return


def __advance(ctx):
    ctx.exam["course_index"] += 1
    ctx.exam["answers"] = {}
    ctx.exam["tier_index"] = 0
    ctx.exam_result = None
    ctx.exam_session = None
    ctx.play_sfx("page_turn")
    ctx.go(ScreenState.EXAM)


def render(ctx, screen):
    result = ctx.exam_result
    if result is None:
        screen.fill(BG)
        return
    title = __title(ctx)
    __ui(ctx).render(
        screen,
        title=title,
        course_code=result.get_course_code(),
        per_tier=result.get_per_tier_outcome(),
        time_cost_days=result.get_time_cost_days(),
        credits_awarded=result.get_credits_awarded(),
        is_optimized=result.is_optimized(),
        flavour_lines=FLAVOUR_PASS if title == TITLE_PASSED else FLAVOUR_FAIL,
    )

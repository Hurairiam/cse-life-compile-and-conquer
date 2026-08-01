"""
The ceremonial between-semesters card, and the one that opens the game.

Contract used by every caller:
    ctx.monologue_title / ctx.monologue_subtitle / ctx.monologue_lines
        the beat to show (set by start_opening() / start_semester())
    ctx.monologue_next
        the ScreenState to enter once the player dismisses it

First press completes the reveal, second press advances — that is
skip_to_end() returning True then False, in that order.
"""
import pygame

from engine.screen_manager import ScreenState
from ui.monologue_screen import (
    MonologueScreen, build_opening_beat, build_semester_beat)

__screen = None


def __ui(ctx):
    global __screen
    if __screen is None:
        __screen = MonologueScreen(ctx.screen_w, ctx.screen_h, audio=ctx.audio)
    return __screen


def start_opening(ctx, next_state=None):
    """Queue the game's opening beat. Call before ctx.go(MONOLOGUE)."""
    title, subtitle, lines = build_opening_beat()
    __arm(ctx, title, subtitle, lines, next_state)


def start_semester(ctx, semester_number, next_state=None):
    """Queue semester N's beat. Call before ctx.go(MONOLOGUE)."""
    title, subtitle, lines = build_semester_beat(int(semester_number))
    __arm(ctx, title, subtitle, lines, next_state)


def __arm(ctx, title, subtitle, lines, next_state):
    ctx.monologue_title = title
    ctx.monologue_subtitle = subtitle
    ctx.monologue_lines = list(lines)
    if next_state is not None:
        ctx.monologue_next = next_state


def enter(ctx):
    __ui(ctx).reset()
    if not ctx.monologue_lines:
        start_semester(ctx, ctx.semester().get_semester_number())
    ctx.play_music("dialogue")


def __advance(ctx):
    ui = __ui(ctx)
    if ui.skip_to_end():
        return                                   # first press: finish reveal
    ctx.play_sfx("page_turn")
    ctx.monologue_lines = []
    ctx.go(ctx.monologue_next or ScreenState.REGISTRATION)


def handle_events(ctx, events):
    ui = __ui(ctx)
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                ctx.quit()
                return
            __advance(ctx)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if ui.get_continue_rect().collidepoint(event.pos):
                __advance(ctx)
                return


def update(ctx, dt):
    __ui(ctx).update(dt)


def render(ctx, screen):
    ui = __ui(ctx)
    ui.render(screen, ctx.monologue_title, ctx.monologue_subtitle,
              ctx.monologue_lines, ui.get_revealed_chars())

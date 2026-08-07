"""
engine/states/cutscene.py

Displays a cinematic text cutscene over a blurred snapshot of the
current map.

Uses MonologueScreen for the UI while keeping the Exploration screen
visible underneath as a blurred background.
"""

import pygame
import textwrap

from content.dialogues import CUTSCENES
from engine.screen_manager import ScreenState
from ui.monologue_screen import MonologueScreen

__screen = None
__blurred_bg = None


def __ui(ctx):
    global __screen
    if __screen is None:
        __screen = MonologueScreen(
            ctx.screen_w,
            ctx.screen_h,
            audio=ctx.audio
        )
    return __screen


def __make_blur(surface):
    """
    Creates a cheap blur by shrinking then enlarging the map snapshot.
    """
    w, h = surface.get_size()

    small = pygame.transform.smoothscale(surface, (w // 8, h // 8))
    blurred = pygame.transform.smoothscale(small, (w, h))

    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    blurred.blit(overlay, (0, 0))

    return blurred


def __data(ctx):
    return CUTSCENES.get(
        ctx.semester().get_semester_number(),
        {"title": "", "lines": []}
    )
def __wrapped_lines(lines):
    wrapped = []

    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=72))

    return wrapped

def enter(ctx):
    global __blurred_bg

    from engine.states import exploration

    # Make sure the player's room exists.
    exploration.ensure_level(ctx)

    ui = __ui(ctx)
    ui.reset()

    # Draw the room onto an off-screen surface.
    exploration.render(ctx, ctx.snapshot_surface)

    # Blur it.
    __blurred_bg = __make_blur(ctx.snapshot_surface)


def __advance(ctx):
    ui = __ui(ctx)
    data = __data(ctx)
    wrapped = __wrapped_lines(data["lines"])

    if not ui.is_fully_revealed(wrapped):
        ui.skip_to_end()
        return

    ctx.go(ScreenState.EXPLORATION)


def handle_events(ctx, events):
    for event in events:

        if event.type == pygame.KEYDOWN:

            if event.key in (
                pygame.K_SPACE,
                pygame.K_RETURN,
                pygame.K_ESCAPE,
            ):
                __advance(ctx)

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            __advance(ctx)


def update(ctx, dt):
    __ui(ctx).update(dt)


def render(ctx, screen):

    if __blurred_bg is not None:
        screen.blit(__blurred_bg, (0, 0))

    data = __data(ctx)

    __ui(ctx).render(
        screen,
        data["title"],
        "",
            __wrapped_lines(data["lines"]),
        __ui(ctx).get_revealed_chars(),
    )
"""Epilogue. STAGE 9 adds the certificate hand-off."""
import pygame
from ui.endgame_screen import EndgameScreen

__screen = None


def enter(ctx):
    global __screen
    if __screen is None:
        __screen = EndgameScreen()
    if ctx.endgame_result is None:
        manager = ctx.session.trigger_endgame_evaluation()
        ctx.endgame_result = manager.evaluate(ctx.player())
    ctx.play_music("endgame")


def handle_events(ctx, events):
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            ctx.quit()


def render(ctx, screen):
    if __screen is not None and ctx.endgame_result is not None:
        __screen.render(screen, **ctx.endgame_result)

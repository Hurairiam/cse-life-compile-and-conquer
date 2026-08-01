"""NPC dialogue. STAGE 4 upgrades this to ui/dialog_box.py + choices."""
import pygame
from engine.screen_manager import ScreenState

BG = (20, 24, 38)


def handle_events(ctx, events):
    for event in events:
        advance = (
            (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE)
            or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1))
        if advance and not ctx.dialogue_manager.advance():
            ctx.go(ctx.dialogue_return or ScreenState.EXPLORATION)


def update(ctx, dt):
    ctx.dialogue_manager.update(dt)


def render(ctx, screen):
    screen.fill(BG)
    ctx.dialogue_manager.render(screen)

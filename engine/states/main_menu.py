"""Title screen — ui/main_menu_screen.py driven."""
import pygame

from engine import save_bridge
from engine.app_context import VERSION
from engine.screen_manager import ScreenState
from ui.main_menu_screen import (
    MainMenuScreen, START_GAME, LOAD_GAME, SETTINGS, EXIT)

__screen = None


def __ui(ctx):
    global __screen
    if __screen is None:
        __screen = MainMenuScreen(ctx.screen_w, ctx.screen_h, audio=ctx.audio)
    return __screen


def enter(ctx):
    __ui(ctx)
    # Music is set centrally by engine/soundtrack.py via the router:
    # every screen takes the "menu" track except EXAM, which is silent.


def __activate(ctx, index):
    ui = __ui(ctx)
    ui.notify_activated()
    if index == START_GAME:
        save_bridge.new_game(ctx)
        from engine.states import monologue
        monologue.start_opening(ctx, ScreenState.REGISTRATION)
        ctx.go(ScreenState.MONOLOGUE)
    elif index == LOAD_GAME:
        ctx.return_state = ScreenState.MAIN_MENU
        ctx.go(ScreenState.LOAD_GAME)
    elif index == SETTINGS:
        ctx.return_state = ScreenState.MAIN_MENU
        ctx.go(ScreenState.SETTINGS)
    elif index == EXIT:
        ctx.quit()


def handle_events(ctx, events):
    ui = __ui(ctx)
    count = len(ui.get_button_rects())
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                ctx.menu_focus = (ctx.menu_focus + 1) % count
                ctx.play_sfx("select")
            elif event.key in (pygame.K_UP, pygame.K_w):
                ctx.menu_focus = (ctx.menu_focus - 1) % count
                ctx.play_sfx("select")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                __activate(ctx, ctx.menu_focus)
                return
            elif event.key == pygame.K_ESCAPE:
                ctx.quit()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = ui.get_button_index_at(event.pos)
            if index >= 0:
                ctx.menu_focus = index
                __activate(ctx, index)
                return
        elif event.type == pygame.MOUSEMOTION:
            index = ui.get_button_index_at(event.pos)
            if index >= 0 and index != ctx.menu_focus:
                ctx.menu_focus = index


def render(ctx, screen):
    __ui(ctx).render(screen, ctx.menu_focus, VERSION)

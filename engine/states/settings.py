"""
Settings screen. Reached from the main menu (STAGE 3) and the pause
menu (STAGE 8). ctx.return_state says where BACK/APPLY goes.

Live-edit model: the sliders and chips write straight into ctx, so the
change is audible immediately. APPLY persists to settings.json and
re-opens the window if the display mode changed. BACK reverts to the
values that were on disk when the screen was entered.
"""
import pygame

from engine import settings_store
from engine.screen_manager import ScreenState
from ui.settings_screen import (
    SettingsScreen, value_from_x, VOLUME_STEP)

__screen = None
__before = None


def __ui(ctx):
    global __screen
    if __screen is None:
        __screen = SettingsScreen(ctx.screen_w, ctx.screen_h, audio=ctx.audio)
    return __screen


def enter(ctx):
    global __before
    __ui(ctx)
    __before = settings_store.capture(ctx)


def __push(ctx):
    if ctx.audio is not None:
        ctx.audio.set_music_volume(ctx.music_volume)
        ctx.audio.set_sfx_volume(ctx.sfx_volume)


def __leave(ctx):
    ctx.go(ctx.return_state or ScreenState.MAIN_MENU)


def handle_events(ctx, events):
    ui = __ui(ctx)
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            __revert(ctx)
            __leave(ctx)
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            continue
        pos = event.pos

        if ui.get_music_track_rect().collidepoint(pos):
            ctx.music_volume = value_from_x(ui.get_music_track_rect(), pos[0])
            __push(ctx)
        elif ui.get_sfx_track_rect().collidepoint(pos):
            ctx.sfx_volume = value_from_x(ui.get_sfx_track_rect(), pos[0])
            __push(ctx)
            ctx.play_sfx("click")
        elif ui.get_windowed_chip_rect().collidepoint(pos):
            ctx.is_fullscreen = False
            ui.notify_clicked()
        elif ui.get_fullscreen_chip_rect().collidepoint(pos):
            ctx.is_fullscreen = True
            ui.notify_clicked()
        elif ui.get_apply_rect().collidepoint(pos):
            settings_store.apply_display(ctx)
            settings_store.apply_all(ctx)
            settings_store.save(settings_store.capture(ctx))
            ctx.play_sfx("confirm")
            __leave(ctx)
            return
        elif ui.get_back_rect().collidepoint(pos):
            ctx.play_sfx("cancel")
            __revert(ctx)
            __leave(ctx)
            return
        else:
            speed = ui.get_text_speed_at(pos)
            if speed:
                ctx.text_speed = speed
                settings_store.apply_text_speed(speed)
                ui.notify_clicked()


def __revert(ctx):
    if __before is None:
        return
    ctx.music_volume = __before["music_volume"]
    ctx.sfx_volume = __before["sfx_volume"]
    ctx.text_speed = __before["text_speed"]
    ctx.is_fullscreen = __before["fullscreen"]
    settings_store.apply_all(ctx)


def render(ctx, screen):
    __ui(ctx).render(screen, ctx.music_volume, ctx.sfx_volume,
                     ctx.is_fullscreen, ctx.text_speed)

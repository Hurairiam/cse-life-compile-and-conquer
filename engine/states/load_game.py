"""Save-slot browser. LOAD rehydrates the whole game via save_bridge."""
import pygame

from engine import save_bridge
from engine.screen_manager import ScreenState
from ui.load_game_screen import LoadGameScreen, format_slot_row
from ui.popup import RESULT_CONFIRM, SEVERITY_DANGER, SEVERITY_INFO

__screen = None
__slots = []


def __ui(ctx):
    global __screen
    if __screen is None:
        __screen = LoadGameScreen(ctx.screen_w, ctx.screen_h, audio=ctx.audio)
    return __screen


def __refresh(ctx):
    global __slots
    __slots = ctx.saves.list_slots()


def enter(ctx):
    __ui(ctx)
    __refresh(ctx)
    ctx.load_selected = 0
    ctx.pending_save_slot = None


def __selected(ctx):
    if 0 <= ctx.load_selected < len(__slots):
        return __slots[ctx.load_selected]
    return None


def __do_load(ctx):
    slot = __selected(ctx)
    if slot is None or slot.is_empty() or slot.is_corrupt():
        ctx.play_sfx("error")
        return
    payload = ctx.saves.load(slot.get_slot_id())
    if payload is None or not save_bridge.restore(ctx, payload):
        ctx.message_popup.open(
            "LOAD FAILED",
            [ctx.saves.get_last_error()[:48] or "Unreadable save."],
            SEVERITY_DANGER)
        ctx.play_sfx("error")
        return
    ctx.play_sfx("confirm")
    ctx.go(ScreenState.EXPLORATION)


def handle_events(ctx, events):
    ui = __ui(ctx)
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                ctx.go(ctx.return_state or ScreenState.MAIN_MENU)
                return
            if event.key == pygame.K_DOWN:
                ctx.load_selected = min(
                    len(__slots) - 1, ctx.load_selected + 1)
                ui.notify_selected()
            elif event.key == pygame.K_UP:
                ctx.load_selected = max(0, ctx.load_selected - 1)
                ui.notify_selected()
            elif event.key == pygame.K_RETURN:
                __do_load(ctx)
                return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            index = ui.get_row_index_at(pos, len(__slots))
            if index >= 0:
                ctx.load_selected = index
                ui.notify_selected()
            elif ui.get_load_rect().collidepoint(pos):
                __do_load(ctx)
                return
            elif ui.get_delete_rect().collidepoint(pos):
                slot = __selected(ctx)
                if slot is not None and not slot.is_empty():
                    ctx.pending_save_slot = slot.get_slot_id()
                    ctx.popup.open("DELETE SAVE?",
                                   ["%s will be erased." % slot.get_label(),
                                    "This cannot be undone."],
                                   SEVERITY_DANGER)
                else:
                    ctx.play_sfx("error")
            elif ui.get_back_rect().collidepoint(pos):
                ctx.play_sfx("cancel")
                ctx.go(ctx.return_state or ScreenState.MAIN_MENU)
                return


def update(ctx, dt):
    result = ctx.popup.take_result()
    if result is None:
        return
    if result == RESULT_CONFIRM and ctx.pending_save_slot is not None:
        ctx.saves.delete(ctx.pending_save_slot)
        __refresh(ctx)
        ctx.load_selected = min(ctx.load_selected, max(0, len(__slots) - 1))
        ctx.play_sfx("confirm")
    ctx.pending_save_slot = None


def render(ctx, screen):
    slot = __selected(ctx)
    usable = slot is not None and not slot.is_empty() and not slot.is_corrupt()
    __ui(ctx).render(screen,
                     [format_slot_row(s) for s in __slots],
                     ctx.load_selected,
                     can_load=usable,
                     can_delete=slot is not None and not slot.is_empty())

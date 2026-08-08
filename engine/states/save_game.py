"""
The save-slot picker the pause menu's SAVE GAME opens.

Before this screen existed, SAVE GAME wrote straight to the autosave
slot -- one file the player never chose and could not keep. The three
manual slots were there the whole time (save_manager.SAVE_SLOTS = 3);
nothing had ever offered them.

ONLY THE MANUAL SLOTS ARE LISTED. The autosave is not a slot the
player controls: QUIT TO MENU overwrites it on the way out, so a save
placed there by hand would not survive the next quit. It stays
readable on the LOAD GAME screen, which still lists all four.

Writing an occupied slot asks first (ui.popup.ConfirmPopup, the same
modal DELETE SAVE? uses). An empty one is written immediately -- there
is nothing to lose and nothing to warn about.

The table is ui/load_game_screen.py under another title. Same rows,
same rects, same geometry; only the heading and the green button's
word differ, both passed into render().
"""
import pygame

from engine import save_bridge
from engine.screen_manager import ScreenState
from ui.load_game_screen import (
    LoadGameScreen, SAVE_CONFIRM_TEXT, SAVE_TITLE_TEXT, format_slot_row,
    format_slot_summary)
from ui.popup import (
    RESULT_CONFIRM, SEVERITY_DANGER, SEVERITY_INFO, SEVERITY_WARNING)

__screen = None
__slots = []
__selected = 0


def __ui(ctx):
    global __screen
    if __screen is None:
        __screen = LoadGameScreen(ctx.screen_w, ctx.screen_h, audio=ctx.audio)
    return __screen


def __refresh(ctx):
    """Re-read the manual slots from disk, autosave filtered out."""
    global __slots
    __slots = [slot for slot in ctx.saves.list_slots()
               if not slot.is_autosave()]


def enter(ctx):
    global __selected
    __ui(ctx)
    __refresh(ctx)
    # Selection is module-level rather than on ctx: ctx.load_selected
    # belongs to the LOAD GAME screen, and the two must not drag each
    # other's highlight around.
    __selected = 0
    ctx.pending_save_slot = None


def __chosen():
    if 0 <= __selected < len(__slots):
        return __slots[__selected]
    return None


def __leave(ctx):
    """Back to whatever the player paused from."""
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def __write(ctx, slot_id):
    """Capture the live game into one slot and report the outcome."""
    ok = ctx.saves.save(slot_id, save_bridge.capture(ctx))
    if not ok:
        # Stay on the picker: the player can try another slot rather
        # than being dropped back into the world with nothing saved.
        ctx.play_sfx("error")
        ctx.message_popup.open(
            "SAVE FAILED",
            [ctx.saves.get_last_error()[:48] or "Could not write."],
            SEVERITY_DANGER)
        return
    ctx.play_sfx("confirm")
    ctx.message_popup.open("GAME SAVED",
                           ["%s updated." % __label(slot_id),
                            "Load it from the title screen."],
                           SEVERITY_INFO)
    __leave(ctx)


def __label(slot_id):
    """The row label for a slot id, without re-reading the disk."""
    for slot in __slots:
        if slot.get_slot_id() == slot_id:
            return slot.get_label()
    return "SLOT %d" % slot_id


def __save_selected(ctx):
    """SAVE on the highlighted row: write it, or ask before overwriting."""
    slot = __chosen()
    if slot is None:
        ctx.play_sfx("error")
        return
    if slot.is_empty():
        __write(ctx, slot.get_slot_id())
        return
    # A corrupt file counts as occupied -- it is still something the
    # player would be throwing away, and is_empty() reports it empty.
    ctx.pending_save_slot = slot.get_slot_id()
    # Amber, with the default terracotta confirm button: this is the
    # UNSAVED CHANGES / DISCARD THEM? shape, not the ENTER LAB BLOCK?
    # one. The player gains a save but loses the one already there.
    ctx.popup.open("OVERWRITE %s?" % slot.get_label(),
                   [format_slot_summary(slot),
                    "This cannot be undone."],
                   SEVERITY_WARNING,
                   confirm_label="OVERWRITE")


def handle_events(ctx, events):
    global __selected
    ui = __ui(ctx)
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                ctx.play_sfx("cancel")
                __leave(ctx)
                return
            if event.key == pygame.K_DOWN:
                __selected = min(len(__slots) - 1, __selected + 1)
                ui.notify_selected()
            elif event.key == pygame.K_UP:
                __selected = max(0, __selected - 1)
                ui.notify_selected()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                __save_selected(ctx)
                return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            index = ui.get_row_index_at(pos, len(__slots))
            if index >= 0:
                __selected = index
                ui.notify_selected()
            elif ui.get_load_rect().collidepoint(pos):
                __save_selected(ctx)
                return
            elif ui.get_delete_rect().collidepoint(pos):
                # Drawn muted here: deleting belongs to LOAD GAME, and
                # overwriting already covers everything it would do.
                ctx.play_sfx("error")
            elif ui.get_back_rect().collidepoint(pos):
                ctx.play_sfx("cancel")
                __leave(ctx)
                return


def update(ctx, dt):
    result = ctx.popup.take_result()
    if result is None:
        return
    if result == RESULT_CONFIRM and ctx.pending_save_slot is not None:
        slot_id = ctx.pending_save_slot
        ctx.pending_save_slot = None
        __write(ctx, slot_id)
        return
    ctx.pending_save_slot = None


def render(ctx, screen):
    __ui(ctx).render(screen,
                     [format_slot_row(slot) for slot in __slots],
                     __selected,
                     can_load=True,
                     can_delete=False,
                     title=SAVE_TITLE_TEXT,
                     confirm_label=SAVE_CONFIRM_TEXT)

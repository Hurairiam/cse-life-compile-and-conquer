"""
The exam / lecture / cancel choice a classroom prop opens.

Reached through the normal menu-prop path: a prop whose interaction
kind is "menu" and whose menu id is "activity" routes here, so an
author wires a lectern up entirely from the level editor.

    START EXAM     -> ScreenState.EXAM
    START LECTURE  -> nothing yet, deliberately (see below)
    CANCEL         -> back to wherever the player came from

The lecture branch is a live, focusable, clickable button that
currently only reports itself. That is the owner's ruling: the lecture
scripts do not exist yet, and a button wired to a screen that is not
written would either crash or silently do nothing. It is one line to
point at once those files land -- see __start_lecture.
"""
import pygame

from engine.screen_manager import ScreenState
from ui.activity_choice_screen import (
    ENTRIES, ENTRY_CANCEL, ENTRY_EXAM, ENTRY_LECTURE,
)
from ui.popup import SEVERITY_INFO

# Not yet routable. Listed here rather than hard-coded at the two
# places that care, so wiring the lecture up is a single deletion.
UNAVAILABLE = (ENTRY_LECTURE,)


def enter(ctx):
    """Focus the first entry each time the card opens."""
    ctx.activity_focus = 0


def __leave(ctx):
    """Close the card and hand control back to the map."""
    ctx.play_sfx("cancel")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def __start_exam(ctx):
    """Send the player into the exam phase."""
    ctx.play_sfx("confirm")
    # return_state is left alone: the exam decides where it goes next
    # (result card, then registration or the map), and overwriting it
    # here would send the player back to this card afterwards.
    ctx.go(ScreenState.EXAM)


def __start_lecture(ctx):
    """
    The lecture is not built yet.

    Replace this body with `ctx.go(ScreenState.LECTURE)` (and drop
    ENTRY_LECTURE from UNAVAILABLE) once the lecture state exists.
    """
    ctx.play_sfx("error")
    ctx.message_popup.open(
        "NOT YET",
        ["Lectures are not implemented yet.",
         "This button is wired and waiting."], SEVERITY_INFO)


def __choose(ctx, index):
    """Act on an entry by index. Unavailable entries are refused."""
    key = ENTRIES[index][0] if 0 <= index < len(ENTRIES) else ""
    if key == ENTRY_CANCEL:
        __leave(ctx)
    elif key == ENTRY_EXAM:
        __start_exam(ctx)
    elif key == ENTRY_LECTURE:
        __start_lecture(ctx)


def handle_events(ctx, events):
    """Arrows or mouse to move the focus, ENTER or click to commit."""
    count = len(ENTRIES)
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                ctx.activity_focus = (ctx.activity_focus + 1) % count
                ctx.play_sfx("select")
            elif event.key in (pygame.K_UP, pygame.K_w):
                ctx.activity_focus = (ctx.activity_focus - 1) % count
                ctx.play_sfx("select")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                __choose(ctx, ctx.activity_focus)
                return
            elif event.key == pygame.K_ESCAPE:
                __leave(ctx)
                return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = ctx.activity_screen.get_entry_at(
                pygame.display.get_surface(), event.pos)
            if index >= 0:
                ctx.activity_focus = index
                __choose(ctx, index)
                return
        elif event.type == pygame.MOUSEMOTION:
            index = ctx.activity_screen.get_entry_at(
                pygame.display.get_surface(), event.pos)
            # Focus follows the cursor, but SILENTLY: a hover is not a
            # choice, and ticking on it turns a mouse sweep into noise.
            if index >= 0:
                ctx.activity_focus = index


def render(ctx, screen):
    """
    Draw the map, then the card over it.

    The map is redrawn here rather than left over from the previous
    frame because the router only renders the ACTIVE state -- without
    this the card would sit on whatever was last flipped to the screen.
    Exploration's render is pure drawing, so calling it is safe.
    """
    from engine.states import exploration
    if getattr(ctx, "level", None) is not None:
        exploration.render(ctx, screen)
    ctx.activity_screen.render(
        screen,
        focused_index=getattr(ctx, "activity_focus", 0),
        disabled=UNAVAILABLE,
    )

"""
The exam / lecture / cancel choice a classroom prop opens.

Reached through the normal menu-prop path: a prop whose interaction
kind is "menu" and whose menu id is "activity" routes here, so an
author wires a lectern up entirely from the level editor.

    START EXAM     -> ScreenState.EXAM
    START LECTURE  -> ScreenState.LECTURE
    CANCEL         -> back to wherever the player came from

This card is currently the ONLY route into the lecture state. Ayesha's
engine/states/lecture.py and content/lectures.py landed on main with no
entry point -- nothing anywhere called ctx.go(ScreenState.LECTURE) --
so without this the whole lecture feature was unreachable.

Both activities read from the semester's REGISTERED COURSES, so an
entry is greyed out when there is nothing for it to run rather than
dropping the player into an empty screen.
"""
import pygame

from engine.screen_manager import ScreenState
from ui.activity_choice_screen import (
    ENTRIES, ENTRY_CANCEL, ENTRY_EXAM, ENTRY_LECTURE,
)
from ui.popup import SEVERITY_INFO


def __registered(ctx):
    """The courses this semester's activities run over."""
    try:
        return list(ctx.semester().get_registered_courses())
    except (AttributeError, TypeError):
        return []


def unavailable(ctx):
    """
    Entry keys that cannot be chosen right now.

    A lecture over an empty course list shows a blank dialogue box the
    player has to press SPACE at twice to escape, so it is refused up
    front instead. The exam screen already handles "nothing to sit"
    gracefully with its own message, so it is left enabled.
    """
    return () if __registered(ctx) else (ENTRY_LECTURE,)


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
    Run this semester's lectures, one per registered course.

    Refused with a notice when nothing is registered, matching what the
    card already draws greyed -- a click on a disabled entry should say
    why, not silently do nothing.
    """
    if not __registered(ctx):
        ctx.play_sfx("error")
        ctx.message_popup.open(
            "NOTHING TO ATTEND",
            ["You have no registered courses.",
             "Register first, then come back."], SEVERITY_INFO)
        return
    ctx.play_sfx("confirm")
    # lecture.py returns to EXPLORATION on its own, so return_state is
    # not consulted there; it is left as the caller set it.
    ctx.go(ScreenState.LECTURE)


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
        disabled=unavailable(ctx),
        subtitle="%d COURSE(S) REGISTERED" % len(__registered(ctx)),
    )

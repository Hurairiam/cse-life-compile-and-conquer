"""
Name entry. Asked between Roya's briefing and registration.

PHASE 18 MOVED IT AND STRIPPED IT. It used to be the first thing START
GAME showed, and committing a name armed the ceremonial opening
monologue. Roya's briefing (beat 1) does that job now, so this screen
sits after it and hands straight to REGISTRATION. The MONOLOGUE state
itself is untouched and still runs between semesters 2-12 -- only the
call site here went away.

ORDER MATTERS. main_menu calls save_bridge.new_game() before routing
here, and that rebuilds the GameSession -- and with it a brand new
Player carrying the default name. Setting the name any earlier would
be wiped by that reset, which is why this screen sits after it and
writes straight onto ctx.player().

Blank submit is allowed by owner ruling and leaves the default name in
place. That needs no branch here: Character.set_display_name() rejects
a blank and changes nothing, so submitting "" is simply a no-op.

Everywhere the player's identity is drawn -- the registration panel,
the stats card, the certificate, and the name on a save slot -- already
reads player.get_display_name(), so this one write reaches all of them.
"""
import pygame

from engine import intro_sequence
from engine.screen_manager import ScreenState
from ui.name_entry_screen import (
    NameEntryScreen, MAX_NAME_LENGTH, is_allowed_char)

CARET_PERIOD = 1.0      # seconds for one full blink cycle
CARET_ON = 0.5          # the caret is drawn for the first half of it

__screen = None
__name = ""
__caret = 0.0


def __ui(ctx):
    global __screen
    if __screen is None:
        __screen = NameEntryScreen(ctx.screen_w, ctx.screen_h)
    return __screen


def enter(ctx):
    global __name, __caret
    __ui(ctx)
    # Cleared on every entry, not just the first: backing out to the
    # title and starting again must not hand the next run the previous
    # attempt's half-typed name.
    __name = ""
    __caret = 0.0
    # Music is set centrally by engine/soundtrack.py via the router:
    # every screen takes the "menu" track except EXAM, which is silent.


def __commit(ctx):
    """Name the player, then hand back to the intro."""
    ctx.player().set_display_name(__name)
    ctx.play_sfx("confirm")
    ctx.go(intro_sequence.after_name_entry(ctx))       # -> REGISTRATION


def __back(ctx):
    ctx.play_sfx("cancel")
    ctx.go(ScreenState.MAIN_MENU)


def __type(event):
    """Apply one keystroke to the field. Refused keys change nothing."""
    global __name, __caret
    if event.key == pygame.K_BACKSPACE:
        __name = __name[:-1]
        __caret = 0.0                       # a visible caret while editing
        return
    char = event.unicode
    if not is_allowed_char(char) or len(__name) >= MAX_NAME_LENGTH:
        return
    # A leading space is refused rather than trimmed later: it would
    # hide the placeholder and move the counter off zero while leaving
    # the field looking empty, and set_display_name() would strip it
    # back to blank on submit anyway.
    if char == " " and not __name:
        return
    __name += char
    __caret = 0.0


def handle_events(ctx, events):
    ui = __ui(ctx)
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                __back(ctx)
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                __commit(ctx)
                return
            __type(event)
        # Phase 18 §9: the CONFIRM and BACK buttons are gone from the
        # card, so the two mouse branches that hit-tested them go with
        # them. ENTER commits and ESC goes back -- that is the whole
        # control set, and it is what this file's docstring already
        # said the keyboard does.


def update(ctx, dt):
    global __caret
    __caret = (__caret + dt) % CARET_PERIOD


def render(ctx, screen):
    __ui(ctx).render(screen, __name, __caret < CARET_ON)

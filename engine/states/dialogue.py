"""
NPC conversation. DialogueManager owns the card, the portrait, the
speaker name and the typewriter; this module owns input and the
return route. Which chain plays and where a reply jumps to belong to
engine/dialogue_flow.py.

ctx.dialogue_return  -> ScreenState to go back to (default EXPLORATION)
ctx.choice_options   -> list[str]; non-empty docks the ChoiceBox above
                        the card. Set by dialogue_flow.open_choice()
                        when a chain that declares a branch runs out of
                        lines, cleared by dialogue_flow.resolve_choice().

WHILE A BRANCH IS OPEN THE CHOICE BOX OWNS EVERY EVENT. It has to:
SPACE and RETURN both confirm a reply AND advance a line, and a click
that misses a reply row used to fall through to the advance path and
skip the question entirely. Swallowing the lot means the only way past
a branch is to answer it.
"""
import pygame

from engine import dialogue_flow
from engine.screen_manager import ScreenState

BG = (20, 24, 38)


def enter(ctx):
    ctx.dialogue_manager.set_typewriter_enabled(True)
    # A reply list left over from the previous conversation would draw
    # over this one's first line, so the branch state starts clean.
    dialogue_flow.reset_choice(ctx)


def __leave(ctx):
    target = ctx.dialogue_return or ScreenState.EXPLORATION
    dialogue_flow.end_talk(ctx)
    ctx.go(target)


def __at_last_line(ctx):
    """True when the line on screen is the final one of this chain."""
    shown, total = ctx.dialogue_manager.get_progress()
    return total > 0 and shown >= total


def __advance(ctx):
    """SPACE/click: finish the line first, then move to the next one."""
    if ctx.dialogue_manager.skip_reveal():
        return
    # A branch is asked while its last line is STILL ON SCREEN, not
    # after. advance() past the end deactivates DialogueManager, and an
    # inactive manager renders nothing — the reply list would then float
    # over an empty screen with no sight of what it is replying to.
    # ui/choice_box.py docks deliberately above the dialog card so the
    # two read as one panel, which only works if the card is still there.
    if __at_last_line(ctx) and dialogue_flow.open_choice(ctx):
        return
    ctx.play_sfx("page_turn")
    if ctx.dialogue_manager.advance():
        return
    __leave(ctx)


def __answer(ctx, index):
    """Commit the picked reply, and leave if it ended the conversation."""
    if not dialogue_flow.resolve_choice(ctx, index):
        __leave(ctx)


def handle_events(ctx, events):
    for event in events:
        if dialogue_flow.is_choice_open(ctx):
            __handle_choice_event(ctx, event)
            continue
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            __leave(ctx)
            return
        advance = (
            (event.type == pygame.KEYDOWN
             and event.key in (pygame.K_SPACE, pygame.K_RETURN))
            or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1))
        if advance:
            __advance(ctx)
            return


def __handle_choice_event(ctx, event):
    """
    Route one event to the reply list, and consume it either way.

    ESC is deliberately NOT an escape hatch here. Everywhere else it
    backs out, but a branch is a question the player was asked, and
    letting ESC skip it would leave the answer unrecorded while the
    conversation ended anyway — the one outcome the author cannot
    express. There is always a reply that ends the talk if that is
    what the choice is for.
    """
    if ctx.choice_box is None:
        # No widget to answer with — refusing to strand the player
        # matters more than the branch.
        __leave(ctx)
        return
    count = len(ctx.choice_options)
    if not ctx.choice_box.handle_event(event, count):
        return
    if ctx.choice_box.take_confirmed():
        ctx.play_sfx("confirm")
        index = ctx.choice_box.get_selected()
        ctx.choice_result = index
        __answer(ctx, index)


def update(ctx, dt):
    ctx.dialogue_manager.update(dt)


def render(ctx, screen):
    screen.fill(BG)
    ctx.dialogue_manager.render(screen)
    if dialogue_flow.is_choice_open(ctx) and ctx.choice_box is not None:
        prompt = getattr(ctx, "choice_prompt", "") or "CHOOSE A REPLY"
        ctx.choice_box.render(screen, ctx.choice_options,
                              ctx.choice_box.get_selected(), prompt)

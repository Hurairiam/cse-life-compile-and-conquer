"""
NPC conversation. DialogueManager owns the card, the portrait, the
speaker name and the typewriter; this module only owns input and the
return route.

ctx.dialogue_return  -> ScreenState to go back to (default EXPLORATION)
ctx.choice_options   -> list[str]; non-empty draws the ChoiceBox above
                        the card. Nothing sets it today; the hook is here
                        so a branching section needs no rewrite.
"""
import pygame

from engine.screen_manager import ScreenState

BG = (20, 24, 38)


def enter(ctx):
    ctx.dialogue_manager.set_typewriter_enabled(True)
    if ctx.choice_box is not None:
        ctx.choice_box.reset()


def __leave(ctx):
    ctx.choice_options = []
    if ctx.choice_box is not None:
        ctx.choice_box.reset()
    ctx.go(ctx.dialogue_return or ScreenState.EXPLORATION)

def __advance(ctx):
    """SPACE/click: finish the line first, then move to the next one."""
    if ctx.dialogue_manager.skip_reveal():
        return
    ctx.play_sfx("page_turn")
    if ctx.dialogue_manager.advance():
        return
    if ctx.choice_options:
        # Choices are already showing — wait for the choice box's own
        # input (arrows + Enter, or a click). SPACE must not fall
        # through to __leave() while a decision is pending.
        return
    if ctx.pending_quest_npc:
        from content.npc_quest_offers import SEMESTER_QUEST_OFFERS
        offer = SEMESTER_QUEST_OFFERS[ctx.pending_quest_npc]
        ctx.dialogue_manager.load_dialogue(offer["offer_lines"])
        ctx.choice_options = ["Accept", "Decline"]
        return
    __leave(ctx)


def handle_events(ctx, events):
    options = ctx.choice_options
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            __leave(ctx)
            return
        if options and ctx.choice_box is not None:
            if ctx.choice_box.handle_event(event, len(options)):
                if ctx.choice_box.take_confirmed():
                    ctx.play_sfx("confirm")
                    picked_index = ctx.choice_box.get_selected()
                    ctx.choice_options = []
                    ctx.choice_box.reset()
                    if ctx.pending_quest_npc:
                        from content.npc_quest_offers import SEMESTER_QUEST_OFFERS
                        offer = SEMESTER_QUEST_OFFERS[ctx.pending_quest_npc]
                        if picked_index == 0:  # Accept
                            ctx.unlocked_side_quests.add(offer["quest_id"])
                            ctx.dialogue_manager.load_dialogue(offer["accept_lines"])
                        else:  # Decline
                            ctx.dialogue_manager.load_dialogue(offer["decline_lines"])
                        ctx.decided_quest_semesters.add(ctx.pending_quest_npc)
                        ctx.pending_quest_npc = None
                    else:
                        __leave(ctx)
                continue
        advance = (
            (event.type == pygame.KEYDOWN
             and event.key in (pygame.K_SPACE, pygame.K_RETURN))
            or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1))
        if advance:
            __advance(ctx)
            return


def update(ctx, dt):
    ctx.dialogue_manager.update(dt)


def render(ctx, screen):
    screen.fill(BG)
    ctx.dialogue_manager.render(screen)
    if ctx.choice_options and ctx.choice_box is not None:
        ctx.choice_box.render(screen, ctx.choice_options,
                              ctx.choice_box.get_selected())

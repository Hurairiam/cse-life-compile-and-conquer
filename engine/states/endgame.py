"""
The epilogue. A keypress turns the page to the certificate — the
epilogue delivers the verdict, the certificate is the record.
"""
import pygame

from engine import ending_gate
from engine.screen_manager import ScreenState


def enter(ctx):
    if ctx.endgame_result is None:
        manager = ctx.session.trigger_endgame_evaluation()
        # PHASE 16 — the skill axis of the ending. "Highly skilled" is
        # all twelve side quests Completed and nothing else; the rule
        # and the reasoning are in engine/ending_gate.py. This is the
        # manager's only caller, so it is the only place the verdict
        # has to be supplied — the machine hangs off ctx and a Player
        # cannot reach it.
        ctx.endgame_result = manager.evaluate(
            ctx.player(), ending_gate.is_highly_skilled(ctx))
    # Music is set centrally by engine/soundtrack.py via the router:
    # every screen takes the "menu" track except EXAM, which is silent.
    if ctx.audio is not None:
        ctx.audio.stop_ambient()


def handle_events(ctx, events):
    for event in events:
        if event.type == pygame.KEYDOWN or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            ctx.play_sfx("page_turn")
            ctx.go(ScreenState.CERTIFICATE)
            return


def render(ctx, screen):
    if ctx.endgame_result is None:
        return
    ctx.endgame_screen.render(screen, **ctx.endgame_result)

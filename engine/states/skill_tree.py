"""
Skill graph + detail panel. The screen draws; this module navigates.

TASK 4 — THIS MODULE NO LONGER SPENDS ANYTHING.
Its docstring used to end "the screen draws; this module spends", and
`__invest()` was the spending. Skills are binary now: a skill completes
by reading its side-quest lecture to the last sheet, and
`engine/skill_completion.py` is the one place that answers whether it
did. There is no manual investment path left anywhere on this screen —
all three entry points went with the handler:

    ENTER / SPACE  -> was __invest(), now does nothing
    click on get_invest_rect() -> the rect no longer exists
    (no context menu or second binding existed; checked)

`progression.available_points()` is no longer read here either, so the
view model is built without a points figure and every node's
`can_invest` comes back False from its own default. The layout module
was not edited for this — `build_view_model()` already defaults
`available_points` to 0.
"""
import pygame

from content.skill_tree_layout import NODE_ORDER, build_view_model
from engine import skill_completion
from engine.screen_manager import ScreenState


def __nodes(ctx):
    """
    The view model, built off the completed flag and with no points.

    Two changes from before, both Task 4's consequences:

    `build_view_model(tree)` defaults `available_points` to 0, which
    makes every `can_invest` False — the honest answer now that nothing
    can be invested.

    The tree handed in is `skill_completion.tree_view(ctx)`, not the real
    SkillTree. Every real level is 0 now, so the actual tree would draw
    twelve LOCKED nodes; the view reports the flag in the shape the
    layout module reads, and the screen goes on working unedited. See
    CompletionView's own docstring for why it is shaped that way.
    """
    return build_view_model(skill_completion.tree_view(ctx))


def enter(ctx):
    if not ctx.selected_skill_id:
        ctx.selected_skill_id = NODE_ORDER[0] if NODE_ORDER else ""


def __leave(ctx):
    ctx.play_sfx("cancel")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def handle_events(ctx, events):
    nodes = __nodes(ctx)
    rects = ctx.skill_tree_screen.get_node_rects(nodes)
    order = [n["skill_id"] for n in nodes]
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                __leave(ctx)
                return
            # ENTER and SPACE used to invest. They are deliberately not
            # rebound to anything else: this screen is a reader now, and
            # a key that silently does nothing is better than one that
            # does something the player did not ask for.
            if event.key in (pygame.K_DOWN, pygame.K_RIGHT) and order:
                index = (order.index(ctx.selected_skill_id) + 1) % len(order) \
                    if ctx.selected_skill_id in order else 0
                ctx.selected_skill_id = order[index]
                ctx.play_sfx("select")
            elif event.key in (pygame.K_UP, pygame.K_LEFT) and order:
                index = (order.index(ctx.selected_skill_id) - 1) % len(order) \
                    if ctx.selected_skill_id in order else 0
                ctx.selected_skill_id = order[index]
                ctx.play_sfx("select")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if ctx.skill_tree_screen.get_back_rect().collidepoint(pos):
                __leave(ctx)
                return
            for skill_id, rect in rects.items():
                if rect.collidepoint(pos):
                    ctx.selected_skill_id = skill_id
                    ctx.play_sfx("click")
                    break


def render(ctx, screen):
    ctx.skill_tree_screen.render(screen, __nodes(ctx), ctx.selected_skill_id)

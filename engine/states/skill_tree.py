"""Skill graph + detail panel. The screen draws; this module spends."""
import pygame

from content.skill_tree_layout import NODE_ORDER, build_view_model
from engine import progression
from engine.screen_manager import ScreenState


def __nodes(ctx):
    return build_view_model(ctx.player().get_skill_tree(),
                            progression.available_points(ctx))


def enter(ctx):
    if not ctx.selected_skill_id:
        ctx.selected_skill_id = NODE_ORDER[0] if NODE_ORDER else ""


def __entry(ctx, nodes):
    for node in nodes:
        if node["skill_id"] == ctx.selected_skill_id:
            return node
    return nodes[0] if nodes else None


def __leave(ctx):
    ctx.play_sfx("cancel")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def __invest(ctx, nodes):
    entry = __entry(ctx, nodes)
    if entry is None or not entry.get("can_invest"):
        ctx.play_sfx("error")
        return
    if progression.invest(ctx, entry["skill_id"]):
        ctx.play_sfx("level_up")
    else:
        ctx.play_sfx("error")


def handle_events(ctx, events):
    nodes = __nodes(ctx)
    rects = ctx.skill_tree_screen.get_node_rects(nodes)
    order = [n["skill_id"] for n in nodes]
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                __leave(ctx)
                return
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                __invest(ctx, nodes)
            elif event.key in (pygame.K_DOWN, pygame.K_RIGHT) and order:
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
            if ctx.skill_tree_screen.get_invest_rect().collidepoint(pos):
                __invest(ctx, nodes)
                continue
            for skill_id, rect in rects.items():
                if rect.collidepoint(pos):
                    ctx.selected_skill_id = skill_id
                    ctx.play_sfx("click")
                    break


def render(ctx, screen):
    ctx.skill_tree_screen.render(screen, __nodes(ctx), ctx.selected_skill_id,
                                 progression.available_points(ctx))

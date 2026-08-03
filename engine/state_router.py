"""
engine/state_router.py
Maps ScreenState -> engine/states/<lowercase name>.py and drives it.

A state module may define any of:
    enter(ctx)                  called once when the state becomes active
    exit(ctx)                   called once when it stops being active
    handle_events(ctx, events)  events NOT already eaten by an open modal
    update(ctx, dt)             dt in seconds
    render(ctx, screen)         required
A missing module or a missing hook is a silent no-op, so a state can be
added later by dropping in one file. The router is never edited again.
"""
from __future__ import annotations

import importlib

import pygame

from engine.screen_manager import ScreenState

# HUD is hidden on these. Everything else shows it.
HUD_HIDDEN = (
    ScreenState.MAIN_MENU, ScreenState.ENDGAME, ScreenState.MONOLOGUE,
    ScreenState.SETTINGS, ScreenState.LOAD_GAME, ScreenState.CERTIFICATE,
    ScreenState.SKILL_TREE, ScreenState.STATS, ScreenState.EXAM_RESULT,
)


class StateRouter:

    def __init__(self, ctx) -> None:
        self.__ctx = ctx
        self.__cache = {}
        self.__active = None

    # -- module resolution -------------------------------------------
    def __module(self, state):
        if state is None:
            return None
        name = state.name.lower()
        if name not in self.__cache:
            try:
                self.__cache[name] = importlib.import_module(
                    "engine.states." + name)
            except ModuleNotFoundError:
                self.__cache[name] = None
        return self.__cache[name]

    def __call(self, state, hook, *args):
        mod = self.__module(state)
        fn = getattr(mod, hook, None) if mod is not None else None
        if fn is not None:
            fn(self.__ctx, *args)

    # -- frame -------------------------------------------------------
    def sync(self) -> None:
        """Fire exit()/enter() when the active state changed."""
        state = self.__ctx.screen_mgr.get_current_state()
        if state is self.__active:
            return
        self.__call(self.__active, "exit")
        self.__active = state
        self.__call(state, "enter")

    def __modals(self):
        """Open modals, highest priority first. None entries skipped."""
        ctx = self.__ctx
        out = []
        for m in (ctx.gate_notice, ctx.message_popup, ctx.popup,
                  ctx.pause_menu):
            if m is not None and m.is_open():
                out.append(m)
        return out

    def handle_events(self, events) -> None:
        ctx = self.__ctx
        modals = self.__modals()
        passthrough = []
        for event in events:
            if event.type == pygame.QUIT:
                ctx.running = False
                return
            eaten = False
            for m in modals:
                if m.handle_event(event):
                    eaten = True
                    break
            if not eaten:
                passthrough.append(event)
        self.__call(self.__active, "handle_events", passthrough)

    def update(self, dt: float) -> None:
        self.__call(self.__active, "update", dt)

    def render(self, screen) -> None:
        self.__call(self.__active, "render", screen)
        self.render_overlays(screen)

    # -- overlays: drawn above every state, in this order ------------
    def render_overlays(self, screen) -> None:
        ctx = self.__ctx
        state = self.__active
        if ctx.hud is not None and state not in HUD_HIDDEN:
            semester = ctx.semester()
            ctx.hud.render(
                screen,
                time_pool=semester.get_time_pool_days(),
                wallet=ctx.player().get_wallet_balance(),
                semester=semester.get_semester_number(),
                credits=ctx.player().get_accumulated_credits(),
            )
        if ctx.pause_menu is not None and ctx.pause_menu.is_open():
            ctx.pause_menu.render(screen, ctx.pause_focus)
        if ctx.gate_notice is not None and ctx.gate_notice.is_open():
            ctx.gate_notice.render(screen, **ctx.gate_args)
        if ctx.popup is not None and ctx.popup.is_open():
            ctx.popup.render(screen)
        if ctx.message_popup is not None and ctx.message_popup.is_open():
            ctx.message_popup.render(screen)

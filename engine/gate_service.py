"""
engine/gate_service.py
The one place a gate is weighed, shown and paid for.

Three outcomes, and only three:
  OPEN_FREE   requirements met, no toll  -> cleared silently, walk through
  OPEN_PAID   requirements met, toll due -> confirmation, then GameClock
  BLOCKED     something unmet, or the toll is unaffordable -> notice only

A cell is remembered in ctx.gates_cleared once it has been passed, so a
paid door charges exactly once per run and a free one never re-prompts.
"""
from __future__ import annotations

from engine.gate_evaluator import GateEntryAction, GateEvaluator
from ui.gate_notice import MODE_CONFIRM, MODE_LOCKED
from ui.popup import RESULT_CONFIRM

OPEN_FREE = "open_free"
OPEN_PAID = "open_paid"
BLOCKED = "blocked"

CANNOT_AFFORD = "You cannot cover the toll right now."


def evaluator(ctx) -> GateEvaluator:
    if ctx.gate_evaluator is None:
        ctx.gate_evaluator = GateEvaluator()
    return ctx.gate_evaluator


def is_cleared(ctx, cell) -> bool:
    return tuple(cell) in ctx.gates_cleared


def clear(ctx, cell) -> None:
    ctx.gates_cleared.add(tuple(cell))


def classify(ctx, gate):
    """(outcome, GateResult) for a gate against the live player."""
    result = evaluator(ctx).evaluate(gate, ctx.player())
    if not result.is_open():
        return (BLOCKED, result)
    if not result.has_cost():
        return (OPEN_FREE, result)
    if not evaluator(ctx).can_afford_costs(gate, ctx.player()):
        return (BLOCKED, result)
    return (OPEN_PAID, result)


def present(ctx, cell, gate) -> bool:
    """
    Handle a gate the player just met.

    Returns True when the player must be HELD BACK this frame
    (blocked, or waiting on the paid-entry confirmation).
    """
    outcome, result = classify(ctx, gate)

    if outcome == OPEN_FREE:
        clear(ctx, cell)
        return False

    flavour = list(gate.get_locked_lines())[:3]
    title = gate.get_locked_title() or "LOCKED"

    if outcome == OPEN_PAID:
        ctx.pending_gate = (tuple(cell), gate)
        ctx.gate_args = {
            "title": title,
            "requirements": result.get_rows(),
            "flavour_lines": flavour,
            "costs": result.get_costs(),
            "mode": MODE_CONFIRM,
        }
        ctx.gate_notice.open(MODE_CONFIRM)
        return True

    if result.is_open():                       # open but unaffordable
        flavour = ([CANNOT_AFFORD] + flavour)[:3]
    ctx.pending_gate = None
    ctx.gate_args = {
        "title": title,
        "requirements": result.get_rows(),
        "flavour_lines": flavour,
        "costs": result.get_costs(),
        "mode": MODE_LOCKED,
    }
    ctx.gate_notice.open(MODE_LOCKED)
    ctx.play_sfx("gate_locked")
    return True


def resolve_pending(ctx) -> None:
    """
    Consume the notice's button once the player has pressed one.
    Call every frame from the exploration state's update().
    """
    if ctx.gate_notice is None:
        return
    result = ctx.gate_notice.take_result()
    if result is None:
        return
    pending = ctx.pending_gate
    ctx.pending_gate = None
    if result != RESULT_CONFIRM or pending is None:
        ctx.play_sfx("cancel")
        return
    cell, gate = pending
    action = GateEntryAction.for_gate(gate)
    if action is not None:
        ctx.game_clock.process_time_consumable(action)
    clear(ctx, cell)
    ctx.play_sfx("confirm")


def badge_states(ctx) -> dict:
    """
    {(x, y): bool} for MapScreen — True draws a green badge (met),
    False a red one. Cleared cells stop being drawn as gates at all.
    """
    states = {}
    if ctx.level is None:
        return states
    player = ctx.player()
    for zone in ctx.level.get_zones():
        gate = zone.get_gate()
        if gate is None or gate.is_default():
            continue
        met = evaluator(ctx).evaluate(gate, player).is_open()
        x, y, w, h = zone.get_rect()
        for cy in range(y, y + h):
            for cx in range(x, x + w):
                if (cx, cy) not in ctx.gates_cleared:
                    states[(cx, cy)] = met
    for prop in ctx.level.get_props():
        gate = prop.get_gate()
        if gate is None or gate.is_default():
            continue
        cell = prop.get_position()
        if cell in ctx.gates_cleared:
            continue
        states[cell] = evaluator(ctx).evaluate(gate, player).is_open()
    return states

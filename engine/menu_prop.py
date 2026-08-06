"""
engine/menu_prop.py
CSE Life: Compile & Conquer — prop -> screen routing
─────────────────────────────────────────────────────────────
One job: turn a level-authored `menu_id` into a screen transition.

WHY THIS IS ITS OWN FILE
────────────────────────
The routing could have been six more lines inside
`engine/states/exploration.py`, but that file belongs to the Sprint 4
state refactor and is shared. A new module cannot produce a merge
conflict, so all the logic lives here and exploration.py carries a
two-line call instead of a branch — the smallest possible footprint in
a file somebody else is also editing.

HOW A MENU PROP WORKS
─────────────────────
    tools/level_editor.py   author sets a prop's interaction kind to
                            "menu" and picks a menu from MENU_REGISTRY
    content/level_schema.py stores it as interaction.menu_id
    THIS FILE               menu_id -> ScreenState, and the way back

`MENU_REGISTRY[menu_id]["state"]` names a ScreenState member rather
than importing one, because content/ is pure data and may not import
engine/. The name is resolved here, where the enum is already in
scope. A registry entry naming a state that does not exist is treated
as an authoring mistake and reported, never raised — a typo in one
level must not take the whole game down.

RETURN PATH
───────────
Every screen the router owns already returns via
`ctx.go(ctx.return_state or ScreenState.EXPLORATION)`, so setting
`ctx.return_state` before the transition is the whole of "and put the
player back where they were standing".
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Any, Optional

from content.level_registry import get_menu_display_name, get_menu_state
from engine.screen_manager import ScreenState

# Popup severity is imported lazily inside the failure paths so this
# module stays importable by tooling that has no ui/ or pygame.


def resolve_state(menu_id: str) -> Optional[ScreenState]:
    """
    The ScreenState a menu id opens, or None when it cannot be routed.

    None covers all three ways this can go wrong — a blank id, an id
    missing from MENU_REGISTRY, and an entry naming a ScreenState this
    build does not have — because the caller treats them identically.
    """
    if not menu_id:
        return None
    state_name = get_menu_state(menu_id)
    if not state_name:
        return None
    return getattr(ScreenState, state_name, None)


def can_open(menu_id: str) -> bool:
    """True when this menu id will actually route somewhere."""
    return resolve_state(menu_id) is not None


def open_menu(ctx: Any, menu_id: str) -> bool:
    """
    Send the player to the screen a menu prop names. True if it routed.

    Sets `ctx.return_state` first so the screen's own BACK button
    brings them back to the map rather than the main menu.
    """
    state = resolve_state(menu_id)
    if state is None:
        __report_unroutable(ctx, menu_id)
        return False

    ctx.return_state = ScreenState.EXPLORATION
    ctx.play_sfx("confirm")
    ctx.go(state)
    return True


def trigger(ctx: Any, prop: Any) -> bool:
    """
    Handle a prop if it is a menu prop. True when it was handled.

    Called before the reward path in exploration.__trigger_prop, and
    deliberately BEFORE the triggers-per-semester check: a menu prop is
    a door, not a payout, so a registration desk usable once a term
    would be wrong.
    """
    if prop.get_interaction_kind() != "menu":
        return False
    open_menu(ctx, prop.get_menu_id())
    return True


def __report_unroutable(ctx: Any, menu_id: str) -> None:
    """Tell the player, and name the id so the author can fix it."""
    from ui.popup import SEVERITY_INFO

    if menu_id:
        lines = ["This should open: %s" % get_menu_display_name(menu_id),
                 "But '%s' does not map to a screen." % menu_id]
    else:
        lines = ["This opens a menu,", "but no menu was chosen for it."]
    ctx.play_sfx("error")
    ctx.message_popup.open("NOTHING HAPPENS", lines, SEVERITY_INFO)

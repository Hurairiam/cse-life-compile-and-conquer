"""
engine/return_points.py
Remembers where the player was standing in each area when they left it,
so walking back in puts them beside the door they used instead of at
that level's one SET SPAWN cell.

This lives in its own module on purpose. `engine/states/exploration.py`
owns the interaction precedence half the remaining phases want a piece
of, so the rule `engine/menu_prop.py` already set stands: new logic
goes in a new file and the state module carries a call rather than a
branch.

One entry per level id, overwritten every time the player leaves:

    ctx.return_positions["campus_main"] = (12, 7, 12, 6)
                                           ^^^^^  ^^^^^
                                           landing  the cell they
                                           cell     actually stood on

The landing cell is the doorway plus TWO steps back the way the player
came, so re-entering never drops them on the threshold. The cell they
actually stood on is kept as the second chance: if the level was edited
since, the ideal cell may no longer be walkable while the one beside it
still is.

Pure Python. No pygame, no level loading, no screen state.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# How far back from the doorway the player reappears, in cells.
STEP_BACK: int = 2


def record(ctx, doorway, origin: Optional[Tuple[int, int]]) -> None:
    """
    Remember how the player left the level they are standing in.

    `doorway` is the portal or travel prop being used and `origin` the
    cell the player came from -- the cell they held before stepping on,
    for a portal, or the cell they are standing on while pressing E, for
    a door. Must be called BEFORE ctx.level_id is repointed at the
    destination, since the entry is filed under the level being left.
    """
    level_id = ctx.level_id
    if not level_id or origin is None:
        return
    door_x, door_y = doorway.get_position()
    step_x = __sign(origin[0] - door_x)
    step_y = __sign(origin[1] - door_y)
    if step_x == 0 and step_y == 0:
        # The player is on the doorway itself with no direction to step
        # back along. Recording that cell would bounce them straight out
        # again on arrival, so nothing is recorded and the area keeps
        # whatever return point it already had.
        return
    ctx.return_positions[level_id] = (
        door_x + step_x * STEP_BACK, door_y + step_y * STEP_BACK,
        int(origin[0]), int(origin[1]))


def arrival(ctx, level, fallback: Tuple[int, int]) -> Tuple[int, int]:
    """
    Where the player lands in `level`: the recorded landing cell, then
    the cell they actually stood on, then `fallback` -- which the caller
    has already validated.

    Both candidates are tested with is_walkable(), and that already
    returns False for anything off the grid, so a level the editor
    shrank cannot strand the player outside it.
    """
    entry = getattr(ctx, "return_positions", {}).get(level.get_level_id())
    if entry is None:
        return fallback
    for cell in ((entry[0], entry[1]), (entry[2], entry[3])):
        if level.is_walkable(*cell):
            return cell
    return fallback


# ── save payload ───────────────────────────────────────────────

def to_state(ctx) -> Dict[str, list]:
    """The table as plain JSON types: {level_id: [lx, ly, sx, sy]}."""
    table = getattr(ctx, "return_positions", None) or {}
    return {str(level_id): [int(value) for value in entry]
            for level_id, entry in table.items()}


def from_state(saved: Any) -> Dict[str, Tuple[int, int, int, int]]:
    """
    Rebuild the table from a save, dropping anything malformed.

    A save written before this phase carries no key at all and loads as
    an empty table, which only means every area opens at its SET SPAWN
    cell the way it always did -- so no schema bump is needed.
    """
    table: Dict[str, Tuple[int, int, int, int]] = {}
    if not isinstance(saved, dict):
        return table
    for level_id, entry in saved.items():
        if not isinstance(entry, (list, tuple)) or len(entry) != 4:
            continue
        try:
            table[str(level_id)] = (int(entry[0]), int(entry[1]),
                                    int(entry[2]), int(entry[3]))
        except (TypeError, ValueError):
            continue
    return table


# ── private ────────────────────────────────────────────────────

def __sign(value: int) -> int:
    """-1, 0 or +1. Applied per axis, so a diagonal exit reads back as
    a diagonal return rather than being flattened onto one axis."""
    return (value > 0) - (value < 0)

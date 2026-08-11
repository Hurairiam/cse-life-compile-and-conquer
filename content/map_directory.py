"""
content/map_directory.py
CSE Life: Compile & Conquer — which areas the player can walk to
─────────────────────────────────────────────────────────────
There is no registry of map locations in this project, and this file
does not add one. An area IS a file in `levels/`, and the only thing
joining two of them is a prop carrying a `target_level_id` — a step-on
portal, or any prop given the "travel" interaction kind. The campus is
already a directed graph the level files describe; this module reads it
back out.

    walk_reachable()  ->  [(level_id, display_name), ...] for every
                          area connected to ROOT_LEVEL_ID, in walking
                          order out from it

DERIVED, NEVER LISTED — that is the whole point of the file. A map
dropped into `levels/` and wired to an existing one turns up in the
teleport menu on its own, with no Python to edit and nothing to
remember. A map nothing leads INTO does not, because teleport would
then be the only way in and the only way back out of it, which reads as
a broken door rather than a feature. Three of those exist today:
`outdoor_cafeteria`, `outdoor_lecturehall` and `outdoor_library`.

Gates are deliberately ignored. A locked door still joins two areas —
whether the player may pass it is engine/gate_evaluator.py's ruling,
made at the door, not a reason to hide a place from a map.

Pure data, per the `content/` convention: no pygame, no engine imports.
It reads the levels folder through content/level_schema.py the same way
content/asset_scanner.py reads the assets folder.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from content.level_schema import (
    LEVELS_DIR, LevelSchemaError, list_level_files, read_level)

# Where walking starts. engine/states/registration.py forces this level
# at the top of every term (START_LEVEL_ID), so it is the root of the
# graph by construction. Spelled out again here rather than imported
# because content/ may not import engine/ — if that constant ever moves,
# this one moves with it.
ROOT_LEVEL_ID: str = "player_room"

# {(root, folder signature): rows} — see __signature() for why the key
# is shaped that way. Only ever holds the most recent answer.
__cache: Dict[tuple, List[Tuple[str, str]]] = {}


def display_name(level_id: str, level_name: str = "") -> str:
    """
    What to call an area on screen.

    `meta.level_name` wins wherever an author set a real one. Four
    levels still carry a bare slug there, and those are de-underscored
    and title-cased exactly the way ui/hud.py already prints the
    location strip, so `outdoor_library` reads as "Outdoor Library" in
    both places instead of one of them shouting a filename.
    """
    text = str(level_name or "").strip() or str(level_id or "").strip()
    if not text:
        return ""
    if "_" in text or text.islower():
        return text.replace("_", " ").title()
    return text


def walk_reachable(levels_dir: str = LEVELS_DIR,
                   root: str = ROOT_LEVEL_ID) -> List[Tuple[str, str]]:
    """
    Every area reachable on foot from `root`, including `root` itself.

    Returned in breadth-first walking order — the room, then what it
    opens onto, then what those open onto — because that is the order
    the player learned the campus in, and a menu that matches it is
    read faster than an alphabetical one.

    A root with no level file has no walking order to describe, so the
    whole folder comes back sorted by name instead. That is a degraded
    answer rather than an empty menu, which is the right failure for a
    file somebody renamed.
    """
    signature = (str(root), __signature(levels_dir))
    cached = __cache.get(signature)
    if cached is not None:
        return list(cached)

    names, edges = __graph(levels_dir)
    if root in names:
        order = __breadth_first(root, edges)
    else:
        order = sorted(names, key=lambda level_id: display_name(
            level_id, names[level_id]))
    rows = [(level_id, display_name(level_id, names[level_id]))
            for level_id in order]

    # One folder is ever in play, and every entry but the newest is
    # dead the moment a map is saved, so the table is replaced rather
    # than grown.
    __cache.clear()
    __cache[signature] = rows
    return list(rows)


# ── private ────────────────────────────────────────────────────

def __breadth_first(root: str, edges: Dict[str, List[str]]) -> List[str]:
    """Level ids reachable from `root`, nearest first, no repeats."""
    order: List[str] = [root]
    seen = {root}
    queue = [root]
    while queue:
        current = queue.pop(0)
        for target in edges.get(current, ()):
            if target in seen:
                continue
            seen.add(target)
            order.append(target)
            queue.append(target)
    return order


def __graph(levels_dir: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    ({level_id: meta.level_name}, {level_id: [target ids]}).

    A file that will not parse is skipped rather than raised on — a map
    half-written by the editor must not stop the teleport menu opening —
    and an edge naming a level with no file is dropped for the same
    reason. Targets are sorted so the walking order above is stable
    between runs instead of following prop placement order.
    """
    names: Dict[str, str] = {}
    targets: Dict[str, set] = {}
    for path in list_level_files(levels_dir):
        try:
            level = read_level(path)
        except LevelSchemaError:
            continue
        level_id = level.get_level_id()
        if not level_id:
            continue
        names[level_id] = level.get_level_name()
        targets[level_id] = {
            prop.get_target_level_id() for prop in level.get_props()
            if prop.has_travel_fields() and prop.get_target_level_id()}
    return names, {level_id: sorted(found & names.keys())
                   for level_id, found in targets.items()}


def __signature(levels_dir: str) -> tuple:
    """
    A fingerprint of the levels folder: every path and its mtime.

    Reading all twelve maps costs about 11 ms, which is nothing on a
    menu open but is still not worth paying twice. Keying the cache on
    the mtimes rather than just remembering the answer means a map
    edited or added while the game is running is picked up, instead of
    being cached out of existence until the next launch.
    """
    stamped = []
    for path in list_level_files(levels_dir):
        try:
            stamped.append((path, os.path.getmtime(path)))
        except OSError:
            stamped.append((path, 0.0))
    return tuple(stamped)


# -------------------------------------------------------------
# STUB TEST -- see what this derives from the maps as they stand:
#
#     python -m content.map_directory
#
# Run as a module from the project root, not as a bare path: this file
# imports content/level_schema.py, and content/level_schema.py has the
# same constraint for the same reason. Headless -- no pygame, no
# display, and nothing is written.
# -------------------------------------------------------------
if __name__ == "__main__":
    every = {read_level(path).get_level_id() for path in list_level_files()}
    rows = walk_reachable()
    print("root: %s" % ROOT_LEVEL_ID)
    print("reachable on foot (%d):" % len(rows))
    for index, (level_id, name) in enumerate(rows):
        print("  %2d. %-22s %s" % (index + 1, level_id, name))
    orphans = sorted(every - {level_id for level_id, _ in rows})
    print("nothing walks into (%d): %s" % (len(orphans),
                                           ", ".join(orphans) or "-"))

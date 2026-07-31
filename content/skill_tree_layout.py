"""
content/skill_tree_layout.py
CSE Life: Compile & Conquer — phase F10  (Feature 7, the node graph)
─────────────────────────────────────────────────────────────
Where the skill tree's SHAPE lives.

core/skill_tree.py (Saif's) stores a free-form {skill_id: level}
map and nothing else — no columns, no prerequisites, no ceiling.
That is the right design for a store, but a screen cannot draw it,
so the structure lives here instead. Saif's file is READ, never
forked and never edited (owner ruling, Build Plan §F10).

This module is pure data plus one adapter. It has no pygame, no
game logic, and it never calls a SkillTree mutator — build_view_model
reads levels and hands back plain dicts for ui/skill_tree_screen.py
to draw.

The node set is the 12 canonical IDs from
engine/endgame_manager.py::TRACKED_SKILL_IDS (Build Plan §1.4).
NOTE the deliberate, owner-ruled divergence: content/level_registry.py
::SKILL_IDS is a DIFFERENT, shorter 9-entry authoring list used by
level gates. Both stay as they are; the lead reconciles at
integration.

Structural data only — no narrative prose (Build Plan §F10). The
description lines are terse factual capability notes, not story text.
─────────────────────────────────────────────────────────────
Created by Nangiba Tasnim (Dev 3), branch nangiba-temp-01.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────
# TUNING
# ─────────────────────────────────────────────────────────────
# Every node shares one ceiling for now. A node may override it with
# its own "max_level" key; none does today, which keeps the level bar
# comparable across the whole tree.
NODE_MAX_LEVEL_DEFAULT: int = 10

# The four states a node can be in, in ascending order of progress.
STATE_LOCKED: str = "locked"
STATE_AVAILABLE: str = "available"
STATE_UNLOCKED: str = "unlocked"
STATE_MASTERED: str = "mastered"

VALID_STATES = (STATE_LOCKED, STATE_AVAILABLE, STATE_UNLOCKED,
                STATE_MASTERED)

# ─────────────────────────────────────────────────────────────
# THE GRAPH
# ─────────────────────────────────────────────────────────────
# A 3-column x 5-row grid. Column is depth: column 0 nodes are the
# foundations and require nothing, and every "requires" entry always
# names a node in an EARLIER column, so the graph is acyclic by
# construction and the screen's connectors only ever run left to right.
#
# The dependency shape follows the Build Plan's worked example:
#   programming_language -> dsa -> debugging_testing
#   git -> linux_cli -> docker
#   databases_sql -> web_app_dev
#   oop after programming_language
#   networking, ai_tools and technical_communication kept shallow
# ─────────────────────────────────────────────────────────────

SKILL_NODES: Dict[str, Dict[str, Any]] = {

    # ── column 0 — foundations, no prerequisites ──────────────
    "programming_language": {
        "display_name": "Programming",
        "column": 0, "row": 0,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": [],
        "description": ["Language syntax, control",
                        "flow and idiomatic style."],
    },
    "git": {
        "display_name": "Version Control",
        "column": 0, "row": 2,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": [],
        "description": ["Branching, merging and",
                        "collaborative history."],
    },
    "networking": {
        "display_name": "Networking",
        "column": 0, "row": 3,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": [],
        "description": ["Protocol layers and",
                        "client-server models."],
    },
    "technical_communication": {
        "display_name": "Tech Writing",
        "column": 0, "row": 4,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": [],
        "description": ["Documentation, reports",
                        "and presenting work."],
    },

    # ── column 1 — core, one step in ──────────────────────────
    "dsa": {
        "display_name": "Data Structures",
        "column": 1, "row": 0,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": ["programming_language"],
        "description": ["Lists, trees, graphs,",
                        "hashing and complexity."],
    },
    "oop": {
        "display_name": "OOP",
        "column": 1, "row": 1,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": ["programming_language"],
        "description": ["Encapsulation and",
                        "inheritance. Polymorphism",
                        "and abstraction."],
    },
    "linux_cli": {
        "display_name": "Linux CLI",
        "column": 1, "row": 2,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": ["git"],
        "description": ["Shell navigation, pipes,",
                        "permissions, scripting."],
    },
    "databases_sql": {
        "display_name": "Databases & SQL",
        "column": 1, "row": 3,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": ["programming_language"],
        "description": ["Schema design, joins,",
                        "indexes and transactions."],
    },

    # ── column 2 — applied, two steps in ──────────────────────
    "debugging_testing": {
        "display_name": "Debug & Test",
        "column": 2, "row": 0,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": ["dsa", "oop"],
        "description": ["Unit tests, breakpoints",
                        "and fault isolation."],
    },
    "ai_tools": {
        "display_name": "AI Tools",
        "column": 2, "row": 1,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": ["dsa"],
        "description": ["Applying model-backed",
                        "tooling to dev tasks."],
    },
    "docker": {
        "display_name": "Docker",
        "column": 2, "row": 2,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": ["linux_cli"],
        "description": ["Images, containers and",
                        "reproducible builds."],
    },
    "web_app_dev": {
        "display_name": "Web App Dev",
        "column": 2, "row": 3,
        "max_level": NODE_MAX_LEVEL_DEFAULT,
        "requires": ["databases_sql", "oop"],
        "description": ["Routing, templating,",
                        "state and deployment."],
    },
}

# Draw order: column-major, then row, so a caller iterating this list
# lays the graph out left to right without re-sorting.
NODE_ORDER: List[str] = sorted(
    SKILL_NODES, key=lambda key: (SKILL_NODES[key]["column"],
                                  SKILL_NODES[key]["row"]))

GRID_COLUMNS: int = max(node["column"] for node in SKILL_NODES.values()) + 1
GRID_ROWS: int = max(node["row"] for node in SKILL_NODES.values()) + 1


# ─────────────────────────────────────────────────────────────
# QUERIES
# ─────────────────────────────────────────────────────────────


def get_node(skill_id: str) -> Optional[Dict[str, Any]]:
    """One node's static data, or None for an unknown id."""
    node = SKILL_NODES.get(str(skill_id))
    return dict(node) if node else None


def get_max_level(skill_id: str) -> int:
    """A node's ceiling, or the default for an unknown id."""
    node = SKILL_NODES.get(str(skill_id))
    if not node:
        return NODE_MAX_LEVEL_DEFAULT
    return int(node.get("max_level", NODE_MAX_LEVEL_DEFAULT))


def get_requirements(skill_id: str) -> List[str]:
    """The ids a node depends on, as a copy. [] for a root or unknown id."""
    node = SKILL_NODES.get(str(skill_id))
    if not node:
        return []
    return list(node.get("requires", []))


# ─────────────────────────────────────────────────────────────
# THE ADAPTER
# ─────────────────────────────────────────────────────────────


def resolve_state(level: int, max_level: int, requires_met: bool) -> str:
    """
    The state one node is in, from its level and whether its
    prerequisites are unlocked.

    The order of these tests is the rule, not an implementation detail:
    a node at its ceiling is MASTERED however it got there; any level at
    all is UNLOCKED; a level-0 node whose prerequisites are all unlocked
    is AVAILABLE to invest in; anything else is LOCKED.

    Note that a node at level >= 1 reads as unlocked even if a
    prerequisite were somehow not — the player's earned levels are never
    taken away by a layout change.
    """
    if max_level > 0 and level >= max_level:
        return STATE_MASTERED
    if level >= 1:
        return STATE_UNLOCKED
    if requires_met:
        return STATE_AVAILABLE
    return STATE_LOCKED


def build_view_model(skill_tree: Any = None,
                     available_points: int = 0) -> List[Dict[str, Any]]:
    """
    Turn Saif's SkillTree into the list ui/skill_tree_screen.py draws.

    THE one adapter between the store and the screen. Each entry:

        {"skill_id", "display_name", "level", "max_level", "state",
         "column", "row", "requires", "description", "can_invest"}

    READ-ONLY: only skill_tree.get_skill_level() and is_skill_unlocked()
    are called, never a mutator. A None tree (or one that raises) reads
    as every level 0, so the screen still draws a full locked tree
    instead of crashing.

    `can_invest` is the one derived flag, and it is derived HERE on
    purpose: the screen is forbidden from deciding whether a node can be
    unlocked (§6.1), so the decision — enough points, not already at the
    ceiling, prerequisites satisfied — is made in this layer and the
    screen just draws the button state it is handed.

    Entries come back in NODE_ORDER (column-major), so a caller can lay
    the graph out without sorting.
    """
    points = max(0, int(available_points or 0))
    levels = {skill_id: _read_level(skill_tree, skill_id)
              for skill_id in SKILL_NODES}

    model: List[Dict[str, Any]] = []
    for skill_id in NODE_ORDER:
        node = SKILL_NODES[skill_id]
        max_level = int(node.get("max_level", NODE_MAX_LEVEL_DEFAULT))
        level = levels[skill_id]
        requires = list(node.get("requires", []))
        # A prerequisite counts as met once it is unlocked (level >= 1),
        # which is exactly what SkillTree.is_skill_unlocked() reports.
        requires_met = all(_read_unlocked(skill_tree, required, levels)
                           for required in requires)
        state = resolve_state(level, max_level, requires_met)
        model.append({
            "skill_id": skill_id,
            "display_name": node["display_name"],
            "level": level,
            "max_level": max_level,
            "state": state,
            "column": int(node["column"]),
            "row": int(node["row"]),
            "requires": requires,
            "description": list(node.get("description", [])),
            "can_invest": (points > 0
                           and level < max_level
                           and state in (STATE_AVAILABLE, STATE_UNLOCKED)),
        })
    return model


def get_unmet_requirements(skill_id: str, skill_tree: Any = None) -> List[str]:
    """
    The display names of a node's prerequisites that are not yet unlocked.

    Feeds the detail panel's BAR_RED "you still need" list, so the screen
    never has to work out what is missing.
    """
    unmet: List[str] = []
    for required in get_requirements(skill_id):
        if not _read_unlocked(skill_tree, required, None):
            node = SKILL_NODES.get(required)
            unmet.append(node["display_name"] if node else required)
    return unmet


# ── private readers — a broken tree never crashes the screen ──


def _read_level(skill_tree: Any, skill_id: str) -> int:
    """One skill's level, 0 when the tree is missing or unreadable."""
    if skill_tree is None:
        return 0
    try:
        return max(0, int(skill_tree.get_skill_level(skill_id)))
    except (AttributeError, TypeError, ValueError):
        return 0


def _read_unlocked(skill_tree: Any, skill_id: str,
                   cache: Optional[Dict[str, int]] = None) -> bool:
    """
    Whether one skill is unlocked (level >= 1).

    Prefers SkillTree.is_skill_unlocked() — the store's own answer — and
    falls back to the level it already read, so a tree that only
    implements get_skill_level() still works.
    """
    if skill_tree is None:
        return False
    try:
        return bool(skill_tree.is_skill_unlocked(skill_id))
    except (AttributeError, TypeError, ValueError):
        if cache is not None and skill_id in cache:
            return cache[skill_id] >= 1
        return _read_level(skill_tree, skill_id) >= 1


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to inspect the graph.
# Abu Huraira removes this block when he plugs in the real game.
#   (no window: pure data, so the stub prints the tree as a grid and
#    then walks one player's progress through every state)
# -------------------------------------------------------------
if __name__ == "__main__":
    from core.skill_tree import SkillTree

    print(f"=== SKILL TREE LAYOUT: {len(SKILL_NODES)} nodes, "
          f"{GRID_COLUMNS} columns x {GRID_ROWS} rows ===\n")

    for row in range(GRID_ROWS):
        cells = []
        for column in range(GRID_COLUMNS):
            found = [key for key in NODE_ORDER
                     if SKILL_NODES[key]["column"] == column
                     and SKILL_NODES[key]["row"] == row]
            cells.append(SKILL_NODES[found[0]]["display_name"][:18].ljust(18)
                         if found else " " * 18)
        print("  " + " | ".join(cells))

    print("\n--- a player part-way through ---")
    tree = SkillTree()
    tree.increment_skill("programming_language", 10)   # mastered
    tree.increment_skill("dsa", 3)                     # unlocked
    tree.increment_skill("oop", 1)                     # unlocked
    tree.increment_skill("git", 2)                     # unlocked

    for entry in build_view_model(tree, available_points=2):
        flag = "INVEST" if entry["can_invest"] else "-"
        print(f"  {entry['display_name']:<18} "
              f"lv {entry['level']:>2}/{entry['max_level']:<2} "
              f"{entry['state']:<10} {flag}")

    print("\n--- unmet prerequisites for the locked nodes ---")
    for entry in build_view_model(tree):
        if entry["state"] == STATE_LOCKED:
            missing = get_unmet_requirements(entry["skill_id"], tree)
            print(f"  {entry['display_name']:<18} needs {missing}")

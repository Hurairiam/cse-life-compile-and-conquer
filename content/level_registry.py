"""
content/level_registry.py
CSE Life: Compile & Conquer — Level system, phase E1
─────────────────────────────────────────────────────────────
PURE DATA. No pygame, no engine imports, no game state.

The single source of truth for every piece of level content:
tiles, props and NPCs, plus the numeric bounds the editor
widgets and the runtime validator both clamp against.

Imported by BOTH:
    tools/level_editor.py   (palette previews, settings widgets)
    content/level_schema.py (validation)
    engine/level_loader.py  (runtime construction)

ART CONTRACT
────────────
Every registry entry points at a sprite *sheet* and a cell
(col, row) inside it. Single-image assets are simply a 1x1
sheet (col 0, row 0). `cell_px` is the size of one cell in the
SOURCE file; the renderer scales it up to TILE_SIZE_PX (48) so
16x16 pixel-art tiles stay crisp at 3x.

Missing art never blocks: an entry may name a file that does
not exist yet, and every consumer must fall back to the Style
Guide PLACEHOLDER square (§5.2 placeholder protocol).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────
# Every path in this file is written repo-relative because that is
# what reads well here and in the level JSON. Resolving them against
# the CURRENT WORKING DIRECTORY would be a bug: the editor and the
# game must load the same art whether they were started from the
# project root, from an IDE, or from a shortcut. So they are anchored
# to this file's location instead, and callers resolve through
# resolve_asset() rather than opening the raw string.
# ─────────────────────────────────────────────────────────────

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_asset(relative_path: str) -> str:
    """
    Turn a repo-relative asset path into an absolute one. Absolute
    paths and empty strings are handed back untouched.
    """
    if not relative_path or os.path.isabs(relative_path):
        return relative_path
    return os.path.join(PROJECT_ROOT, relative_path)


# ─────────────────────────────────────────────────────────────
# GRID + SPRITE CONSTANTS
# ─────────────────────────────────────────────────────────────

TILE_SIZE_PX: int = 48          # on-screen size of one cell (Style Guide §5.4)
EMPTY_TILE: int = -1            # "no tile here" — overlay layer only

GRID_MIN: int = 10              # Spec §4.4 grid-size stepper range
GRID_MAX: int = 200

LAYER_GROUND: str = "ground"
LAYER_OVERLAY: str = "overlay"
LAYER_NAMES: tuple = (LAYER_GROUND, LAYER_OVERLAY)

# ─────────────────────────────────────────────────────────────
# AMBIENT PRESETS  (Spec §4.4 — a STATIC cosmetic tint.)
# Owner ruling 2026-07-29: this is NOT a clock and NOT a time
# speed setting. Levels never drain pool days.
# ─────────────────────────────────────────────────────────────

AMBIENT_PRESETS: tuple = ("morning", "day", "evening", "night")
AMBIENT_DEFAULT: str = "day"

# RGBA tint blitted over the finished level render. "day" = no tint.
AMBIENT_TINTS: Dict[str, tuple] = {
    "morning": (255, 214, 170, 40),
    "day":     (0, 0, 0, 0),
    "evening": (232, 150, 96, 55),
    "night":   (40, 46, 96, 90),
}

# ─────────────────────────────────────────────────────────────
# TILE REGISTRY
# ─────────────────────────────────────────────────────────────
# key   : the int written into the layer arrays
# name  : palette label
# sheet : source PNG (may be missing → placeholder square)
# col/row/cell_px : cell inside the sheet
# walkable : collision
# layer : which layer the paint tool writes into (Spec §3.3)
#
# WALKABILITY RULE (E1 ruling, documented in PHASELOG_E1):
#   a cell is walkable if it has an overlay tile and that tile
#   is walkable, else if it has no overlay and its ground tile
#   is walkable. Overlay wins — that is what makes walls work.
# ─────────────────────────────────────────────────────────────

TILE_REGISTRY: Dict[int, Dict[str, Any]] = {
    0: {"name": "grass",     "sheet": "assets/tiles/grass_0.png",
        "col": 0, "row": 0, "cell_px": 16, "walkable": True,
        "layer": LAYER_GROUND},
    1: {"name": "grass_alt", "sheet": "assets/tiles/grass_1.png",
        "col": 0, "row": 0, "cell_px": 16, "walkable": True,
        "layer": LAYER_GROUND},
    2: {"name": "dirt",      "sheet": "assets/tiles/dirt_0.png",
        "col": 0, "row": 0, "cell_px": 16, "walkable": True,
        "layer": LAYER_GROUND},
    3: {"name": "dirt_alt",  "sheet": "assets/tiles/dirt_1.png",
        "col": 0, "row": 0, "cell_px": 16, "walkable": True,
        "layer": LAYER_GROUND},
    4: {"name": "road",      "sheet": "assets/tiles/road_0.png",
        "col": 0, "row": 0, "cell_px": 16, "walkable": True,
        "layer": LAYER_GROUND},
    # [TILE PLACEHOLDER: assets/tiles/wall_0.png — 16x16 solid campus wall]
    5: {"name": "wall",      "sheet": "assets/tiles/wall_0.png",
        "col": 0, "row": 0, "cell_px": 16, "walkable": False,
        "layer": LAYER_OVERLAY},
    # [TILE PLACEHOLDER: assets/tiles/water_0.png — 16x16 pond water]
    6: {"name": "water",     "sheet": "assets/tiles/water_0.png",
        "col": 0, "row": 0, "cell_px": 16, "walkable": False,
        "layer": LAYER_OVERLAY},
}

DEFAULT_GROUND_TILE: int = 0    # what NEW levels and grid-growth pad with

# ─────────────────────────────────────────────────────────────
# PROP REGISTRY
# ─────────────────────────────────────────────────────────────
# default_passthrough : starting value for a freshly placed instance
# portal props carry target_level_id / target_spawn instead of a
# money/skill reward (Spec §9 — travel between campus locations).
# ─────────────────────────────────────────────────────────────

PROP_REGISTRY: Dict[str, Dict[str, Any]] = {
    "rock": {"name": "rock", "sheet": "assets/props/rock_0.png",
             "col": 0, "row": 0, "cell_px": 16,
             "default_passthrough": False},
    "prop_fence": {"name": "fence", "sheet": "assets/props/prop_fence.png",
             "col": 0, "row": 0, "cell_px": 16,
             "default_passthrough": False},
    "rock_moss": {"name": "mossy rock",
                  "sheet": "assets/props/rock_passthrough.png",
                  "col": 0, "row": 0, "cell_px": 16,
                  "default_passthrough": True},
    # [PROP PLACEHOLDER: assets/props/portal_0.png — doorway / arch marker]
    "portal": {"name": "portal", "sheet": "assets/props/portal_0.png",
               "col": 0, "row": 0, "cell_px": 16,
               "default_passthrough": True, "is_portal": True},
}

PORTAL_TYPE_ID: str = "portal"

# ─────────────────────────────────────────────────────────────
# NPC REGISTRY
# ─────────────────────────────────────────────────────────────
# idle_sheet   : the walking-around-the-map sprite (owner ruling:
#                the "idle" art is what gets PLACED in the map)
# editor_icon  : the "level_editor" art — palette + canvas preview
#                inside the editor ONLY
# portraits    : emotion -> 96x96 face used by the in-game dialog
#                box when a chain declares that emotion
# ─────────────────────────────────────────────────────────────

NPC_REGISTRY: Dict[str, Dict[str, Any]] = {
    "hoque": {
        "name": "Prof. Hoque",
        "idle_sheet": "assets/npcs/npc_hoque_idle.png",
        "frames": 4,
        "cell_px": 48,
        "editor_icon": "assets/npcs/npc_hoque_level_editor.png",
        "portraits": {
            "neutral":   "assets/npcs/npc_hoque_neutral.png",
            "approving": "assets/npcs/npc_hoque_approving.png",
            "strict":    "assets/npcs/npc_hoque_strict.png",
        },
        "default_emotion": "neutral",
    },
    "roya": {
        "name": "Roya",
        "idle_sheet": "assets/npcs/npc_roya_idle.png",
        "frames": 4,
        "cell_px": 48,
        "editor_icon": "assets/npcs/npc_roya_level_editor.png",
        "portraits": {
            "neutral": "assets/npcs/npc_roya_neutral.png",
            "happy":   "assets/npcs/npc_roya_happy.png",
            "serious": "assets/npcs/npc_roya_serious.png",
        },
        "default_emotion": "neutral",
    },
    "kabir": {
        "name": "Kabir",
        "idle_sheet": "assets/npcs/npc_kabir_idle.png",
        "frames": 4,
        "cell_px": 48,
        "editor_icon": "assets/npcs/npc_kabir_level_editor.png",
        "portraits": {
            "neutral": "assets/npcs/npc_kabir_neutral.png",
            "happy":   "assets/npcs/npc_kabir_happy.png",
            "serious": "assets/npcs/npc_kabir_serious.png",
        },
        "default_emotion": "neutral",
    },
    "zayan": {
        "name": "Zayan",
        "idle_sheet": "assets/npcs/npc_zayan_idle.png",
        "frames": 4,
        "cell_px": 48,
        "editor_icon": "assets/npcs/npc_zayan_level_editor.png",
        "portraits": {
            "neutral": "assets/npcs/npc_zayan_neutral.png",
            "happy":   "assets/npcs/npc_zayan_happy.png",
            "serious": "assets/npcs/npc_zayan_serious.png",
        },
        "default_emotion": "neutral",
    },
    "purnno": {
        "name": "Purnno",
        "idle_sheet": "assets/npcs/npc_purnno_idle.png",
        "frames": 4,
        "cell_px": 48,
        "editor_icon": "assets/npcs/npc_purnno_level_editor.png",
        "portraits": {
            "neutral": "assets/npcs/npc_purnno_neutral.png",
            "happy":   "assets/npcs/npc_purnno_happy.png",
            "serious": "assets/npcs/npc_purnno_serious.png",
        },
        "default_emotion": "neutral",
    },
    "rafi": {
        "name": "Rafi",
        "idle_sheet": "assets/npcs/npc_rafi_idle.png",
        "frames": 4,
        "cell_px": 48,
        "editor_icon": "assets/npcs/npc_rafi_level_editor.png",
        "portraits": {
            "neutral": "assets/npcs/npc_rafi_neutral.png",
            "happy":   "assets/npcs/npc_rafi_happy.png",
            "serious": "assets/npcs/npc_rafi_serious.png",
        },
        "default_emotion": "neutral",
    },
    "rahman": {
        "name": "Rahman",
        "idle_sheet": "assets/npcs/npc_rahman_idle.png",
        "frames": 4,
        "cell_px": 48,
        "editor_icon": "assets/npcs/npc_rahman_level_editor.png",
        "portraits": {
            "neutral": "assets/npcs/npc_rahman_neutral.png",
            "happy":   "assets/npcs/npc_rahman_happy.png",
            "serious": "assets/npcs/npc_rahman_serious.png",
        },
        "default_emotion": "neutral",
    },
}

# ─────────────────────────────────────────────────────────────
# NPC ROSTER BINDING  (Feature 6, phase F5)
# ─────────────────────────────────────────────────────────────
# content/npc_roster.py is the CANONICAL source of NPC ids and of
# the semester each NPC becomes available (Build Plan §1.3), so the
# gate defaults are DERIVED from it rather than retyped here. If
# Ayesha moves an NPC from semester 5 to semester 6, the editor's
# gate default follows with no edit to this file.
#
# Only ids whose art exists today are registered, so the editor
# palette never offers a broken entry. The other five roster
# members are listed below, commented out, ready to uncomment the
# moment their sprites land.
# ─────────────────────────────────────────────────────────────

_ROSTER_ID_BY_TYPE: Dict[str, str] = {
    "hoque": "professor_hoque",
    "roya": "career_advisor_roya",
    "kabir": "late_bloomer_kabir",
    "zayan": "struggling_friend_zayan",
    "rafi": "overachiever_classmate_rafi",
    "rahman": "professor_rahman",
    "purnno": "warm_classmate_purnno",
    # Waiting on art before they join NPC_REGISTRY above:
    # [NPC PLACEHOLDER: assets/npcs/npc_purnno_idle.png -- 192x48 idle strip]
    # "purnno": "warm_classmate_purnno",
    # [NPC PLACEHOLDER: assets/npcs/npc_rafi_idle.png -- 192x48 idle strip]
    # "rafi": "overachiever_classmate_rafi",
    # [NPC PLACEHOLDER: assets/npcs/npc_zayan_idle.png -- 192x48 idle strip]
    # "zayan": "struggling_friend_zayan",
    # [NPC PLACEHOLDER: assets/npcs/npc_kabir_idle.png -- 192x48 idle strip]
    # "kabir": "late_bloomer_kabir",
    # [NPC PLACEHOLDER: assets/npcs/npc_rahman_idle.png -- 192x48 idle strip]
    # "rahman": "professor_rahman",
}

# Used only if content/npc_roster.py cannot be imported, so this
# module stays usable standalone. The real numbers come from the
# roster; these mirror it and are asserted equal by the tests.
_MIN_SEMESTER_FALLBACK: Dict[str, int] = {"hoque": 5, "roya": 4,}

MIN_SEMESTER_DEFAULT: int = 1


def _bind_roster_fields() -> None:
    """
    Stamp `roster_id` and `min_semester` onto every NPC_REGISTRY entry.

    Run once at import. Building the mapping programmatically rather
    than hand-writing two more keys per entry is what keeps the two
    files honest: a roster change cannot silently disagree with the
    editor.
    """
    try:
        from content.npc_roster import NPC_ROSTER
    except ImportError:                      # pragma: no cover
        NPC_ROSTER = {}                      # type: ignore[assignment]

    for type_id, entry in NPC_REGISTRY.items():
        roster_id = _ROSTER_ID_BY_TYPE.get(type_id, "")
        entry["roster_id"] = roster_id
        roster_entry = NPC_ROSTER.get(roster_id) if roster_id else None
        if roster_entry is not None:
            entry["min_semester"] = int(
                roster_entry.get("semester_available_from",
                                 MIN_SEMESTER_DEFAULT))
        else:
            entry["min_semester"] = _MIN_SEMESTER_FALLBACK.get(
                type_id, MIN_SEMESTER_DEFAULT)


_bind_roster_fields()

FACINGS: tuple = ("down", "left", "right", "up")
FACING_DEFAULT: str = "down"

# Dialog recurrence once every chain has been played (Spec §6.2).
ON_COMPLETE_MODES: tuple = ("loop_last", "loop_all", "silent")
ON_COMPLETE_DEFAULT: str = "loop_last"

# ─────────────────────────────────────────────────────────────
# PROP INTERACTION BOUNDS  (Spec §5.3)
# ─────────────────────────────────────────────────────────────

INTERACTION_KINDS: tuple = ("none", "money", "skill")
INTERACTION_KIND_DEFAULT: str = "none"

MONEY_MIN: float = 50.0
MONEY_MAX: float = 1000.0
MONEY_STEP: float = 50.0

EXP_MIN: int = 1
EXP_MAX: int = 10          # hard cap: no prop may ever beat a SideQuest's +10
EXP_STEP: int = 1

TRIGGERS_MIN: int = 1
TRIGGERS_MAX: int = 5
TRIGGERS_DEFAULT: int = 1

SPEED_MODIFIER_MIN: float = 0.1
SPEED_MODIFIER_MAX: float = 2.0
SPEED_MODIFIER_BASE: float = 1.0
SPEED_MODIFIER_STEP: float = 0.05
SPEED_SMOOTH_RATE: float = 5.0     # eased per second, never snaps (Spec §5.2)

BASE_PLAYER_SPEED_PX_S: float = 150.0

# ─────────────────────────────────────────────────────────────
# PER-SEMESTER REWARD GUARDRAILS  (Spec §5.4, owner ruling)
# The ENGINE enforces these at runtime; the editor's validator
# only WARNS when a level's totals could exceed them. Declared
# here so both read one number. Starting values — retune in a
# balance pass and log the change.
# ─────────────────────────────────────────────────────────────

MAX_PROP_MONEY_PER_SEMESTER: float = 2000.0
MAX_PROP_EXP_PER_SEMESTER: int = 20

# ─────────────────────────────────────────────────────────────
# SKILL IDS
# ─────────────────────────────────────────────────────────────
# SkillTree keys are free-form strings, so the game has no formal
# skill list yet. This is the canonical set the editor's skill
# dropdown offers, so level data can never invent a typo'd node.
# Extend here when the skill tree content lands.
# ─────────────────────────────────────────────────────────────

SKILL_IDS: tuple = (
    "programming",
    "algorithms",
    "mathematics",
    "hardware",
    "networking",
    "databases",
    "software_engineering",
    "communication",
    "general",
)

# ─────────────────────────────────────────────────────────────
# GATE BOUNDS  (Feature 6, phase F5)
# ─────────────────────────────────────────────────────────────
# The numeric limits a GateData clamps against, and the same ones
# the editor's GatePopup steppers use. Declared here with the rest
# of the bounds so the widget and the validator read ONE number.
#
# The four game-rule figures are fixed by IMPLEMENTATION_PLAN §3
# and must not be retuned here: 12 semesters, 140 credits, an
# 80-day semester pool, and the graduation flag.
# ─────────────────────────────────────────────────────────────

GATE_SEMESTER_MIN: int = 0        # 0 = no semester requirement
GATE_SEMESTER_MAX: int = 12       # 12 semesters in the degree

GATE_CREDITS_MIN: int = 0
GATE_CREDITS_MAX: int = 140       # the credit goal
GATE_CREDITS_STEP: int = 3        # one course is 3 credits

GATE_DAYS_MIN: int = 0
GATE_DAYS_MAX: int = 80           # one semester's time pool

GATE_WALLET_MIN: float = 0.0
GATE_WALLET_MAX: float = 200000.0
GATE_WALLET_STEP: float = 500.0

GATE_SKILL_LEVEL_MIN: int = 0
GATE_SKILL_LEVEL_MAX: int = 20

GATE_MONEY_COST_MIN: float = 0.0
GATE_MONEY_COST_MAX: float = 200000.0

GATE_LOCKED_TITLE_DEFAULT: str = "ACCESS DENIED"
GATE_LOCKED_LINES_MAX: int = 3    # ui/gate_notice.py draws at most three

ZONE_UID_PREFIX: str = "zone"

# ─────────────────────────────────────────────────────────────
# LOOKUP HELPERS  (kept here so nobody re-implements them)
# ─────────────────────────────────────────────────────────────


def get_tile_def(tile_index: int) -> Optional[Dict[str, Any]]:
    """Return the TILE_REGISTRY entry, or None for unknown/empty."""
    return TILE_REGISTRY.get(tile_index)


def get_prop_def(type_id: str) -> Optional[Dict[str, Any]]:
    """Return the PROP_REGISTRY entry, or None if the type is unknown."""
    return PROP_REGISTRY.get(type_id)


def get_npc_def(type_id: str) -> Optional[Dict[str, Any]]:
    """Return the NPC_REGISTRY entry, or None if the type is unknown."""
    return NPC_REGISTRY.get(type_id)


def get_npc_roster_id(type_id: str) -> str:
    """
    The content/npc_roster.py key this NPC type maps to, or "".

    The roster is the canonical id source (Build Plan §1.3); this is
    the bridge from the editor's short type id to it.
    """
    entry = NPC_REGISTRY.get(type_id)
    if entry is None:
        return ""
    return str(entry.get("roster_id", ""))


def get_npc_min_semester(type_id: str) -> int:
    """
    The semester this NPC first becomes available, from the roster.

    Seeds the default `min_semester` on an NPC's gate, so an author
    who gates Prof. Hoque's door starts from the semester Ayesha
    already said he appears in. Unknown types return the default 1.
    """
    entry = NPC_REGISTRY.get(type_id)
    if entry is None:
        return MIN_SEMESTER_DEFAULT
    try:
        return int(entry.get("min_semester", MIN_SEMESTER_DEFAULT))
    except (TypeError, ValueError):
        return MIN_SEMESTER_DEFAULT


def is_tile_walkable(tile_index: int) -> bool:
    """Walkability of a single tile index. Unknown/empty tiles are walkable."""
    entry = TILE_REGISTRY.get(tile_index)
    if entry is None:
        return True
    return bool(entry.get("walkable", True))


def get_tile_layer(tile_index: int) -> str:
    """Which layer the paint tool writes this tile into."""
    entry = TILE_REGISTRY.get(tile_index)
    if entry is None:
        return LAYER_GROUND
    return str(entry.get("layer", LAYER_GROUND))


def get_tile_indices() -> List[int]:
    """Registry keys in stable palette order."""
    return sorted(TILE_REGISTRY.keys())


def get_prop_type_ids() -> List[str]:
    """Prop type ids in stable palette order."""
    return list(PROP_REGISTRY.keys())


def get_npc_type_ids() -> List[str]:
    """NPC type ids in stable palette order."""
    return list(NPC_REGISTRY.keys())


def get_npc_emotions(type_id: str) -> List[str]:
    """
    Emotions this NPC has portrait art for, default emotion first.
    Used by the dialog editor's emotion chips and by the in-game
    dialog box when it picks a face for a chain.
    """
    entry = NPC_REGISTRY.get(type_id)
    if entry is None:
        return []
    portraits: Dict[str, str] = entry.get("portraits", {})
    default: str = entry.get("default_emotion", "")
    ordered: List[str] = [default] if default in portraits else []
    ordered.extend(e for e in portraits if e != default)
    return ordered


def get_npc_portrait_path(type_id: str, emotion: str) -> Optional[str]:
    """
    Path to the emotion portrait for an NPC, falling back to that
    NPC's default emotion. None when the NPC type is unknown.
    """
    entry = NPC_REGISTRY.get(type_id)
    if entry is None:
        return None
    portraits: Dict[str, str] = entry.get("portraits", {})
    if emotion in portraits:
        return portraits[emotion]
    return portraits.get(entry.get("default_emotion", ""), None)


def get_npc_display_name(type_id: str) -> str:
    """Human-facing name used as the dialog-box speaker label."""
    entry = NPC_REGISTRY.get(type_id)
    if entry is None:
        return type_id.upper()
    return str(entry.get("name", type_id))

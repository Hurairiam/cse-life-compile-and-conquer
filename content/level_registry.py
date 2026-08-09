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
import random
from typing import Any, Dict, List, Optional

from content.asset_scanner import (
    SOURCE_CELL_PX,
    cells_for_px,
    family_of_path,
    scan_npcs,
    scan_props,
    scan_tiles,
)

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

# One cell of SOURCE art, the unit every sprite is measured in. Owned
# by content/asset_scanner.py (which runs with no pygame and no
# registry) and re-exported here so nothing outside content/ has to
# know which of the two modules holds it.
TILE_SOURCE_PX: int = SOURCE_CELL_PX

# ─────────────────────────────────────────────────────────────
# NPC DRAW SIZE
# ─────────────────────────────────────────────────────────────
# NPCs are drawn LARGER than the cell they stand on. A character
# scaled to exactly one tile reads as scenery — the same size as the
# rock next to them — and one centred in the cell appears to hover.
#
# So the sprite is scaled up and anchored by the FEET: it is centred
# horizontally on the cell and its bottom edge sits on the cell's
# bottom edge, with the extra height overhanging the cells behind.
# Collision is unaffected; an NPC still occupies exactly one cell.
#
# Expressed as a MULTIPLE of the cell rather than a pixel count so the
# level editor's 32 / 48 / 96 px zoom steps all stay correct.
# ─────────────────────────────────────────────────────────────

NPC_DRAW_SCALE: float = 1.5


def npc_sprite_px(cell_px: int = TILE_SIZE_PX) -> int:
    """On-screen size of an NPC sprite for a given cell size."""
    return max(1, int(round(cell_px * NPC_DRAW_SCALE)))


def npc_blit_offset(cell_px: int = TILE_SIZE_PX) -> tuple:
    """
    (dx, dy) from a cell's top-left corner to the NPC sprite's corner.

    dy is negative: the sprite is taller than the cell and hangs off
    the top, which is what puts the feet on the floor.
    """
    size = npc_sprite_px(cell_px)
    return ((cell_px - size) // 2, cell_px - size)

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
# MULTI-CELL PROPS  (trees and anything else taller than a tile)
# ─────────────────────────────────────────────────────────────
# A prop may cover more than one cell. Its stored (x, y) is always the
# BOTTOM-LEFT cell — the corner of its root — and the sprite extends
# up and to the right from there. Anchoring at the bottom is what makes
# a tree "stand on" the cell you clicked instead of hanging from it.
#
#     cells_w / cells_h : footprint, in cells
#     root_h            : how many rows at the BOTTOM are solid
#
# Only the root blocks. The canopy above it is walk-behind, and the
# renderer fades the whole prop while the player is behind it so they
# are never lost under a tree.
#
# Both are DERIVED from the art by default: a 32x48 sprite of 16 px
# cells is 2 wide and 3 tall, so an artist gets a correct footprint by
# drawing the tree at the size they want it. The `_props.json` override
# is there for the cases that rule gets wrong — a wide canopy over a
# one-cell trunk wants root_h 1, which is already the default, but a
# hedge that is solid all the way up wants root_h equal to cells_h.
# ─────────────────────────────────────────────────────────────

PROP_ROOT_H_DEFAULT: int = 1

# ─────────────────────────────────────────────────────────────
# ROTATION
# ─────────────────────────────────────────────────────────────
# Tiles and props may be turned in 90-degree steps. Quarter turns
# only: pixel art rotated by an arbitrary angle has to be resampled,
# which softens the very hard edges the whole look depends on. At 90,
# 180 and 270 the rotation is exact and every pixel survives.
#
# Stored as DEGREES rather than an index so a hand-edited level file
# reads plainly, and clamped by normalise_rotation() so a typo becomes
# the nearest legal turn instead of a crash.
# ─────────────────────────────────────────────────────────────

ROTATIONS: tuple = (0, 90, 180, 270)
ROTATION_DEFAULT: int = 0


def normalise_rotation(value: Any) -> int:
    """Snap any number to the nearest legal quarter turn."""
    try:
        degrees = int(value) % 360
    except (TypeError, ValueError):
        return ROTATION_DEFAULT
    return min(ROTATIONS, key=lambda legal: abs(legal - degrees))


def next_rotation(value: Any) -> int:
    """The next quarter turn clockwise, wrapping at 270 -> 0."""
    current = normalise_rotation(value)
    return ROTATIONS[(ROTATIONS.index(current) + 1) % len(ROTATIONS)]


def get_prop_pixel_size(type_id: str) -> tuple:
    """
    (width, height) of a prop's art in SOURCE pixels.

    This is what the renderers scale from, so a prop is drawn at its
    own proportions rather than squeezed into a square. Entries that
    never declared px_w/px_h — every hand-written 16x16 prop above —
    fall back to their footprint, which for those is the same number.
    """
    entry = PROP_REGISTRY.get(type_id)
    if entry is None:
        return (TILE_SOURCE_PX, TILE_SOURCE_PX)
    if entry.get("px_w") and entry.get("px_h"):
        return (max(1, int(entry["px_w"])), max(1, int(entry["px_h"])))
    cell = max(1, int(entry.get("cell_px", TILE_SOURCE_PX)))
    return (max(1, int(entry.get("cells_w", 1))) * cell,
            max(1, int(entry.get("cells_h", 1))) * cell)


def get_prop_draw_size(type_id: str, cell_px: int = TILE_SIZE_PX) -> tuple:
    """
    The on-screen (width, height) of a prop at a given cell size.

    Scaled from the art's own pixels against the 16 px cell unit, so a
    16x16 prop is exactly one cell, a 16x48 tree is one by three, and a
    24x40 signboard is one and a half by two and a half. Fractions of a
    cell are fine here — only COLLISION rounds to whole cells.
    """
    px_w, px_h = get_prop_pixel_size(type_id)
    scale = max(1, int(cell_px)) / TILE_SOURCE_PX
    return (max(1, int(round(px_w * scale))),
            max(1, int(round(px_h * scale))))


def get_prop_footprint(type_id: str) -> tuple:
    """
    (cells_w, cells_h) of GRID a prop claims. Unknown types are 1x1.

    Declared values win; anything else is derived from the art, rounded
    up, so a prop drawn 24 px wide reserves the two cells it physically
    overlaps instead of the one it would fit in.
    """
    entry = PROP_REGISTRY.get(type_id)
    if entry is None:
        return (1, 1)
    px_w, px_h = get_prop_pixel_size(type_id)
    return (max(1, int(entry.get("cells_w", cells_for_px(px_w)))),
            max(1, int(entry.get("cells_h", cells_for_px(px_h)))))


def get_prop_root_height(type_id: str) -> int:
    """
    How many bottom rows of a prop are solid, clamped to its height.

    Defaults to 1: one row of trunk under any amount of canopy.
    """
    entry = PROP_REGISTRY.get(type_id)
    if entry is None:
        return 1
    _, cells_h = get_prop_footprint(type_id)
    return max(1, min(cells_h, int(entry.get("root_h",
                                             PROP_ROOT_H_DEFAULT))))


def is_multicell_prop(type_id: str) -> bool:
    """True when this prop covers more than the cell it stands on."""
    return get_prop_footprint(type_id) != (1, 1)


def prop_cells(type_id: str, x: int, y: int) -> list:
    """
    Every cell a prop covers, given its bottom-left anchor.

    Returned as (cx, cy, is_root) so callers do not each re-derive
    which rows block and which are walk-behind canopy.
    """
    cells_w, cells_h = get_prop_footprint(type_id)
    root_h = get_prop_root_height(type_id)
    out = []
    for row in range(cells_h):
        cy = y - row                      # row 0 is the anchor itself
        for col in range(cells_w):
            out.append((x + col, cy, row < root_h))
    return out

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
# ASSET AUTO-DISCOVERY
# ─────────────────────────────────────────────────────────────
# Everything above is CURATED: hand-written names, hand-chosen
# walkability, hand-chosen indices. Everything found in assets/ that
# those entries do not already claim is folded in here, so dropping a
# PNG into assets/tiles, assets/props or assets/npcs is enough to make
# it paintable — no Python edit, no restart of anything but the editor.
#
# Curated entries ALWAYS win. Discovery only ever ADDS keys; it never
# rewrites one, so "grass" stays "grass" and wall_0 stays unwalkable.
# Discovered entries carry "discovered": True so the editor can label
# them and the tests can tell the two sources apart.
#
# Discovered tiles take their index from content/tile_ids.json, which
# pins a name to a number permanently. Levels store those ints, so an
# index that moved between runs would silently repaint finished maps.
# ─────────────────────────────────────────────────────────────


def _merge_discovered() -> None:
    """
    Top the three registries up from assets/. Run once at import.

    Deliberately additive and deliberately silent: a missing assets
    folder, an unreadable PNG or a malformed override file all mean
    "nothing extra to add", never an exception. The editor opening is
    worth more than a strict scan.
    """
    claimed_tile_paths = {str(entry.get("sheet", ""))
                          for entry in TILE_REGISTRY.values()}
    for index, entry in scan_tiles(claimed_tile_paths,
                                   list(TILE_REGISTRY)).items():
        TILE_REGISTRY.setdefault(index, entry)

    claimed_prop_paths = {str(entry.get("sheet", ""))
                          for entry in PROP_REGISTRY.values()}
    for type_id, entry in scan_props(claimed_prop_paths).items():
        PROP_REGISTRY.setdefault(type_id, entry)

    for type_id, entry in scan_npcs(set(NPC_REGISTRY)).items():
        NPC_REGISTRY.setdefault(type_id, entry)


_merge_discovered()


# ─────────────────────────────────────────────────────────────
# TILE VARIANT FAMILIES
# ─────────────────────────────────────────────────────────────
# Art almost never ships one grass. It ships grass_0, grass_1,
# grass_2 — the same surface with the blades in different places, so a
# painted field does not read as wallpaper. The editor's RANDOM toggle
# turns that folder convention into a brush.
#
# A family is derived from the SHEET FILENAME, not the display name:
# the curated entries are called "grass" and "grass_alt" and share no
# name prefix, but both point at grass_N.png and so are one family.
# A tile whose file carries no _<digits> suffix belongs to no family
# and paints as itself, randomise or not.
# ─────────────────────────────────────────────────────────────


def get_tile_family(tile_index: int) -> str:
    """The variant family of a tile, or "" when it stands alone."""
    entry = TILE_REGISTRY.get(tile_index)
    if entry is None:
        return ""
    return family_of_path(str(entry.get("sheet", "")))


def get_tile_variants(tile_index: int) -> List[int]:
    """
    Every tile index sharing this tile's family, in registry order.

    Always includes the tile itself, so callers can paint from the
    result unconditionally. A tile with no family returns just itself,
    which is what makes randomised painting a safe no-op on loners.
    """
    family = get_tile_family(tile_index)
    if not family:
        return [tile_index]
    return sorted(index for index in TILE_REGISTRY
                  if get_tile_family(index) == family)


def has_tile_variants(tile_index: int) -> bool:
    """True when this tile has at least one sibling to randomise with."""
    return len(get_tile_variants(tile_index)) > 1


def pick_tile_variant(tile_index: int,
                      rng: Optional[random.Random] = None) -> int:
    """
    One member of this tile's family, chosen at random.

    Every variant is equally likely, including the one that was asked
    for — weighting the selection toward the "base" tile would defeat
    the point, which is that a painted field should not read as a
    repeating pattern.
    """
    variants = get_tile_variants(tile_index)
    if len(variants) < 2:
        return tile_index
    return (rng or random).choice(variants)


def get_tile_families() -> Dict[str, List[int]]:
    """Every family with more than one member, for tooling and tests."""
    families: Dict[str, List[int]] = {}
    for index in TILE_REGISTRY:
        family = get_tile_family(index)
        if family:
            families.setdefault(family, []).append(index)
    return {name: sorted(members)
            for name, members in families.items() if len(members) > 1}


def is_discovered_tile(tile_index: int) -> bool:
    """True when this tile came from assets/ rather than from this file."""
    return bool((TILE_REGISTRY.get(tile_index) or {}).get("discovered"))


# ─────────────────────────────────────────────────────────────
# NPC ROSTER BINDING  (Feature 6, phase F5)
# ─────────────────────────────────────────────────────────────
# content/npc_roster.py is the CANONICAL source of NPC ids and of
# the semester each NPC becomes available (Build Plan §1.3), so the
# gate defaults are DERIVED from it rather than retyped here. If
# Ayesha moves an NPC from semester 5 to semester 6, the editor's
# gate default follows with no edit to this file.
#
# All seven roster members are mapped. Five of them (purnno, rafi,
# zayan, kabir, rahman) are NOT hand-written in NPC_REGISTRY above —
# they are picked up by the asset scanner from their npc_<id>_idle.png
# sheets. The mapping still has to be listed here, because a scanned
# NPC knows its art but not which roster entry it is, and without that
# link every one of them would default to min_semester 1 instead of
# the semester Ayesha actually gave them.
# ─────────────────────────────────────────────────────────────

_ROSTER_ID_BY_TYPE: Dict[str, str] = {
    "hoque": "professor_hoque",
    "roya": "career_advisor_roya",
    "kabir": "late_bloomer_kabir",
    "zayan": "struggling_friend_zayan",
    "rafi": "overachiever_classmate_rafi",
    "rahman": "professor_rahman",
    "purnno": "warm_classmate_purnno",
}

# Used only if content/npc_roster.py cannot be imported, so this
# module stays usable standalone. The real numbers come from the
# roster; these mirror it and are asserted equal by the tests.
_MIN_SEMESTER_FALLBACK: Dict[str, int] = {
    "purnno": 1, "rafi": 1, "rahman": 1, "zayan": 2, "kabir": 3,
    "roya": 4, "hoque": 5,
}

MIN_SEMESTER_DEFAULT: int = 1


def _bind_roster_fields() -> None:
    """
    Stamp `roster_id`, `min_semester` and `name` onto every NPC_REGISTRY
    entry.

    Run once at import. Building the mapping programmatically rather
    than hand-writing two more keys per entry is what keeps the two
    files honest: a roster change cannot silently disagree with the
    editor.

    `name` is bound for the same reason and was found drifting: the
    roster called them "Prof. Rahman" and "Ms. Roya", the hand-written
    entries below said "Rahman" and "Roya", and it is the entry below
    that gets drawn on the dialogue card. The roster is where a
    character's name is decided, so it wins. A hand-written name is
    still honoured wherever the roster has nothing to say — a placeable
    NPC with no narrative entry keeps the one written here.
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
            entry["name"] = str(
                roster_entry.get("display_name") or entry.get("name", type_id))
        else:
            entry["min_semester"] = _MIN_SEMESTER_FALLBACK.get(
                type_id, MIN_SEMESTER_DEFAULT)


_bind_roster_fields()

FACINGS: tuple = ("down", "left", "right", "up")
FACING_DEFAULT: str = "down"

# Dialog recurrence once every chain has been played (Spec §6.2).
ON_COMPLETE_MODES: tuple = ("loop_last", "loop_all", "silent")
ON_COMPLETE_DEFAULT: str = "loop_last"

# How many replies a DialogChain's branch may offer. MUST stay equal to
# ui/choice_box.py::MAX_OPTIONS — that is what actually gets drawn, and
# a fifth reply would be authored, saved and then silently invisible.
# Declared here rather than imported because content/ is pure data and
# may not pull in pygame; ui/choice_box.py carries the matching comment.
CHOICE_OPTIONS_MAX: int = 4

# ─────────────────────────────────────────────────────────────
# PROP INTERACTION BOUNDS  (Spec §5.3)
# ─────────────────────────────────────────────────────────────

INTERACTION_KINDS: tuple = ("none", "money", "skill", "menu", "travel")
INTERACTION_KIND_DEFAULT: str = "none"

# ─────────────────────────────────────────────────────────────
# MENU REGISTRY
# ─────────────────────────────────────────────────────────────
# The screens a "menu" prop may open. A noticeboard opens the
# registration screen, a terminal opens the skill tree, a results
# board opens the exam result — the prop is the door, this is the
# list of rooms behind it.
#
# Hand-written on purpose. Deriving it by importing ui/ would drag
# pygame into a module the schema and the tests load with no display,
# and scanning ui/*.py filenames cannot tell a SCREEN from a widget
# (ui/popup.py, ui/hud.py and ui/ui_widgets.py are not destinations).
# One line per screen is the honest cost.
#
# Adding a screen: add its id here, then handle that id wherever
# menu props are dispatched (play_sandbox.__open_menu today). The
# editor's dropdown needs no edit — it reads this dict.
#
# `state` names the engine/screen_manager.py ScreenState where one
# exists; screens routed some other way leave it "" and are opened
# directly by the dispatcher.
# ─────────────────────────────────────────────────────────────

MENU_REGISTRY: Dict[str, Dict[str, Any]] = {
    "registration": {"name": "Course Registration", "state": "REGISTRATION"},
    "skill_tree":   {"name": "Skill Tree",          "state": "SKILL_TREE"},
    "stats":        {"name": "Player Stats",        "state": "STATS"},
    "certificate":  {"name": "Certifications",      "state": "CERTIFICATE"},
    "exam":         {"name": "Exam",                "state": "EXAM"},
    "exam_result":  {"name": "Exam Results",        "state": "EXAM_RESULT"},
    "settings":     {"name": "Settings",            "state": "SETTINGS"},
    "load_game":    {"name": "Load Game",           "state": "LOAD_GAME"},
    "main_menu":    {"name": "Main Menu",           "state": "MAIN_MENU"},
    "activity":     {"name": "Exam / Lecture",      "state": "ACTIVITY"},
    # Appended, never inserted: this dict is a shared choke point and a
    # pure append conflicts far less than a reorder.
    "teleport":     {"name": "Teleport",            "state": "TELEPORT"},
    # Ends the current semester once its exams are done. A prop wearing
    # this is the door out of the post-exam free-roam stretch, so which
    # object it hangs on is an authoring choice rather than a hardcoded
    # one -- the editor's menu dropdown reads this dict, so adding it
    # needed no editor change at all.
    "end_semester": {"name": "End Semester",        "state": "END_SEMESTER"},
    # Hands every day left in the term to the main quest at one go,
    # through the same GameClock pipeline every other cost uses -- so the
    # end-of-semester warning and the HUD counter fire on the way down
    # without either being repeated. Appended, never inserted, for the
    # reason above.
    "pass_days":    {"name": "Pass Remaining Days",  "state": "PASS_DAYS"},
    # The side quest list. Hung on the PC in the player's room, but a
    # menu id rather than a hardcoded prop so any terminal an author
    # likes can open it. Appended, never inserted, for the reason above.
    "side_quests":  {"name": "Side Quests",          "state": "SIDE_QUESTS"},
}

MENU_ID_DEFAULT: str = "registration"

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

# ─────────────────────────────────────────────────────────────
# PASS FROM BEHIND  (per-prop collision mode)
# ─────────────────────────────────────────────────────────────
# A third collision mode beside "blocking" and "passthrough": the
# player WALKS INTO the prop's cells and comes out BEHIND it. The prop
# is drawn over the player and fades, so they are never lost inside a
# bookshelf or a shopfront.
#
# Stored as a TRANSPARENCY percentage rather than an alpha byte
# because that is the number an author types: 35 means "35% see-through
# while somebody is behind it", and a hand-edited level reads plainly.
# 0 is fully solid-looking (and therefore hides the player, which is
# why the popup warns about it); the maximum stops short of 100 so a
# faded prop never vanishes completely and leaves an invisible object
# on the map.
#
# Distinct from the automatic canopy fade a multi-cell tree already
# gets: that one is derived from the footprint, this one is a switch
# the author throws on any prop of any size.
# ─────────────────────────────────────────────────────────────

PASS_BEHIND_DEFAULT: bool = False
BEHIND_TRANSPARENCY_DEFAULT: int = 35      # percent see-through
BEHIND_TRANSPARENCY_MIN: int = 0
BEHIND_TRANSPARENCY_MAX: int = 95
BEHIND_TRANSPARENCY_STEP: int = 5


def normalise_transparency(value: Any) -> int:
    """Clamp a transparency percentage into the legal range."""
    try:
        percent = int(round(float(value)))
    except (TypeError, ValueError):
        return BEHIND_TRANSPARENCY_DEFAULT
    return max(BEHIND_TRANSPARENCY_MIN,
               min(BEHIND_TRANSPARENCY_MAX, percent))


def transparency_to_alpha(percent: Any) -> int:
    """
    Blit alpha (0-255) for a transparency percentage.

    35% transparent is 65% opaque, which is 166 — the one conversion
    in the codebase, so the editor's preview and the game's fade can
    never drift apart.
    """
    return int(round(255 * (100 - normalise_transparency(percent)) / 100))

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
# The set the editor's skill dropdown offers, so level data can never
# invent a typo'd node.
#
# RECONCILED (owner ruling, 2026-08-08). This used to be a separate
# 9-entry authoring list — programming, algorithms, mathematics,
# hardware, networking, databases, software_engineering, communication,
# general — that overlapped the real skill tree on "networking" alone.
# A skill prop or a gate authored against it therefore named a node the
# tree never draws, the save file never stores and the endgame never
# counts. Saif's twelve are the source of truth:
#
#     academic/side_quest_catalog.py      the 12 SideQuest topics
#     engine/endgame_manager.py           TRACKED_SKILL_IDS
#     engine/save_bridge.py               TRACKED_SKILL_IDS
#     content/skill_tree_layout.py        SKILL_NODES  (mirrors them)
#
# DERIVED, not hand-copied. SKILL_NODES is the one content-package
# module that already carries the full set, and reading it here is the
# same trick _bind_roster_fields() uses on npc_roster: a change to the
# tree cannot silently disagree with the editor, because there is only
# one list. _SKILL_IDS_FALLBACK mirrors it purely so this module stays
# importable on its own; it is never consulted when the import works.
#
# "general" is deliberately NOT offered. SideQuest.execute_action() and
# exploration.__trigger_prop() still fall back to it in code when no id
# is set, but it is not a tree node and nothing counts it, so an author
# must never be able to pick it.
# ─────────────────────────────────────────────────────────────

_SKILL_IDS_FALLBACK: tuple = (
    "programming_language", "git", "networking", "technical_communication",
    "dsa", "oop", "linux_cli", "databases_sql", "debugging_testing",
    "ai_tools", "docker", "web_app_dev",
)


def _load_skill_ids() -> tuple:
    """The canonical skill ids, read from the skill tree's own node set."""
    try:
        from content.skill_tree_layout import SKILL_NODES
    except ImportError:                      # pragma: no cover
        return _SKILL_IDS_FALLBACK
    return tuple(SKILL_NODES) or _SKILL_IDS_FALLBACK


SKILL_IDS: tuple = _load_skill_ids()

# Human-readable labels for the editor's dropdowns. Raw ids like
# "technical_communication" are what the level file stores, but they are
# not what an author should have to read off a 450 px cycler.
_SKILL_NAME_FALLBACK: Dict[str, str] = {
    "programming_language": "Programming",
    "git": "Version Control",
    "networking": "Networking",
    "technical_communication": "Tech Writing",
    "dsa": "Data Structures",
    "oop": "OOP",
    "linux_cli": "Linux CLI",
    "databases_sql": "Databases & SQL",
    "debugging_testing": "Debug & Test",
    "ai_tools": "AI Tools",
    "docker": "Docker",
    "web_app_dev": "Web App Dev",
}


def get_skill_display_name(skill_id: str) -> str:
    """
    The label the editor shows for a skill id.

    Falls back to the id with underscores opened out, so a node added to
    the tree without a label here still reads sensibly instead of
    vanishing from the dropdown.
    """
    if not skill_id:
        return ""
    try:
        from content.skill_tree_layout import SKILL_NODES
        node = SKILL_NODES.get(skill_id)
        if node and node.get("display_name"):
            return str(node["display_name"])
    except ImportError:                      # pragma: no cover
        pass
    name = _SKILL_NAME_FALLBACK.get(skill_id)
    return name if name else skill_id.replace("_", " ").title()

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


def get_menu_def(menu_id: str) -> Optional[Dict[str, Any]]:
    """Return the MENU_REGISTRY entry, or None for an unknown id."""
    return MENU_REGISTRY.get(menu_id)


def get_menu_ids() -> List[str]:
    """Menu ids in stable registry order — the editor's dropdown."""
    return list(MENU_REGISTRY.keys())


def get_menu_display_name(menu_id: str) -> str:
    """Human-facing menu label, falling back to the raw id."""
    entry = MENU_REGISTRY.get(menu_id)
    if entry is None:
        return menu_id
    return str(entry.get("name", menu_id))


def get_menu_state(menu_id: str) -> str:
    """
    The ScreenState name this menu maps to, or "".

    Read by the runtime dispatcher; screens with no state of their own
    are opened directly instead of routed.
    """
    entry = MENU_REGISTRY.get(menu_id)
    if entry is None:
        return ""
    return str(entry.get("state", ""))

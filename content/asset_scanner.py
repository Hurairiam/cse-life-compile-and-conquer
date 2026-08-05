"""
content/asset_scanner.py
CSE Life: Compile & Conquer — Level system, asset auto-discovery
─────────────────────────────────────────────────────────────
PURE PYTHON (stdlib only). No pygame, no engine imports, no game
state — the same contract content/level_registry.py holds, because
this module runs *inside* that one at import time.

WHY THIS EXISTS
───────────────
Before this module every new tile, prop and NPC had to be hand-typed
into content/level_registry.py before the editor would show it. That
put a Python edit between the artist and their own art. Now the
registries are seeded from the dicts that are still written by hand,
and then TOPPED UP from whatever is actually sitting in assets/.

Drop a PNG in, relaunch the editor, paint with it.

Hand-written entries always win. A file already named by one of them
is not discovered a second time, so the curated names ("grass",
"grass_alt") and the curated walkability survive untouched.

NAMING CONVENTIONS
──────────────────
Nothing about walkability or animation is visible in a PNG, so it is
read off the FILENAME instead. All of it is optional; the defaults are
the common case.

    assets/tiles/<name>.png
        A ground tile, walkable. 16x16 source art is the norm but any
        square image works — cell_px is read from the file header.

        <name> ending in  _solid / _wall / _block      -> blocking
        <name> containing "wall" or "water"            -> blocking
        Blocking tiles are placed on the OVERLAY layer, which is what
        makes them behave as walls (level_registry WALKABILITY RULE).

    assets/props/<name>.png
        A prop, solid by default.
        <name> containing "passthrough" or ending _open -> walk-through

    assets/npcs/npc_<id>_idle.png          the map sprite (required)
    assets/npcs/npc_<id>_level_editor.png  the palette icon
    assets/npcs/npc_<id>_<emotion>.png     one dialog portrait each

        An NPC is only discovered when its _idle sheet exists, because
        that is the frame the game actually stands in the map. Frame
        count is width // height, so a 192x48 strip is read as 4
        frames of 48 px with nothing to declare.

OVERRIDES
─────────
Anything the filename cannot express goes in an optional JSON file
next to the art. Both are hand-written, both are entirely optional,
and unknown keys are ignored:

    assets/tiles/_tiles.json   {"<name>": {"walkable": false, ...}}
    assets/props/_props.json   {"<name>": {"default_passthrough": true}}

TILE INDEX STABILITY
────────────────────
Tiles are written into levels/*.json as raw ints, so a discovered
tile's index MUST NOT move between runs — a shifted index would
silently repaint every level that used it. Sorting by filename would
do exactly that the first time somebody added "brick.png".

So assignments are PERSISTED in content/tile_ids.json: a name gets the
next free index once, and keeps it forever. The file is generated but
belongs in version control, so every machine and every teammate reads
the same numbers. Deleting art does not free its index.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import re
import struct
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────
# Anchored to this file, never to the working directory, for the same
# reason level_registry.resolve_asset() is: the editor and the game
# must find one assets/ folder however they were launched.

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TILES_DIR: str = os.path.join("assets", "tiles")
PROPS_DIR: str = os.path.join("assets", "props")
NPCS_DIR: str = os.path.join("assets", "npcs")

TILE_IDS_PATH: str = os.path.join(PROJECT_ROOT, "content", "tile_ids.json")

# Discovered tiles start well clear of the hand-written block so the
# curated indices (0-6 today) stay readable and never collide.
DISCOVERED_TILE_BASE: int = 100

TILE_OVERRIDES_FILE: str = "_tiles.json"
PROP_OVERRIDES_FILE: str = "_props.json"

# ─────────────────────────────────────────────────────────────
# FILENAME CONVENTIONS
# ─────────────────────────────────────────────────────────────

_SOLID_SUFFIXES: tuple = ("_solid", "_wall", "_block")
_SOLID_WORDS: tuple = ("wall", "water", "cliff", "fence")
_PASSTHROUGH_WORDS: tuple = ("passthrough",)
_PASSTHROUGH_SUFFIXES: tuple = ("_open",)

NPC_PREFIX: str = "npc_"
NPC_IDLE_SUFFIX: str = "_idle"
NPC_EDITOR_SUFFIX: str = "_level_editor"

# A trailing _<digits> marks a variant of a family: grass_0 and grass_1
# are both "grass". Used by the editor's randomise toggle.
_VARIANT_RE = re.compile(r"^(?P<family>.+?)_(?P<ordinal>\d+)$")


# ─────────────────────────────────────────────────────────────
# LOW-LEVEL FILE HELPERS
# ─────────────────────────────────────────────────────────────


def read_png_size(path: str) -> Optional[Tuple[int, int]]:
    """
    (width, height) straight out of a PNG's IHDR chunk, or None.

    Parsed by hand rather than with pygame/PIL because this module is
    imported by content/level_registry.py, which must stay pure data —
    the schema and the tests import it with no display initialised.
    A malformed or unreadable file returns None and the caller falls
    back to a sane default rather than raising at import time.
    """
    try:
        with open(path, "rb") as handle:
            header = handle.read(24)
    except OSError:
        return None
    if len(header) < 24:
        return None
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    try:
        width, height = struct.unpack(">II", header[16:24])
    except struct.error:
        return None
    if width <= 0 or height <= 0:
        return None
    return (int(width), int(height))


def _list_pngs(relative_dir: str) -> List[Tuple[str, str]]:
    """
    Every PNG in a folder as (stem, repo-relative path), sorted by name.

    A missing folder is not an error — a project that has no props yet
    simply discovers no props. Files starting with "_" are skipped so
    the override JSONs and any scratch art stay out of the palette.
    """
    absolute = os.path.join(PROJECT_ROOT, relative_dir)
    try:
        names = sorted(os.listdir(absolute))
    except OSError:
        return []
    found: List[Tuple[str, str]] = []
    for name in names:
        stem, extension = os.path.splitext(name)
        if extension.lower() != ".png" or stem.startswith("_"):
            continue
        found.append((stem, (relative_dir + "/" + name).replace("\\", "/")))
    return found


def _read_overrides(relative_dir: str, filename: str) -> Dict[str, Any]:
    """
    The optional per-folder override map, or {} when absent/unreadable.

    Deliberately forgiving: a typo in a hand-written override must not
    stop the editor from opening, it must just not apply.
    """
    path = os.path.join(PROJECT_ROOT, relative_dir, filename)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def _cell_px(path: str, fallback: int = 16) -> int:
    """Source cell size of a single-cell image, from its own header."""
    size = read_png_size(os.path.join(PROJECT_ROOT, path))
    if size is None:
        return fallback
    return size[1]


# ─────────────────────────────────────────────────────────────
# VARIANT FAMILIES
# ─────────────────────────────────────────────────────────────


def split_variant(stem: str) -> Tuple[str, Optional[int]]:
    """
    Split "grass_1" into ("grass", 1); "rock_passthrough" stays whole.

    Only a trailing run of DIGITS counts, so a descriptive suffix is
    never mistaken for a variant number.
    """
    match = _VARIANT_RE.match(stem)
    if match is None:
        return (stem, None)
    return (match.group("family"), int(match.group("ordinal")))


def family_of_path(path: str) -> str:
    """
    The variant family a sprite path belongs to, or "" for a loner.

    Read off the FILE STEM rather than the registry's display name on
    purpose: the hand-written entries are called "grass" and
    "grass_alt", which share no name prefix, but both point at
    grass_N.png and so are correctly one family.
    """
    if not path:
        return ""
    stem = os.path.splitext(os.path.basename(path))[0]
    family, ordinal = split_variant(stem)
    return family if ordinal is not None else ""


# ─────────────────────────────────────────────────────────────
# TILE INDEX LEDGER
# ─────────────────────────────────────────────────────────────

_LEDGER_README: str = (
    "Generated by content/asset_scanner.py — COMMIT THIS FILE. It pins "
    "each discovered tile to a permanent index; levels/*.json store "
    "those ints, so an index must never be reused or moved."
)


def _load_tile_ledger() -> Dict[str, int]:
    """The persisted name -> index map. Missing or corrupt reads as {}."""
    try:
        with open(TILE_IDS_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    ledger: Dict[str, int] = {}
    for name, index in data.get("tiles", {}).items():
        try:
            ledger[str(name)] = int(index)
        except (TypeError, ValueError):
            continue
    return ledger


def _save_tile_ledger(ledger: Dict[str, int]) -> bool:
    """
    Persist the map. Best-effort: a read-only checkout or a locked file
    must not stop the editor from opening, it just means the newest
    tiles get re-derived (identically) next launch.
    """
    payload = {
        "_README": _LEDGER_README,
        "tiles": {name: ledger[name] for name in sorted(ledger)},
    }
    try:
        os.makedirs(os.path.dirname(TILE_IDS_PATH), exist_ok=True)
        with open(TILE_IDS_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
    except OSError:
        return False
    return True


def assign_tile_indices(names: List[str], reserved: List[int]) -> Dict[str, int]:
    """
    Give every discovered tile name a permanent index.

    Names already in the ledger keep their number. New ones take the
    next free index above DISCOVERED_TILE_BASE, in sorted order so a
    batch of art added at once lands predictably. Indices belonging to
    art that has since been deleted are NOT recycled — a level may
    still reference them, and re-issuing one would repaint it.
    """
    ledger = _load_tile_ledger()
    taken = set(reserved) | set(ledger.values())

    next_free = DISCOVERED_TILE_BASE
    added = False
    for name in sorted(names):
        if name in ledger:
            continue
        while next_free in taken:
            next_free += 1
        ledger[name] = next_free
        taken.add(next_free)
        added = True

    if added:
        _save_tile_ledger(ledger)
    return {name: ledger[name] for name in names if name in ledger}


# ─────────────────────────────────────────────────────────────
# SCANNERS
# ─────────────────────────────────────────────────────────────


def _is_solid_tile(stem: str) -> bool:
    """Filename convention for a tile that blocks the player."""
    lowered = stem.lower()
    if lowered.endswith(_SOLID_SUFFIXES):
        return True
    return any(word in lowered for word in _SOLID_WORDS)


def _is_passthrough_prop(stem: str) -> bool:
    """Filename convention for a prop the player may walk over."""
    lowered = stem.lower()
    if lowered.endswith(_PASSTHROUGH_SUFFIXES):
        return True
    return any(word in lowered for word in _PASSTHROUGH_WORDS)


def scan_tiles(claimed_paths: Optional[set] = None,
               claimed_indices: Optional[List[int]] = None
               ) -> Dict[int, Dict[str, Any]]:
    """
    Every tile PNG that no hand-written entry already claims, keyed by
    its permanent index.

    `claimed_paths` are the sheets the curated TILE_REGISTRY already
    points at; `claimed_indices` are the numbers it already uses.
    """
    claimed_paths = claimed_paths or set()
    overrides = _read_overrides(TILES_DIR, TILE_OVERRIDES_FILE)

    discovered: Dict[str, Dict[str, Any]] = {}
    for stem, path in _list_pngs(TILES_DIR):
        if path in claimed_paths:
            continue
        solid = _is_solid_tile(stem)
        entry: Dict[str, Any] = {
            "name": stem,
            "sheet": path,
            "col": 0,
            "row": 0,
            "cell_px": _cell_px(path),
            "walkable": not solid,
            # Blocking tiles must sit on the overlay layer or they can
            # never act as walls — see the WALKABILITY RULE.
            "layer": "overlay" if solid else "ground",
            "discovered": True,
        }
        entry.update(overrides.get(stem, {}))
        # A hand-edited override may flip walkability; keep the layer
        # consistent with it unless the override also named a layer.
        if "walkable" in overrides.get(stem, {}) and \
                "layer" not in overrides.get(stem, {}):
            entry["layer"] = "ground" if entry.get("walkable", True) \
                else "overlay"
        discovered[stem] = entry

    indices = assign_tile_indices(list(discovered),
                                  list(claimed_indices or []))
    return {indices[stem]: entry for stem, entry in discovered.items()
            if stem in indices}


def scan_props(claimed_paths: Optional[set] = None
               ) -> Dict[str, Dict[str, Any]]:
    """Every prop PNG no hand-written entry claims, keyed by type id."""
    claimed_paths = claimed_paths or set()
    overrides = _read_overrides(PROPS_DIR, PROP_OVERRIDES_FILE)

    discovered: Dict[str, Dict[str, Any]] = {}
    for stem, path in _list_pngs(PROPS_DIR):
        if path in claimed_paths:
            continue
        entry: Dict[str, Any] = {
            "name": stem.replace("_", " "),
            "sheet": path,
            "col": 0,
            "row": 0,
            "cell_px": _cell_px(path),
            "default_passthrough": _is_passthrough_prop(stem),
            "discovered": True,
        }
        entry.update(overrides.get(stem, {}))
        discovered[stem] = entry
    return discovered


def scan_npcs(claimed_ids: Optional[set] = None
              ) -> Dict[str, Dict[str, Any]]:
    """
    Every NPC with an `_idle` sheet that no hand-written entry claims,
    keyed by the short type id pulled out of `npc_<id>_idle.png`.

    Portraits are whatever else carries the same id, with the emotion
    taken from the tail of the filename. `neutral` is preferred as the
    default because that is the convention the curated entries use;
    otherwise the first portrait found stands in, so an NPC with only
    one face still gets a working dialog box.
    """
    claimed_ids = claimed_ids or set()
    files = _list_pngs(NPCS_DIR)

    # Pass one: find the ids that actually have a map sprite.
    idle_by_id: Dict[str, str] = {}
    for stem, path in files:
        if not stem.startswith(NPC_PREFIX) or not stem.endswith(
                NPC_IDLE_SUFFIX):
            continue
        type_id = stem[len(NPC_PREFIX):-len(NPC_IDLE_SUFFIX)]
        if type_id and type_id not in claimed_ids:
            idle_by_id[type_id] = path

    # Pass two: attach the editor icon and the emotion portraits.
    discovered: Dict[str, Dict[str, Any]] = {}
    for type_id, idle_path in idle_by_id.items():
        prefix = NPC_PREFIX + type_id + "_"
        editor_icon = ""
        portraits: Dict[str, str] = {}
        for stem, path in files:
            if not stem.startswith(prefix):
                continue
            tail = stem[len(prefix):]
            if tail == NPC_EDITOR_SUFFIX.lstrip("_"):
                editor_icon = path
            elif tail != NPC_IDLE_SUFFIX.lstrip("_"):
                portraits[tail] = path

        size = read_png_size(os.path.join(PROJECT_ROOT, idle_path))
        if size is not None and size[1] > 0:
            cell_px = size[1]
            frames = max(1, size[0] // size[1])
        else:
            cell_px, frames = 48, 1

        default_emotion = "neutral" if "neutral" in portraits else (
            sorted(portraits)[0] if portraits else "")

        discovered[type_id] = {
            "name": type_id.replace("_", " ").title(),
            "idle_sheet": idle_path,
            "frames": frames,
            "cell_px": cell_px,
            # Falls back to the idle sheet so a missing palette icon
            # shows the NPC rather than an empty placeholder square.
            "editor_icon": editor_icon or idle_path,
            "portraits": portraits,
            "default_emotion": default_emotion,
            "discovered": True,
        }
    return discovered

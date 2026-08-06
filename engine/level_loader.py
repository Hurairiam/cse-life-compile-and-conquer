"""
engine/level_loader.py
CSE Life: Compile & Conquer — Level system, phase E1
─────────────────────────────────────────────────────────────
PURE PYTHON. No pygame (Spec §11 compliance item 1).

Turns a level JSON file into a `Level` — the READ-ONLY runtime
view the game walks around in. The editable document model and
the §7 validation rules live in `content/level_schema.py`; this
module is the game's one-way door: it reads, it validates, it
never writes. Level files are authored ONLY by the editor.

    LevelData  (content/)   editable, serialisable, validated
        │  load_level()
        ▼
    Level      (engine/)    immutable view + O(1) collision grid

`ui/map_screen.py` renders a Level; `main.py` swaps between them
when the player steps on a portal prop.
─────────────────────────────────────────────────────────────
REVISION — phase F7, branch nangiba-temp-01 (Nangiba Tasnim).

Ported unchanged in behaviour and API. Three ADDITIVE getters
were appended for the Feature 6 zone/gate extension F5 added to
content/level_schema.py:

    get_zones()          every ZoneData in the level
    get_zone_at(x, y)    the zone covering a cell, or None
    get_gate_at(x, y)    the gate guarding a cell, or None

They mirror the document model's own resolution order exactly
(prop gate first, then the enclosing zone's) rather than
re-deciding it, so the editor's preview and the running game can
never disagree about what is locked. Like everything else here
they are read-only — a gate is content, not state, and
engine/gate_evaluator.py (F8) is what judges it against a player.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from content.level_registry import (
    AMBIENT_TINTS,
    LAYER_NAMES,
    SPEED_MODIFIER_BASE,
    get_npc_display_name,
)
from content.level_schema import (
    LEVELS_DIR,
    GateData,
    LevelData,
    LevelSchemaError,
    NpcData,
    PropData,
    ValidationReport,
    ZoneData,
    level_path,
    read_level,
)

# NPCs are reachable during the first 20 of the semester's 80 days
# (Plan §3 — availability ratio 0.75-1.00). Stored on every NPC the
# loader builds so GameClock has the boundary it expires them at.
NPC_SEMESTER_EXPIRY_DAY: int = 20


class LevelLoadError(Exception):
    """Raised when a level cannot be turned into a playable Level."""

    def __init__(self, message: str,
                 report: Optional[ValidationReport] = None) -> None:
        super().__init__(message)
        self.__report: Optional[ValidationReport] = report

    def get_report(self) -> Optional[ValidationReport]:
        """The validation report that caused the refusal, if any."""
        return self.__report


class Level:
    """
    One loaded, playable level.

    OOP: Encapsulation — every field is private and exposed through
    getters only. Nothing here can be mutated by the game; a level is
    content, not state. The player's position, the props they have
    already triggered and the NPCs they have talked to all live in
    game state, never in here.
    """

    def __init__(self, document: LevelData) -> None:
        self.__level_id: str = document.get_level_id()
        self.__level_name: str = document.get_level_name()
        self.__grid_width: int = document.get_grid_width()
        self.__grid_height: int = document.get_grid_height()
        self.__ambient: str = document.get_ambient()
        self.__music: str = document.get_music()
        self.__spawn: Tuple[int, int] = document.get_spawn()
        self.__ground: List[List[int]] = [
            list(row) for row in document.get_layer_rows("ground")]
        self.__overlay: List[List[int]] = [
            list(row) for row in document.get_layer_rows("overlay")]
        self.__props: List[PropData] = document.get_props()
        self.__npcs: List[NpcData] = document.get_npcs()
        self.__zones: List[ZoneData] = document.get_zones()

        # Precomputed lookups — the movement update runs these every
        # frame, so it must never walk the entity lists.
        self.__walkable: List[List[bool]] = [
            [document.is_cell_walkable(x, y)
             for x in range(self.__grid_width)]
            for y in range(self.__grid_height)]
        self.__tile_rotations: Dict[Tuple[str, int, int], int] = {
            (layer, x, y): document.get_tile_rotation(layer, x, y)
            for layer in LAYER_NAMES
            for x in range(self.__grid_width)
            for y in range(self.__grid_height)
            if document.get_tile_rotation(layer, x, y)}
        self.__prop_at: Dict[Tuple[int, int], PropData] = {
            p.get_position(): p for p in self.__props}
        self.__npc_at: Dict[Tuple[int, int], NpcData] = {
            n.get_position(): n for n in self.__npcs}

    # ── identity ──────────────────────────────────────────────

    def get_level_id(self) -> str:
        """Slug — doubles as the player's current_location_id."""
        return self.__level_id

    def get_level_name(self) -> str:
        """Human-facing name for HUD / dialog headers."""
        return self.__level_name

    def get_grid_size(self) -> Tuple[int, int]:
        """(width, height) in cells."""
        return (self.__grid_width, self.__grid_height)

    def get_spawn(self) -> Tuple[int, int]:
        """Default entry cell."""
        return self.__spawn

    def get_ambient(self) -> str:
        """Ambient preset name — a static tint, never a clock."""
        return self.__ambient

    def get_ambient_tint(self) -> tuple:
        """RGBA the renderer blits over the finished frame."""
        return AMBIENT_TINTS.get(self.__ambient, (0, 0, 0, 0))

    def get_music(self) -> str:
        """BGM asset path ("" = silent)."""
        return self.__music

    # ── tiles + collision ─────────────────────────────────────

    def get_ground_rows(self) -> List[List[int]]:
        """Ground layer rows (by reference — render only, never write)."""
        return self.__ground

    def get_overlay_rows(self) -> List[List[int]]:
        """Overlay layer rows (by reference — render only, never write)."""
        return self.__overlay

    def get_tile_rotation(self, layer: str, x: int, y: int) -> int:
        """
        Quarter-turn rotation of one painted cell; 0 when unturned.

        Purely a render detail — the collision grid was baked without
        it, because turning a wall does not open it.
        """
        return self.__tile_rotations.get((layer, x, y), 0)

    def is_inside(self, x: int, y: int) -> bool:
        """True when (x, y) is a real cell."""
        return 0 <= x < self.__grid_width and 0 <= y < self.__grid_height

    def is_walkable(self, x: int, y: int) -> bool:
        """
        O(1) collision test combining overlay tiles, ground tiles and
        solid props. Everything outside the grid blocks — that is what
        keeps the player inside the level without an edge wall.
        """
        if not self.is_inside(x, y):
            return False
        return self.__walkable[y][x]

    def get_speed_modifier_at(self, x: int, y: int) -> float:
        """
        Speed multiplier the player eases toward on this cell (Spec
        §5.2). 1.0 anywhere without a modifier prop.
        """
        prop = self.__prop_at.get((x, y))
        if prop is None or not prop.get_passthrough():
            return SPEED_MODIFIER_BASE
        return prop.get_speed_modifier()

    # ── entities ──────────────────────────────────────────────

    def get_props(self) -> List[PropData]:
        """Every placed prop."""
        return list(self.__props)

    def get_prop_at(self, x: int, y: int) -> Optional[PropData]:
        """The prop on a cell, or None."""
        return self.__prop_at.get((x, y))

    def get_npcs(self) -> List[NpcData]:
        """Every placed NPC."""
        return list(self.__npcs)

    def get_npc_at(self, x: int, y: int) -> Optional[NpcData]:
        """The NPC on a cell, or None."""
        return self.__npc_at.get((x, y))

    def get_portal_at(self, x: int, y: int) -> Optional[PropData]:
        """
        The portal prop on a cell, or None. Stepping onto one is what
        moves the player between campus locations (Spec §9) — the
        state manager reads target_level_id / target_spawn off it.
        """
        prop = self.__prop_at.get((x, y))
        if prop is not None and prop.is_portal():
            return prop
        return None

    def get_interactable_at(self, x: int, y: int) -> Optional[PropData]:
        """The prop on a cell that the player may trigger, or None."""
        prop = self.__prop_at.get((x, y))
        if prop is not None and prop.get_interactable():
            return prop
        return None

    # ── zones + gates  (F7 addition, over the F5 schema extension) ──

    def get_zones(self) -> List[ZoneData]:
        """
        Every zone rectangle in the level, as a copy of the list.

        A zone is an authored area — a building interior, a restricted
        wing — that carries one gate instead of the author tagging every
        cell. Handing back a copy keeps the runtime view read-only even
        though ZoneData itself is a mutable document object.
        """
        return list(self.__zones)

    def get_zone_at(self, x: int, y: int) -> Optional[ZoneData]:
        """
        The zone covering a cell, or None.

        Overlapping zones resolve LAST-wins, matching the document
        model's paint order, so a small strict area authored inside a
        larger loose one is the one that answers.
        """
        found: Optional[ZoneData] = None
        for zone in self.__zones:
            if zone.contains(x, y):
                found = zone
        return found

    def get_gate_at(self, x: int, y: int) -> Optional[GateData]:
        """
        The gate guarding a cell: the prop's first, then the zone's.

        A prop gate beats a zone gate because a specific door inside a
        gated building is the tighter statement of intent — the same
        precedence LevelData.get_gate_at() uses, deliberately mirrored
        rather than re-decided. An open (default) gate counts as no
        gate, so callers never have to test is_default() themselves.

        engine/gate_evaluator.py (F8) is what weighs the returned gate
        against a player; this only says which gate applies.
        """
        prop = self.__prop_at.get((x, y))
        if prop is not None and prop.get_gate().has_requirements():
            return prop.get_gate()
        zone = self.get_zone_at(x, y)
        if zone is not None and zone.get_gate().has_requirements():
            return zone.get_gate()
        return None

    def build_npc_characters(self) -> List[Any]:
        """
        Construct real `core.character.NPC` objects for this level, one
        per placed NPC, with `character_id = uid` and `location_id =
        level_id` (Spec §6.1). Dialogue lines from the FIRST chain are
        preloaded so `NPC.get_dialogue_node()` works; the full chain
        sequence is driven by the dialog state machine at runtime.

        The 0.75-1.00 availability window is NOT set here — it is a
        game rule the NPC class already owns and the editor may not
        override (Spec §6.1).
        """
        from core.character.npc import NPC     # local: keeps import cost off
        characters: List[Any] = []             # every other level operation
        for data in self.__npcs:
            character = NPC(character_id=data.get_uid(),
                            display_name=get_npc_display_name(
                                data.get_type_id()),
                            location_id=self.__level_id,
                            semester_bound_expiry=NPC_SEMESTER_EXPIRY_DAY)
            chains = data.get_chains()
            if chains:
                character.load_dialogue(chains[0].get_lines())
            characters.append(character)
        return characters


# ─────────────────────────────────────────────────────────────
# LOADING
# ─────────────────────────────────────────────────────────────


def load_level(level_ref: str, levels_dir: str = LEVELS_DIR,
               strict: bool = True) -> Level:
    """
    Load a level by id ("campus_main") or by path ("levels/x.json").

    With `strict` on (the default) a file carrying §7 BLOCKERS is
    refused — the editor cannot save one, so a blocker in a shipped
    level means the file was hand-edited or an asset registry entry
    was removed. Warnings never block loading.

    Raises LevelLoadError on a missing/unreadable file or blockers.
    """
    path = level_ref if level_ref.endswith(".json") \
        else level_path(level_ref, levels_dir)
    if not os.path.isfile(path):
        raise LevelLoadError(f"level file not found: {path}")
    try:
        document = read_level(path)
    except LevelSchemaError as error:
        raise LevelLoadError(str(error)) from error

    report = document.validate()
    if strict and not report.is_saveable():
        first = report.get_blockers()[0]
        raise LevelLoadError(
            f"'{path}' has {len(report.get_blockers())} blocking problem(s); "
            f"first: {first.get_message()}", report)
    return Level(document)


def load_level_document(level_ref: str,
                        levels_dir: str = LEVELS_DIR) -> LevelData:
    """
    Read a level as its editable document form. Used by tests and by
    tooling — the running game should call load_level() instead so it
    only ever holds the read-only view.
    """
    path = level_ref if level_ref.endswith(".json") \
        else level_path(level_ref, levels_dir)
    return read_level(path)

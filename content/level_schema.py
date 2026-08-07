"""
content/level_schema.py
CSE Life: Compile & Conquer — Level system, phase E1
─────────────────────────────────────────────────────────────
PURE PYTHON (stdlib only). No pygame. No engine imports.
No game state — this module knows about level FILES, not about
players, semesters or wallets.

Holds the level document model that both sides of the system
share:

    tools/level_editor.py   mutates a LevelData and writes it out
    engine/level_loader.py  reads one back and builds the runtime
                            Level the game walks around in

Spec §1 says the editor must not import game state. Putting the
schema here (rather than inside engine/level_loader.py) honours
that while keeping ONE implementation of the format and ONE
implementation of the §7 validation rules — an editor that
validated differently from the loader would be worse than no
validation at all. Documented in PHASELOG_E1.

OOP: Encapsulation — every field is name-mangled private behind
validated accessors. Invalid mutations return False and leave the
document untouched; they never raise and never half-apply.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import re
from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Tuple

from content.level_registry import (
    AMBIENT_DEFAULT,
    AMBIENT_PRESETS,
    CHOICE_OPTIONS_MAX,
    DEFAULT_GROUND_TILE,
    EMPTY_TILE,
    EXP_MAX,
    EXP_MIN,
    FACING_DEFAULT,
    FACINGS,
    GATE_CREDITS_MAX,
    GATE_CREDITS_MIN,
    GATE_DAYS_MAX,
    GATE_DAYS_MIN,
    GATE_LOCKED_LINES_MAX,
    GATE_LOCKED_TITLE_DEFAULT,
    GATE_MONEY_COST_MAX,
    GATE_MONEY_COST_MIN,
    GATE_SEMESTER_MAX,
    GATE_SEMESTER_MIN,
    GATE_SKILL_LEVEL_MAX,
    GATE_SKILL_LEVEL_MIN,
    GATE_WALLET_MAX,
    GATE_WALLET_MIN,
    GRID_MAX,
    GRID_MIN,
    INTERACTION_KIND_DEFAULT,
    INTERACTION_KINDS,
    LAYER_GROUND,
    LAYER_NAMES,
    LAYER_OVERLAY,
    MAX_PROP_EXP_PER_SEMESTER,
    MAX_PROP_MONEY_PER_SEMESTER,
    MENU_ID_DEFAULT,
    MENU_REGISTRY,
    MONEY_MAX,
    MONEY_MIN,
    ON_COMPLETE_DEFAULT,
    ON_COMPLETE_MODES,
    PASS_BEHIND_DEFAULT,
    BEHIND_TRANSPARENCY_DEFAULT,
    PORTAL_TYPE_ID,
    PROJECT_ROOT,
    ROTATION_DEFAULT,
    get_prop_footprint,
    is_multicell_prop,
    normalise_rotation,
    normalise_transparency,
    prop_cells,
    transparency_to_alpha,
    SKILL_IDS,
    SPEED_MODIFIER_BASE,
    SPEED_MODIFIER_MAX,
    SPEED_MODIFIER_MIN,
    TRIGGERS_DEFAULT,
    TRIGGERS_MAX,
    TRIGGERS_MIN,
    ZONE_UID_PREFIX,
    get_npc_def,
    get_npc_emotions,
    get_npc_min_semester,
    get_prop_def,
    get_tile_def,
    is_tile_walkable,
)

# ─────────────────────────────────────────────────────────────
# FORMAT CONSTANTS
# ─────────────────────────────────────────────────────────────

SCHEMA_VERSION: int = 1              # what this module writes
SUPPORTED_SCHEMA_VERSION: int = 1    # highest version it will read

# Anchored to the project, not to the working directory: `levels/` is
# repo content, so the editor must find (and write) the same folder no
# matter where it was launched from. Callers that need a different
# folder — the tests, mainly — pass `levels_dir` explicitly.
LEVELS_DIR: str = os.path.join(PROJECT_ROOT, "levels")
LEVEL_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")

SEVERITY_BLOCKER: str = "blocker"
SEVERITY_WARNING: str = "warning"

# Top-level keys this module understands; anything else is carried
# through untouched for forward compatibility (Spec §2.1).
_KNOWN_TOP_KEYS: tuple = ("schema_version", "meta", "layers", "props", "npcs",
                          "zones", "tile_rotations")
_KNOWN_META_KEYS: tuple = ("level_name", "level_id", "grid_width",
                           "grid_height", "ambient", "music", "spawn")
_KNOWN_PROP_KEYS: tuple = ("uid", "type_id", "x", "y", "passthrough",
                           "speed_modifier", "interactable", "interaction",
                           "gate", "rotation", "pass_behind",
                           "behind_transparency")
_KNOWN_NPC_KEYS: tuple = ("uid", "type_id", "x", "y", "facing",
                          "interactable", "dialog", "gate")
_KNOWN_ZONE_KEYS: tuple = ("uid", "zone_id", "display_name", "x", "y",
                           "w", "h", "gate")


class LevelSchemaError(Exception):
    """Raised only for files this module fundamentally cannot read."""


# ─────────────────────────────────────────────────────────────
# VALIDATION RESULT
# ─────────────────────────────────────────────────────────────


class ValidationIssue:
    """
    One line in the validation report (Spec §7).

    Blockers stop a save; warnings are listed in amber and allowed.
    `cell` is the grid coordinate the results popup pans to when a
    row is double-clicked, or None for whole-file issues.
    """

    def __init__(self, severity: str, code: str, message: str,
                 cell: Optional[Tuple[int, int]] = None) -> None:
        self.__severity: str = severity
        self.__code: str = code
        self.__message: str = message
        self.__cell: Optional[Tuple[int, int]] = cell

    def get_severity(self) -> str:
        """"blocker" or "warning"."""
        return self.__severity

    def get_code(self) -> str:
        """Short machine-readable identifier, e.g. "SPAWN_BLOCKED"."""
        return self.__code

    def get_message(self) -> str:
        """Human-readable one-liner for the results popup."""
        return self.__message

    def get_cell(self) -> Optional[Tuple[int, int]]:
        """Grid cell this issue points at, if any."""
        return self.__cell

    def is_blocker(self) -> bool:
        """True when this issue must be fixed before saving."""
        return self.__severity == SEVERITY_BLOCKER

    def __repr__(self) -> str:
        where = f" at {self.__cell}" if self.__cell else ""
        return f"[{self.__severity}] {self.__code}: {self.__message}{where}"


class ValidationReport:
    """The full result of validating one level document."""

    def __init__(self, issues: List[ValidationIssue]) -> None:
        self.__issues: List[ValidationIssue] = list(issues)

    def get_issues(self) -> List[ValidationIssue]:
        """Every issue, blockers first (that is the order they are added)."""
        return list(self.__issues)

    def get_blockers(self) -> List[ValidationIssue]:
        """Only the issues that prevent a save."""
        return [i for i in self.__issues if i.is_blocker()]

    def get_warnings(self) -> List[ValidationIssue]:
        """Only the advisory issues."""
        return [i for i in self.__issues if not i.is_blocker()]

    def is_saveable(self) -> bool:
        """True when nothing blocks a save."""
        return not self.get_blockers()

    def is_clean(self) -> bool:
        """True when there is nothing to report at all."""
        return not self.__issues

    def __len__(self) -> int:
        return len(self.__issues)


# ─────────────────────────────────────────────────────────────
# GATE  (Feature 6, phase F5)
# ─────────────────────────────────────────────────────────────


class GateData:
    """
    The requirements for entering somewhere, and what entering costs.

    Attachable to a prop (a door), an NPC (someone who will not talk to
    you yet) or a zone (a whole building interior). This class only
    STORES the conditions -- it never evaluates them. Comparing a gate
    against a player is engine/gate_evaluator.py's job (F8); doing it
    here would drag game state into a pure data module.

    Every setter clamps and returns bool. None of them raise, so a
    hand-edited file or a stuck editor stepper can never corrupt a
    document.

    THE DEFAULT GATE SERIALISES TO NOTHING. is_default() is true for a
    freshly-built gate, and every to_dict() that owns one omits the key
    entirely -- which is what lets every pre-gate level file, including
    levels/campus_main.json, still round-trip byte-identical.
    """

    def __init__(self) -> None:
        """Build an open gate: no requirements, no costs."""
        self.__min_semester: int = 0
        self.__min_credits: int = 0
        self.__min_days_remaining: int = 0
        self.__min_wallet: float = 0.0
        self.__required_skill_id: Optional[str] = None
        self.__required_skill_level: int = 0
        self.__required_course_codes: List[str] = []
        self.__requires_graduated: bool = False
        self.__cost_days: int = 0
        self.__cost_money: float = 0.0
        self.__locked_title: str = GATE_LOCKED_TITLE_DEFAULT
        self.__locked_lines: List[str] = []

    # ── requirements ──────────────────────────────────────────

    def get_min_semester(self) -> int:
        """Semester the player must have reached; 0 = no requirement."""
        return self.__min_semester

    def set_min_semester(self, value: int) -> bool:
        """Clamp to 0-12 and store. False when the value did not change."""
        return self.__set_int("_GateData__min_semester", value,
                              GATE_SEMESTER_MIN, GATE_SEMESTER_MAX)

    def get_min_credits(self) -> int:
        """Credits the player must hold; 0 = no requirement."""
        return self.__min_credits

    def set_min_credits(self, value: int) -> bool:
        """Clamp to 0-140 and store."""
        return self.__set_int("_GateData__min_credits", value,
                              GATE_CREDITS_MIN, GATE_CREDITS_MAX)

    def get_min_days_remaining(self) -> int:
        """Days that must be left in the pool; 0 = no requirement."""
        return self.__min_days_remaining

    def set_min_days_remaining(self, value: int) -> bool:
        """Clamp to 0-80 and store."""
        return self.__set_int("_GateData__min_days_remaining", value,
                              GATE_DAYS_MIN, GATE_DAYS_MAX)

    def get_min_wallet(self) -> float:
        """BDT the player must have; 0 = no requirement."""
        return self.__min_wallet

    def set_min_wallet(self, value: float) -> bool:
        """Clamp to 0-200,000 and store."""
        return self.__set_float("_GateData__min_wallet", value,
                                GATE_WALLET_MIN, GATE_WALLET_MAX)

    def get_required_skill_id(self) -> Optional[str]:
        """The skill that must be levelled, or None."""
        return self.__required_skill_id

    def set_required_skill_id(self, skill_id: Optional[str]) -> bool:
        """
        Name the required skill, or None to clear it.

        An id outside SKILL_IDS is REFUSED rather than clamped: there is
        no nearest sensible skill to fall back to, and silently picking
        one would gate a door on something the author never chose.
        """
        if skill_id is None or skill_id == "":
            changed = self.__required_skill_id is not None
            self.__required_skill_id = None
            return changed
        text = str(skill_id)
        if text not in SKILL_IDS:
            return False
        changed = text != self.__required_skill_id
        self.__required_skill_id = text
        return changed

    def get_required_skill_level(self) -> int:
        """Level that skill must reach; 0 = no requirement."""
        return self.__required_skill_level

    def set_required_skill_level(self, value: int) -> bool:
        """Clamp to 0-20 and store."""
        return self.__set_int("_GateData__required_skill_level", value,
                              GATE_SKILL_LEVEL_MIN, GATE_SKILL_LEVEL_MAX)

    def get_required_course_codes(self) -> List[str]:
        """Course codes that must be completed, upper-cased."""
        return list(self.__required_course_codes)

    def set_required_course_codes(self, codes: Any) -> bool:
        """
        Replace the required course list, upper-casing on the way in.

        Accepts a comma-separated string or a sequence. Blanks and
        duplicates are dropped, so "cse101, , CSE101" becomes
        ["CSE101"] -- the editor field is free text and people type
        untidily.
        """
        if isinstance(codes, str):
            candidates: List[Any] = codes.split(",")
        elif isinstance(codes, (list, tuple)):
            candidates = list(codes)
        else:
            return False
        cleaned: List[str] = []
        for code in candidates:
            text = str(code).strip().upper()
            if text and text not in cleaned:
                cleaned.append(text)
        changed = cleaned != self.__required_course_codes
        self.__required_course_codes = cleaned
        return changed

    def get_requires_graduated(self) -> bool:
        """True when only a graduate may pass."""
        return self.__requires_graduated

    def set_requires_graduated(self, value: bool) -> bool:
        """Set the graduation requirement."""
        flag = bool(value)
        changed = flag != self.__requires_graduated
        self.__requires_graduated = flag
        return changed

    # ── costs ─────────────────────────────────────────────────

    def get_cost_days(self) -> int:
        """Days charged on successful entry; 0 = free."""
        return self.__cost_days

    def set_cost_days(self, value: int) -> bool:
        """Clamp to 0-80 and store."""
        return self.__set_int("_GateData__cost_days", value,
                              GATE_DAYS_MIN, GATE_DAYS_MAX)

    def get_cost_money(self) -> float:
        """BDT charged on successful entry; 0 = free."""
        return self.__cost_money

    def set_cost_money(self, value: float) -> bool:
        """Clamp to 0-200,000 and store."""
        return self.__set_float("_GateData__cost_money", value,
                                GATE_MONEY_COST_MIN, GATE_MONEY_COST_MAX)

    def has_cost(self) -> bool:
        """True when entering charges days or money."""
        return self.__cost_days > 0 or self.__cost_money > 0.0

    # ── locked message ────────────────────────────────────────

    def get_locked_title(self) -> str:
        """ALL-CAPS title for the locked popup."""
        return self.__locked_title

    def set_locked_title(self, title: str) -> bool:
        """Set the popup title; blank restores the default."""
        text = str(title).strip().upper() or GATE_LOCKED_TITLE_DEFAULT
        changed = text != self.__locked_title
        self.__locked_title = text
        return changed

    def get_locked_lines(self) -> List[str]:
        """Flavour lines shown under the requirement table."""
        return list(self.__locked_lines)

    def set_locked_lines(self, lines: Any) -> bool:
        """
        Replace the flavour text, keeping at most GATE_LOCKED_LINES_MAX.

        Blank lines are dropped, so an author who leaves the middle of
        three editor fields empty does not get a gap in the popup.
        """
        if isinstance(lines, str):
            candidates: List[Any] = [lines]
        elif isinstance(lines, (list, tuple)):
            candidates = list(lines)
        else:
            return False
        cleaned = [str(line).strip() for line in candidates
                   if str(line).strip()][:GATE_LOCKED_LINES_MAX]
        changed = cleaned != self.__locked_lines
        self.__locked_lines = cleaned
        return changed

    # ── state ─────────────────────────────────────────────────

    def has_requirements(self) -> bool:
        """True when the gate actually demands something of the player."""
        return bool(self.__min_semester or self.__min_credits
                    or self.__min_days_remaining or self.__min_wallet
                    or (self.__required_skill_id
                        and self.__required_skill_level)
                    or self.__required_course_codes
                    or self.__requires_graduated)

    def is_default(self) -> bool:
        """
        True when nothing has been set away from the defaults.

        A default gate is an OPEN gate and serialises to nothing. This
        is the check that keeps every pre-gate level file byte-identical
        after the F5 extension.
        """
        return (not self.has_requirements()
                and not self.has_cost()
                and self.__locked_title == GATE_LOCKED_TITLE_DEFAULT
                and not self.__locked_lines)

    def clear(self) -> None:
        """Restore every field to its default -- the CLEAR GATE button."""
        self.__init__()

    # ── private clamping helpers ──────────────────────────────

    def __set_int(self, attribute: str, value: Any,
                  low: int, high: int) -> bool:
        """Clamp an int into [low, high] and store it under `attribute`."""
        try:
            number = int(value)
        except (TypeError, ValueError):
            return False
        number = max(low, min(high, number))
        changed = getattr(self, attribute) != number
        setattr(self, attribute, number)
        return changed

    def __set_float(self, attribute: str, value: Any,
                    low: float, high: float) -> bool:
        """Clamp a float into [low, high] and store it under `attribute`."""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return False
        number = max(low, min(high, number))
        changed = getattr(self, attribute) != number
        setattr(self, attribute, number)
        return changed

    # ── serialisation ─────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialise, omitting every field still at its default.

        A default gate returns {} and its owner drops the key entirely,
        so gates cost nothing in files that do not use them.
        """
        data: Dict[str, Any] = {}
        if self.__min_semester:
            data["min_semester"] = self.__min_semester
        if self.__min_credits:
            data["min_credits"] = self.__min_credits
        if self.__min_days_remaining:
            data["min_days_remaining"] = self.__min_days_remaining
        if self.__min_wallet:
            data["min_wallet"] = self.__min_wallet
        if self.__required_skill_id:
            data["required_skill_id"] = self.__required_skill_id
        if self.__required_skill_level:
            data["required_skill_level"] = self.__required_skill_level
        if self.__required_course_codes:
            data["required_course_codes"] = list(self.__required_course_codes)
        if self.__requires_graduated:
            data["requires_graduated"] = True
        if self.__cost_days:
            data["cost_days"] = self.__cost_days
        if self.__cost_money:
            data["cost_money"] = self.__cost_money
        if self.__locked_title != GATE_LOCKED_TITLE_DEFAULT:
            data["locked_title"] = self.__locked_title
        if self.__locked_lines:
            data["locked_lines"] = list(self.__locked_lines)
        return data

    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> "GateData":
        """Rebuild a gate, tolerating a missing or partial dict."""
        gate = GateData()
        if not isinstance(data, dict):
            return gate
        gate.set_min_semester(data.get("min_semester", 0))
        gate.set_min_credits(data.get("min_credits", 0))
        gate.set_min_days_remaining(data.get("min_days_remaining", 0))
        gate.set_min_wallet(data.get("min_wallet", 0.0))
        # An unknown skill id is preserved verbatim rather than dropped,
        # so validate() can warn about it and the author sees what they
        # actually typed instead of the file being quietly rewritten.
        skill_id = data.get("required_skill_id")
        if skill_id:
            if not gate.set_required_skill_id(skill_id):
                gate._GateData__required_skill_id = str(skill_id)
        gate.set_required_skill_level(data.get("required_skill_level", 0))
        gate.set_required_course_codes(data.get("required_course_codes", []))
        gate.set_requires_graduated(data.get("requires_graduated", False))
        gate.set_cost_days(data.get("cost_days", 0))
        gate.set_cost_money(data.get("cost_money", 0.0))
        gate.set_locked_title(data.get("locked_title",
                                       GATE_LOCKED_TITLE_DEFAULT))
        gate.set_locked_lines(data.get("locked_lines", []))
        return gate

    def clone(self) -> "GateData":
        """A detached copy -- the settings popup edits one of these."""
        return GateData.from_dict(self.to_dict())

    def __repr__(self) -> str:
        if self.is_default():
            return "GateData(open)"
        return f"GateData({self.to_dict()})"


# ─────────────────────────────────────────────────────────────
# ZONE  (Feature 6, phase F5)
# ─────────────────────────────────────────────────────────────


class ZoneData:
    """
    A named rectangle of cells carrying one gate.

    Gating a whole building interior by tagging every cell would be
    miserable to author and would bloat the file; a zone says "these
    forty cells are the lab block, and this is what it takes to get in"
    in a single entry.
    """

    def __init__(self, uid: str, zone_id: str, x: int, y: int,
                 w: int = 1, h: int = 1) -> None:
        """Build a zone rectangle. Width and height are forced positive."""
        self.__uid: str = uid
        self.__zone_id: str = zone_id
        self.__display_name: str = ""
        self.__x: int = int(x)
        self.__y: int = int(y)
        self.__w: int = max(1, int(w))
        self.__h: int = max(1, int(h))
        self.__gate: GateData = GateData()
        self.__extra: Dict[str, Any] = {}

    # ── identity ──────────────────────────────────────────────

    def get_uid(self) -> str:
        """Stable per-file id, assigned by the editor."""
        return self.__uid

    def get_zone_id(self) -> str:
        """Author-facing slug, e.g. "lab_block"."""
        return self.__zone_id

    def set_zone_id(self, zone_id: str) -> bool:
        """Slugify and store. An empty result is refused."""
        text = re.sub(r"[^a-z0-9_]+", "_", str(zone_id).strip().lower())
        text = text.strip("_")
        if not text:
            return False
        self.__zone_id = text
        return True

    def get_display_name(self) -> str:
        """Human-readable name drawn in the editor and the gate popup."""
        return self.__display_name

    def set_display_name(self, name: str) -> bool:
        """Store the display name."""
        self.__display_name = str(name).strip()
        return True

    # ── geometry ──────────────────────────────────────────────

    def get_rect(self) -> Tuple[int, int, int, int]:
        """(x, y, w, h) in grid cells."""
        return (self.__x, self.__y, self.__w, self.__h)

    def set_rect(self, x: int, y: int, w: int, h: int) -> bool:
        """Move and resize. Negative origins and empty rects are refused."""
        if int(x) < 0 or int(y) < 0 or int(w) < 1 or int(h) < 1:
            return False
        self.__x, self.__y = int(x), int(y)
        self.__w, self.__h = int(w), int(h)
        return True

    def contains(self, x: int, y: int) -> bool:
        """True when a cell falls inside this zone."""
        return (self.__x <= x < self.__x + self.__w
                and self.__y <= y < self.__y + self.__h)

    def get_cell_count(self) -> int:
        """How many cells the zone covers."""
        return self.__w * self.__h

    def overlaps(self, other: "ZoneData") -> bool:
        """True when two zones share at least one cell."""
        ox, oy, ow, oh = other.get_rect()
        return not (self.__x + self.__w <= ox or ox + ow <= self.__x
                    or self.__y + self.__h <= oy or oy + oh <= self.__y)

    # ── gate ──────────────────────────────────────────────────

    def get_gate(self) -> GateData:
        """The zone's gate. Always present; may be an open default."""
        return self.__gate

    def set_gate(self, gate: Optional[GateData]) -> bool:
        """Attach a gate. None clears it back to an open default."""
        if gate is None:
            self.__gate = GateData()
            return True
        if not isinstance(gate, GateData):
            return False
        self.__gate = gate
        return True

    def is_gated(self) -> bool:
        """True when this zone actually restricts entry."""
        return self.__gate.has_requirements()

    # ── serialisation ─────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialise, re-emitting any unknown keys we read in."""
        data: Dict[str, Any] = dict(self.__extra)
        data.update({
            "uid": self.__uid,
            "zone_id": self.__zone_id,
            "display_name": self.__display_name,
            "x": self.__x,
            "y": self.__y,
            "w": self.__w,
            "h": self.__h,
        })
        gate = self.__gate.to_dict()
        if gate:
            data["gate"] = gate
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ZoneData":
        """Rebuild a zone, tolerating missing optional keys."""
        zone = ZoneData(str(data.get("uid", "")),
                        str(data.get("zone_id", "zone")),
                        int(data.get("x", 0)), int(data.get("y", 0)),
                        int(data.get("w", 1)), int(data.get("h", 1)))
        zone.set_display_name(str(data.get("display_name", "")))
        zone.set_gate(GateData.from_dict(data.get("gate")))
        zone._ZoneData__extra = {
            k: v for k, v in data.items() if k not in _KNOWN_ZONE_KEYS
        }
        return zone

    def __repr__(self) -> str:
        return (f"ZoneData({self.__zone_id!r} at {self.get_rect()}, "
                f"gated={self.is_gated()})")


# ─────────────────────────────────────────────────────────────
# PROP INSTANCE
# ─────────────────────────────────────────────────────────────


class PropData:
    """
    One placed prop. Registry supplies the art and the DEFAULT
    passthrough; everything else is per-instance and edited in the
    right-click popup (Spec §5.3).
    """

    def __init__(self, uid: str, type_id: str, x: int, y: int) -> None:
        definition = get_prop_def(type_id)
        default_passthrough = bool(
            definition.get("default_passthrough", False)) if definition else False
        self.__uid: str = uid
        self.__type_id: str = type_id
        self.__x: int = int(x)
        self.__y: int = int(y)
        self.__passthrough: bool = default_passthrough
        self.__pass_behind: bool = PASS_BEHIND_DEFAULT
        self.__behind_transparency: int = BEHIND_TRANSPARENCY_DEFAULT
        self.__speed_modifier: float = SPEED_MODIFIER_BASE
        self.__interactable: bool = False
        self.__kind: str = INTERACTION_KIND_DEFAULT
        self.__amount: float = 0.0
        self.__skill_id: Optional[str] = None
        self.__menu_id: str = ""
        self.__rotation: int = ROTATION_DEFAULT
        self.__triggers_per_semester: int = TRIGGERS_DEFAULT
        self.__target_level_id: str = ""
        self.__target_spawn: Optional[Tuple[int, int]] = None
        self.__gate: GateData = GateData()
        self.__extra: Dict[str, Any] = {}

    # ── identity ──────────────────────────────────────────────

    def get_uid(self) -> str:
        """Stable per-file id, assigned by the editor."""
        return self.__uid

    def get_type_id(self) -> str:
        """PROP_REGISTRY key."""
        return self.__type_id

    def get_position(self) -> Tuple[int, int]:
        """Grid cell (x, y)."""
        return (self.__x, self.__y)

    def set_position(self, x: int, y: int) -> bool:
        """Move the prop. Negative coordinates are rejected."""
        if x < 0 or y < 0:
            return False
        self.__x, self.__y = int(x), int(y)
        return True

    def get_rotation(self) -> int:
        """Quarter-turn rotation in degrees: 0, 90, 180 or 270."""
        return self.__rotation

    def set_rotation(self, degrees: Any) -> bool:
        """
        Turn the prop, snapping to the nearest quarter.

        Rotation is PURELY VISUAL. A turned prop still occupies the
        same cells and blocks the same way -- rotating a footprint
        would let an author silently reshape collision from a keypress,
        and a 1x3 tree laid on its side is a bug, not a feature.
        """
        value = normalise_rotation(degrees)
        changed = value != self.__rotation
        self.__rotation = value
        return changed

    def get_footprint_rect(self) -> Tuple[int, int, int, int]:
        """
        (x, y, w, h) in CELLS of everything this prop covers.

        The stored position is the prop's BOTTOM-LEFT corner, so the
        rectangle runs upward from it and its top row is y - h + 1.
        Rotation is ignored on purpose, the same way set_rotation()
        ignores it: a turned prop occupies the cells it always did.
        """
        cells_w, cells_h = get_prop_footprint(self.__type_id)
        return (self.__x, self.__y - cells_h + 1, cells_w, cells_h)

    def covers_cell(self, x: int, y: int) -> bool:
        """True when a cell falls anywhere inside this prop's footprint."""
        fx, fy, fw, fh = self.get_footprint_rect()
        return fx <= x < fx + fw and fy <= y < fy + fh

    def overlaps(self, other: "PropData") -> bool:
        """
        True when two props' footprints share at least one cell.

        This is what makes "bring forward" mean something: the props a
        given one is actually stacked with, rather than every prop in
        the level.
        """
        ax, ay, aw, ah = self.get_footprint_rect()
        bx, by, bw, bh = other.get_footprint_rect()
        return (ax < bx + bw and bx < ax + aw
                and ay < by + bh and by < ay + ah)

    def is_portal(self) -> bool:
        """
        True for the step-on portal prop type (Spec §9).

        Distinct from `travels_on_interact()`: a portal fires the moment
        the player walks onto it, while ANY prop can be given the
        "travel" interaction kind and fires on E instead. Both carry the
        same target_level_id / target_spawn fields.
        """
        return self.__type_id == PORTAL_TYPE_ID

    def travels_on_interact(self) -> bool:
        """
        True when pressing E on this prop should move the player.

        A door you open rather than a threshold you cross. Restrictions
        come from the prop's own gate, which exploration.__interact
        already evaluates before it ever reaches the prop.
        """
        return (self.__interactable and self.__kind == "travel"
                and bool(self.__target_level_id))

    def has_travel_fields(self) -> bool:
        """True when this prop stores a destination at all."""
        return self.is_portal() or self.__kind == "travel"

    # ── collision + movement ──────────────────────────────────

    def get_passthrough(self) -> bool:
        """True = walk-through, False = solid."""
        return self.__passthrough

    def set_passthrough(self, value: bool) -> None:
        """
        Toggle solidity. The stored speed modifier is deliberately
        kept: flipping a prop to BLOCKING makes its modifier dead
        data, which validate() then flags (MODIFIER_ON_BLOCKER)
        rather than silently discarding the designer's setting.

        Making a prop solid also drops "pass from behind", because a
        prop the player cannot walk into is one they can never end up
        behind — the two settings would contradict each other and the
        collision grid would have to pick a winner silently.
        """
        self.__passthrough = bool(value)
        if not self.__passthrough:
            self.__pass_behind = False

    def get_pass_behind(self) -> bool:
        """
        True when the player walks BEHIND this prop instead of over it.

        The prop is then drawn above the player and faded to
        get_behind_transparency() while they are inside its footprint,
        so a shopfront or a bookshelf can be stood behind without the
        player disappearing into it.
        """
        return self.__pass_behind

    def set_pass_behind(self, value: bool) -> None:
        """
        Turn walk-behind on or off.

        Turning it ON also makes the prop passthrough: the whole point
        is that the player walks INTO its cells, which a solid prop can
        never allow. Writing both means every reader that predates this
        setting — the collision grid, the validator, the game's own
        older draw path — still gets the right answer from the
        `passthrough` flag alone.
        """
        self.__pass_behind = bool(value)
        if self.__pass_behind:
            self.__passthrough = True

    def get_behind_transparency(self) -> int:
        """How see-through the prop goes, in percent, while walked behind."""
        return self.__behind_transparency

    def set_behind_transparency(self, value: Any) -> bool:
        """Clamp into the legal range. True when the value changed."""
        percent = normalise_transparency(value)
        changed = percent != self.__behind_transparency
        self.__behind_transparency = percent
        return changed

    def get_behind_alpha(self) -> int:
        """The blit alpha (0-255) to draw this prop at while walked behind."""
        return transparency_to_alpha(self.__behind_transparency)

    def get_speed_modifier(self) -> float:
        """Multiplier the player's speed eases toward on this cell."""
        return self.__speed_modifier

    def set_speed_modifier(self, value: float) -> bool:
        """
        Clamp into [0.1, 2.0]. Only meaningful on passthrough props —
        the popup disables the slider when the prop is blocking
        (Spec §5.2), and validate() warns if one slips through.
        """
        clamped = max(SPEED_MODIFIER_MIN, min(SPEED_MODIFIER_MAX, float(value)))
        self.__speed_modifier = round(clamped, 2)
        return True

    # ── interaction ───────────────────────────────────────────

    def get_interactable(self) -> bool:
        """True when the player can trigger this prop."""
        return self.__interactable

    def set_interactable(self, value: bool) -> None:
        """Toggle interactivity; keeps the configured reward around."""
        self.__interactable = bool(value)

    def get_interaction_kind(self) -> str:
        """"none", "money", "skill" or "menu"."""
        return self.__kind

    def set_interaction_kind(self, kind: str) -> bool:
        """
        Switch reward type, re-seeding the amount into that kind's
        legal range so the popup never shows an out-of-range value.

        "menu" grants nothing — it opens a screen — so it clears the
        amount exactly as "none" does and seeds a menu id instead.
        """
        if kind not in INTERACTION_KINDS:
            return False
        self.__kind = kind
        if kind == "money":
            self.__amount = max(MONEY_MIN, min(MONEY_MAX, self.__amount))
            if self.__amount <= 0:
                self.__amount = MONEY_MIN
            self.__skill_id = None
        elif kind == "skill":
            self.__amount = max(float(EXP_MIN),
                                min(float(EXP_MAX), self.__amount))
            if self.__amount <= 0:
                self.__amount = float(EXP_MIN)
            if self.__skill_id is None:
                self.__skill_id = SKILL_IDS[0]
        elif kind == "menu":
            self.__amount = 0.0
            self.__skill_id = None
            if not self.__menu_id:
                self.__menu_id = MENU_ID_DEFAULT
        elif kind == "travel":
            # A door grants nothing; it moves you. The destination is
            # kept in the same fields a portal uses.
            self.__amount = 0.0
            self.__skill_id = None
        else:
            self.__amount = 0.0
            self.__skill_id = None
        return True

    def get_menu_id(self) -> str:
        """
        The screen a "menu" prop opens ("" = unset).

        Kept even after the kind is switched away, so an author who
        flips a noticeboard to money and back does not lose which
        screen they had chosen. Only the active kind is acted on.
        """
        return self.__menu_id

    def set_menu_id(self, menu_id: Optional[str]) -> bool:
        """
        Name the screen to open, or None/"" to clear it.

        An id outside MENU_REGISTRY is REFUSED rather than coerced:
        there is no nearest sensible screen, and quietly substituting
        one would send the player somewhere the author never chose.
        """
        if menu_id is None or menu_id == "":
            changed = self.__menu_id != ""
            self.__menu_id = ""
            return changed
        text = str(menu_id)
        if text not in MENU_REGISTRY:
            return False
        changed = text != self.__menu_id
        self.__menu_id = text
        return changed

    def opens_menu(self) -> bool:
        """True when interacting with this prop should open a screen."""
        return (self.__interactable and self.__kind == "menu"
                and bool(self.__menu_id))

    def get_amount(self) -> float:
        """BDT for money rewards, EXP points for skill rewards."""
        return self.__amount

    def set_amount(self, value: float) -> bool:
        """
        Clamp to the active kind's range. The EXP ceiling of 10 is a
        hard rule: no prop may out-earn a SideQuest (Spec §5.3).
        """
        if self.__kind == "money":
            self.__amount = max(MONEY_MIN, min(MONEY_MAX, float(value)))
            return True
        if self.__kind == "skill":
            self.__amount = float(
                max(EXP_MIN, min(EXP_MAX, int(round(float(value))))))
            return True
        return False

    def get_skill_id(self) -> Optional[str]:
        """Target skill node for skill rewards, else None."""
        return self.__skill_id

    def set_skill_id(self, skill_id: Optional[str]) -> bool:
        """Only ids from the canonical SKILL_IDS list are accepted."""
        if skill_id is None:
            self.__skill_id = None
            return True
        if skill_id not in SKILL_IDS:
            return False
        self.__skill_id = skill_id
        return True

    def get_triggers_per_semester(self) -> int:
        """How many times this prop may pay out per semester (1-5)."""
        return self.__triggers_per_semester

    def set_triggers_per_semester(self, value: int) -> bool:
        """Clamp into [1, 5]."""
        self.__triggers_per_semester = max(TRIGGERS_MIN,
                                           min(TRIGGERS_MAX, int(value)))
        return True

    # ── portal settings ───────────────────────────────────────

    def get_target_level_id(self) -> str:
        """Destination level for portal props ("" = unset)."""
        return self.__target_level_id

    def set_target_level_id(self, level_id: str) -> bool:
        """Accepts a slug, or "" to clear."""
        text = (level_id or "").strip()
        if text and not LEVEL_ID_PATTERN.match(text):
            return False
        self.__target_level_id = text
        return True

    def get_target_spawn(self) -> Optional[Tuple[int, int]]:
        """Cell to drop the player on in the destination level."""
        return self.__target_spawn

    def set_target_spawn(self, cell: Optional[Tuple[int, int]]) -> bool:
        """Set or clear (None) the destination cell."""
        if cell is None:
            self.__target_spawn = None
            return True
        x, y = cell
        if x < 0 or y < 0:
            return False
        self.__target_spawn = (int(x), int(y))
        return True

    # ── gate (Feature 6, phase F5) ────────────────────────────

    def get_gate(self) -> GateData:
        """
        This prop's gate. Always present; may be an open default.

        A gated prop is a door: the player may stand next to it, but
        interacting with it runs the gate first.
        """
        return self.__gate

    def set_gate(self, gate: Optional[GateData]) -> bool:
        """Attach a gate. None clears it back to an open default."""
        if gate is None:
            self.__gate = GateData()
            return True
        if not isinstance(gate, GateData):
            return False
        self.__gate = gate
        return True

    def is_gated(self) -> bool:
        """True when this prop actually restricts the player."""
        return self.__gate.has_requirements()

    # ── serialisation ─────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialise, re-emitting any unknown keys we read in."""
        data: Dict[str, Any] = dict(self.__extra)
        data.update({
            "uid": self.__uid,
            "type_id": self.__type_id,
            "x": self.__x,
            "y": self.__y,
            "passthrough": self.__passthrough,
            "speed_modifier": self.__speed_modifier,
            "interactable": self.__interactable,
            "interaction": {
                "kind": self.__kind,
                "amount": self.__amount,
                "skill_id": self.__skill_id,
                "triggers_per_semester": self.__triggers_per_semester,
            },
        })
        # Written only when a menu was actually chosen, the same rule
        # `gate` and `zones` follow: a prop that opens no menu
        # serialises exactly as it did before menus existed, so every
        # level authored earlier still round-trips byte-identical.
        if self.__menu_id:
            data["interaction"]["menu_id"] = self.__menu_id
        # Omitted while unturned, so a level with no rotated props
        # serialises exactly as it did before rotation existed.
        if self.__rotation:
            data["rotation"] = self.__rotation
        # Same rule for walk-behind: a prop that does not use it writes
        # neither key, so every level authored before the setting
        # existed round-trips byte-identical.
        if self.__pass_behind:
            data["pass_behind"] = True
            data["behind_transparency"] = self.__behind_transparency
        # Written for step-on portals AND for any prop whose interaction
        # kind is "travel". A prop that does neither omits both keys, so
        # every level authored before travel props round-trips unchanged.
        if self.has_travel_fields():
            data["target_level_id"] = self.__target_level_id
            data["target_spawn"] = (list(self.__target_spawn)
                                    if self.__target_spawn else None)
        # Omitted entirely when the gate is open, so a level with no
        # gates serialises exactly as it did before F5.
        gate = self.__gate.to_dict()
        if gate:
            data["gate"] = gate
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PropData":
        """Rebuild a prop, tolerating missing optional keys."""
        prop = PropData(str(data.get("uid", "")),
                        str(data.get("type_id", "")),
                        int(data.get("x", 0)), int(data.get("y", 0)))
        prop.set_passthrough(bool(data.get("passthrough",
                                           prop.get_passthrough())))
        prop.set_speed_modifier(float(data.get("speed_modifier",
                                               SPEED_MODIFIER_BASE)))
        prop.set_interactable(bool(data.get("interactable", False)))
        prop.set_rotation(data.get("rotation", ROTATION_DEFAULT))
        # After set_passthrough, never before: turning walk-behind on
        # forces passthrough, and a stored `passthrough: false` beside
        # `pass_behind: true` must not win over it.
        prop.set_behind_transparency(data.get("behind_transparency",
                                              BEHIND_TRANSPARENCY_DEFAULT))
        prop.set_pass_behind(bool(data.get("pass_behind",
                                           PASS_BEHIND_DEFAULT)))

        interaction: Dict[str, Any] = data.get("interaction") or {}
        # Read BEFORE the kind so switching to "menu" sees the stored
        # id and does not overwrite it with the default.
        if interaction.get("menu_id"):
            prop.set_menu_id(str(interaction["menu_id"]))
        prop.set_interaction_kind(str(interaction.get(
            "kind", INTERACTION_KIND_DEFAULT)))
        if interaction.get("amount") is not None:
            prop.set_amount(float(interaction["amount"]))
        if interaction.get("skill_id"):
            prop.set_skill_id(str(interaction["skill_id"]))
        prop.set_triggers_per_semester(int(interaction.get(
            "triggers_per_semester", TRIGGERS_DEFAULT)))

        if prop.has_travel_fields():
            prop.set_target_level_id(str(data.get("target_level_id", "")))
            spawn = data.get("target_spawn")
            if isinstance(spawn, (list, tuple)) and len(spawn) == 2:
                prop.set_target_spawn((int(spawn[0]), int(spawn[1])))

        prop.set_gate(GateData.from_dict(data.get("gate")))

        prop.__extra = {
            k: v for k, v in data.items()
            if k not in _KNOWN_PROP_KEYS
            and k not in ("target_level_id", "target_spawn")
        }
        return prop


# ─────────────────────────────────────────────────────────────
# DIALOG
# ─────────────────────────────────────────────────────────────


class DialogChain:
    """
    One conversation beat: an ordered list of pre-split lines plus
    the emotion the dialog box wears while playing them.

    The emotion field is an E1 extension to Spec §6.2, added so the
    in-game chat box can show the right NPC face (owner request:
    "in interaction chatboxes it should be the npc images with the
    emotions"). Chains without it fall back to the NPC's default.

    CHOICE (owner request, 2026-08-08). A chain may end in a branch
    instead of simply finishing: `choice` carries a prompt and up to
    CHOICE_OPTIONS_MAX replies, each naming the chain to jump to.

        {"prompt": "WHAT DO YOU SAY?",
         "options": [{"label": "Sure.",       "goto": "rafi_yes"},
                     {"label": "Not today.",  "goto": "rafi_no"}]}

    An option whose `goto` is "" ends the conversation, which is what
    makes a plain accept/decline pair work without authoring a dead
    chain for the decline arm. A `goto` naming a chain that does not
    exist is a WARNING, not a blocker — the conversation just ends,
    and a typo in one reply must never stop a level loading.

    Serialised only when there IS a choice, so every level file that
    predates this still round-trips byte for byte.
    """

    def __init__(self, chain_id: str, lines: Optional[List[str]] = None,
                 emotion: str = "") -> None:
        self.__chain_id: str = chain_id
        self.__lines: List[str] = list(lines) if lines else []
        self.__emotion: str = emotion
        self.__choice_prompt: str = ""
        self.__choice_options: List[Dict[str, str]] = []
        self.__extra: Dict[str, Any] = {}

    def get_chain_id(self) -> str:
        """Identifier shown in the editor's chain table."""
        return self.__chain_id

    def set_chain_id(self, chain_id: str) -> bool:
        """Rename the chain. Empty names are rejected."""
        text = (chain_id or "").strip()
        if not text:
            return False
        self.__chain_id = text
        return True

    def get_lines(self) -> List[str]:
        """Copy of the line list — mutate via the methods below."""
        return list(self.__lines)

    def get_line_count(self) -> int:
        """Number of lines in this chain."""
        return len(self.__lines)

    def add_line(self, text: str, index: Optional[int] = None) -> None:
        """Append, or insert at `index`."""
        if index is None:
            self.__lines.append(text)
        else:
            self.__lines.insert(max(0, min(len(self.__lines), index)), text)

    def set_line(self, index: int, text: str) -> bool:
        """Replace one line."""
        if not 0 <= index < len(self.__lines):
            return False
        self.__lines[index] = text
        return True

    def remove_line(self, index: int) -> bool:
        """Delete one line."""
        if not 0 <= index < len(self.__lines):
            return False
        del self.__lines[index]
        return True

    def move_line(self, index: int, delta: int) -> bool:
        """Reorder one line by `delta` positions."""
        target = index + delta
        if not 0 <= index < len(self.__lines):
            return False
        if not 0 <= target < len(self.__lines):
            return False
        self.__lines[index], self.__lines[target] = \
            self.__lines[target], self.__lines[index]
        return True

    def get_emotion(self) -> str:
        """Portrait emotion for this chain ("" = the NPC's default)."""
        return self.__emotion

    def set_emotion(self, emotion: str) -> None:
        """Set the portrait emotion; validated against the NPC later."""
        self.__emotion = emotion or ""

    # ── choice (owner request, 2026-08-08) ────────────────────

    def has_choice(self) -> bool:
        """True when this chain ends in a branch rather than just stopping."""
        return len(self.__choice_options) > 0

    def get_choice_prompt(self) -> str:
        """The ALL-CAPS strip above the replies ("" = the box default)."""
        return self.__choice_prompt

    def set_choice_prompt(self, prompt: str) -> None:
        """Label the reply list. Empty falls back to the box's own text."""
        self.__choice_prompt = str(prompt or "").strip()

    def get_choice_options(self) -> List[Dict[str, str]]:
        """Copy of the reply list — mutate via set_choice()."""
        return [dict(option) for option in self.__choice_options]

    def get_choice_labels(self) -> List[str]:
        """Just the reply text, in order, for the ChoiceBox to draw."""
        return [option["label"] for option in self.__choice_options]

    def get_choice_goto(self, index: int) -> str:
        """
        The chain id reply `index` jumps to, or "".

        "" covers both "this reply ends the conversation" and "there is
        no such reply", because the caller does the same thing for each.
        """
        if not 0 <= index < len(self.__choice_options):
            return ""
        return self.__choice_options[index].get("goto", "")

    def set_choice(self, prompt: str,
                   options: Optional[Sequence[Any]]) -> bool:
        """
        Replace the branch. An empty list clears it.

        `options` accepts dicts ({"label":..., "goto":...}), (label, goto)
        pairs, or bare strings for a reply that just ends the talk.
        Options past CHOICE_OPTIONS_MAX are dropped rather than accepted
        and then silently not drawn — ui/choice_box.py renders at most
        that many, and a reply the player cannot see is worse than one
        the author is told about.
        """
        cleaned: List[Dict[str, str]] = []
        for option in (options or []):
            if isinstance(option, dict):
                label = str(option.get("label", "")).strip()
                goto = str(option.get("goto", "")).strip()
            elif isinstance(option, (tuple, list)) and option:
                label = str(option[0]).strip()
                goto = str(option[1]).strip() if len(option) > 1 else ""
            else:
                label, goto = str(option).strip(), ""
            if label:
                cleaned.append({"label": label, "goto": goto})
        self.__choice_prompt = str(prompt or "").strip()
        self.__choice_options = cleaned[:CHOICE_OPTIONS_MAX]
        return True

    def clear_choice(self) -> None:
        """Drop the branch; the chain then simply ends."""
        self.__choice_prompt = ""
        self.__choice_options = []

    def to_dict(self) -> Dict[str, Any]:
        """Serialise, re-emitting unknown keys."""
        data: Dict[str, Any] = dict(self.__extra)
        data.update({"chain_id": self.__chain_id, "lines": list(self.__lines)})
        if self.__emotion:
            data["emotion"] = self.__emotion
        # Omitted entirely when there is no branch, so a level authored
        # before choices existed serialises exactly as it did before.
        if self.__choice_options:
            choice: Dict[str, Any] = {
                "options": [dict(o) for o in self.__choice_options]}
            if self.__choice_prompt:
                choice["prompt"] = self.__choice_prompt
            data["choice"] = choice
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DialogChain":
        """Rebuild a chain from raw JSON."""
        lines = [str(line) for line in (data.get("lines") or [])]
        chain = DialogChain(str(data.get("chain_id", "chain")), lines,
                            str(data.get("emotion", "")))
        raw_choice = data.get("choice")
        if isinstance(raw_choice, dict):
            chain.set_choice(str(raw_choice.get("prompt", "")),
                             raw_choice.get("options"))
        chain.__extra = {
            k: v for k, v in data.items()
            if k not in ("chain_id", "lines", "emotion", "choice")
        }
        return chain


# ─────────────────────────────────────────────────────────────
# NPC INSTANCE
# ─────────────────────────────────────────────────────────────


class NpcData:
    """
    One placed NPC (Spec §6). Carries only placement + dialog:
    the 0.75-1.00 availability window is a GAME rule enforced at
    runtime, deliberately not editable here (Spec §6.1).
    """

    def __init__(self, uid: str, type_id: str, x: int, y: int) -> None:
        self.__uid: str = uid
        self.__type_id: str = type_id
        self.__x: int = int(x)
        self.__y: int = int(y)
        self.__facing: str = FACING_DEFAULT
        self.__interactable: bool = True
        self.__chains: List[DialogChain] = []
        self.__on_complete: str = ON_COMPLETE_DEFAULT
        self.__gate: GateData = GateData()
        self.__extra: Dict[str, Any] = {}

    # ── identity + placement ──────────────────────────────────

    def get_uid(self) -> str:
        """Stable per-file id."""
        return self.__uid

    def get_type_id(self) -> str:
        """NPC_REGISTRY key."""
        return self.__type_id

    def get_position(self) -> Tuple[int, int]:
        """Grid cell (x, y)."""
        return (self.__x, self.__y)

    def set_position(self, x: int, y: int) -> bool:
        """Move the NPC. Negative coordinates are rejected."""
        if x < 0 or y < 0:
            return False
        self.__x, self.__y = int(x), int(y)
        return True

    def get_facing(self) -> str:
        """One of down / left / right / up."""
        return self.__facing

    def set_facing(self, facing: str) -> bool:
        """Set facing; unknown values are rejected."""
        if facing not in FACINGS:
            return False
        self.__facing = facing
        return True

    def get_interactable(self) -> bool:
        """False = scenery NPC, cannot be talked to."""
        return self.__interactable

    def set_interactable(self, value: bool) -> None:
        """Toggle whether the player can start a conversation."""
        self.__interactable = bool(value)

    # ── dialog ────────────────────────────────────────────────

    def get_chains(self) -> List[DialogChain]:
        """Copy of the chain list in play order."""
        return list(self.__chains)

    def get_chain(self, index: int) -> Optional[DialogChain]:
        """Chain at `index`, or None."""
        if 0 <= index < len(self.__chains):
            return self.__chains[index]
        return None

    def find_chain(self, chain_id: str) -> Optional[DialogChain]:
        """
        Chain by its authored id, or None — what a choice's `goto` needs.

        Ids are unique per NPC (add_chain suffixes a duplicate), so the
        first match is the only match.
        """
        if not chain_id:
            return None
        for chain in self.__chains:
            if chain.get_chain_id() == chain_id:
                return chain
        return None

    def find_chain_index(self, chain_id: str) -> int:
        """The position of a chain by id, or -1."""
        for index, chain in enumerate(self.__chains):
            if chain.get_chain_id() == chain_id:
                return index
        return -1

    def get_chain_count(self) -> int:
        """Number of chains."""
        return len(self.__chains)

    def add_chain(self, chain_id: str = "") -> DialogChain:
        """Append a new empty chain with a unique auto id if needed."""
        if not chain_id:
            chain_id = f"chain_{len(self.__chains) + 1}"
        existing = {c.get_chain_id() for c in self.__chains}
        base, n = chain_id, 2
        while chain_id in existing:
            chain_id = f"{base}_{n}"
            n += 1
        chain = DialogChain(chain_id)
        default_emotion = (get_npc_def(self.__type_id) or {}).get(
            "default_emotion", "")
        chain.set_emotion(default_emotion)
        self.__chains.append(chain)
        return chain

    def remove_chain(self, index: int) -> bool:
        """Delete a chain."""
        if not 0 <= index < len(self.__chains):
            return False
        del self.__chains[index]
        return True

    def move_chain(self, index: int, delta: int) -> bool:
        """Reorder a chain — play order IS list order (Spec §6.2)."""
        target = index + delta
        if not 0 <= index < len(self.__chains):
            return False
        if not 0 <= target < len(self.__chains):
            return False
        self.__chains[index], self.__chains[target] = \
            self.__chains[target], self.__chains[index]
        return True

    def get_on_complete(self) -> str:
        """loop_last / loop_all / silent (Spec §6.2)."""
        return self.__on_complete

    def set_on_complete(self, mode: str) -> bool:
        """Set the recurrence mode; unknown modes are rejected."""
        if mode not in ON_COMPLETE_MODES:
            return False
        self.__on_complete = mode
        return True

    def get_total_line_count(self) -> int:
        """Every line across every chain — used by the editor readout."""
        return sum(c.get_line_count() for c in self.__chains)

    # ── gate (Feature 6, phase F5) ────────────────────────────

    def get_gate(self) -> GateData:
        """
        This NPC's gate. Always present; may be an open default.

        NOTE the roster interaction. The build plan asks for an NPC's
        gate to "default min_semester to get_npc_min_semester(type_id)".
        Seeding the STORED gate that way would make every NPC's gate
        non-default the moment it was created, which would serialise a
        gate into every existing level file and break the byte-identical
        round trip that is F5's acceptance test.

        So the stored gate stays open, and the roster figure is applied
        in the two places it is actually needed:
            make_default_gate()          what the editor pre-fills
            get_effective_min_semester() what the runtime enforces
        Both are documented in PHASELOG_F5 §8.
        """
        return self.__gate

    def set_gate(self, gate: Optional[GateData]) -> bool:
        """Attach a gate. None clears it back to an open default."""
        if gate is None:
            self.__gate = GateData()
            return True
        if not isinstance(gate, GateData):
            return False
        self.__gate = gate
        return True

    def is_gated(self) -> bool:
        """True when this NPC actually restricts the player."""
        return self.__gate.has_requirements()

    def make_default_gate(self) -> GateData:
        """
        A fresh gate pre-filled from the roster, for the editor to edit.

        Opening the gate form on Prof. Hoque starts at semester 5
        because content/npc_roster.py already says that is when he
        appears -- the author does not have to remember it.
        """
        gate = GateData()
        gate.set_min_semester(get_npc_min_semester(self.__type_id))
        return gate

    def get_effective_min_semester(self) -> int:
        """
        The semester this NPC really becomes available.

        The stricter of the roster's figure and any explicit gate, so an
        author can delay an NPC past their roster debut but never drag
        them earlier than the narrative allows.
        """
        return max(get_npc_min_semester(self.__type_id),
                   self.__gate.get_min_semester())

    # ── serialisation ─────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialise, re-emitting unknown keys."""
        data: Dict[str, Any] = dict(self.__extra)
        data.update({
            "uid": self.__uid,
            "type_id": self.__type_id,
            "x": self.__x,
            "y": self.__y,
            "facing": self.__facing,
            "interactable": self.__interactable,
            "dialog": {
                "chains": [c.to_dict() for c in self.__chains],
                "on_complete": self.__on_complete,
            },
        })
        # Omitted entirely when the gate is open, so a level with no
        # gates serialises exactly as it did before F5.
        gate = self.__gate.to_dict()
        if gate:
            data["gate"] = gate
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "NpcData":
        """Rebuild an NPC, tolerating missing optional keys."""
        npc = NpcData(str(data.get("uid", "")), str(data.get("type_id", "")),
                      int(data.get("x", 0)), int(data.get("y", 0)))
        npc.set_facing(str(data.get("facing", FACING_DEFAULT)))
        npc.set_interactable(bool(data.get("interactable", True)))

        dialog: Dict[str, Any] = data.get("dialog") or {}
        npc.__chains = [DialogChain.from_dict(c)
                        for c in (dialog.get("chains") or [])]
        npc.set_on_complete(str(dialog.get("on_complete",
                                           ON_COMPLETE_DEFAULT)))
        npc.set_gate(GateData.from_dict(data.get("gate")))
        npc.__extra = {
            k: v for k, v in data.items() if k not in _KNOWN_NPC_KEYS
        }
        return npc


# ─────────────────────────────────────────────────────────────
# LEVEL DOCUMENT
# ─────────────────────────────────────────────────────────────


class LevelData:
    """
    The whole level file, in memory.

    This is the EDITABLE document. `engine.level_loader.Level` is the
    read-only runtime view built from it — keeping the two apart is
    what stops the game from ever writing level files (Spec §1).
    """

    def __init__(self, level_name: str = "New Level",
                 level_id: str = "new_level",
                 grid_width: int = 40, grid_height: int = 24,
                 fill_tile: int = DEFAULT_GROUND_TILE) -> None:
        width = max(GRID_MIN, min(GRID_MAX, int(grid_width)))
        height = max(GRID_MIN, min(GRID_MAX, int(grid_height)))
        self.__schema_version: int = SCHEMA_VERSION
        self.__level_name: str = level_name
        self.__level_id: str = level_id
        self.__grid_width: int = width
        self.__grid_height: int = height
        self.__ambient: str = AMBIENT_DEFAULT
        self.__music: str = ""
        self.__spawn: Tuple[int, int] = (width // 2, height // 2)
        self.__ground: List[List[int]] = [[fill_tile] * width
                                          for _ in range(height)]
        self.__overlay: List[List[int]] = [[EMPTY_TILE] * width
                                           for _ in range(height)]
        # Tile rotation is SPARSE: {(layer, x, y): degrees} holding only
        # the cells actually turned. A parallel full-size array would
        # double every level file to record a feature most maps never
        # use, and would rewrite all fourteen existing files on first
        # save. An absent key means 0.
        self.__tile_rotations: Dict[Tuple[str, int, int], int] = {}
        self.__props: List[PropData] = []
        self.__npcs: List[NpcData] = []
        self.__zones: List[ZoneData] = []
        self.__meta_extra: Dict[str, Any] = {}
        self.__extra: Dict[str, Any] = {}
        self.__source_path: str = ""

    # ── meta ──────────────────────────────────────────────────

    def get_schema_version(self) -> int:
        """Version of the format this document was read as."""
        return self.__schema_version

    def get_level_name(self) -> str:
        """Human-facing name shown in the editor's top bar."""
        return self.__level_name

    def set_level_name(self, name: str) -> bool:
        """Rename the level. Empty names are rejected."""
        text = (name or "").strip()
        if not text:
            return False
        self.__level_name = text
        return True

    def get_level_id(self) -> str:
        """Slug — filename AND the game's current_location_id."""
        return self.__level_id

    def set_level_id(self, level_id: str) -> bool:
        """Set the slug; must match [a-z0-9_]+."""
        text = (level_id or "").strip()
        if not LEVEL_ID_PATTERN.match(text):
            return False
        self.__level_id = text
        return True

    def get_grid_width(self) -> int:
        """Columns."""
        return self.__grid_width

    def get_grid_height(self) -> int:
        """Rows."""
        return self.__grid_height

    def get_ambient(self) -> str:
        """Static cosmetic tint preset — never a clock."""
        return self.__ambient

    def set_ambient(self, ambient: str) -> bool:
        """Pick one of the four presets."""
        if ambient not in AMBIENT_PRESETS:
            return False
        self.__ambient = ambient
        return True

    def get_music(self) -> str:
        """Asset path of the level BGM ("" = silent)."""
        return self.__music

    def set_music(self, path: str) -> None:
        """Set the BGM path; not required to exist yet."""
        self.__music = (path or "").strip()

    def get_spawn(self) -> Tuple[int, int]:
        """Cell the player starts on."""
        return self.__spawn

    def set_spawn(self, x: int, y: int) -> bool:
        """Move the spawn marker. Must stay inside the grid."""
        if not self.is_inside(x, y):
            return False
        self.__spawn = (int(x), int(y))
        return True

    def get_source_path(self) -> str:
        """Path this document was read from, or "" for a fresh level."""
        return self.__source_path

    def set_source_path(self, path: str) -> None:
        """Remember where this document lives on disk."""
        self.__source_path = path

    # ── grid ──────────────────────────────────────────────────

    def is_inside(self, x: int, y: int) -> bool:
        """True when (x, y) is a real cell."""
        return 0 <= x < self.__grid_width and 0 <= y < self.__grid_height

    def __layer(self, layer: str) -> Optional[List[List[int]]]:
        """Internal: pick a layer array by name."""
        if layer == LAYER_GROUND:
            return self.__ground
        if layer == LAYER_OVERLAY:
            return self.__overlay
        return None

    def get_layer_rows(self, layer: str) -> List[List[int]]:
        """
        The raw rows of a layer. Returned by reference for rendering
        speed — the editor only writes through set_tile().
        """
        rows = self.__layer(layer)
        return rows if rows is not None else []

    def get_tile(self, layer: str, x: int, y: int) -> int:
        """Tile index at a cell, or EMPTY_TILE when out of bounds."""
        rows = self.__layer(layer)
        if rows is None or not self.is_inside(x, y):
            return EMPTY_TILE
        return rows[y][x]

    def set_tile(self, layer: str, x: int, y: int, value: int) -> bool:
        """
        Paint one cell. Rejects unknown tile indices, out-of-bounds
        cells, and EMPTY on the ground layer (ground must stay fully
        painted — Spec §2.1).
        """
        rows = self.__layer(layer)
        if rows is None or not self.is_inside(x, y):
            return False
        if value == EMPTY_TILE:
            if layer == LAYER_GROUND:
                return False
        elif get_tile_def(value) is None:
            return False
        if rows[y][x] == value:
            return False
        rows[y][x] = value
        return True

    def get_tile_rotation(self, layer: str, x: int, y: int) -> int:
        """Quarter-turn rotation of one painted cell; 0 when unturned."""
        return self.__tile_rotations.get((layer, x, y), ROTATION_DEFAULT)

    def set_tile_rotation(self, layer: str, x: int, y: int,
                          degrees: Any) -> bool:
        """
        Turn one painted cell. False when nothing changed.

        A rotation of 0 DELETES the entry rather than storing a zero,
        which is what keeps the map sparse and keeps an unrotated level
        serialising to exactly the bytes it had before.

        Purely visual, like a prop's: walkability comes from the tile's
        registry entry, and turning a wall does not open it.
        """
        if layer not in LAYER_NAMES or not self.is_inside(x, y):
            return False
        value = normalise_rotation(degrees)
        key = (layer, x, y)
        current = self.__tile_rotations.get(key, ROTATION_DEFAULT)
        if value == current:
            return False
        if value == ROTATION_DEFAULT:
            self.__tile_rotations.pop(key, None)
        else:
            self.__tile_rotations[key] = value
        return True

    def get_tile_rotation_count(self) -> int:
        """How many cells carry a rotation — used by the editor readout."""
        return len(self.__tile_rotations)

    def is_terrain_walkable(self, x: int, y: int) -> bool:
        """
        Collision from the MAP ALONE: overlay wins over ground, and a
        solid prop blocks regardless of the tiles under it.

        Split out from is_cell_walkable() so the validator can ask
        "is this a sensible place to stand?" about a cell an NPC is
        already standing on. Asking the combined question there would
        report every NPC in the level as standing somewhere blocked.
        """
        if not self.is_inside(x, y):
            return False
        overlay = self.__overlay[y][x]
        tile_ok = (is_tile_walkable(overlay) if overlay != EMPTY_TILE
                   else is_tile_walkable(self.__ground[y][x]))
        if not tile_ok:
            return False
        # Root, not anchor: a tree blocks every cell of its trunk, and
        # nothing at all under its canopy.
        prop = self.get_prop_root_at(x, y)
        if prop is not None and not prop.get_passthrough():
            return False
        return True

    def is_cell_walkable(self, x: int, y: int) -> bool:
        """
        Can the player occupy this cell? Terrain, plus entities.

        An NPC is SOLID: you talk to them from the next cell over, you
        do not walk through them. `engine/level_loader.py` bakes this
        into its collision grid, so the rule reaches the game as well
        as the editor from this one place.
        """
        if not self.is_terrain_walkable(x, y):
            return False
        return self.get_npc_at(x, y) is None

    def resize(self, width: int, height: int,
               fill_tile: int = DEFAULT_GROUND_TILE) -> bool:
        """
        Change the grid. Growing pads with `fill_tile` on ground and
        empty on overlay; shrinking DELETES out-of-range rows,
        columns and entities (the editor warns first — Spec §4.4).
        """
        if not GRID_MIN <= width <= GRID_MAX:
            return False
        if not GRID_MIN <= height <= GRID_MAX:
            return False
        if get_tile_def(fill_tile) is None:
            return False

        def _resize(rows: List[List[int]], pad: int) -> List[List[int]]:
            out: List[List[int]] = []
            for y in range(height):
                if y < len(rows):
                    row = rows[y][:width]
                    row.extend([pad] * (width - len(row)))
                else:
                    row = [pad] * width
                out.append(row)
            return out

        self.__ground = _resize(self.__ground, fill_tile)
        self.__overlay = _resize(self.__overlay, EMPTY_TILE)
        self.__grid_width, self.__grid_height = width, height

        self.__props = [p for p in self.__props
                        if self.is_inside(*p.get_position())]
        self.__npcs = [n for n in self.__npcs
                       if self.is_inside(*n.get_position())]
        sx, sy = self.__spawn
        self.__spawn = (min(sx, width - 1), min(sy, height - 1))
        return True

    def count_out_of_range(self, width: int, height: int) -> int:
        """How many entities a shrink to (width, height) would delete."""
        lost = 0
        for entity in list(self.__props) + list(self.__npcs):
            x, y = entity.get_position()
            if x >= width or y >= height:
                lost += 1
        return lost

    # ── props ─────────────────────────────────────────────────

    def get_props(self) -> List[PropData]:
        """
        Copy of the prop list, in DRAW ORDER — bottom of the stack
        first, so a renderer can simply walk it forwards.

        The list order IS the layering. It survives a save because JSON
        arrays are ordered, and it is what reorder_prop() rearranges.
        """
        return list(self.__props)

    def get_props_at(self, x: int, y: int) -> List[PropData]:
        """
        Every prop ANCHORED on a cell, bottom of the stack first.

        Props stack: a rug, a table on it and a lamp on that are three
        props on one cell, drawn in this order.
        """
        return [prop for prop in self.__props
                if prop.get_position() == (x, y)]

    def get_prop_at(self, x: int, y: int) -> Optional[PropData]:
        """
        The TOPMOST prop anchored on a cell, or None.

        This is identity, not coverage: a 1x3 tree anchored at (4, 9)
        answers only for (4, 9). Use get_prop_root_at() to ask whether
        something solid occupies a cell.

        Topmost, because that is the one an author is pointing at — it
        is the one drawn over the others, so it is the one right-click
        should edit and the eraser should take first.
        """
        for prop in reversed(self.__props):
            if prop.get_position() == (x, y):
                return prop
        return None

    def get_prop_by_uid(self, uid: str) -> Optional[PropData]:
        """The prop with this uid, or None."""
        for prop in self.__props:
            if prop.get_uid() == uid:
                return prop
        return None

    @staticmethod
    def __root_covers(prop: PropData, x: int, y: int) -> bool:
        """True when a cell falls under a prop's SOLID rows."""
        px, py = prop.get_position()
        type_id = prop.get_type_id()
        if not is_multicell_prop(type_id):
            return (px, py) == (x, y)
        return any(is_root and (cx, cy) == (x, y)
                   for cx, cy, is_root in prop_cells(type_id, px, py))

    def get_prop_root_at(self, x: int, y: int) -> Optional[PropData]:
        """
        The prop whose ROOT covers this cell, anchored here or not.

        A multi-cell prop only blocks on its root rows; the canopy is
        walk-behind, so this deliberately ignores those cells. Anything
        1x1 behaves exactly as before.

        When props are STACKED on a cell a blocking one wins over a
        walk-through one however they are layered. Collision is not a
        drawing question: one solid thing on a cell is enough to stop
        the player, and answering with whichever happened to be drawn
        on top would make a wall vanish the moment a rug was laid over
        its cell.
        """
        found: Optional[PropData] = None
        for prop in self.__props:
            if not self.__root_covers(prop, x, y):
                continue
            if not prop.get_passthrough():
                return prop
            found = prop
        return found

    def get_props_covering(self, x: int, y: int) -> List[PropData]:
        """
        Every prop whose FOOTPRINT covers this cell, bottom first.

        The renderer's fade list: with props stacked, more than one can
        be standing over the player at once.
        """
        return [prop for prop in self.__props if prop.covers_cell(x, y)]

    def get_prop_covering(self, x: int, y: int) -> Optional[PropData]:
        """
        The TOPMOST prop whose footprint covers this cell, root or
        canopy, or None.

        Used by the renderer to decide when the player is standing
        behind something and it should fade.
        """
        for prop in reversed(self.__props):
            if prop.covers_cell(x, y):
                return prop
        return None

    def add_prop(self, type_id: str, x: int, y: int) -> Optional[PropData]:
        """
        Place a prop ON TOP of whatever is already on the cell.
        Returns None for unknown types or out-of-bounds cells.

        Props STACK. Before layering this replaced the prop on the
        cell, which made a lamp on a desk, or a sign on a wall,
        impossible to author — the second placement silently deleted
        the first. The new prop goes at the end of the list, so it
        draws over everything already there, and reorder_prop() moves
        it afterwards.
        """
        if get_prop_def(type_id) is None or not self.is_inside(x, y):
            return None
        prop = PropData(self.__next_uid("prop"), type_id, x, y)
        self.__props.append(prop)
        return prop

    def remove_prop_at(self, x: int, y: int) -> bool:
        """
        Delete the TOPMOST prop anchored on a cell, if any.

        One layer per call, so holding the eraser over a stack peels it
        the same way the eraser already peels NPC > prop > overlay >
        ground.
        """
        prop = self.get_prop_at(x, y)
        if prop is None:
            return False
        self.__props.remove(prop)
        return True

    def remove_prop(self, uid: str) -> bool:
        """Delete one prop by uid, wherever it sits in the stack."""
        prop = self.get_prop_by_uid(uid)
        if prop is None:
            return False
        self.__props.remove(prop)
        return True

    def reorder_prop(self, uid: str, action: str) -> bool:
        """
        Move a prop through the draw order. True when it actually moved.

        `action` is one of:

            "forward"  / "backward"   one step within its own stack
            "front"    / "back"       above / below everything

        A step is measured against the props this one OVERLAPS, not
        against the whole list. Stepping through every unrelated prop
        in the level would mean pressing ] forty times to lift a lamp
        over the desk it is standing on, with nothing changing on
        screen in between.
        """
        index = next((i for i, prop in enumerate(self.__props)
                      if prop.get_uid() == uid), -1)
        if index < 0:
            return False
        prop = self.__props[index]

        if action == "front":
            target = len(self.__props) - 1
        elif action == "back":
            target = 0
        elif action == "forward":
            target = next((i for i in range(index + 1, len(self.__props))
                           if prop.overlaps(self.__props[i])), -1)
        elif action == "backward":
            target = next((i for i in range(index - 1, -1, -1)
                           if prop.overlaps(self.__props[i])), -1)
        else:
            return False
        if target < 0 or target == index:
            return False

        self.__props.pop(index)
        self.__props.insert(target, prop)
        return True

    def get_prop_depth(self, uid: str) -> Tuple[int, int]:
        """
        (position, size) of a prop within its own overlapping stack,
        counted from the bottom and 1-based — "2 of 3".

        (0, 0) when there is no such prop. The editor prints this after
        a reorder so an author can see the move landed even when the
        two sprites look alike.
        """
        prop = self.get_prop_by_uid(uid)
        if prop is None:
            return (0, 0)
        stack = [other for other in self.__props if prop.overlaps(other)]
        return (stack.index(prop) + 1, len(stack))

    def replace_prop(self, uid: str, data: Dict[str, Any]) -> bool:
        """
        Swap a prop's settings wholesale, keeping its uid, type and cell.

        The settings popup edits a detached copy and hands the result
        back here, so one popup session is exactly one undo step and a
        cancelled popup cannot have half-applied anything.
        """
        for index, prop in enumerate(self.__props):
            if prop.get_uid() != uid:
                continue
            merged = dict(data)
            merged["uid"] = uid
            merged["type_id"] = prop.get_type_id()
            merged["x"], merged["y"] = prop.get_position()
            self.__props[index] = PropData.from_dict(merged)
            return True
        return False

    # ── npcs ──────────────────────────────────────────────────

    def get_npcs(self) -> List[NpcData]:
        """Copy of the NPC list."""
        return list(self.__npcs)

    def get_npc_at(self, x: int, y: int) -> Optional[NpcData]:
        """The NPC on a cell — at most one (Spec §4.3)."""
        for npc in self.__npcs:
            if npc.get_position() == (x, y):
                return npc
        return None

    def add_npc(self, type_id: str, x: int, y: int) -> Optional[NpcData]:
        """
        Place an NPC, replacing whatever NPC was already on the cell.
        Returns None for unknown types or out-of-bounds cells.
        """
        if get_npc_def(type_id) is None or not self.is_inside(x, y):
            return None
        self.remove_npc_at(x, y)
        npc = NpcData(self.__next_uid("npc"), type_id, x, y)
        self.__npcs.append(npc)
        return npc

    def remove_npc_at(self, x: int, y: int) -> bool:
        """Delete the NPC on a cell, if any."""
        npc = self.get_npc_at(x, y)
        if npc is None:
            return False
        self.__npcs.remove(npc)
        return True

    def replace_npc(self, uid: str, data: Dict[str, Any]) -> bool:
        """
        Swap an NPC's settings and dialog wholesale, keeping its uid,
        type and cell — the dialog editor's one-undo-step commit path.
        """
        for index, npc in enumerate(self.__npcs):
            if npc.get_uid() != uid:
                continue
            merged = dict(data)
            merged["uid"] = uid
            merged["type_id"] = npc.get_type_id()
            merged["x"], merged["y"] = npc.get_position()
            self.__npcs[index] = NpcData.from_dict(merged)
            return True
        return False

    # ── zones (Feature 6, phase F5) ───────────────────────────

    def get_zones(self) -> List[ZoneData]:
        """Copy of the zone list."""
        return list(self.__zones)

    def get_zone_count(self) -> int:
        """How many zones this level defines."""
        return len(self.__zones)

    def get_zone(self, zone_uid: str) -> Optional[ZoneData]:
        """One zone by uid, or None."""
        for zone in self.__zones:
            if zone.get_uid() == zone_uid:
                return zone
        return None

    def add_zone(self, x: int, y: int, w: int = 1,
                 h: int = 1) -> Optional[ZoneData]:
        """
        Create a zone rectangle. Returns None for an invalid rect.

        Unlike props and NPCs, zones are NOT one-per-cell: overlapping
        zones are legal but warned about, because an author may
        genuinely want a small strict area inside a larger loose one.
        """
        if w < 1 or h < 1 or not self.is_inside(x, y):
            return None
        uid = self.__next_uid(ZONE_UID_PREFIX)
        zone = ZoneData(uid, f"{ZONE_UID_PREFIX}_{len(self.__zones) + 1}",
                        x, y, w, h)
        self.__zones.append(zone)
        return zone

    def remove_zone(self, zone_uid: str) -> bool:
        """Delete a zone by uid."""
        zone = self.get_zone(zone_uid)
        if zone is None:
            return False
        self.__zones.remove(zone)
        return True

    def replace_zone(self, zone_uid: str, data: Dict[str, Any]) -> bool:
        """
        Swap a zone's settings wholesale, keeping its uid.

        Same one-undo-step commit path the prop and NPC popups use: the
        popup edits a detached dict and hands the result back here.
        """
        for index, zone in enumerate(self.__zones):
            if zone.get_uid() != zone_uid:
                continue
            merged = dict(data)
            merged["uid"] = zone_uid
            self.__zones[index] = ZoneData.from_dict(merged)
            return True
        return False

    def get_zone_at(self, x: int, y: int) -> Optional[ZoneData]:
        """
        The zone covering a cell, or None.

        When zones overlap the LAST one wins, matching paint order --
        the most recently authored zone is the one on top.
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
        gated building is the tighter statement of intent. Returns None
        when nothing gates the cell -- an open default gate counts as
        nothing, so callers never have to check is_default().
        """
        prop = self.get_prop_at(x, y)
        if prop is not None and prop.get_gate().has_requirements():
            return prop.get_gate()
        zone = self.get_zone_at(x, y)
        if zone is not None and zone.get_gate().has_requirements():
            return zone.get_gate()
        return None

    # ── uids ──────────────────────────────────────────────────

    def __next_uid(self, prefix: str) -> str:
        """
        Next free `<prefix>_NNNN`, derived as (highest live number + 1)
        rather than (count + 1) so deleting the middle of a list can
        never mint a duplicate.

        A number freed by a deletion IS handed out again later. That is
        safe because uids only have to be unique within one file, and
        undo restores whole-document snapshots — it never replays a
        deletion against a document that has since reused the number.
        Deriving the counter from the document rather than storing it
        also means a hand-edited file self-heals on the next placement.
        """
        highest = 0
        entities: List[Any] = (list(self.__props) + list(self.__npcs)
                               + list(self.__zones))
        for entity in entities:
            uid = entity.get_uid()
            if uid.startswith(prefix + "_"):
                tail = uid[len(prefix) + 1:]
                if tail.isdigit():
                    highest = max(highest, int(tail))
        return f"{prefix}_{highest + 1:04d}"

    # ── serialisation ─────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """The exact structure written to JSON (Spec §2.1)."""
        meta: Dict[str, Any] = dict(self.__meta_extra)
        meta.update({
            "level_name": self.__level_name,
            "level_id": self.__level_id,
            "grid_width": self.__grid_width,
            "grid_height": self.__grid_height,
            "ambient": self.__ambient,
            "music": self.__music,
            "spawn": {"x": self.__spawn[0], "y": self.__spawn[1]},
        })
        data: Dict[str, Any] = dict(self.__extra)
        data.update({
            "schema_version": self.__schema_version,
            "meta": meta,
            "layers": {
                LAYER_GROUND: [list(row) for row in self.__ground],
                LAYER_OVERLAY: [list(row) for row in self.__overlay],
            },
            "props": [p.to_dict() for p in self.__props],
            "npcs": [n.to_dict() for n in self.__npcs],
        })
        # "zones" is omitted entirely when there are none, so a level
        # authored before F5 -- levels/campus_main.json included --
        # still writes byte-for-byte the same file it did before.
        if self.__zones:
            data["zones"] = [z.to_dict() for z in self.__zones]
        # Same rule for rotations: nested per layer, "x,y" keys, and the
        # whole block omitted when nothing is turned.
        rotations: Dict[str, Dict[str, int]] = {}
        for (layer, x, y), degrees in sorted(self.__tile_rotations.items()):
            rotations.setdefault(layer, {})[f"{x},{y}"] = degrees
        if rotations:
            data["tile_rotations"] = rotations
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "LevelData":
        """
        Rebuild a document from parsed JSON.

        Raises LevelSchemaError only for files from a FUTURE schema
        version — everything else is repaired here and reported by
        validate() so the editor can show the user what is wrong
        instead of refusing to open the file.
        """
        version = int(data.get("schema_version", SCHEMA_VERSION))
        if version > SUPPORTED_SCHEMA_VERSION:
            raise LevelSchemaError(
                f"level uses schema_version {version}; this build "
                f"understands up to {SUPPORTED_SCHEMA_VERSION}")

        meta: Dict[str, Any] = data.get("meta") or {}
        try:
            width = int(meta.get("grid_width", 40))
            height = int(meta.get("grid_height", 24))
        except (TypeError, ValueError) as error:
            raise LevelSchemaError(f"grid size is not numeric: {error}") \
                from error
        # A grid outside GRID_MIN..GRID_MAX is a validate() blocker, not a
        # read failure — the user must be able to open it and fix it. Only
        # values that would blow up memory are refused outright.
        if not 1 <= width <= GRID_MAX or not 1 <= height <= GRID_MAX:
            raise LevelSchemaError(
                f"grid {width}x{height} is unusable (hard limit {GRID_MAX})")

        level = LevelData(str(meta.get("level_name", "Untitled")),
                          "untitled", width, height)
        level.__schema_version = version
        level.__level_id = str(meta.get("level_id", "untitled"))
        level.__grid_width = width
        level.__grid_height = height
        level.set_ambient(str(meta.get("ambient", AMBIENT_DEFAULT)))
        level.set_music(str(meta.get("music", "")))

        layers: Dict[str, Any] = data.get("layers") or {}
        level.__ground = _normalise_rows(
            layers.get(LAYER_GROUND), width, height, DEFAULT_GROUND_TILE)
        level.__overlay = _normalise_rows(
            layers.get(LAYER_OVERLAY), width, height, EMPTY_TILE)

        spawn = meta.get("spawn") or {}
        level.__spawn = (int(spawn.get("x", 0)), int(spawn.get("y", 0)))

        level.__props = [PropData.from_dict(p)
                         for p in (data.get("props") or [])]
        level.__npcs = [NpcData.from_dict(n)
                        for n in (data.get("npcs") or [])]
        level.__zones = [ZoneData.from_dict(z)
                         for z in (data.get("zones") or [])]

        # A malformed key is skipped, not fatal: a hand-edited file with
        # one bad coordinate should lose that rotation, not fail to open.
        for layer, cells in (data.get("tile_rotations") or {}).items():
            if layer not in LAYER_NAMES or not isinstance(cells, dict):
                continue
            for coordinate, degrees in cells.items():
                try:
                    cx, cy = (int(part) for part in str(coordinate).split(","))
                except (TypeError, ValueError):
                    continue
                value = normalise_rotation(degrees)
                if value:
                    level.__tile_rotations[(layer, cx, cy)] = value

        level.__meta_extra = {k: v for k, v in meta.items()
                              if k not in _KNOWN_META_KEYS}
        level.__extra = {k: v for k, v in data.items()
                         if k not in _KNOWN_TOP_KEYS}
        return level

    def clone(self) -> "LevelData":
        """
        Deep copy via a dict round-trip — the undo stack stores these
        (Spec §3.3 asks for >=50 steps; a 40x24 document is tiny).
        """
        copy = LevelData.from_dict(self.to_dict())
        copy.set_source_path(self.__source_path)
        return copy

    # ── validation (Spec §7) ──────────────────────────────────

    def validate(self) -> ValidationReport:
        """
        Run every §7 check. Blockers first, then warnings, each in a
        stable order so the results popup does not jump around
        between runs.
        """
        issues: List[ValidationIssue] = []
        self.__check_blockers(issues)
        self.__check_warnings(issues)
        return ValidationReport(issues)

    def __check_blockers(self, issues: List[ValidationIssue]) -> None:
        """Everything that must be fixed before the file may be saved."""
        if not LEVEL_ID_PATTERN.match(self.__level_id):
            issues.append(ValidationIssue(
                SEVERITY_BLOCKER, "BAD_LEVEL_ID",
                f"level_id '{self.__level_id}' must match [a-z0-9_]+"))

        if not GRID_MIN <= self.__grid_width <= GRID_MAX or \
                not GRID_MIN <= self.__grid_height <= GRID_MAX:
            issues.append(ValidationIssue(
                SEVERITY_BLOCKER, "BAD_GRID_SIZE",
                f"grid {self.__grid_width}x{self.__grid_height} outside "
                f"{GRID_MIN}-{GRID_MAX}"))

        for name, rows in ((LAYER_GROUND, self.__ground),
                           (LAYER_OVERLAY, self.__overlay)):
            if len(rows) != self.__grid_height or \
                    any(len(r) != self.__grid_width for r in rows):
                issues.append(ValidationIssue(
                    SEVERITY_BLOCKER, "LAYER_SHAPE",
                    f"layer '{name}' does not match the declared grid size"))

        for y, row in enumerate(self.__ground):
            for x, value in enumerate(row):
                if value == EMPTY_TILE:
                    issues.append(ValidationIssue(
                        SEVERITY_BLOCKER, "GROUND_HOLE",
                        f"ground cell ({x},{y}) is unpainted", (x, y)))
                elif get_tile_def(value) is None:
                    issues.append(ValidationIssue(
                        SEVERITY_BLOCKER, "UNKNOWN_TILE",
                        f"ground cell ({x},{y}) uses unknown tile {value}",
                        (x, y)))

        for y, row in enumerate(self.__overlay):
            for x, value in enumerate(row):
                if value != EMPTY_TILE and get_tile_def(value) is None:
                    issues.append(ValidationIssue(
                        SEVERITY_BLOCKER, "UNKNOWN_TILE",
                        f"overlay cell ({x},{y}) uses unknown tile {value}",
                        (x, y)))

        seen_uids: Dict[str, int] = {}
        for entity, kind, registry_lookup in (
                [(p, "prop", get_prop_def) for p in self.__props] +
                [(n, "npc", get_npc_def) for n in self.__npcs]):
            uid = entity.get_uid()
            x, y = entity.get_position()
            seen_uids[uid] = seen_uids.get(uid, 0) + 1
            if not uid:
                issues.append(ValidationIssue(
                    SEVERITY_BLOCKER, "MISSING_UID",
                    f"a {kind} at ({x},{y}) has no uid", (x, y)))
            if registry_lookup(entity.get_type_id()) is None:
                issues.append(ValidationIssue(
                    SEVERITY_BLOCKER, "UNKNOWN_TYPE",
                    f"{kind} '{uid}' has unknown type_id "
                    f"'{entity.get_type_id()}'", (x, y)))
            if not self.is_inside(x, y):
                issues.append(ValidationIssue(
                    SEVERITY_BLOCKER, "OUT_OF_BOUNDS",
                    f"{kind} '{uid}' sits outside the grid at ({x},{y})"))

        for uid, count in seen_uids.items():
            if count > 1 and uid:
                issues.append(ValidationIssue(
                    SEVERITY_BLOCKER, "DUPLICATE_UID",
                    f"uid '{uid}' is used {count} times"))

        sx, sy = self.__spawn
        if not self.is_inside(sx, sy):
            issues.append(ValidationIssue(
                SEVERITY_BLOCKER, "SPAWN_OUTSIDE",
                f"spawn ({sx},{sy}) is outside the grid"))
        elif not self.is_cell_walkable(sx, sy):
            issues.append(ValidationIssue(
                SEVERITY_BLOCKER, "SPAWN_BLOCKED",
                f"spawn ({sx},{sy}) is on a blocked cell", (sx, sy)))

    def __check_warnings(self, issues: List[ValidationIssue]) -> None:
        """Advisory issues — listed in amber, saving still allowed."""
        for npc in self.__npcs:
            x, y = npc.get_position()
            # Terrain-only: NPCs are solid now, so the combined check
            # would flag every one of them for standing on itself.
            if self.is_inside(x, y) and not self.is_terrain_walkable(x, y):
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "NPC_ON_BLOCKED",
                    f"npc '{npc.get_uid()}' stands on a blocked cell", (x, y)))
            if npc.get_interactable() and npc.get_total_line_count() == 0:
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "EMPTY_DIALOG",
                    f"npc '{npc.get_uid()}' is interactable but has no "
                    f"dialog lines", (x, y)))
            valid_emotions = get_npc_emotions(npc.get_type_id())
            for chain in npc.get_chains():
                emotion = chain.get_emotion()
                if emotion and valid_emotions and emotion not in valid_emotions:
                    issues.append(ValidationIssue(
                        SEVERITY_WARNING, "UNKNOWN_EMOTION",
                        f"npc '{npc.get_uid()}' chain "
                        f"'{chain.get_chain_id()}' uses emotion "
                        f"'{emotion}' with no portrait", (x, y)))
                # A reply pointing at a chain that is not there just ends
                # the conversation, so this is advisory: a mistyped goto
                # must never stop the level loading.
                for option in chain.get_choice_options():
                    goto = option.get("goto", "")
                    if goto and npc.find_chain(goto) is None:
                        issues.append(ValidationIssue(
                            SEVERITY_WARNING, "DANGLING_CHOICE_GOTO",
                            f"npc '{npc.get_uid()}' chain "
                            f"'{chain.get_chain_id()}' reply "
                            f"'{option.get('label', '')}' jumps to "
                            f"'{goto}', which does not exist", (x, y)))

        total_money = 0.0
        total_exp = 0
        for prop in self.__props:
            x, y = prop.get_position()
            if prop.get_interactable() and \
                    prop.get_interaction_kind() == "none" and \
                    not prop.is_portal():
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "IDLE_INTERACTABLE",
                    f"prop '{prop.get_uid()}' is interactable but grants "
                    f"nothing", (x, y)))
            if not prop.get_passthrough() and \
                    prop.get_speed_modifier() != SPEED_MODIFIER_BASE:
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "MODIFIER_ON_BLOCKER",
                    f"prop '{prop.get_uid()}' is blocking, so its speed "
                    f"modifier never applies", (x, y)))
            if prop.get_pass_behind() and \
                    prop.get_behind_transparency() <= 0:
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "BEHIND_NOT_TRANSPARENT",
                    f"prop '{prop.get_uid()}' is walked behind at 0% "
                    f"transparency, so it hides the player completely",
                    (x, y)))
            if prop.is_portal() and not prop.get_target_level_id():
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "PORTAL_NO_TARGET",
                    f"portal '{prop.get_uid()}' has no target level", (x, y)))
            if prop.get_interactable() and \
                    prop.get_interaction_kind() == "travel" and \
                    not prop.get_target_level_id():
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "TRAVEL_NO_TARGET",
                    f"prop '{prop.get_uid()}' travels but has no target "
                    f"level", (x, y)))
            if prop.get_interactable() and \
                    prop.get_interaction_kind() == "menu":
                menu_id = prop.get_menu_id()
                if not menu_id:
                    issues.append(ValidationIssue(
                        SEVERITY_WARNING, "MENU_NO_TARGET",
                        f"prop '{prop.get_uid()}' opens a menu but none is "
                        f"chosen", (x, y)))
                elif menu_id not in MENU_REGISTRY:
                    issues.append(ValidationIssue(
                        SEVERITY_WARNING, "UNKNOWN_MENU",
                        f"prop '{prop.get_uid()}' opens unknown menu "
                        f"'{menu_id}'", (x, y)))
            if prop.get_interactable():
                payout = prop.get_amount() * prop.get_triggers_per_semester()
                if prop.get_interaction_kind() == "money":
                    total_money += payout
                elif prop.get_interaction_kind() == "skill":
                    total_exp += int(payout)

        # Props stack now, so the same art can be placed twice on one
        # cell without anything looking different. That is almost always
        # a double-click rather than an intention, and it is invisible
        # on the canvas — hence a warning naming the cell.
        stacked: Dict[Tuple[int, int, str], int] = {}
        for prop in self.__props:
            key = (*prop.get_position(), prop.get_type_id())
            stacked[key] = stacked.get(key, 0) + 1
        for (x, y, type_id), count in stacked.items():
            if count > 1:
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "DUPLICATE_PROP",
                    f"{count} copies of '{type_id}' are stacked on "
                    f"({x},{y})", (x, y)))

        if total_money > MAX_PROP_MONEY_PER_SEMESTER:
            issues.append(ValidationIssue(
                SEVERITY_WARNING, "MONEY_OVER_CAP",
                f"props can pay {total_money:.0f} BDT per semester; the "
                f"engine caps rewards at "
                f"{MAX_PROP_MONEY_PER_SEMESTER:.0f}"))
        if total_exp > MAX_PROP_EXP_PER_SEMESTER:
            issues.append(ValidationIssue(
                SEVERITY_WARNING, "EXP_OVER_CAP",
                f"props can grant {total_exp} EXP per semester; the engine "
                f"caps rewards at {MAX_PROP_EXP_PER_SEMESTER}"))

        unreachable = self.count_unreachable_cells()
        if unreachable > 0:
            issues.append(ValidationIssue(
                SEVERITY_WARNING, "UNREACHABLE",
                f"{unreachable} walkable cell(s) cannot be reached from "
                f"the spawn point"))

        self.__check_gate_warnings(issues)

    def __check_gate_warnings(self, issues: List[ValidationIssue]) -> None:
        """
        Advisory checks for gates and zones (Feature 6, phase F5).

        NEVER blockers. A gate is authoring intent, and a half-finished
        gate must not make a file unsavable -- the author has to be able
        to save, go and check what the skill is actually called, and
        come back. Everything here is amber.
        """
        spawn_x, spawn_y = self.__spawn

        # Props, NPCs and zones all carry the same GateData, so they are
        # checked through one loop rather than three near-copies.
        carriers: List[Tuple[str, str, GateData, Optional[Tuple[int, int]]]] = []
        for prop in self.__props:
            carriers.append(("prop", prop.get_uid(), prop.get_gate(),
                             prop.get_position()))
        for npc in self.__npcs:
            carriers.append(("npc", npc.get_uid(), npc.get_gate(),
                             npc.get_position()))
        for zone in self.__zones:
            zx, zy, _, _ = zone.get_rect()
            carriers.append(("zone", zone.get_uid(), zone.get_gate(),
                             (zx, zy)))

        for kind, uid, gate, cell in carriers:
            if gate.is_default():
                continue

            if gate.has_requirements() and not gate.get_locked_lines():
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "GATE_NO_MESSAGE",
                    f"{kind} '{uid}' has gate requirements but no locked "
                    f"message, so the player is refused with no reason",
                    cell))

            if gate.get_cost_days() >= GATE_DAYS_MAX:
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "GATE_COST_EXCEEDS_POOL",
                    f"{kind} '{uid}' costs {gate.get_cost_days()} days, "
                    f"the entire {GATE_DAYS_MAX}-day semester pool", cell))

            skill_id = gate.get_required_skill_id()
            if skill_id and skill_id not in SKILL_IDS:
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "GATE_UNKNOWN_SKILL",
                    f"{kind} '{uid}' requires unknown skill "
                    f"'{skill_id}'", cell))

        # A gate over the spawn cell is a soft-lock: the player starts
        # inside something they may not be allowed into.
        spawn_gate_sources: List[str] = []
        prop = self.get_prop_at(spawn_x, spawn_y)
        if prop is not None and prop.get_gate().has_requirements():
            spawn_gate_sources.append(f"prop '{prop.get_uid()}'")
        for zone in self.__zones:
            if zone.contains(spawn_x, spawn_y) and \
                    zone.get_gate().has_requirements():
                spawn_gate_sources.append(f"zone '{zone.get_uid()}'")
        for source in spawn_gate_sources:
            issues.append(ValidationIssue(
                SEVERITY_WARNING, "GATE_ON_SPAWN",
                f"{source} gates the spawn cell ({spawn_x},{spawn_y}); the "
                f"player would start locked in", (spawn_x, spawn_y)))

        for zone in self.__zones:
            zx, zy, zw, zh = zone.get_rect()
            if not self.is_inside(zx, zy) or \
                    not self.is_inside(zx + zw - 1, zy + zh - 1):
                issues.append(ValidationIssue(
                    SEVERITY_WARNING, "ZONE_OUT_OF_BOUNDS",
                    f"zone '{zone.get_uid()}' extends outside the grid "
                    f"at ({zx},{zy}) {zw}x{zh}", (zx, zy)))

        for index, zone in enumerate(self.__zones):
            for other in self.__zones[index + 1:]:
                if zone.overlaps(other):
                    zx, zy, _, _ = zone.get_rect()
                    issues.append(ValidationIssue(
                        SEVERITY_WARNING, "ZONE_OVERLAP",
                        f"zones '{zone.get_uid()}' and '{other.get_uid()}' "
                        f"overlap; the later one wins on shared cells",
                        (zx, zy)))

    def count_unreachable_cells(self) -> int:
        """
        Flood-fill from the spawn over walkable cells; anything
        walkable it never touches is cut off from the player.
        """
        sx, sy = self.__spawn
        if not self.is_inside(sx, sy) or not self.is_cell_walkable(sx, sy):
            return 0
        seen = {(sx, sy)}
        queue: deque = deque([(sx, sy)])
        while queue:
            x, y = queue.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in seen or not self.is_inside(nx, ny):
                    continue
                if not self.is_cell_walkable(nx, ny):
                    continue
                seen.add((nx, ny))
                queue.append((nx, ny))

        walkable = sum(1 for y in range(self.__grid_height)
                       for x in range(self.__grid_width)
                       if self.is_cell_walkable(x, y))
        return walkable - len(seen)


# ─────────────────────────────────────────────────────────────
# MODULE HELPERS
# ─────────────────────────────────────────────────────────────


def _normalise_rows(rows: Any, width: int, height: int,
                    pad: int) -> List[List[int]]:
    """
    Coerce whatever the file held into a height x width int grid.
    Shape problems are padded here and REPORTED by validate() — a
    malformed file must still open so the user can repair it.
    """
    out: List[List[int]] = []
    source: List[Any] = rows if isinstance(rows, list) else []
    for y in range(height):
        row: List[int] = []
        raw = source[y] if y < len(source) and isinstance(source[y], list) \
            else []
        for x in range(width):
            value = raw[x] if x < len(raw) else pad
            try:
                row.append(int(value))
            except (TypeError, ValueError):
                row.append(pad)
        out.append(row)
    return out


def level_path(level_id: str, levels_dir: str = LEVELS_DIR) -> str:
    """Canonical file path for a level id."""
    return os.path.join(levels_dir, f"{level_id}.json")


def list_level_files(levels_dir: str = LEVELS_DIR) -> List[str]:
    """Every `levels/*.json` path, sorted — feeds the LOAD picker."""
    if not os.path.isdir(levels_dir):
        return []
    return sorted(os.path.join(levels_dir, name)
                  for name in os.listdir(levels_dir)
                  if name.endswith(".json"))


def read_level(path: str) -> LevelData:
    """
    Parse a level file into a LevelData.
    Raises LevelSchemaError on unreadable JSON or a future schema.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise LevelSchemaError(f"cannot read '{path}': {error}") from error
    if not isinstance(data, dict):
        raise LevelSchemaError(f"'{path}' is not a level object")
    level = LevelData.from_dict(data)
    level.set_source_path(path)
    return level


def write_level(level: LevelData, path: str,
                validate: bool = True) -> ValidationReport:
    """
    Write a level to disk, pretty-printed with 2-space indent.
    With `validate` on (the default), blockers abort the write and
    come back in the report — nothing is touched on disk.
    """
    report = level.validate()
    if validate and not report.is_saveable():
        return report
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(level.to_dict(), handle, indent=2)
        handle.write("\n")
    level.set_source_path(path)
    return report

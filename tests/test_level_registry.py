"""
tests/test_level_registry.py
CSE Life: Compile & Conquer — phase F5

The registry is the single source of truth for level content, and
the F5 extension made it derive NPC gate defaults from
content/npc_roster.py. These tests guard both halves: the ported
registry contract, and the new roster binding.

The most important one here is
test_min_semester_matches_the_roster: if Ayesha moves an NPC to a
different semester, the editor's gate default has to follow, and
nothing else in the codebase will notice if it does not.
"""

from __future__ import annotations

import pytest

from content import level_registry as reg
from content.npc_roster import NPC_ROSTER


# ─────────────────────────────────────────────────────────────
# COMPLETENESS
# ─────────────────────────────────────────────────────────────


def test_tile_registry_is_complete():
    """Every tile carries everything the renderer and validator need."""
    assert reg.TILE_REGISTRY
    for index, entry in reg.TILE_REGISTRY.items():
        assert isinstance(index, int)
        for key in ("name", "sheet", "col", "row", "cell_px", "walkable",
                    "layer"):
            assert key in entry, f"tile {index} missing '{key}'"
        assert entry["layer"] in reg.LAYER_NAMES


def test_prop_registry_is_complete():
    """Every prop carries its art coordinates and collision default."""
    assert reg.PROP_REGISTRY
    for type_id, entry in reg.PROP_REGISTRY.items():
        assert type_id == type_id.lower()
        for key in ("sheet", "col", "row", "cell_px", "default_passthrough"):
            assert key in entry, f"prop {type_id} missing '{key}'"


def test_npc_registry_is_complete():
    """Every NPC carries art, portraits and the F5 roster fields."""
    assert reg.NPC_REGISTRY
    for type_id, entry in reg.NPC_REGISTRY.items():
        for key in ("name", "idle_sheet", "frames", "editor_icon",
                    "portraits", "default_emotion",
                    "roster_id", "min_semester"):
            assert key in entry, f"npc {type_id} missing '{key}'"
        assert entry["default_emotion"] in entry["portraits"]


def test_portal_type_is_registered():
    """The portal prop the loader looks for actually exists."""
    assert reg.get_prop_def(reg.PORTAL_TYPE_ID) is not None


# ─────────────────────────────────────────────────────────────
# EMOTIONS AND PORTRAITS
# ─────────────────────────────────────────────────────────────


def test_npc_emotions_put_the_default_first():
    """The dialog editor shows the default emotion first, always."""
    for type_id in reg.get_npc_type_ids():
        emotions = reg.get_npc_emotions(type_id)
        assert emotions
        assert emotions[0] == reg.NPC_REGISTRY[type_id]["default_emotion"]


def test_unknown_emotion_falls_back_to_the_default_portrait():
    """A chain naming an emotion with no art still renders a face."""
    for type_id in reg.get_npc_type_ids():
        default = reg.NPC_REGISTRY[type_id]["default_emotion"]
        assert reg.get_npc_portrait_path(type_id, "furious") == \
            reg.get_npc_portrait_path(type_id, default)


def test_every_registered_emotion_has_a_path():
    """No emotion is offered that cannot be drawn."""
    for type_id in reg.get_npc_type_ids():
        for emotion in reg.get_npc_emotions(type_id):
            assert reg.get_npc_portrait_path(type_id, emotion)


# ─────────────────────────────────────────────────────────────
# HARD RULES
# ─────────────────────────────────────────────────────────────


def test_prop_exp_never_beats_a_side_quest():
    """Spec §5.3 — a hard rule, not a tuning value."""
    assert reg.EXP_MAX == 10


def test_skill_ids_were_left_alone():
    """
    Build Plan §1.4: the registry's 9-entry SKILL_IDS and the
    endgame manager's 12 TRACKED_SKILL_IDS are a KNOWN divergence and
    the owner ruled that neither may be reconciled in this branch.

    This test exists so a future phase cannot quietly "fix" it.
    """
    assert reg.SKILL_IDS == (
        "programming", "algorithms", "mathematics", "hardware",
        "networking", "databases", "software_engineering",
        "communication", "general")
    assert len(reg.SKILL_IDS) == 9


def test_numeric_bounds_are_unchanged():
    """The ported clamps the editor widgets and validator share."""
    assert (reg.TILE_SIZE_PX, reg.EMPTY_TILE) == (48, -1)
    assert (reg.GRID_MIN, reg.GRID_MAX) == (10, 200)
    assert reg.DEFAULT_GROUND_TILE == 0
    assert reg.AMBIENT_PRESETS == ("morning", "day", "evening", "night")
    assert reg.ON_COMPLETE_MODES == ("loop_last", "loop_all", "silent")
    assert reg.INTERACTION_KINDS == ("none", "money", "skill")
    assert reg.FACINGS == ("down", "left", "right", "up")
    assert (reg.MONEY_MIN, reg.MONEY_MAX, reg.MONEY_STEP) == (50, 1000, 50)
    assert (reg.EXP_MIN, reg.EXP_MAX, reg.EXP_STEP) == (1, 10, 1)
    assert (reg.TRIGGERS_MIN, reg.TRIGGERS_MAX,
            reg.TRIGGERS_DEFAULT) == (1, 5, 1)
    assert (reg.SPEED_MODIFIER_MIN, reg.SPEED_MODIFIER_MAX,
            reg.SPEED_MODIFIER_BASE, reg.SPEED_MODIFIER_STEP) == \
        (0.1, 2.0, 1.0, 0.05)
    assert reg.SPEED_SMOOTH_RATE == 5.0
    assert reg.BASE_PLAYER_SPEED_PX_S == 150.0
    assert reg.MAX_PROP_MONEY_PER_SEMESTER == 2000.0
    assert reg.MAX_PROP_EXP_PER_SEMESTER == 20


def test_gate_bounds_follow_the_game_rules():
    """The F5 gate clamps mirror IMPLEMENTATION_PLAN §3."""
    assert (reg.GATE_SEMESTER_MIN, reg.GATE_SEMESTER_MAX) == (0, 12)
    assert (reg.GATE_CREDITS_MIN, reg.GATE_CREDITS_MAX) == (0, 140)
    assert (reg.GATE_DAYS_MIN, reg.GATE_DAYS_MAX) == (0, 80)
    assert (reg.GATE_SKILL_LEVEL_MIN, reg.GATE_SKILL_LEVEL_MAX) == (0, 20)
    assert reg.GATE_LOCKED_TITLE_DEFAULT == "ACCESS DENIED"
    assert reg.GATE_LOCKED_LINES_MAX == 3


# ─────────────────────────────────────────────────────────────
# UNKNOWN IDS
# ─────────────────────────────────────────────────────────────


def test_registry_lookups_return_none_for_unknown_ids():
    """Nothing raises on an id that is not there."""
    assert reg.get_tile_def(999) is None
    assert reg.get_prop_def("nope") is None
    assert reg.get_npc_def("nope") is None


def test_unknown_npc_accessors_degrade_quietly():
    """The F5 accessors have safe answers for an unknown type."""
    assert reg.get_npc_roster_id("nope") == ""
    assert reg.get_npc_min_semester("nope") == reg.MIN_SEMESTER_DEFAULT
    assert reg.get_npc_emotions("nope") == []


def test_unknown_tile_is_walkable():
    """An unpainted or unknown cell never traps the player."""
    assert reg.is_tile_walkable(999) is True


# ─────────────────────────────────────────────────────────────
# THE ROSTER BINDING  (F5 extension)
# ─────────────────────────────────────────────────────────────


def test_every_registered_npc_maps_to_a_real_roster_entry():
    """No registry entry points at a roster id that does not exist."""
    for type_id in reg.get_npc_type_ids():
        roster_id = reg.get_npc_roster_id(type_id)
        assert roster_id, f"{type_id} has no roster_id"
        assert roster_id in NPC_ROSTER, \
            f"{type_id} -> '{roster_id}' is not in NPC_ROSTER"


@pytest.mark.parametrize("type_id", sorted(reg.NPC_REGISTRY))
def test_min_semester_matches_the_roster(type_id):
    """
    THE BINDING TEST.

    min_semester must equal the roster's semester_available_from. If
    the two ever disagree, an author gating Prof. Hoque's door gets a
    default that contradicts the narrative.
    """
    roster_id = reg.get_npc_roster_id(type_id)
    expected = int(NPC_ROSTER[roster_id]["semester_available_from"])
    assert reg.get_npc_min_semester(type_id) == expected
    assert reg.NPC_REGISTRY[type_id]["min_semester"] == expected


def test_the_known_roster_figures():
    """Spelled out so a silent roster edit is visible in the diff."""
    assert reg.get_npc_roster_id("hoque") == "professor_hoque"
    assert reg.get_npc_min_semester("hoque") == 5
    assert reg.get_npc_roster_id("roya") == "career_advisor_roya"
    assert reg.get_npc_min_semester("roya") == 4


def test_only_npcs_with_art_are_registered():
    """
    The editor palette must never offer an NPC whose sprite is missing.

    The other five roster members are staged as commented-out rows in
    _ROSTER_ID_BY_TYPE, ready to uncomment when their art lands.
    """
    assert set(reg.get_npc_type_ids()) == {"hoque", "roya"}
    assert len(NPC_ROSTER) == 7, "the roster still has seven NPCs"


def test_fallback_table_agrees_with_the_roster():
    """
    _MIN_SEMESTER_FALLBACK only applies if npc_roster.py cannot be
    imported. It must still agree with the roster, or an import failure
    would silently change the gate defaults.
    """
    for type_id, fallback in reg._MIN_SEMESTER_FALLBACK.items():
        roster_id = reg._ROSTER_ID_BY_TYPE[type_id]
        assert fallback == NPC_ROSTER[roster_id]["semester_available_from"]

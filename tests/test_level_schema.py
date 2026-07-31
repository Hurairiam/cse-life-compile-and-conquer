"""
tests/test_level_schema.py
Level system E1 — the document model, the registries and the
Spec §7 validation rules.
"""

from __future__ import annotations

import json

import pytest

from content import level_registry as reg
from content.level_schema import (
    SCHEMA_VERSION,
    DialogChain,
    LevelData,
    LevelSchemaError,
    NpcData,
    PropData,
    read_level,
    write_level,
)


# ─────────────────────────────────────────────────────────────
# REGISTRIES
# ─────────────────────────────────────────────────────────────


def test_tile_registry_entries_are_complete():
    for index, entry in reg.TILE_REGISTRY.items():
        assert isinstance(index, int)
        for key in ("name", "sheet", "col", "row", "cell_px",
                    "walkable", "layer"):
            assert key in entry, f"tile {index} missing '{key}'"
        assert entry["layer"] in reg.LAYER_NAMES


def test_prop_and_npc_registry_entries_are_complete():
    for type_id, entry in reg.PROP_REGISTRY.items():
        assert type_id == type_id.lower()
        for key in ("sheet", "col", "row", "cell_px", "default_passthrough"):
            assert key in entry, f"prop {type_id} missing '{key}'"
    for type_id, entry in reg.NPC_REGISTRY.items():
        for key in ("name", "idle_sheet", "frames", "editor_icon",
                    "portraits", "default_emotion"):
            assert key in entry, f"npc {type_id} missing '{key}'"
        assert entry["default_emotion"] in entry["portraits"]


def test_npc_emotions_put_the_default_first():
    for type_id in reg.get_npc_type_ids():
        emotions = reg.get_npc_emotions(type_id)
        assert emotions
        assert emotions[0] == reg.NPC_REGISTRY[type_id]["default_emotion"]
        assert reg.get_npc_portrait_path(type_id, emotions[0])


def test_unknown_emotion_falls_back_to_the_default_portrait():
    assert reg.get_npc_portrait_path("roya", "furious") == \
        reg.get_npc_portrait_path("roya", "neutral")


def test_prop_exp_never_beats_a_side_quest():
    # Spec §5.3 — a hard rule, not a tuning value.
    assert reg.EXP_MAX == 10


def test_registry_lookups_return_none_for_unknown_ids():
    assert reg.get_tile_def(999) is None
    assert reg.get_prop_def("nope") is None
    assert reg.get_npc_def("nope") is None


# ─────────────────────────────────────────────────────────────
# GRID + TILES
# ─────────────────────────────────────────────────────────────


def _blank(width: int = 12, height: int = 10) -> LevelData:
    return LevelData("Test", "test_level", width, height)


def test_new_level_ground_is_fully_painted():
    level = _blank()
    for y in range(level.get_grid_height()):
        for x in range(level.get_grid_width()):
            assert level.get_tile("ground", x, y) != reg.EMPTY_TILE
            assert level.get_tile("overlay", x, y) == reg.EMPTY_TILE


def test_set_tile_rejects_bad_input():
    level = _blank()
    assert level.set_tile("ground", 0, 0, reg.EMPTY_TILE) is False
    assert level.set_tile("ground", 0, 0, 999) is False
    assert level.set_tile("ground", -1, 0, 2) is False
    assert level.set_tile("ground", 0, 99, 2) is False
    assert level.set_tile("nowhere", 0, 0, 2) is False


def test_set_tile_reports_no_op_repaints():
    # The editor uses this to keep identical repaints off the undo stack.
    level = _blank()
    assert level.set_tile("ground", 1, 1, 2) is True
    assert level.set_tile("ground", 1, 1, 2) is False


def test_overlay_may_be_cleared_but_ground_may_not():
    level = _blank()
    assert level.set_tile("overlay", 2, 2, 5) is True
    assert level.set_tile("overlay", 2, 2, reg.EMPTY_TILE) is True


def test_overlay_walkability_wins_over_ground():
    level = _blank()
    assert level.is_cell_walkable(3, 3) is True
    level.set_tile("overlay", 3, 3, 5)            # wall
    assert level.is_cell_walkable(3, 3) is False
    level.set_tile("overlay", 3, 3, reg.EMPTY_TILE)
    assert level.is_cell_walkable(3, 3) is True


def test_solid_props_block_a_walkable_tile():
    level = _blank()
    prop = level.add_prop("rock", 4, 4)
    assert prop.get_passthrough() is False        # registry default
    assert level.is_cell_walkable(4, 4) is False
    prop.set_passthrough(True)
    assert level.is_cell_walkable(4, 4) is True


def test_cells_outside_the_grid_are_never_walkable():
    level = _blank()
    assert level.is_cell_walkable(-1, 0) is False
    assert level.is_cell_walkable(0, 999) is False


# ─────────────────────────────────────────────────────────────
# RESIZE
# ─────────────────────────────────────────────────────────────


def test_resize_grows_with_padding_and_keeps_content():
    level = _blank(12, 10)
    level.set_tile("ground", 1, 1, 4)
    assert level.resize(20, 16) is True
    assert level.get_grid_width() == 20 and level.get_grid_height() == 16
    assert level.get_tile("ground", 1, 1) == 4
    assert level.get_tile("ground", 19, 15) == reg.DEFAULT_GROUND_TILE
    assert level.get_tile("overlay", 19, 15) == reg.EMPTY_TILE


def test_resize_shrinking_drops_out_of_range_entities():
    level = _blank(20, 20)
    level.add_prop("rock", 18, 18)
    level.add_npc("roya", 2, 2)
    assert level.count_out_of_range(12, 12) == 1
    assert level.resize(12, 12) is True
    assert level.get_props() == []
    assert len(level.get_npcs()) == 1


def test_resize_pulls_the_spawn_back_inside():
    level = _blank(20, 20)
    level.set_spawn(19, 19)
    level.resize(12, 12)
    assert level.get_spawn() == (11, 11)


def test_resize_refuses_out_of_range_dimensions():
    level = _blank()
    assert level.resize(reg.GRID_MIN - 1, 20) is False
    assert level.resize(20, reg.GRID_MAX + 1) is False
    assert level.get_grid_width() == 12


# ─────────────────────────────────────────────────────────────
# ENTITIES + UIDS
# ─────────────────────────────────────────────────────────────


def test_one_prop_and_one_npc_per_cell():
    level = _blank()
    level.add_prop("rock", 5, 5)
    level.add_prop("rock_moss", 5, 5)
    assert len(level.get_props()) == 1
    assert level.get_prop_at(5, 5).get_type_id() == "rock_moss"
    # a prop and an NPC may share a cell — they are separate layers
    level.add_npc("hoque", 5, 5)
    assert level.get_npc_at(5, 5) is not None
    assert level.get_prop_at(5, 5) is not None


def test_add_entity_rejects_unknown_types_and_bad_cells():
    level = _blank()
    assert level.add_prop("chair", 1, 1) is None
    assert level.add_npc("dean", 1, 1) is None
    assert level.add_prop("rock", 99, 1) is None


def test_uids_are_unique_within_a_file():
    level = _blank()
    first = level.add_prop("rock", 1, 1).get_uid()
    second = level.add_prop("rock", 2, 2).get_uid()
    assert (first, second) == ("prop_0001", "prop_0002")
    # deleting the MIDDLE of the list must not mint a duplicate:
    # the counter is (highest live number + 1), not (count + 1)
    level.remove_prop_at(1, 1)
    third = level.add_prop("rock", 3, 3).get_uid()
    assert third == "prop_0003"
    assert len({p.get_uid() for p in level.get_props()}) == 2
    # props and NPCs number independently
    assert level.add_npc("roya", 4, 4).get_uid() == "npc_0001"


def test_replace_prop_keeps_identity_and_cell():
    # the settings popup edits a detached copy and hands back a dict;
    # uid, type and position must survive that round trip
    level = _blank()
    prop = level.add_prop("rock_moss", 5, 5)
    edited = prop.to_dict()
    edited["uid"] = "tampered"
    edited["x"], edited["y"] = 99, 99
    edited["type_id"] = "portal"
    edited["passthrough"] = True
    edited["interactable"] = True
    edited["interaction"] = {"kind": "money", "amount": 300.0,
                             "skill_id": None, "triggers_per_semester": 3}

    assert level.replace_prop(prop.get_uid(), edited) is True
    updated = level.get_prop_at(5, 5)
    assert updated.get_uid() == prop.get_uid()
    assert updated.get_type_id() == "rock_moss"
    assert updated.get_position() == (5, 5)
    assert updated.get_amount() == 300.0
    assert updated.get_triggers_per_semester() == 3


def test_replace_npc_swaps_dialog_wholesale():
    level = _blank()
    npc = level.add_npc("hoque", 4, 4)
    edited = npc.to_dict()
    edited["facing"] = "left"
    edited["dialog"] = {
        "chains": [{"chain_id": "new", "lines": ["a", "b"],
                    "emotion": "strict"}],
        "on_complete": "loop_all",
    }
    assert level.replace_npc(npc.get_uid(), edited) is True
    updated = level.get_npc_at(4, 4)
    assert updated.get_facing() == "left"
    assert updated.get_on_complete() == "loop_all"
    assert updated.get_chain(0).get_lines() == ["a", "b"]
    assert updated.get_chain(0).get_emotion() == "strict"


def test_replace_reports_unknown_uids():
    level = _blank()
    assert level.replace_prop("prop_9999", {}) is False
    assert level.replace_npc("npc_9999", {}) is False


def test_remove_reports_whether_anything_was_there():
    level = _blank()
    assert level.remove_prop_at(6, 6) is False
    level.add_prop("rock", 6, 6)
    assert level.remove_prop_at(6, 6) is True


# ─────────────────────────────────────────────────────────────
# PROP SETTINGS CLAMPS  (Spec §5.3)
# ─────────────────────────────────────────────────────────────


def test_speed_modifier_is_clamped():
    prop = PropData("prop_0001", "rock_moss", 0, 0)
    prop.set_speed_modifier(9.0)
    assert prop.get_speed_modifier() == reg.SPEED_MODIFIER_MAX
    prop.set_speed_modifier(-3.0)
    assert prop.get_speed_modifier() == reg.SPEED_MODIFIER_MIN


def test_money_amount_is_clamped_to_its_range():
    prop = PropData("prop_0001", "rock_moss", 0, 0)
    prop.set_interaction_kind("money")
    prop.set_amount(99999)
    assert prop.get_amount() == reg.MONEY_MAX
    prop.set_amount(1)
    assert prop.get_amount() == reg.MONEY_MIN


def test_skill_exp_is_hard_capped_at_ten():
    prop = PropData("prop_0001", "rock_moss", 0, 0)
    prop.set_interaction_kind("skill")
    prop.set_amount(500)
    assert prop.get_amount() == 10
    assert prop.get_skill_id() in reg.SKILL_IDS


def test_skill_id_must_come_from_the_canonical_list():
    prop = PropData("prop_0001", "rock_moss", 0, 0)
    prop.set_interaction_kind("skill")
    assert prop.set_skill_id("time_travel") is False
    assert prop.set_skill_id("algorithms") is True


def test_switching_kind_to_none_clears_the_reward():
    prop = PropData("prop_0001", "rock_moss", 0, 0)
    prop.set_interaction_kind("money")
    prop.set_amount(500)
    prop.set_interaction_kind("none")
    assert prop.get_amount() == 0.0
    assert prop.get_skill_id() is None
    assert prop.set_interaction_kind("bribe") is False


def test_triggers_per_semester_is_clamped():
    prop = PropData("prop_0001", "rock_moss", 0, 0)
    prop.set_triggers_per_semester(50)
    assert prop.get_triggers_per_semester() == reg.TRIGGERS_MAX
    prop.set_triggers_per_semester(0)
    assert prop.get_triggers_per_semester() == reg.TRIGGERS_MIN


def test_portal_target_must_be_a_slug():
    prop = PropData("prop_0001", "portal", 0, 0)
    assert prop.is_portal() is True
    assert prop.set_target_level_id("Campus Lab") is False
    assert prop.set_target_level_id("campus_lab") is True
    assert prop.set_target_spawn((3, 4)) is True
    assert prop.set_target_spawn((-1, 4)) is False


# ─────────────────────────────────────────────────────────────
# DIALOG MODEL  (Spec §6.2)
# ─────────────────────────────────────────────────────────────


def test_chains_play_in_list_order_and_reorder():
    npc = NpcData("npc_0001", "roya", 0, 0)
    npc.add_chain("a")
    npc.add_chain("b")
    assert [c.get_chain_id() for c in npc.get_chains()] == ["a", "b"]
    assert npc.move_chain(0, 1) is True
    assert [c.get_chain_id() for c in npc.get_chains()] == ["b", "a"]
    assert npc.move_chain(1, 1) is False          # off the end
    assert npc.remove_chain(0) is True
    assert npc.get_chain_count() == 1


def test_duplicate_chain_ids_are_made_unique():
    npc = NpcData("npc_0001", "roya", 0, 0)
    npc.add_chain("intro")
    npc.add_chain("intro")
    ids = [c.get_chain_id() for c in npc.get_chains()]
    assert ids == ["intro", "intro_2"]


def test_new_chains_inherit_the_npc_default_emotion():
    npc = NpcData("npc_0001", "hoque", 0, 0)
    assert npc.add_chain().get_emotion() == "neutral"


def test_line_editing():
    chain = DialogChain("intro")
    chain.add_line("one")
    chain.add_line("three")
    chain.add_line("two", index=1)
    assert chain.get_lines() == ["one", "two", "three"]
    assert chain.set_line(0, "ONE") is True
    assert chain.set_line(9, "x") is False
    assert chain.move_line(0, 1) is True
    assert chain.get_lines() == ["two", "ONE", "three"]
    assert chain.remove_line(2) is True
    assert chain.get_line_count() == 2


def test_on_complete_only_accepts_known_modes():
    npc = NpcData("npc_0001", "roya", 0, 0)
    assert npc.set_on_complete("loop_all") is True
    assert npc.set_on_complete("explode") is False
    assert npc.get_on_complete() == "loop_all"


def test_facing_only_accepts_known_directions():
    npc = NpcData("npc_0001", "roya", 0, 0)
    assert npc.set_facing("up") is True
    assert npc.set_facing("sideways") is False


# ─────────────────────────────────────────────────────────────
# VALIDATION  (Spec §7)
# ─────────────────────────────────────────────────────────────


def _codes(level: LevelData) -> set:
    return {i.get_code() for i in level.validate().get_issues()}


def test_a_fresh_level_is_saveable():
    level = _blank()
    report = level.validate()
    assert report.is_saveable() is True
    assert report.is_clean() is True


def test_blocker_spawn_on_a_blocked_cell():
    level = _blank()
    level.set_spawn(2, 2)
    level.set_tile("overlay", 2, 2, 5)
    assert "SPAWN_BLOCKED" in _codes(level)
    assert level.validate().is_saveable() is False


def test_blocker_spawn_outside_the_grid():
    raw = _blank().to_dict()
    raw["meta"]["spawn"] = {"x": 400, "y": 400}
    assert "SPAWN_OUTSIDE" in _codes(LevelData.from_dict(raw))


def test_set_spawn_refuses_cells_outside_the_grid():
    level = _blank()
    before = level.get_spawn()
    assert level.set_spawn(500, 500) is False
    assert level.get_spawn() == before


def test_blocker_ground_hole():
    level = _blank()
    # only reachable by hand-editing a file, which is exactly the case
    # the loader must survive
    raw = level.to_dict()
    raw["layers"]["ground"][0][0] = reg.EMPTY_TILE
    assert "GROUND_HOLE" in _codes(LevelData.from_dict(raw))


def test_blocker_unknown_tile_index():
    level = _blank()
    raw = level.to_dict()
    raw["layers"]["ground"][1][1] = 987
    assert "UNKNOWN_TILE" in _codes(LevelData.from_dict(raw))


def test_blocker_unknown_type_id():
    level = _blank()
    raw = level.to_dict()
    raw["props"] = [{"uid": "prop_0001", "type_id": "sofa", "x": 1, "y": 1}]
    assert "UNKNOWN_TYPE" in _codes(LevelData.from_dict(raw))


def test_blocker_duplicate_uid():
    level = _blank()
    raw = level.to_dict()
    raw["props"] = [
        {"uid": "prop_0001", "type_id": "rock", "x": 1, "y": 1},
        {"uid": "prop_0001", "type_id": "rock", "x": 2, "y": 2},
    ]
    assert "DUPLICATE_UID" in _codes(LevelData.from_dict(raw))


def test_blocker_entity_outside_the_grid():
    level = _blank()
    raw = level.to_dict()
    raw["npcs"] = [{"uid": "npc_0001", "type_id": "roya", "x": 500, "y": 1}]
    assert "OUT_OF_BOUNDS" in _codes(LevelData.from_dict(raw))


def test_blocker_bad_level_id_and_grid_size():
    level = _blank()
    raw = level.to_dict()
    raw["meta"]["level_id"] = "Campus Main"
    raw["meta"]["grid_width"] = 4
    raw["layers"]["ground"] = [[0] * 4 for _ in range(10)]
    raw["layers"]["overlay"] = [[-1] * 4 for _ in range(10)]
    codes = _codes(LevelData.from_dict(raw))
    assert "BAD_LEVEL_ID" in codes
    assert "BAD_GRID_SIZE" in codes


def test_a_malformed_layer_is_padded_so_the_file_still_opens():
    # A ragged layer must not stop the editor from opening the file —
    # the user has to be able to see and repair it. from_dict pads the
    # rows back to the declared size; the LAYER_SHAPE blocker then only
    # fires for in-memory documents, which the editor cannot produce.
    level = _blank()
    raw = level.to_dict()
    raw["layers"]["overlay"] = [[-1, -1]]        # far too small
    raw["layers"]["ground"] = [[0, 0], "junk"]   # ragged AND wrong type
    repaired = LevelData.from_dict(raw)
    assert repaired.get_grid_width() == level.get_grid_width()
    assert len(repaired.get_layer_rows("overlay")) == level.get_grid_height()
    assert "GROUND_HOLE" not in _codes(repaired)  # padded with real ground


def test_warning_npc_on_a_blocked_cell():
    level = _blank()
    level.add_npc("roya", 3, 3)
    level.set_tile("overlay", 3, 3, 5)
    assert "NPC_ON_BLOCKED" in _codes(level)
    assert level.validate().is_saveable() is True     # warning only


def test_warning_empty_dialog_on_an_interactable_npc():
    level = _blank()
    level.add_npc("roya", 3, 3)
    assert "EMPTY_DIALOG" in _codes(level)


def test_warning_interactable_prop_that_grants_nothing():
    level = _blank()
    prop = level.add_prop("rock_moss", 3, 3)
    prop.set_interactable(True)
    assert "IDLE_INTERACTABLE" in _codes(level)


def test_warning_speed_modifier_on_a_blocking_prop():
    level = _blank()
    prop = level.add_prop("rock_moss", 3, 3)
    prop.set_speed_modifier(1.8)
    prop.set_passthrough(False)
    assert "MODIFIER_ON_BLOCKER" in _codes(level)


def test_warning_portal_without_a_target():
    level = _blank()
    level.add_prop("portal", 3, 3)
    assert "PORTAL_NO_TARGET" in _codes(level)


def test_warning_unknown_emotion_on_a_chain():
    level = _blank()
    npc = level.add_npc("hoque", 3, 3)
    chain = npc.add_chain("intro")
    chain.add_line("hello")
    chain.set_emotion("ecstatic")
    assert "UNKNOWN_EMOTION" in _codes(level)


def test_warning_reward_totals_over_the_engine_caps():
    level = _blank(20, 20)
    for i in range(6):
        prop = level.add_prop("rock_moss", i, 1)
        prop.set_interactable(True)
        prop.set_interaction_kind("money")
        prop.set_amount(reg.MONEY_MAX)
        prop.set_triggers_per_semester(1)
    codes = _codes(level)
    assert "MONEY_OVER_CAP" in codes
    assert level.validate().is_saveable() is True


def test_warning_unreachable_region():
    level = _blank(20, 20)
    level.set_spawn(1, 1)
    for y in range(20):                       # wall the grid in half
        level.set_tile("overlay", 10, y, 5)
    assert "UNREACHABLE" in _codes(level)


def test_unreachable_count_is_zero_on_an_open_level():
    assert _blank(20, 20).count_unreachable_cells() == 0


# ─────────────────────────────────────────────────────────────
# SERIALISATION
# ─────────────────────────────────────────────────────────────


def test_round_trip_is_lossless():
    level = LevelData("Round Trip", "round_trip", 14, 12)
    level.set_tile("ground", 2, 2, 4)
    level.set_tile("overlay", 3, 3, 5)
    level.set_ambient("night")
    level.set_music("assets/audio/quad.ogg")
    level.set_spawn(1, 1)
    prop = level.add_prop("rock_moss", 5, 5)
    prop.set_interactable(True)
    prop.set_interaction_kind("skill")
    prop.set_skill_id("networking")
    prop.set_amount(7)
    npc = level.add_npc("hoque", 6, 6)
    chain = npc.add_chain("intro")
    chain.add_line("Round trip.")
    chain.set_emotion("strict")

    again = LevelData.from_dict(level.to_dict())
    assert again.to_dict() == level.to_dict()
    assert again.get_ambient() == "night"
    assert again.get_prop_at(5, 5).get_skill_id() == "networking"
    assert again.get_npc_at(6, 6).get_chain(0).get_emotion() == "strict"


def test_clone_is_independent():
    level = _blank()
    copy = level.clone()
    copy.set_tile("ground", 0, 0, 4)
    copy.add_prop("rock", 1, 1)
    assert level.get_tile("ground", 0, 0) != 4
    assert level.get_props() == []


def test_unknown_keys_survive_a_round_trip():
    level = _blank()
    raw = level.to_dict()
    raw["future_field"] = {"weather": "monsoon"}
    raw["meta"]["author"] = "Nangiba"
    raw["props"] = [{
        "uid": "prop_0001", "type_id": "rock", "x": 1, "y": 1,
        "shimmer": True,
    }]
    raw["npcs"] = [{
        "uid": "npc_0001", "type_id": "roya", "x": 2, "y": 2,
        "dialog": {"chains": [{"chain_id": "a", "lines": ["hi"],
                               "voice": "soft"}]},
    }]
    out = LevelData.from_dict(raw).to_dict()
    assert out["future_field"] == {"weather": "monsoon"}
    assert out["meta"]["author"] == "Nangiba"
    assert out["props"][0]["shimmer"] is True
    assert out["npcs"][0]["dialog"]["chains"][0]["voice"] == "soft"


def test_a_future_schema_version_is_refused():
    raw = _blank().to_dict()
    raw["schema_version"] = SCHEMA_VERSION + 1
    with pytest.raises(LevelSchemaError):
        LevelData.from_dict(raw)


def test_an_absurd_grid_size_is_refused_outright():
    raw = _blank().to_dict()
    raw["meta"]["grid_width"] = 100000
    with pytest.raises(LevelSchemaError):
        LevelData.from_dict(raw)


def test_write_refuses_to_save_a_level_with_blockers(tmp_path):
    level = _blank()
    level.set_spawn(2, 2)
    level.set_tile("overlay", 2, 2, 5)          # spawn now blocked
    target = tmp_path / "broken.json"
    report = write_level(level, str(target))
    assert report.is_saveable() is False
    assert not target.exists()                  # nothing touched on disk


def test_write_then_read_produces_the_same_document(tmp_path):
    level = _blank()
    level.add_prop("rock", 2, 2)
    target = tmp_path / "ok.json"
    assert write_level(level, str(target)).is_saveable() is True
    assert json.loads(target.read_text(encoding="utf-8")) == level.to_dict()
    assert read_level(str(target)).to_dict() == level.to_dict()


def test_read_reports_unreadable_files(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(LevelSchemaError):
        read_level(str(broken))
    with pytest.raises(LevelSchemaError):
        read_level(str(tmp_path / "missing.json"))


# ─────────────────────────────────────────────────────────────
# GATES AND ZONES  (Feature 6, phase F5 extension)
# ─────────────────────────────────────────────────────────────
# Everything below this line was ADDED in F5. Everything above it
# is the quarry's suite, ported verbatim and still green.

import os

from content.level_schema import GateData, ZoneData


def _gated_level():
    """A small valid level with one prop and one NPC to hang gates on."""
    level = LevelData("Gate Test", "gate_test", 12, 12)
    level.set_spawn(1, 1)
    level.add_prop("rock", 5, 5)
    level.add_npc("hoque", 6, 6)
    return level


# ── the default gate is open and invisible ───────────────────


def test_a_new_gate_is_open_and_serialises_to_nothing():
    gate = GateData()
    assert gate.is_default() is True
    assert gate.has_requirements() is False
    assert gate.has_cost() is False
    assert gate.to_dict() == {}


def test_default_gates_add_nothing_to_a_document():
    level = _gated_level()
    data = level.to_dict()
    assert "zones" not in data
    for entry in data["props"] + data["npcs"]:
        assert "gate" not in entry


def test_campus_main_round_trips_byte_identical_after_the_extension(tmp_path):
    """
    THE F5 ACCEPTANCE TEST.

    The shipped fixture predates gates entirely. If GateData or ZoneData
    ever start emitting a default value, this fails -- which is exactly
    what it is here to catch.
    """
    source = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "levels", "campus_main.json")
    original = open(source, "rb").read()

    level = read_level(source)
    report = level.validate()
    assert report.is_saveable() is True
    assert report.is_clean() is True, [str(i) for i in report.get_issues()]

    target = tmp_path / "campus_main.json"
    assert write_level(level, str(target)).is_saveable() is True
    assert target.read_bytes() == original


# ── clamping, and never raising ──────────────────────────────


@pytest.mark.parametrize("setter, getter, low, high", [
    ("set_min_semester", "get_min_semester", 0, 12),
    ("set_min_credits", "get_min_credits", 0, 140),
    ("set_min_days_remaining", "get_min_days_remaining", 0, 80),
    ("set_required_skill_level", "get_required_skill_level", 0, 20),
    ("set_cost_days", "get_cost_days", 0, 80),
])
def test_integer_fields_clamp_to_their_range(setter, getter, low, high):
    gate = GateData()
    getattr(gate, setter)(10 ** 6)
    assert getattr(gate, getter)() == high
    getattr(gate, setter)(-(10 ** 6))
    assert getattr(gate, getter)() == low


@pytest.mark.parametrize("setter, getter, low, high", [
    ("set_min_wallet", "get_min_wallet", 0.0, 200000.0),
    ("set_cost_money", "get_cost_money", 0.0, 200000.0),
])
def test_float_fields_clamp_to_their_range(setter, getter, low, high):
    gate = GateData()
    getattr(gate, setter)(10 ** 9)
    assert getattr(gate, getter)() == high
    getattr(gate, setter)(-1.0)
    assert getattr(gate, getter)() == low


@pytest.mark.parametrize("junk", ["banana", None, [], {}, object()])
def test_rubbish_input_is_refused_not_raised(junk):
    gate = GateData()
    assert gate.set_min_semester(junk) is False
    assert gate.set_min_wallet(junk) is False
    assert gate.set_cost_days(junk) is False
    assert gate.is_default() is True


def test_unknown_skill_id_is_refused_by_the_setter():
    gate = GateData()
    assert gate.set_required_skill_id("not_a_skill") is False
    assert gate.get_required_skill_id() is None
    assert gate.set_required_skill_id(reg.SKILL_IDS[0]) is True
    assert gate.get_required_skill_id() == reg.SKILL_IDS[0]
    assert gate.set_required_skill_id(None) is True
    assert gate.get_required_skill_id() is None


def test_course_codes_are_upper_cased_and_deduplicated():
    gate = GateData()
    gate.set_required_course_codes("cse101, , CSE101 , mat120")
    assert gate.get_required_course_codes() == ["CSE101", "MAT120"]
    gate.set_required_course_codes(["phy101"])
    assert gate.get_required_course_codes() == ["PHY101"]
    assert gate.set_required_course_codes(42) is False


def test_locked_lines_are_capped_and_blanks_dropped():
    gate = GateData()
    gate.set_locked_lines(["one", "", "two", "three", "four"])
    assert gate.get_locked_lines() == ["one", "two", "three"]


def test_blank_locked_title_restores_the_default():
    gate = GateData()
    gate.set_locked_title("staff only")
    assert gate.get_locked_title() == "STAFF ONLY"
    gate.set_locked_title("   ")
    assert gate.get_locked_title() == reg.GATE_LOCKED_TITLE_DEFAULT
    assert gate.is_default() is True


def test_clear_restores_every_default():
    gate = GateData()
    gate.set_min_semester(5)
    gate.set_cost_days(10)
    gate.set_locked_lines(["nope"])
    assert gate.is_default() is False
    gate.clear()
    assert gate.is_default() is True
    assert gate.to_dict() == {}


# ── serialisation ────────────────────────────────────────────


def test_gate_round_trips_through_a_dict():
    gate = GateData()
    gate.set_min_semester(5)
    gate.set_min_credits(60)
    gate.set_min_days_remaining(15)
    gate.set_min_wallet(12000.0)
    gate.set_required_skill_id(reg.SKILL_IDS[1])
    gate.set_required_skill_level(3)
    gate.set_required_course_codes("cse101")
    gate.set_requires_graduated(True)
    gate.set_cost_days(10)
    gate.set_cost_money(500.0)
    gate.set_locked_title("lab access")
    gate.set_locked_lines(["The door does not move."])

    assert GateData.from_dict(gate.to_dict()).to_dict() == gate.to_dict()
    assert gate.clone().to_dict() == gate.to_dict()


def test_gate_from_dict_tolerates_rubbish():
    assert GateData.from_dict(None).is_default() is True
    assert GateData.from_dict({}).is_default() is True
    assert GateData.from_dict("nope").is_default() is True
    partial = GateData.from_dict({"min_semester": 4})
    assert partial.get_min_semester() == 4
    assert partial.get_min_credits() == 0


def test_an_unknown_skill_in_a_file_is_preserved_for_the_warning():
    """A hand-edited typo must survive to be reported, not be erased."""
    gate = GateData.from_dict({"required_skill_id": "wrong_skill",
                               "required_skill_level": 2})
    assert gate.get_required_skill_id() == "wrong_skill"


def test_gates_survive_a_full_document_round_trip():
    level = _gated_level()
    prop = level.get_props()[0]
    prop.get_gate().set_min_semester(5)
    prop.get_gate().set_locked_lines(["Locked."])
    npc = level.get_npcs()[0]
    npc.get_gate().set_min_credits(60)
    npc.get_gate().set_locked_lines(["Not yet."])
    zone = level.add_zone(2, 2, 3, 3)
    zone.get_gate().set_requires_graduated(True)
    zone.get_gate().set_locked_lines(["Graduates only."])

    rebuilt = LevelData.from_dict(level.to_dict())
    assert rebuilt.to_dict() == level.to_dict()
    assert rebuilt.get_props()[0].get_gate().get_min_semester() == 5
    assert rebuilt.get_npcs()[0].get_gate().get_min_credits() == 60
    assert rebuilt.get_zones()[0].get_gate().get_requires_graduated() is True


def test_gate_survives_write_and_read(tmp_path):
    level = _gated_level()
    level.get_props()[0].get_gate().set_min_semester(7)
    level.get_props()[0].get_gate().set_locked_lines(["Sealed."])
    target = tmp_path / "gated.json"
    assert write_level(level, str(target)).is_saveable() is True
    assert read_level(str(target)).to_dict() == level.to_dict()


# ── attaching gates ──────────────────────────────────────────


def test_prop_and_npc_gate_accessors():
    level = _gated_level()
    prop, npc = level.get_props()[0], level.get_npcs()[0]
    assert prop.is_gated() is False and npc.is_gated() is False

    gate = GateData()
    gate.set_min_semester(3)
    assert prop.set_gate(gate) is True
    assert prop.is_gated() is True
    assert prop.set_gate(None) is True
    assert prop.is_gated() is False
    assert prop.set_gate("not a gate") is False


def test_npc_gate_default_is_seeded_from_the_roster():
    """
    The build plan asks an NPC gate to default min_semester from the
    roster. Seeding the STORED gate would break the byte-identical round
    trip, so it is applied where it is used instead.
    """
    level = _gated_level()
    npc = level.get_npcs()[0]                    # hoque, roster semester 5
    assert npc.get_gate().is_default() is True   # stored gate stays open
    assert npc.make_default_gate().get_min_semester() == \
        reg.get_npc_min_semester("hoque") == 5
    assert npc.get_effective_min_semester() == 5

    stricter = GateData()
    stricter.set_min_semester(9)
    npc.set_gate(stricter)
    assert npc.get_effective_min_semester() == 9   # the stricter wins

    looser = GateData()
    looser.set_min_semester(2)
    npc.set_gate(looser)
    assert npc.get_effective_min_semester() == 5   # roster still floors it


# ── zones ────────────────────────────────────────────────────


def test_add_and_remove_zones():
    level = _gated_level()
    assert level.get_zones() == []
    zone = level.add_zone(2, 2, 4, 3)
    assert zone is not None
    assert zone.get_uid().startswith("zone_")
    assert level.get_zone_count() == 1
    assert level.get_zone(zone.get_uid()) is zone
    assert level.remove_zone(zone.get_uid()) is True
    assert level.remove_zone(zone.get_uid()) is False
    assert level.get_zone_count() == 0


def test_add_zone_refuses_bad_rects():
    level = _gated_level()
    assert level.add_zone(2, 2, 0, 3) is None
    assert level.add_zone(2, 2, 3, 0) is None
    assert level.add_zone(999, 999, 2, 2) is None


def test_zone_uids_do_not_collide_with_props_or_npcs():
    level = _gated_level()
    first = level.add_zone(1, 1, 2, 2)
    second = level.add_zone(4, 4, 2, 2)
    assert first.get_uid() != second.get_uid()
    uids = ([p.get_uid() for p in level.get_props()]
            + [n.get_uid() for n in level.get_npcs()]
            + [z.get_uid() for z in level.get_zones()])
    assert len(set(uids)) == len(uids)


def test_zone_contains_and_overlaps():
    zone = ZoneData("zone_0001", "lab", 5, 5, 4, 3)
    assert zone.contains(5, 5) is True
    assert zone.contains(8, 7) is True
    assert zone.contains(9, 7) is False
    assert zone.contains(4, 5) is False
    assert zone.get_cell_count() == 12
    assert zone.overlaps(ZoneData("z2", "b", 8, 7, 2, 2)) is True
    assert zone.overlaps(ZoneData("z3", "c", 20, 20, 2, 2)) is False


def test_zone_id_is_slugified():
    zone = ZoneData("zone_0001", "lab", 0, 0)
    assert zone.set_zone_id("Lab Block 2!") is True
    assert zone.get_zone_id() == "lab_block_2"
    assert zone.set_zone_id("!!!") is False
    assert zone.get_zone_id() == "lab_block_2"


def test_get_zone_at_and_gate_at_precedence():
    level = _gated_level()
    zone = level.add_zone(4, 4, 6, 6)
    zone.get_gate().set_min_credits(30)

    assert level.get_zone_at(5, 5) is zone
    assert level.get_zone_at(0, 0) is None

    # the prop at (5,5) has no gate yet, so the zone gate applies
    assert level.get_gate_at(5, 5) is zone.get_gate()

    # once the prop is gated, the tighter statement wins
    prop_gate = GateData()
    prop_gate.set_min_semester(8)
    level.get_props()[0].set_gate(prop_gate)
    assert level.get_gate_at(5, 5) is prop_gate

    # a cell with neither is ungated
    assert level.get_gate_at(0, 0) is None


def test_get_gate_at_ignores_open_gates():
    """An open default gate must read as no gate, not as a gate."""
    level = _gated_level()
    zone = level.add_zone(4, 4, 4, 4)
    assert zone.get_gate().is_default() is True
    assert level.get_gate_at(5, 5) is None


def test_later_zone_wins_on_overlap():
    level = _gated_level()
    first = level.add_zone(2, 2, 6, 6)
    second = level.add_zone(3, 3, 2, 2)
    assert level.get_zone_at(4, 4) is second
    assert level.get_zone_at(2, 2) is first


def test_replace_zone_keeps_the_uid():
    level = _gated_level()
    zone = level.add_zone(2, 2, 3, 3)
    uid = zone.get_uid()
    data = zone.to_dict()
    data["display_name"] = "Lab Block"
    data["gate"] = {"min_semester": 6, "locked_lines": ["Closed."]}
    assert level.replace_zone(uid, data) is True
    updated = level.get_zone(uid)
    assert updated.get_uid() == uid
    assert updated.get_display_name() == "Lab Block"
    assert updated.get_gate().get_min_semester() == 6
    assert level.replace_zone("no_such_zone", data) is False


def test_zone_round_trips_with_unknown_keys():
    data = {"uid": "zone_0001", "zone_id": "lab", "display_name": "Lab",
            "x": 1, "y": 2, "w": 3, "h": 4, "future_key": "kept"}
    zone = ZoneData.from_dict(data)
    assert zone.to_dict()["future_key"] == "kept"
    assert zone.get_rect() == (1, 2, 3, 4)


# ── the six new warnings, each fired on purpose ──────────────


def test_gate_no_message_warning():
    level = _gated_level()
    level.get_props()[0].get_gate().set_min_semester(5)
    assert "GATE_NO_MESSAGE" in _codes(level)

    level.get_props()[0].get_gate().set_locked_lines(["The door is shut."])
    assert "GATE_NO_MESSAGE" not in _codes(level)


def test_gate_on_spawn_warning():
    level = _gated_level()
    zone = level.add_zone(0, 0, 4, 4)          # covers spawn (1,1)
    zone.get_gate().set_min_semester(5)
    zone.get_gate().set_locked_lines(["Locked."])
    assert "GATE_ON_SPAWN" in _codes(level)


def test_gate_on_spawn_warning_from_a_prop():
    level = LevelData("Spawn Gate", "spawn_gate", 12, 12)
    level.set_spawn(3, 3)
    prop = level.add_prop("rock", 3, 3)
    prop.get_gate().set_min_semester(2)
    prop.get_gate().set_locked_lines(["Locked."])
    assert "GATE_ON_SPAWN" in _codes(level)


def test_gate_cost_exceeds_pool_warning():
    level = _gated_level()
    gate = level.get_props()[0].get_gate()
    gate.set_cost_days(80)
    gate.set_locked_lines(["Expensive."])
    assert "GATE_COST_EXCEEDS_POOL" in _codes(level)

    gate.set_cost_days(10)
    assert "GATE_COST_EXCEEDS_POOL" not in _codes(level)


def test_gate_unknown_skill_warning():
    level = _gated_level()
    # only a hand-edited file can hold an unknown skill; the setter refuses
    rebuilt = GateData.from_dict({"required_skill_id": "not_a_skill",
                                  "required_skill_level": 3,
                                  "locked_lines": ["Learn more."]})
    level.get_props()[0].set_gate(rebuilt)
    assert "GATE_UNKNOWN_SKILL" in _codes(level)


def test_zone_out_of_bounds_warning():
    level = _gated_level()
    zone = level.add_zone(10, 10, 2, 2)
    zone.set_rect(10, 10, 8, 8)                # runs off a 12x12 grid
    assert "ZONE_OUT_OF_BOUNDS" in _codes(level)


def test_zone_overlap_warning():
    level = _gated_level()
    level.add_zone(2, 2, 5, 5)
    level.add_zone(4, 4, 5, 5)
    assert "ZONE_OVERLAP" in _codes(level)


def test_no_gate_warning_is_ever_a_blocker():
    """A half-finished gate must never make a file unsavable."""
    level = _gated_level()
    gate = level.get_props()[0].get_gate()
    gate.set_min_semester(5)
    gate.set_cost_days(80)
    zone = level.add_zone(0, 0, 20, 20)
    zone.get_gate().set_min_credits(60)
    level.add_zone(0, 0, 6, 6)

    report = level.validate()
    assert len(report.get_warnings()) > 0
    assert report.get_blockers() == []
    assert report.is_saveable() is True


def test_a_level_with_no_gates_reports_no_gate_warnings():
    level = _gated_level()
    assert not [c for c in _codes(level)
                if c.startswith("GATE_") or c.startswith("ZONE_")]

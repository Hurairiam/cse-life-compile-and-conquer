"""
tests/test_level_loader.py
Level system E1 — the game-facing loader and the read-only
runtime Level view, plus the shipped campus_main fixture.

Ported to this branch in phase F7. The first seventeen tests are
the quarry's suite unchanged; the block at the bottom is new and
covers the three additive zone/gate getters F7 appended to Level
over the F5 schema extension.
"""

from __future__ import annotations

import json
import os

import pytest

from content import level_registry as reg
from content.level_schema import LevelData, write_level
from engine.level_loader import Level, LevelLoadError, load_level

FIXTURE_ID = "campus_main"


# ─────────────────────────────────────────────────────────────
# ARCHITECTURE  (Spec §11 compliance)
# ─────────────────────────────────────────────────────────────


def test_the_data_layer_and_loader_are_pygame_free():
    for module in ("content/level_registry.py", "content/level_schema.py",
                   "engine/level_loader.py"):
        source = open(module, encoding="utf-8").read()
        assert "import pygame" not in source, f"{module} imports pygame"


def test_the_editor_never_imports_engine_game_state():
    """
    Spec §11: the editor may reach for content/ (data), tools/ (its own
    chrome) and ui/ (pure render classes) — never for game state.
    """
    import glob

    paths = glob.glob("tools/editor_*.py") + ["tools/level_editor.py"]
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        pytest.skip("editor not built yet")
    for path in paths:
        source = open(path, encoding="utf-8").read()
        for banned in ("from engine.", "import engine", "from core.",
                       "import core", "from academic.", "import academic"):
            assert banned not in source, \
                f"{path} imports game state: {banned}"


# ─────────────────────────────────────────────────────────────
# THE SHIPPED FIXTURE
# ─────────────────────────────────────────────────────────────


def test_every_shipped_level_loads_and_validates():
    from content.level_schema import list_level_files, read_level
    files = list_level_files()
    assert files, "no level files found in levels/"
    for path in files:
        report = read_level(path).validate()
        assert report.is_saveable(), \
            f"{path} has blockers: {report.get_blockers()}"


def test_campus_main_is_playable():
    level = load_level(FIXTURE_ID)
    assert isinstance(level, Level)
    assert level.get_level_id() == FIXTURE_ID
    assert level.get_grid_size() == (40, 24)
    assert level.is_walkable(*level.get_spawn()) is True
    assert level.get_npcs(), "the fixture should demo NPC placement"
    assert level.get_props(), "the fixture should demo prop placement"


def test_campus_main_walls_and_water_block():
    level = load_level(FIXTURE_ID)
    assert level.is_walkable(0, 0) is False        # border wall
    assert level.is_walkable(6, 18) is False       # pond
    assert level.is_walkable(-1, 5) is False       # off-grid


def test_campus_main_portal_points_somewhere():
    level = load_level(FIXTURE_ID)
    portals = [p for p in level.get_props() if p.is_portal()]
    assert portals
    portal = portals[0]
    assert portal.get_target_level_id()
    assert level.get_portal_at(*portal.get_position()) is portal


def test_campus_main_speed_modifiers_are_reachable():
    level = load_level(FIXTURE_ID)
    modifiers = {level.get_speed_modifier_at(*p.get_position())
                 for p in level.get_props()}
    assert any(m < 1.0 for m in modifiers), "expected a slow cell"
    assert any(m > 1.0 for m in modifiers), "expected a fast cell"


def test_campus_main_npcs_carry_emotion_tagged_dialog():
    level = load_level(FIXTURE_ID)
    for npc in level.get_npcs():
        emotions = reg.get_npc_emotions(npc.get_type_id())
        assert npc.get_chain_count() >= 1
        for chain in npc.get_chains():
            assert chain.get_line_count() >= 1
            assert chain.get_emotion() in emotions
            assert reg.get_npc_portrait_path(npc.get_type_id(),
                                             chain.get_emotion())


# ─────────────────────────────────────────────────────────────
# RUNTIME VIEW
# ─────────────────────────────────────────────────────────────


def _fixture_document(tmp_path, build) -> str:
    level = LevelData("Temp", "temp_level", 12, 12)
    build(level)
    path = str(tmp_path / "temp_level.json")
    assert write_level(level, path).is_saveable()
    return path


def test_speed_modifier_is_one_off_a_modifier_cell(tmp_path):
    def build(level: LevelData) -> None:
        prop = level.add_prop("rock_moss", 4, 4)
        prop.set_passthrough(True)
        prop.set_speed_modifier(0.4)

    level = load_level(_fixture_document(tmp_path, build))
    assert level.get_speed_modifier_at(4, 4) == 0.4
    assert level.get_speed_modifier_at(5, 5) == reg.SPEED_MODIFIER_BASE


def test_blocking_props_never_report_a_modifier(tmp_path):
    def build(level: LevelData) -> None:
        prop = level.add_prop("rock_moss", 4, 4)
        prop.set_speed_modifier(1.9)
        prop.set_passthrough(False)

    level = load_level(_fixture_document(tmp_path, build))
    assert level.is_walkable(4, 4) is False
    assert level.get_speed_modifier_at(4, 4) == reg.SPEED_MODIFIER_BASE


def test_interactable_lookup(tmp_path):
    def build(level: LevelData) -> None:
        plain = level.add_prop("rock_moss", 2, 2)
        plain.set_passthrough(True)
        reward = level.add_prop("rock_moss", 3, 3)
        reward.set_passthrough(True)
        reward.set_interactable(True)
        reward.set_interaction_kind("money")
        reward.set_amount(reg.MONEY_MIN)

    level = load_level(_fixture_document(tmp_path, build))
    assert level.get_interactable_at(2, 2) is None
    assert level.get_interactable_at(3, 3) is not None
    assert level.get_interactable_at(9, 9) is None


def test_the_runtime_view_cannot_be_edited_through_its_getters(tmp_path):
    def build(level: LevelData) -> None:
        level.add_prop("rock", 5, 5)

    level = load_level(_fixture_document(tmp_path, build))
    props = level.get_props()
    props.clear()
    assert len(level.get_props()) == 1        # the list was a copy


def test_build_npc_characters_makes_real_npc_objects():
    from core.character.npc import NPC

    level = load_level(FIXTURE_ID)
    characters = level.build_npc_characters()
    assert len(characters) == len(level.get_npcs())
    for character in characters:
        assert isinstance(character, NPC)
        assert character.get_current_location_id() == FIXTURE_ID
        assert character.get_dialogue_node(0) != ""
        # the availability window stays a game rule, not editor data
        assert character.get_is_accessible() is True


# ─────────────────────────────────────────────────────────────
# FAILURE PATHS
# ─────────────────────────────────────────────────────────────


def test_a_missing_level_raises():
    with pytest.raises(LevelLoadError):
        load_level("no_such_level")


def test_a_level_with_blockers_is_refused(tmp_path):
    level = LevelData("Broken", "broken", 12, 12)
    path = str(tmp_path / "broken.json")
    raw = level.to_dict()
    raw["layers"]["ground"][0][0] = reg.EMPTY_TILE       # a hole
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(raw, handle)

    with pytest.raises(LevelLoadError) as caught:
        load_level(path)
    report = caught.value.get_report()
    assert report is not None
    assert "GROUND_HOLE" in {i.get_code() for i in report.get_blockers()}


def test_a_level_with_blockers_can_still_be_loaded_non_strict(tmp_path):
    level = LevelData("Broken", "broken", 12, 12)
    path = str(tmp_path / "broken.json")
    raw = level.to_dict()
    raw["layers"]["ground"][0][0] = reg.EMPTY_TILE
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(raw, handle)

    assert load_level(path, strict=False).get_level_id() == "broken"


def test_a_future_schema_file_is_refused(tmp_path):
    path = str(tmp_path / "future.json")
    raw = LevelData("Future", "future", 12, 12).to_dict()
    raw["schema_version"] = 99
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(raw, handle)

    with pytest.raises(LevelLoadError):
        load_level(path)


# ─────────────────────────────────────────────────────────────
# ZONES + GATES  (F7 additions over the F5 schema extension)
# ─────────────────────────────────────────────────────────────


def _gated_zone_level(tmp_path) -> str:
    """A 12x12 level with one gated zone and one gated door prop."""
    def build(level: LevelData) -> None:
        zone = level.add_zone(2, 2, 4, 4)
        zone.set_display_name("Lab Wing")
        zone.get_gate().set_min_semester(5)
        zone.get_gate().set_locked_lines(["The lab is closed to you."])

        door = level.add_prop("rock_moss", 3, 3)
        door.set_passthrough(True)
        door.get_gate().set_min_credits(60)
        door.get_gate().set_locked_lines(["A card reader blinks red."])

    return _fixture_document(tmp_path, build)


def test_zones_survive_the_round_trip_into_the_runtime_view(tmp_path):
    level = load_level(_gated_zone_level(tmp_path))
    zones = level.get_zones()
    assert len(zones) == 1
    assert zones[0].get_display_name() == "Lab Wing"
    assert zones[0].get_rect() == (2, 2, 4, 4)


def test_the_zone_list_is_a_copy_like_every_other_getter(tmp_path):
    level = load_level(_gated_zone_level(tmp_path))
    level.get_zones().clear()
    assert len(level.get_zones()) == 1


def test_get_zone_at_answers_only_inside_the_rectangle(tmp_path):
    level = load_level(_gated_zone_level(tmp_path))
    assert level.get_zone_at(2, 2) is not None      # top-left corner
    assert level.get_zone_at(5, 5) is not None      # bottom-right corner
    assert level.get_zone_at(6, 5) is None          # one cell past the edge
    assert level.get_zone_at(0, 0) is None


def test_a_prop_gate_beats_the_zone_gate_it_sits_inside(tmp_path):
    """
    The door at (3, 3) is inside the semester-5 zone but carries its own
    credit gate. The tighter, more specific statement of intent wins —
    the same precedence content/level_schema.py already uses.
    """
    level = load_level(_gated_zone_level(tmp_path))
    gate = level.get_gate_at(3, 3)
    assert gate is not None
    assert gate.get_min_credits() == 60
    assert gate.get_min_semester() == 0


def test_a_zone_gate_answers_for_a_plain_cell_inside_it(tmp_path):
    level = load_level(_gated_zone_level(tmp_path))
    gate = level.get_gate_at(4, 4)
    assert gate is not None
    assert gate.get_min_semester() == 5


def test_an_ungated_cell_reports_no_gate(tmp_path):
    level = load_level(_gated_zone_level(tmp_path))
    assert level.get_gate_at(9, 9) is None
    assert level.get_gate_at(-1, -1) is None


def test_an_open_default_gate_counts_as_no_gate_at_all(tmp_path):
    """
    Every prop owns a GateData, most of them wide open. A caller must
    never have to test is_default() itself, so an open gate resolves to
    None exactly like a bare cell.
    """
    def build(level: LevelData) -> None:
        level.add_prop("rock_moss", 7, 7).set_passthrough(True)
        level.add_zone(6, 6, 3, 3)

    level = load_level(_fixture_document(tmp_path, build))
    assert level.get_prop_at(7, 7) is not None
    assert level.get_zone_at(7, 7) is not None
    assert level.get_gate_at(7, 7) is None


def test_the_shipped_fixture_gates_nothing_yet(tmp_path):
    """
    campus_main.json predates the gate extension and must stay a clean
    ungated level — that is the F5 byte-identical round-trip baseline.
    """
    level = load_level(FIXTURE_ID)
    assert level.get_zones() == []
    width, height = level.get_grid_size()
    assert all(level.get_gate_at(x, y) is None
               for y in range(height) for x in range(width))

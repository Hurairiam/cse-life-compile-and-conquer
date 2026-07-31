"""
tests/test_level_editor.py
Level system E2/E3 — the editor app, driven headless.

Runs pygame against the dummy video driver, so these are real
render passes and real event routing with no window on screen.
They are smoke-and-behaviour tests: every popup must open, draw
and hand back the right payload, and every edit must land on the
document exactly once so undo stays honest.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame                                             # noqa: E402
import pytest                                             # noqa: E402

from content import level_registry as reg                 # noqa: E402
from content.level_registry import resolve_asset          # noqa: E402
from content.level_schema import (                        # noqa: E402
    LevelData,
    level_path,
    list_level_files,
)
from tools.editor_popups import (                         # noqa: E402
    CANCEL,
    ConfirmPopup,
    FilePickerPopup,
    NewLevelPopup,
    NpcDialogPopup,
    PropSettingsPopup,
    ValidationPopup,
    slugify,
)
from tools.level_editor import (                          # noqa: E402
    CANVAS,
    SIDE_PANEL,
    LevelEditorApp,
    UndoStack,
    resolve_level_argument,
)

FIXTURE = level_path("campus_main")


@pytest.fixture
def app():
    """A fresh editor with the shipped fixture open."""
    editor = LevelEditorApp(FIXTURE)
    yield editor
    pygame.display.quit()


@pytest.fixture
def scratch_app(tmp_path):
    """
    An editor whose SAVE writes to a throwaway folder, so save tests
    cannot touch the repo's real `levels/`.
    """
    levels_dir = str(tmp_path / "levels")
    os.makedirs(levels_dir, exist_ok=True)
    editor = LevelEditorApp(FIXTURE, levels_dir=levels_dir)
    yield editor, levels_dir
    pygame.display.quit()


# ── event helpers ─────────────────────────────────────────────


def click(editor: LevelEditorApp, pos, button: int = 1) -> None:
    """Move the mouse there, then press and release."""
    editor.handle_event(pygame.event.Event(
        pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
    editor.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, pos=pos, button=button))
    editor.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONUP, pos=pos, button=button))


def press(editor: LevelEditorApp, key: int, mod: int = 0) -> None:
    """Send a keydown."""
    editor.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod,
                                           unicode=""))


def cell_pos(editor: LevelEditorApp, x: int, y: int):
    """
    Screen centre of a grid cell, brought on screen first — a click
    outside the canvas is correctly ignored by the editor, so a test
    that wants to paint has to pan there like a user would.
    """
    editor.focus_cell((x, y))
    editor.render()
    rect = editor._LevelEditorApp__cell_screen_rect(x, y)   # view maths only
    return rect.center


def select_palette(editor: LevelEditorApp, kind: str, key: str) -> None:
    """Switch to the right tab and click the palette cell for `key`."""
    tab = {"tile": pygame.K_1, "prop": pygame.K_2, "npc": pygame.K_3}[kind]
    press(editor, tab)
    editor.render()
    palette = editor._LevelEditorApp__palette
    for index, item in enumerate(palette.get_items()):
        if item.get_key() == key:
            click(editor, palette.get_cell_rect(index).center)
            return
    raise AssertionError(f"no palette item {key!r} on the {kind} tab")


# ─────────────────────────────────────────────────────────────
# BOOT
# ─────────────────────────────────────────────────────────────


def test_editor_opens_the_fixture_and_draws(app):
    assert app.get_level().get_level_id() == "campus_main"
    assert app.is_dirty() is False
    app.render()                      # must not raise
    app.update(1 / 60)


def test_layout_regions_do_not_overlap():
    assert CANVAS.right == SIDE_PANEL.x
    assert CANVAS.width + SIDE_PANEL.width == 1280


def test_every_tab_renders(app):
    for key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                pygame.K_5):
        press(app, key)
        app.render()


# ─────────────────────────────────────────────────────────────
# UNDO STACK
# ─────────────────────────────────────────────────────────────


def test_undo_stack_round_trip():
    level = LevelData("T", "t", 12, 12)
    stack = UndoStack(limit=5)
    stack.record(level)
    level.set_tile("ground", 0, 0, 4)
    restored = stack.undo(level)
    assert restored.get_tile("ground", 0, 0) != 4
    assert stack.redo(restored).get_tile("ground", 0, 0) == 4


def test_undo_stack_respects_its_limit():
    level = LevelData("T", "t", 12, 12)
    stack = UndoStack(limit=3)
    for _ in range(10):
        stack.record(level)
    assert stack.get_depth()[0] == 3


def test_undo_stack_is_empty_at_the_start():
    assert UndoStack().undo(LevelData("T", "t", 12, 12)) is None


# ─────────────────────────────────────────────────────────────
# PALETTE + PAINTING
# ─────────────────────────────────────────────────────────────


def test_palette_selection_toggles(app):
    select_palette(app, "tile", "4")
    assert app.get_selection() == ("tile", "4")
    palette = app._LevelEditorApp__palette
    index = [i.get_key() for i in palette.get_items()].index("4")
    click(app, palette.get_cell_rect(index).center)      # same item again
    assert app.get_selection()[0] == ""


def test_selecting_a_prop_clears_a_tile_selection(app):
    select_palette(app, "tile", "4")
    select_palette(app, "prop", "rock")
    assert app.get_selection() == ("prop", "rock")


def test_painting_a_tile_marks_dirty_and_is_one_undo_step(app):
    select_palette(app, "tile", "4")           # road
    click(app, cell_pos(app, 3, 3))
    assert app.get_level().get_tile("ground", 3, 3) == 4
    assert app.is_dirty() is True
    assert app.get_undo_depth()[0] == 1

    press(app, pygame.K_z, pygame.KMOD_CTRL)
    assert app.get_level().get_tile("ground", 3, 3) != 4
    press(app, pygame.K_y, pygame.KMOD_CTRL)
    assert app.get_level().get_tile("ground", 3, 3) == 4


def test_a_drag_stroke_is_a_single_undo_step(app):
    select_palette(app, "tile", "4")
    start = cell_pos(app, 3, 3)
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start,
                                        button=1))
    for x in range(4, 8):
        app.handle_event(pygame.event.Event(
            pygame.MOUSEMOTION, pos=cell_pos(app, x, 3), rel=(1, 0),
            buttons=(1, 0, 0)))
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=start,
                                        button=1))
    assert all(app.get_level().get_tile("ground", x, 3) == 4
               for x in range(3, 8))
    assert app.get_undo_depth()[0] == 1


def test_a_wall_paints_into_the_overlay_layer(app):
    select_palette(app, "tile", "5")           # wall — overlay, blocking
    click(app, cell_pos(app, 3, 4))
    level = app.get_level()
    assert level.get_tile("overlay", 3, 4) == 5
    assert level.is_cell_walkable(3, 4) is False


def test_placing_a_prop_and_an_npc(app):
    select_palette(app, "prop", "rock")
    click(app, cell_pos(app, 4, 5))
    assert app.get_level().get_prop_at(4, 5) is not None

    select_palette(app, "npc", "roya")
    click(app, cell_pos(app, 4, 5))
    assert app.get_level().get_npc_at(4, 5) is not None


def test_the_eraser_works_top_down(app):
    level = app.get_level()
    select_palette(app, "prop", "rock")
    click(app, cell_pos(app, 6, 6))
    select_palette(app, "npc", "roya")
    click(app, cell_pos(app, 6, 6))
    select_palette(app, "tile", "5")
    click(app, cell_pos(app, 6, 6))

    select_palette(app, "tile", reg.EMPTY_TILE and "__eraser__")
    click(app, cell_pos(app, 6, 6))
    assert level.get_npc_at(6, 6) is None            # NPC went first
    assert level.get_prop_at(6, 6) is not None

    click(app, cell_pos(app, 6, 6))
    assert level.get_prop_at(6, 6) is None           # then the prop
    click(app, cell_pos(app, 6, 6))
    assert level.get_tile("overlay", 6, 6) == reg.EMPTY_TILE  # then overlay
    click(app, cell_pos(app, 6, 6))
    assert level.get_tile("ground", 6, 6) == reg.DEFAULT_GROUND_TILE


def test_clicking_off_the_canvas_paints_nothing(app):
    select_palette(app, "tile", "4")
    before = app.get_undo_depth()[0]
    click(app, (360, 20))                              # blank top bar
    click(app, (SIDE_PANEL.centerx, SIDE_PANEL.bottom - 20))  # panel footer
    assert app.get_undo_depth()[0] == before
    assert app.is_dirty() is False


def test_clicking_the_canvas_outside_the_level_paints_nothing(app):
    select_palette(app, "tile", "4")
    app.focus_cell((0, 0))                # puts empty space left of column 0
    app.render()
    before = app.get_undo_depth()[0]
    click(app, (CANVAS.x + 4, CANVAS.y + 4))
    assert app.get_undo_depth()[0] == before


# ─────────────────────────────────────────────────────────────
# VIEW
# ─────────────────────────────────────────────────────────────


def test_zoom_steps_and_clamps(app):
    for _ in range(5):
        press(app, pygame.K_EQUALS)
    app.render()
    for _ in range(9):
        press(app, pygame.K_MINUS)
    app.render()                       # both ends must stay renderable


def test_grid_and_badge_toggles_render(app):
    press(app, pygame.K_g)
    app.render()
    press(app, pygame.K_b)
    app.render()


# ─────────────────────────────────────────────────────────────
# POPUPS
# ─────────────────────────────────────────────────────────────


def test_right_click_opens_the_prop_popup(app):
    prop = app.get_level().get_props()[0]
    click(app, cell_pos(app, *prop.get_position()), button=3)
    modal = app.get_active_modal()
    assert isinstance(modal, PropSettingsPopup)
    modal.render(pygame.display.get_surface())


def test_right_click_opens_the_npc_popup(app):
    npc = app.get_level().get_npcs()[0]
    click(app, cell_pos(app, *npc.get_position()), button=3)
    modal = app.get_active_modal()
    assert isinstance(modal, NpcDialogPopup)
    modal.render(pygame.display.get_surface())


def test_right_click_on_bare_ground_opens_nothing(app):
    click(app, cell_pos(app, 2, 2), button=3)
    assert app.get_active_modal() is None


def test_cancelling_the_prop_popup_changes_nothing(app):
    prop = app.get_level().get_props()[0]
    before = prop.to_dict()
    click(app, cell_pos(app, *prop.get_position()), button=3)
    modal = app.get_active_modal()
    modal.set_result(CANCEL)
    app.update(1 / 60)
    assert app.get_active_modal() is None
    assert app.get_level().get_props()[0].to_dict() == before
    assert app.is_dirty() is False


def test_confirming_the_prop_popup_applies_one_undo_step(app):
    prop = app.get_level().get_props()[0]
    click(app, cell_pos(app, *prop.get_position()), button=3)
    modal = app.get_active_modal()
    edited = prop.to_dict()
    edited["passthrough"] = True
    edited["interactable"] = True
    edited["interaction"] = {"kind": "money", "amount": 150.0,
                             "skill_id": None, "triggers_per_semester": 2}
    modal.set_result(edited)
    app.update(1 / 60)

    updated = app.get_level().get_prop_at(*prop.get_position())
    assert updated.get_interaction_kind() == "money"
    assert updated.get_amount() == 150.0
    assert updated.get_uid() == prop.get_uid()
    assert app.get_undo_depth()[0] == 1


def test_confirming_the_npc_popup_applies_dialog_edits(app):
    npc = app.get_level().get_npcs()[0]
    click(app, cell_pos(app, *npc.get_position()), button=3)
    modal = app.get_active_modal()
    edited = npc.to_dict()
    edited["dialog"] = {"chains": [{"chain_id": "x", "lines": ["hi"],
                                    "emotion": "strict"}],
                        "on_complete": "silent"}
    modal.set_result(edited)
    app.update(1 / 60)

    updated = app.get_level().get_npc_at(*npc.get_position())
    assert updated.get_on_complete() == "silent"
    assert updated.get_chain(0).get_emotion() == "strict"


def test_the_npc_popup_preview_types_out_a_line(app):
    npc = app.get_level().get_npcs()[0]
    click(app, cell_pos(app, *npc.get_position()), button=3)
    modal = app.get_active_modal()
    modal.on_button("preview")
    for _ in range(30):
        modal.update(1 / 60)
        modal.render(pygame.display.get_surface())
    assert modal.is_open() is True          # preview must not close the popup


def test_a_prop_popup_returns_a_clamped_payload(app):
    prop = app.get_level().get_props()[0]
    click(app, cell_pos(app, *prop.get_position()), button=3)
    modal = app.get_active_modal()
    modal.on_button("ok")
    payload = modal.get_result()
    assert payload["speed_modifier"] <= reg.SPEED_MODIFIER_MAX
    assert payload["interaction"]["amount"] <= reg.MONEY_MAX


def test_validate_now_opens_the_report(app):
    press(app, pygame.K_5)          # SETTINGS: was 4, ZONES took 4
    app.render()
    click(app, app._LevelEditorApp__btn_validate.center)
    modal = app.get_active_modal()
    assert isinstance(modal, ValidationPopup)
    modal.render(pygame.display.get_surface())


def test_new_and_load_open_without_unsaved_changes(app):
    press(app, pygame.K_n, pygame.KMOD_CTRL)
    assert isinstance(app.get_active_modal(), NewLevelPopup)
    app.get_active_modal().set_result(CANCEL)
    app.update(1 / 60)

    press(app, pygame.K_o, pygame.KMOD_CTRL)
    assert isinstance(app.get_active_modal(), FilePickerPopup)


def test_unsaved_changes_are_guarded(app):
    select_palette(app, "tile", "4")
    click(app, cell_pos(app, 3, 3))
    assert app.is_dirty() is True

    press(app, pygame.K_o, pygame.KMOD_CTRL)
    modal = app.get_active_modal()
    assert isinstance(modal, ConfirmPopup)
    modal.set_result(True)               # discard
    app.update(1 / 60)
    assert isinstance(app.get_active_modal(), FilePickerPopup)


def test_creating_a_new_level_replaces_the_document(app):
    press(app, pygame.K_n, pygame.KMOD_CTRL)
    app.get_active_modal().set_result(
        {"name": "Lab Block", "level_id": "lab_block",
         "width": 20, "height": 16})
    app.update(1 / 60)
    level = app.get_level()
    assert level.get_level_id() == "lab_block"
    assert (level.get_grid_width(), level.get_grid_height()) == (20, 16)
    assert level.validate().is_saveable() is True
    app.render()


# ─────────────────────────────────────────────────────────────
# SETTINGS SECTION
# ─────────────────────────────────────────────────────────────


def test_ambient_chips_change_the_document(app):
    press(app, pygame.K_5)          # SETTINGS: was 4, ZONES took 4
    app.render()
    chips = app._LevelEditorApp__chips_ambient
    index = chips.get_options().index("night")
    click(app, chips.get_chip_rect(index).center)
    assert app.get_level().get_ambient() == "night"
    assert app.is_dirty() is True


def test_set_spawn_arms_a_single_click(app):
    press(app, pygame.K_5)          # SETTINGS: was 4, ZONES took 4
    app.render()
    click(app, app._LevelEditorApp__btn_spawn.center)
    click(app, cell_pos(app, 9, 9))
    assert app.get_level().get_spawn() == (9, 9)
    # the arm is one-shot: the next click must not move it again
    click(app, cell_pos(app, 11, 11))
    assert app.get_level().get_spawn() == (9, 9)


def test_shrinking_the_grid_asks_first(app):
    press(app, pygame.K_5)          # SETTINGS: was 4, ZONES took 4
    app.render()
    app._LevelEditorApp__step_w.set_value(12)
    app._LevelEditorApp__step_h.set_value(12)
    click(app, app._LevelEditorApp__btn_resize.center)

    modal = app.get_active_modal()
    assert isinstance(modal, ConfirmPopup)      # content would be deleted
    modal.set_result(True)
    app.update(1 / 60)
    assert app.get_level().get_grid_width() == 12
    assert app.get_level().validate().is_saveable() is True


def test_saving_writes_the_file(scratch_app):
    editor, levels_dir = scratch_app
    editor.get_level().set_level_id("scratch_level")
    press(editor, pygame.K_s, pygame.KMOD_CTRL)
    assert os.path.isfile(os.path.join(levels_dir, "scratch_level.json"))
    assert editor.is_dirty() is False


def test_saving_a_broken_level_opens_the_report(scratch_app):
    editor, levels_dir = scratch_app
    select_palette(editor, "tile", "5")                 # wall
    spawn = editor.get_level().get_spawn()
    click(editor, cell_pos(editor, *spawn))             # bury the spawn
    press(editor, pygame.K_s, pygame.KMOD_CTRL)

    assert isinstance(editor.get_active_modal(), ValidationPopup)
    assert not os.path.isfile(os.path.join(levels_dir, "campus_main.json"))
    assert editor.is_dirty() is True


# ─────────────────────────────────────────────────────────────
# PATH RESOLUTION
# ─────────────────────────────────────────────────────────────
# Regression guard for a real bug: every asset and levels path used to
# resolve against the CURRENT WORKING DIRECTORY, so launching the editor
# from anywhere but the project root silently produced an empty level
# full of placeholder squares.


def test_content_loads_from_any_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert list_level_files(), "levels/ must be found from any cwd"

    editor = LevelEditorApp(level_path("campus_main"))
    try:
        editor.render()
        assert editor.get_level().get_level_id() == "campus_main"
        for path in editor.get_missing_assets():
            assert not os.path.isfile(resolve_asset(path)), \
                f"{path} exists on disk but failed to load"
    finally:
        pygame.display.quit()


def test_the_shipped_art_all_loads(app):
    """Only the known-placeholder files may be missing."""
    app.render()
    press(app, pygame.K_2)
    app.render()
    press(app, pygame.K_3)
    app.render()
    for path in app.get_missing_assets():
        assert not os.path.isfile(resolve_asset(path)), \
            f"{path} exists on disk but failed to load"


def test_level_argument_accepts_ids_paths_and_junk(tmp_path):
    assert resolve_level_argument("campus_main") == level_path("campus_main")
    assert resolve_level_argument(level_path("campus_main")) == \
        level_path("campus_main")
    assert resolve_level_argument("levels/campus_main.json") != ""
    assert resolve_level_argument("no_such_level") == ""
    assert resolve_level_argument("") == ""


# ─────────────────────────────────────────────────────────────
# MISC
# ─────────────────────────────────────────────────────────────


def test_slugify_produces_legal_ids():
    assert slugify("Campus Main") == "campus_main"
    assert slugify("  Lab //  Block 2 ") == "lab_block_2"
    assert slugify("!!!") == "level"


def test_quit_is_guarded_when_dirty(app):
    select_palette(app, "tile", "4")
    click(app, cell_pos(app, 3, 3))
    app.handle_event(pygame.event.Event(pygame.QUIT))
    assert isinstance(app.get_active_modal(), ConfirmPopup)
    assert app.is_running() is True


# ─────────────────────────────────────────────────────────────
# GATES AND ZONES  (Feature 6, phase F6 extension)
# ─────────────────────────────────────────────────────────────
# Everything below this line was ADDED in F6. Everything above it
# is the quarry's suite, ported verbatim.

from content.level_schema import GateData                   # noqa: E402
from tools.editor_popups import (                           # noqa: E402
    GatePopup,
    NewZonePopup,
    gate_cost_labels,
    gate_requirement_labels,
)
from tools.level_editor import (                            # noqa: E402
    TAB_NPCS,
    TAB_PROPS,
    TAB_SETTINGS,
    TAB_TILES,
    TAB_ZONES,
    TAB_NAMES,
)


def popup_surface() -> pygame.Surface:
    """A standalone target for popup-only tests -- no display needed."""
    pygame.init()
    return pygame.Surface((1280, 720))


def cell_pair(editor: LevelEditorApp, first, second):
    """
    Screen centres of TWO cells after a single camera settle.

    cell_pos() re-focuses on every call, so calling it twice moves the
    camera between the two lookups and the first position ends up
    pointing at a different cell. A drag needs both measured against
    the same view.
    """
    editor.focus_cell(first)
    editor.render()
    a = editor._LevelEditorApp__cell_screen_rect(*first)
    b = editor._LevelEditorApp__cell_screen_rect(*second)
    return a.center, b.center


def drag(editor: LevelEditorApp, start, end) -> None:
    """Press at one cell, move to another, release -- a zone drag."""
    editor.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, pos=start, button=1))
    editor.handle_event(pygame.event.Event(
        pygame.MOUSEMOTION, pos=end, rel=(1, 1), buttons=(1, 0, 0)))
    editor.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONUP, pos=end, button=1))


# ── the tab row ──────────────────────────────────────────────


def test_zones_tab_exists_between_npcs_and_settings():
    """The F6 tab order, spelled out so a renumber is visible."""
    assert TAB_NAMES == ("TILES", "PROPS", "NPCS", "ZONES", "SETTINGS")
    assert (TAB_TILES, TAB_PROPS, TAB_NPCS, TAB_ZONES, TAB_SETTINGS) == \
        (0, 1, 2, 3, 4)


def test_zones_tab_renders_empty_and_populated(app):
    press(app, pygame.K_4)
    app.render()                              # "No zones yet."
    app.get_level().add_zone(2, 2, 3, 3)
    app.render()                              # the list


def test_hotkey_five_reaches_settings(app):
    press(app, pygame.K_5)
    assert app._LevelEditorApp__tab == TAB_SETTINGS


# ── GatePopup -> GateData -> to_dict round trip ──────────────


def test_gate_popup_commits_every_field():
    gate = GateData()
    gate.set_min_semester(5)
    gate.set_min_credits(60)
    gate.set_min_days_remaining(15)
    gate.set_min_wallet(12000.0)
    gate.set_required_skill_id(reg.SKILL_IDS[2])
    gate.set_required_skill_level(4)
    gate.set_required_course_codes("cse101, mat120")
    gate.set_requires_graduated(True)
    gate.set_cost_days(10)
    gate.set_cost_money(5000.0)
    gate.set_locked_title("lab access")
    gate.set_locked_lines(["The door does not move."])

    popup = GatePopup(gate, "prop_0001")
    popup.render(popup_surface())
    popup.on_button("ok")

    result = popup.get_result()
    assert result != CANCEL
    assert GateData.from_dict(result).to_dict() == gate.to_dict()


def test_gate_popup_cancel_returns_cancel():
    popup = GatePopup(GateData(), "prop_0001")
    popup.on_button(CANCEL)
    assert popup.get_result() == CANCEL


def test_gate_popup_escape_cancels():
    popup = GatePopup(GateData(), "prop_0001")
    popup.handle_event(pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
    assert popup.get_result() == CANCEL


def test_gate_popup_clear_resets_without_closing():
    gate = GateData()
    gate.set_min_semester(7)
    gate.set_cost_days(20)
    gate.set_locked_lines(["Sealed."])

    popup = GatePopup(gate, "zone_0001")
    popup.on_button("clear")
    assert popup.is_open() is True             # CLEAR must not close
    assert popup.get_gate().is_default() is True

    popup.on_button("ok")
    assert popup.get_result() == {}            # an open gate serialises away


def test_gate_popup_seeds_an_empty_gate_from_the_roster():
    """
    PHASELOG_F5 §4.6: the roster semester reaches the author through
    the popup default, not through the stored gate.
    """
    popup = GatePopup(GateData(), "npc_0001", default_min_semester=5)
    assert popup.get_gate().get_min_semester() == 5


def test_gate_popup_does_not_overwrite_an_existing_gate():
    """A gate the author already saved must survive reopening."""
    gate = GateData()
    gate.set_min_semester(2)
    popup = GatePopup(gate, "npc_0001", default_min_semester=9)
    assert popup.get_gate().get_min_semester() == 2


def test_gate_popup_edits_a_detached_copy():
    """CANCEL must genuinely change nothing (the PropSettingsPopup rule)."""
    gate = GateData()
    gate.set_min_semester(3)
    popup = GatePopup(gate, "prop_0001")
    popup.get_gate().set_min_semester(11)
    assert gate.get_min_semester() == 3


def test_gate_popup_renders_at_every_state():
    surface = popup_surface()
    GatePopup(GateData(), "zone_0001").render(surface)      # open gate
    gate = GateData()
    gate.set_min_semester(5)
    gate.set_cost_days(10)
    gate.set_locked_lines(["Closed."])
    GatePopup(gate, "zone_0001").render(surface)            # gated + costed


def test_gate_summary_labels_match_the_style_guide_formats():
    """§7 formats: ALL-CAPS, thousands commas, N / MAX."""
    gate = GateData()
    gate.set_min_semester(5)
    gate.set_min_credits(60)
    gate.set_min_wallet(12000.0)
    gate.set_required_skill_id("databases")
    gate.set_required_skill_level(3)
    gate.set_required_course_codes("cse101")
    gate.set_requires_graduated(True)
    assert gate_requirement_labels(gate) == [
        "SEMESTER 5", "CREDITS 60", "12,000 BDT",
        "DATABASES LEVEL 3", "PASSED CSE101", "GRADUATED"]

    gate.set_cost_days(10)
    gate.set_cost_money(5000.0)
    assert gate_cost_labels(gate) == ["-10 DAYS", "-5,000 BDT"]


def test_an_open_gate_has_no_labels():
    assert gate_requirement_labels(GateData()) == []
    assert gate_cost_labels(GateData()) == []


# ── NewZonePopup ─────────────────────────────────────────────


def test_new_zone_popup_slugifies_and_returns_the_rect():
    popup = NewZonePopup((3, 4, 5, 6), "Lab Block")
    popup.render(popup_surface())
    assert popup.get_rect_cells() == (3, 4, 5, 6)
    popup.on_button("ok")
    assert popup.get_result()["zone_id"] == "lab_block"


def test_new_zone_popup_cancel():
    popup = NewZonePopup((0, 0, 2, 2))
    popup.on_button(CANCEL)
    assert popup.get_result() == CANCEL


def test_new_zone_popup_blank_id_falls_back():
    popup = NewZonePopup((0, 0, 2, 2), "")
    popup.on_button("ok")
    assert popup.get_result()["zone_id"]


# ── zone create / resize / delete through the app ────────────


def test_dragging_on_the_zones_tab_opens_the_new_zone_popup(app):
    press(app, pygame.K_4)
    start, end = cell_pair(app, (4, 4), (7, 6))
    drag(app, start, end)
    assert isinstance(app.get_active_modal(), NewZonePopup)
    assert app.get_active_modal().get_rect_cells() == (4, 4, 4, 3)


def test_a_backwards_drag_is_normalised(app):
    press(app, pygame.K_4)
    end, start = cell_pair(app, (4, 4), (7, 6))
    drag(app, start, end)
    assert app.get_active_modal().get_rect_cells() == (4, 4, 4, 3)


def test_naming_a_zone_creates_it_and_chains_into_the_gate_form(app):
    press(app, pygame.K_4)
    before = app.get_level().get_zone_count()
    drag(app, *cell_pair(app, (4, 4), (7, 6)))

    modal = app.get_active_modal()
    modal.on_button("ok")
    app.update(1 / 60)                       # consumes the finished popup

    level = app.get_level()
    assert level.get_zone_count() == before + 1
    assert level.get_zone_at(5, 5) is not None
    assert app.is_dirty() is True
    # naming chains straight into the gate form
    assert isinstance(app.get_active_modal(), GatePopup)


def test_cancelling_the_name_creates_nothing(app):
    press(app, pygame.K_4)
    before = app.get_level().get_zone_count()
    drag(app, *cell_pair(app, (4, 4), (7, 6)))
    app.get_active_modal().on_button(CANCEL)
    app.update(1 / 60)
    assert app.get_level().get_zone_count() == before
    assert app.get_active_modal() is None


def test_the_chained_gate_lands_on_the_new_zone(app):
    press(app, pygame.K_4)
    drag(app, *cell_pair(app, (4, 4), (7, 6)))
    app.get_active_modal().on_button("ok")
    app.update(1 / 60)

    gate_popup = app.get_active_modal()
    wanted = GateData()
    wanted.set_min_semester(6)
    wanted.set_locked_lines(["Closed to first years."])
    gate_popup.load(wanted)
    gate_popup.on_button("ok")
    app.update(1 / 60)

    zone = app.get_level().get_zone_at(5, 5)
    assert zone.get_gate().get_min_semester() == 6
    assert zone.is_gated() is True


def test_zone_resize_through_set_rect(app):
    zone = app.get_level().add_zone(2, 2, 3, 3)
    assert zone.get_rect() == (2, 2, 3, 3)
    assert zone.set_rect(2, 2, 8, 5) is True
    assert zone.get_rect() == (2, 2, 8, 5)
    assert zone.contains(9, 6) is True
    assert zone.set_rect(2, 2, 0, 5) is False       # refused, unchanged
    assert zone.get_rect() == (2, 2, 8, 5)
    app.render()


def test_selecting_and_deleting_a_zone_from_the_panel(app):
    press(app, pygame.K_4)
    zone = app.get_level().add_zone(2, 2, 3, 3)
    app.render()

    rows = app._LevelEditorApp__zone_row_rects()
    click(app, rows[0].center)
    assert app._LevelEditorApp__zone_selected == zone.get_uid()

    app.render()
    click(app, app._LevelEditorApp__zone_delete_rect().center)
    assert app.get_level().get_zone_count() == 0
    assert app.is_dirty() is True


def test_deleting_a_zone_is_one_undo_step(app):
    press(app, pygame.K_4)
    app.get_level().add_zone(2, 2, 3, 3)
    app.render()
    click(app, app._LevelEditorApp__zone_row_rects()[0].center)
    app.render()
    click(app, app._LevelEditorApp__zone_delete_rect().center)
    assert app.get_level().get_zone_count() == 0

    press(app, pygame.K_z, pygame.KMOD_CTRL)
    assert app.get_level().get_zone_count() == 1


def test_clicking_inside_an_existing_zone_selects_it(app):
    press(app, pygame.K_4)
    zone = app.get_level().add_zone(4, 4, 5, 5)
    app.render()
    drag(app, cell_pos(app, 5, 5), cell_pos(app, 5, 5))
    # selects rather than starting an overlapping zone
    assert app._LevelEditorApp__zone_selected == zone.get_uid()
    assert app.get_active_modal() is None
    assert app.get_level().get_zone_count() == 1


# ── gating props and NPCs from the ZONES tab ─────────────────


def test_right_click_gates_a_prop(app):
    press(app, pygame.K_4)
    prop = app.get_level().get_props()[0]
    x, y = prop.get_position()
    click(app, cell_pos(app, x, y), button=3)

    popup = app.get_active_modal()
    assert isinstance(popup, GatePopup)
    wanted = GateData()
    wanted.set_min_semester(4)
    wanted.set_locked_lines(["Blocked."])
    popup.load(wanted)
    popup.on_button("ok")
    app.update(1 / 60)

    assert app.get_level().get_props()[0].is_gated() is True
    assert app.get_level().get_props()[0].get_gate().get_min_semester() == 4


def test_right_click_gates_an_npc_seeded_from_the_roster(app):
    press(app, pygame.K_4)
    npc = next(n for n in app.get_level().get_npcs()
               if n.get_type_id() == "hoque")
    x, y = npc.get_position()
    click(app, cell_pos(app, x, y), button=3)

    popup = app.get_active_modal()
    assert isinstance(popup, GatePopup)
    # hoque is available from semester 5 in content/npc_roster.py
    assert popup.get_gate().get_min_semester() == 5


def test_right_click_on_empty_ground_gates_nothing(app):
    press(app, pygame.K_4)
    click(app, cell_pos(app, 1, 1), button=3)
    assert app.get_active_modal() is None


def test_gating_is_one_undo_step(app):
    press(app, pygame.K_4)
    prop = app.get_level().get_props()[0]
    x, y = prop.get_position()
    click(app, cell_pos(app, x, y), button=3)
    popup = app.get_active_modal()
    wanted = GateData()
    wanted.set_min_semester(4)
    popup.load(wanted)
    popup.on_button("ok")
    app.update(1 / 60)
    assert app.get_level().get_props()[0].is_gated() is True

    press(app, pygame.K_z, pygame.KMOD_CTRL)
    assert app.get_level().get_props()[0].is_gated() is False


# ── the fixture survives all of this ─────────────────────────


def test_gated_level_still_saves(scratch_app):
    editor, levels_dir = scratch_app
    zone = editor.get_level().add_zone(2, 2, 4, 4)
    zone.get_gate().set_min_semester(5)
    zone.get_gate().set_locked_lines(["Closed."])
    editor.get_level().get_props()[0].get_gate().set_min_credits(30)
    editor.get_level().get_props()[0].get_gate().set_locked_lines(["No."])

    press(editor, pygame.K_s, pygame.KMOD_CTRL)
    written = os.path.join(levels_dir, "campus_main.json")
    assert os.path.isfile(written)

    from content.level_schema import read_level
    reloaded = read_level(written)
    assert reloaded.get_zone_count() == 1
    assert reloaded.get_zone_at(3, 3).get_gate().get_min_semester() == 5
    assert reloaded.get_props()[0].get_gate().get_min_credits() == 30


def test_an_ungated_fixture_still_writes_byte_identical(scratch_app):
    """
    The F5 acceptance property, re-checked through the EDITOR: opening
    and saving the shipped fixture with no edits must not introduce a
    gate or zone key.
    """
    editor, levels_dir = scratch_app
    press(editor, pygame.K_s, pygame.KMOD_CTRL)
    written = os.path.join(levels_dir, "campus_main.json")
    assert open(written, "rb").read() == open(FIXTURE, "rb").read()


def test_load_pushes_a_gate_into_the_controls():
    """
    load() is the mirror of the commit, and the ONLY way to prefill the
    form. Mutating the object get_gate() returns does not reach the
    widgets, so OK would discard it -- that was a real bug during F6.
    """
    popup = GatePopup(GateData(), "zone_0001")

    stray = popup.get_gate()
    stray.set_min_semester(9)                 # direct mutation: ignored
    popup.on_button("ok")
    assert popup.get_result() == {}

    wanted = GateData()
    wanted.set_min_semester(9)
    wanted.set_locked_lines(["Closed."])
    loaded = GatePopup(GateData(), "zone_0001")
    loaded.load(wanted)                        # through the controls: kept
    loaded.on_button("ok")
    assert GateData.from_dict(loaded.get_result()).to_dict() ==         wanted.to_dict()


def test_load_round_trips_every_field():
    """Every control survives a load -> commit cycle unchanged."""
    wanted = GateData()
    wanted.set_min_semester(11)
    wanted.set_min_credits(120)
    wanted.set_min_days_remaining(40)
    wanted.set_min_wallet(50000.0)
    wanted.set_required_skill_id(reg.SKILL_IDS[4])
    wanted.set_required_skill_level(7)
    wanted.set_required_course_codes("cse101, phy101")
    wanted.set_requires_graduated(True)
    wanted.set_cost_days(25)
    wanted.set_cost_money(1500.0)
    wanted.set_locked_title("restricted wing")
    wanted.set_locked_lines(["Staff only.", "Come back later."])

    popup = GatePopup(GateData(), "prop_0001")
    popup.load(wanted)
    popup.render(popup_surface())
    popup.on_button("ok")
    assert GateData.from_dict(popup.get_result()).to_dict() == wanted.to_dict()


def test_every_tab_has_a_button(app):
    """
    The ported __tab_rects() hard-coded four tabs, so adding ZONES left
    SETTINGS clickable only by hotkey. Caught by a screenshot, pinned
    here.
    """
    app.render()
    rects = app._LevelEditorApp__tab_rects()
    assert len(rects) == len(TAB_NAMES)
    for index, rect in enumerate(rects):
        assert SIDE_PANEL.contains(rect), f"tab {TAB_NAMES[index]} is off-panel"
    for i, first in enumerate(rects):
        for second in rects[i + 1:]:
            assert not first.colliderect(second), "tab buttons overlap"


def test_clicking_every_tab_selects_it(app):
    app.render()
    for index, rect in enumerate(app._LevelEditorApp__tab_rects()):
        click(app, rect.center)
        assert app._LevelEditorApp__tab == index, TAB_NAMES[index]
        app.render()


def test_the_tab_row_clears_the_section_below_it(app):
    """SECTION_Y must sit under the last tab row, not on top of it."""
    from tools.level_editor import SECTION_Y
    lowest = max(rect.bottom for rect in app._LevelEditorApp__tab_rects())
    assert SECTION_Y >= lowest

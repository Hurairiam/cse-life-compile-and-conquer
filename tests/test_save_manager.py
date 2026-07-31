"""
tests/test_save_manager.py
CSE Life: Compile & Conquer — phase F4
─────────────────────────────────────────────────────────────
Guards the save system. A save bug costs a player their whole
playthrough, so the interesting cases here are the ugly ones:
corrupt files, half-written files, files from a future build,
and state dicts holding things that will not serialise.

The rule the whole module is built around: NOTHING RAISES.
Every failure is a False or a None with a reason.

Every test runs against a pytest tmp_path, never the project's
real saves/ directory.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os

import pytest

from engine.save_manager import (AUTOSAVE_SLOT_ID, SAVE_SCHEMA_VERSION,
                                 SAVE_SLOTS, SLOT_IDS, SaveManager, SaveSlot,
                                 build_state, is_valid_slot_id,
                                 slot_filename, utc_timestamp)


@pytest.fixture
def manager(tmp_path):
    """A SaveManager pointed at a throwaway directory."""
    return SaveManager(str(tmp_path / "saves"))


@pytest.fixture
def state():
    """A representative, fully-populated state dict."""
    return build_state(
        display_name="Nangiba", character_id="student_01",
        wallet_balance=48200.0, accumulated_credits=84,
        current_semester=7, has_graduated=False,
        skills={"programming_language": 4, "dsa": 3},
        time_pool_days=46, registered_course_codes=["CSE101", "MAT120"],
        completed_course_codes=["CSE100"], backlog_course_codes=["PHY101"],
        level_id="campus_main", spawn_x=6, spawn_y=12,
        triggered_prop_uids=["prop_1"], talked_npc_uids=["npc_2"],
        global_career_clock_days=640, playtime_seconds=7325)


# ─────────────────────────────────────────────────────────────
# CONSTANTS AND HELPERS
# ─────────────────────────────────────────────────────────────


def test_slot_layout():
    """Three manual slots plus one autosave, in display order."""
    assert SAVE_SLOTS == 3
    assert SLOT_IDS == (1, 2, 3, AUTOSAVE_SLOT_ID)
    assert len(SLOT_IDS) == SAVE_SLOTS + 1


def test_slot_id_validation():
    """Only the four real slot ids are accepted."""
    for slot_id in SLOT_IDS:
        assert is_valid_slot_id(slot_id) is True
    for bad in (99, -1, 4, "1", 1.0, None, True):
        assert is_valid_slot_id(bad) is False, bad


def test_slot_filenames_are_distinct():
    """Every slot maps to its own file."""
    names = [slot_filename(slot_id) for slot_id in SLOT_IDS]
    assert len(set(names)) == len(names)
    assert slot_filename(AUTOSAVE_SLOT_ID) == "autosave.json"


def test_timestamp_is_iso_8601():
    """saved_at is ISO-8601 to the second."""
    stamp = utc_timestamp()
    assert "T" in stamp and len(stamp) >= 19
    from datetime import datetime
    assert isinstance(datetime.fromisoformat(stamp), datetime)


def test_constructing_a_manager_touches_no_disk(tmp_path):
    """The save directory is created lazily, not on construction."""
    target = tmp_path / "saves"
    SaveManager(str(target))
    assert not target.exists()


# ─────────────────────────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────────────────────────


def test_list_slots_always_returns_four(manager):
    """Four rows even with no directory at all."""
    slots = manager.list_slots()
    assert len(slots) == 4
    assert [s.get_slot_id() for s in slots] == list(SLOT_IDS)
    assert all(s.is_empty() for s in slots)
    assert [s.get_label() for s in slots] == \
        ["SLOT 1", "SLOT 2", "SLOT 3", "AUTOSAVE"]


def test_empty_slot_fields_are_neutral(manager):
    """Every getter is safe on an empty slot."""
    slot = manager.list_slots()[0]
    assert slot.is_empty() is True
    assert slot.is_corrupt() is False
    assert slot.get_player_name() == ""
    assert slot.get_semester() == 0
    assert slot.get_credits() == 0
    assert slot.get_wallet() == 0.0
    assert slot.get_days_remaining() == 0
    assert slot.get_level_id() == ""
    assert slot.get_playtime_seconds() == 0
    assert slot.get_saved_at() == ""
    assert slot.get_schema_version() == 0
    assert slot.get_payload() is None


def test_loading_an_empty_slot_returns_none(manager):
    """Nothing there is not an error."""
    assert manager.load(1) is None
    assert manager.slot_exists(1) is False


def test_autosave_slot_is_flagged(manager):
    """The autosave row identifies itself."""
    slots = manager.list_slots()
    assert slots[-1].is_autosave() is True
    assert all(not s.is_autosave() for s in slots[:-1])


# ─────────────────────────────────────────────────────────────
# ROUND TRIP
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("slot_id", SLOT_IDS)
def test_round_trip_every_slot(manager, state, slot_id):
    """What goes in comes back out, for all four slots."""
    assert manager.save(slot_id, state) is True
    loaded = manager.load(slot_id)
    assert loaded is not None
    for section in ("player", "semester", "academic", "world", "clock"):
        assert loaded[section] == state[section]
    assert loaded["playtime_seconds"] == state["playtime_seconds"]


def test_save_stamps_version_and_timestamp(manager, state):
    """The manager stamps these, so a caller cannot forget or fake them."""
    state["schema_version"] = 999
    state["saved_at"] = "not a timestamp"
    assert manager.save(1, state) is True
    loaded = manager.load(1)
    assert loaded["schema_version"] == SAVE_SCHEMA_VERSION
    assert loaded["saved_at"] != "not a timestamp"
    assert "T" in loaded["saved_at"]


def test_save_does_not_mutate_the_callers_dict(manager, state):
    """Saving must not rewrite the live game state behind the caller."""
    before = json.dumps(state, sort_keys=True)
    manager.save(1, state)
    assert json.dumps(state, sort_keys=True) == before


def test_saved_slot_summary_fields(manager, state):
    """SaveSlot reads the summary the load screen needs."""
    manager.save(2, state)
    slot = manager.get_slot(2)
    assert slot.is_empty() is False
    assert slot.get_player_name() == "Nangiba"
    assert slot.get_semester() == 7
    assert slot.get_credits() == 84
    assert slot.get_wallet() == 48200.0
    assert slot.get_days_remaining() == 46
    assert slot.get_level_id() == "campus_main"
    assert slot.get_playtime_seconds() == 7325
    assert slot.get_schema_version() == SAVE_SCHEMA_VERSION
    assert slot.get_saved_at() != ""


def test_autosave_writes_the_autosave_slot(manager, state):
    """autosave() is save() aimed at the autosave slot."""
    assert manager.autosave(state) is True
    assert manager.slot_exists(AUTOSAVE_SLOT_ID) is True
    assert manager.slot_exists(1) is False
    assert manager.list_slots()[-1].is_empty() is False


def test_overwrite_replaces_cleanly(manager, state):
    """Saving twice leaves one good file, not a merged one."""
    manager.save(1, state)
    second = build_state(display_name="Rafi", current_semester=2)
    assert manager.save(1, second) is True
    loaded = manager.load(1)
    assert loaded["player"]["display_name"] == "Rafi"
    assert loaded["player"]["accumulated_credits"] == 0


def test_only_primitives_are_written(manager, state):
    """The file is plain JSON -- no pickling, no object references."""
    manager.save(1, state)
    with open(manager.get_slot_path(1), encoding="utf-8") as handle:
        text = handle.read()
    assert "object" not in text
    reparsed = json.loads(text)
    assert isinstance(reparsed, dict)


# ─────────────────────────────────────────────────────────────
# REFUSALS — nothing raises
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_id", [99, -1, 4, "1", None, 1.5])
def test_invalid_slot_ids_are_refused(manager, state, bad_id):
    """Bad ids return False/None and record a reason."""
    assert manager.save(bad_id, state) is False
    assert manager.get_last_error() != ""
    assert manager.load(bad_id) is None
    assert manager.delete(bad_id) is False
    assert manager.slot_exists(bad_id) is False
    assert manager.get_slot(bad_id) is None


@pytest.mark.parametrize("bad_state", ["nope", 42, None, ["a"], object()])
def test_non_dict_state_is_refused(manager, bad_state):
    """Only a dict can be a save."""
    assert manager.save(1, bad_state) is False
    assert "dict" in manager.get_last_error()
    assert manager.slot_exists(1) is False


def test_unserialisable_state_writes_nothing(manager, state):
    """
    A state dict holding a live object fails BEFORE any file is touched.

    This is why save() serialises to a string first: otherwise a bad
    field would leave a half-written temp file behind.
    """
    state["player"]["oops"] = object()
    assert manager.save(1, state) is False
    assert "serialis" in manager.get_last_error()
    assert manager.slot_exists(1) is False
    assert not os.path.exists(manager.get_slot_path(1) + ".tmp")


def test_deleting_an_empty_slot_returns_false(manager):
    """Nothing to delete is reported, not silently swallowed."""
    assert manager.delete(1) is False
    assert manager.get_last_error() != ""


# ─────────────────────────────────────────────────────────────
# CORRUPTION AND VERSIONING
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("junk", [
    "{ this is not json",
    "",
    "[1, 2, 3]",
    "null",
    '{"schema_version": "banana"}',
    "\x00\x01\x02",
])
def test_corrupt_files_load_as_none(manager, junk):
    """Every flavour of broken file degrades to None with a reason."""
    os.makedirs(manager.get_save_dir(), exist_ok=True)
    with open(manager.get_slot_path(1), "w", encoding="utf-8") as handle:
        handle.write(junk)
    assert manager.load(1) is None
    assert manager.get_last_error() != ""


def test_corrupt_slot_reports_itself_in_the_listing(manager):
    """A broken file must not break the whole four-row listing."""
    os.makedirs(manager.get_save_dir(), exist_ok=True)
    with open(manager.get_slot_path(2), "w", encoding="utf-8") as handle:
        handle.write("{ broken")
    slots = manager.list_slots()
    assert len(slots) == 4
    assert slots[1].is_empty() is True
    assert slots[1].is_corrupt() is True
    assert slots[1].get_error() != ""
    # and it does not contaminate its neighbours
    assert slots[0].is_corrupt() is False
    assert slots[2].is_corrupt() is False


def test_partial_json_is_refused(manager, state):
    """A file truncated mid-write is not half-loaded."""
    manager.save(1, state)
    with open(manager.get_slot_path(1), encoding="utf-8") as handle:
        text = handle.read()
    with open(manager.get_slot_path(1), "w", encoding="utf-8") as handle:
        handle.write(text[:len(text) // 2])
    assert manager.load(1) is None
    assert manager.get_last_error() != ""


def test_future_schema_version_is_refused(manager, state):
    """A save from a newer build loads as None, with the reason recorded."""
    manager.save(1, state)
    payload = json.loads(open(manager.get_slot_path(1),
                              encoding="utf-8").read())
    payload["schema_version"] = SAVE_SCHEMA_VERSION + 1
    with open(manager.get_slot_path(1), "w", encoding="utf-8") as handle:
        json.dump(payload, handle)

    assert manager.load(1) is None
    error = manager.get_last_error()
    assert "newer version" in error
    assert str(SAVE_SCHEMA_VERSION + 1) in error


def test_older_schema_version_still_loads(manager, state):
    """Forward compatibility only refuses the future, not the past."""
    manager.save(1, state)
    payload = json.loads(open(manager.get_slot_path(1),
                              encoding="utf-8").read())
    payload["schema_version"] = 0
    with open(manager.get_slot_path(1), "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    assert manager.load(1) is not None


def test_missing_sections_do_not_crash_the_summary(manager):
    """A save missing whole blocks still lists, with neutral defaults."""
    os.makedirs(manager.get_save_dir(), exist_ok=True)
    with open(manager.get_slot_path(1), "w", encoding="utf-8") as handle:
        json.dump({"schema_version": 1, "saved_at": "2026-07-31T00:00:00"},
                  handle)
    slot = manager.get_slot(1)
    assert slot.is_empty() is False
    assert slot.get_player_name() == ""
    assert slot.get_semester() == 0
    assert slot.get_days_remaining() == 0
    assert slot.get_wallet() == 0.0


def test_wrong_typed_fields_do_not_crash_the_summary(manager):
    """Hand-edited nonsense in a field falls back instead of raising."""
    os.makedirs(manager.get_save_dir(), exist_ok=True)
    with open(manager.get_slot_path(1), "w", encoding="utf-8") as handle:
        json.dump({"schema_version": 1,
                   "playtime_seconds": "lots",
                   "player": {"current_semester": "seven",
                              "wallet_balance": None,
                              "accumulated_credits": []},
                   "semester": "not a dict"}, handle)
    slot = manager.get_slot(1)
    assert slot.get_semester() == 0
    assert slot.get_wallet() == 0.0
    assert slot.get_credits() == 0
    assert slot.get_days_remaining() == 0
    assert slot.get_playtime_seconds() == 0


# ─────────────────────────────────────────────────────────────
# ATOMIC WRITES
# ─────────────────────────────────────────────────────────────


def test_no_temp_file_survives_a_successful_save(manager, state):
    """The temp file is renamed away, not left behind."""
    manager.save(1, state)
    assert os.path.isfile(manager.get_slot_path(1))
    assert not os.path.exists(manager.get_slot_path(1) + ".tmp")


def test_a_crash_mid_save_cannot_destroy_the_existing_save(manager, state):
    """
    Simulate a crash: leave a stale temp file next to a good save, then
    load. The real file must be untouched and still readable -- that is
    the whole point of writing to <file>.tmp and os.replace()ing.
    """
    manager.save(1, state)
    with open(manager.get_slot_path(1) + ".tmp", "w",
              encoding="utf-8") as handle:
        handle.write("{ half written")

    loaded = manager.load(1)
    assert loaded is not None
    assert loaded["player"]["display_name"] == "Nangiba"


def test_delete_clears_a_stale_temp_file(manager, state):
    """Deleting a slot tidies its leftovers too."""
    manager.save(1, state)
    tmp = manager.get_slot_path(1) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write("junk")
    assert manager.delete(1) is True
    assert not os.path.exists(tmp)
    assert not os.path.exists(manager.get_slot_path(1))


def test_delete_only_affects_its_own_slot(manager, state):
    """Deleting slot 1 leaves the others alone."""
    for slot_id in SLOT_IDS:
        manager.save(slot_id, state)
    assert manager.delete(1) is True
    assert manager.slot_exists(1) is False
    for slot_id in (2, 3, AUTOSAVE_SLOT_ID):
        assert manager.slot_exists(slot_id) is True


# ─────────────────────────────────────────────────────────────
# THE STATE CONTRACT
# ─────────────────────────────────────────────────────────────


def test_build_state_has_every_documented_key():
    """The state shape documented in PHASELOG_F4 is what build_state emits."""
    state = build_state()
    assert set(state) == {"schema_version", "saved_at", "playtime_seconds",
                          "player", "semester", "academic", "world", "clock"}
    assert set(state["player"]) == {
        "display_name", "character_id", "wallet_balance",
        "accumulated_credits", "current_semester", "has_graduated", "skills"}
    assert set(state["semester"]) == {"number", "time_pool_days",
                                      "registered_course_codes"}
    assert set(state["academic"]) == {"completed_course_codes",
                                      "backlog_course_codes"}
    assert set(state["world"]) == {"level_id", "spawn_x", "spawn_y",
                                   "triggered_prop_uids", "talked_npc_uids"}
    assert set(state["clock"]) == {"global_career_clock_days"}


def test_build_state_is_json_serialisable():
    """Whatever build_state produces can always be written."""
    json.dumps(build_state())


def test_save_manager_imports_no_pygame():
    """
    engine/save_manager.py is a pure-Python layer (Build Plan §0.7).

    The full layer-purity guard arrives in F5; this is the local one, so
    the rule is enforced from the moment the file exists.
    """
    import engine.save_manager as module

    source = open(module.__file__, encoding="utf-8").read()
    assert "import pygame" not in source
    assert "from pygame" not in source

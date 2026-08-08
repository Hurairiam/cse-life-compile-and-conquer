"""
engine/save_manager.py
CSE Life: Compile & Conquer — Save system, phase F4
─────────────────────────────────────────────────────────────
Three manual save slots plus one autosave, stored as plain JSON
under saves/.

PURE PYTHON. No pygame, no ui/ import, no game logic. This file
does not know what a Player is and never will -- it moves a
dictionary of primitives to disk and back. The lead rehydrates
real objects at integration; that separation is deliberate and
is what stops a save file from breaking every time a class
gains a field.

NOTHING HERE RAISES. A missing directory, a corrupt file, a
half-written file, a save from a newer build, a state dict full
of objects that will not serialise -- all of them return False
or None and record a reason in get_last_error(). A save system
that throws is a save system that loses a playthrough.

ATOMIC WRITES. Every save serialises to <file>.tmp and then
os.replace()s it over the real file, which is atomic on POSIX
and on Windows. A crash mid-write can destroy the temp file but
never the existing save.

Created by: Nangiba Tasnim (Dev 3).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────
# Anchored to this file, never to the working directory, so the game
# and the tools read the same saves whatever launched them.
# ─────────────────────────────────────────────────────────────

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SAVE_DIR: str = "saves"
SAVE_SCHEMA_VERSION: int = 1

SAVE_SLOTS: int = 3                 # manual slots, numbered 1..3
AUTOSAVE_SLOT_ID: int = 0           # the autosave is slot 0

# Canonical display order: the three manual slots, then the autosave.
SLOT_IDS: tuple = (1, 2, 3, AUTOSAVE_SLOT_ID)

SLOT_LABELS: Dict[int, str] = {
    1: "SLOT 1",
    2: "SLOT 2",
    3: "SLOT 3",
    AUTOSAVE_SLOT_ID: "AUTOSAVE",
}

TMP_SUFFIX: str = ".tmp"


def slot_filename(slot_id: int) -> str:
    """The bare filename for a slot, autosave included."""
    if slot_id == AUTOSAVE_SLOT_ID:
        return "autosave.json"
    return f"slot_{int(slot_id)}.json"


def is_valid_slot_id(slot_id: Any) -> bool:
    """True for 1..SAVE_SLOTS and for the autosave id."""
    return isinstance(slot_id, int) and not isinstance(slot_id, bool) \
        and slot_id in SLOT_IDS


def utc_timestamp() -> str:
    """The current time as an ISO-8601 string, to the second."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SaveSlot:
    """
    A read-only view of one slot, whether or not anything is in it.

    list_slots() always returns four of these, so a caller never has to
    reason about missing files -- an empty slot is a SaveSlot that
    reports is_empty() and hands back neutral defaults for every field.
    """

    def __init__(self, slot_id: int, payload: Optional[Dict[str, Any]] = None,
                 error: str = "") -> None:
        """Wrap a slot id and, when there is one, its loaded payload."""
        self.__slot_id: int = slot_id
        self.__payload: Optional[Dict[str, Any]] = payload
        self.__error: str = error

    # -- identity ---------------------------------------------
    def get_slot_id(self) -> int:
        """The slot number; AUTOSAVE_SLOT_ID for the autosave."""
        return self.__slot_id

    def get_label(self) -> str:
        """The ALL-CAPS row label: SLOT 1..3 or AUTOSAVE."""
        return SLOT_LABELS.get(self.__slot_id, f"SLOT {self.__slot_id}")

    def is_autosave(self) -> bool:
        """True for the autosave slot."""
        return self.__slot_id == AUTOSAVE_SLOT_ID

    def is_empty(self) -> bool:
        """
        True when there is nothing loadable here.

        A corrupt or future-version file also reports empty, because
        that is what it is worth to the player. is_corrupt() and
        get_error() tell the difference when a caller cares.
        """
        return self.__payload is None

    def is_corrupt(self) -> bool:
        """True when a file exists but could not be read."""
        return self.__payload is None and bool(self.__error)

    def get_error(self) -> str:
        """Why this slot failed to load, or "" if it did not fail."""
        return self.__error

    # -- summary fields (all safe on an empty slot) -----------
    def __field(self, key: str, default: Any) -> Any:
        """Read one top-level or nested summary field, with a default."""
        if self.__payload is None:
            return default
        value = self.__payload.get(key, default)
        return default if value is None else value

    def __player_field(self, key: str, default: Any) -> Any:
        """Read a field out of the payload's player block."""
        if self.__payload is None:
            return default
        player = self.__payload.get("player")
        if not isinstance(player, dict):
            return default
        value = player.get(key, default)
        return default if value is None else value

    def __section_field(self, section: str, key: str, default: Any) -> Any:
        """Read a field out of any named block of the payload."""
        if self.__payload is None:
            return default
        block = self.__payload.get(section)
        if not isinstance(block, dict):
            return default
        value = block.get(key, default)
        return default if value is None else value

    def get_player_name(self) -> str:
        """The saved display name, or "" when empty."""
        return str(self.__player_field("display_name", ""))

    def get_semester(self) -> int:
        """The saved semester number, or 0 when empty."""
        try:
            return int(self.__player_field("current_semester", 0))
        except (TypeError, ValueError):
            return 0

    def get_credits(self) -> int:
        """Accumulated credits, or 0 when empty."""
        try:
            return int(self.__player_field("accumulated_credits", 0))
        except (TypeError, ValueError):
            return 0

    def get_wallet(self) -> float:
        """Wallet balance in BDT, or 0.0 when empty."""
        try:
            return float(self.__player_field("wallet_balance", 0.0))
        except (TypeError, ValueError):
            return 0.0

    def get_days_remaining(self) -> int:
        """Days left in the semester's time pool, or 0 when empty."""
        try:
            return int(self.__section_field("semester", "time_pool_days", 0))
        except (TypeError, ValueError):
            return 0

    def get_level_id(self) -> str:
        """The level the player was standing in, or "" when empty."""
        return str(self.__section_field("world", "level_id", ""))

    def get_playtime_seconds(self) -> int:
        """Seconds played, or 0 when empty."""
        try:
            return int(self.__field("playtime_seconds", 0))
        except (TypeError, ValueError):
            return 0

    def get_saved_at(self) -> str:
        """The ISO-8601 save timestamp, or "" when empty."""
        return str(self.__field("saved_at", ""))

    def get_schema_version(self) -> int:
        """The schema version the file was written with, or 0."""
        try:
            return int(self.__field("schema_version", 0))
        except (TypeError, ValueError):
            return 0

    def get_payload(self) -> Optional[Dict[str, Any]]:
        """A copy of the whole loaded state, or None when empty."""
        return dict(self.__payload) if self.__payload is not None else None


class SaveManager:
    """
    Reads and writes the four save files.

    The directory is created lazily -- constructing a SaveManager never
    touches the disk, so a test, a tool or a screen can build one
    freely. Nothing is written until something is actually saved.
    """

    def __init__(self, save_dir: Optional[str] = None) -> None:
        """
        Point the manager at a save directory.

        `save_dir` defaults to <project root>/saves. It is injectable so
        tests can run against a temporary directory and never write into
        the repository.
        """
        if save_dir is None:
            self.__dir: str = os.path.join(PROJECT_ROOT, SAVE_DIR)
        else:
            self.__dir = str(save_dir)
        self.__last_error: str = ""

    # -- paths ------------------------------------------------
    def get_save_dir(self) -> str:
        """The absolute directory the four save files live in."""
        return self.__dir

    def get_slot_path(self, slot_id: int) -> str:
        """The absolute path of one slot's file."""
        return os.path.join(self.__dir, slot_filename(slot_id))

    def get_last_error(self) -> str:
        """Why the last operation returned False or None, or ""."""
        return self.__last_error

    def __ensure_dir(self) -> bool:
        """Create the save directory if it is not there yet."""
        try:
            os.makedirs(self.__dir, exist_ok=True)
            return True
        except OSError as error:
            self.__last_error = f"cannot create {self.__dir}: {error}"
            return False

    # -- queries ----------------------------------------------
    def slot_exists(self, slot_id: int) -> bool:
        """True when a file is present for this slot."""
        if not is_valid_slot_id(slot_id):
            return False
        return os.path.isfile(self.get_slot_path(slot_id))

    def list_slots(self) -> List[SaveSlot]:
        """
        Every slot in display order: SLOT 1, 2, 3, then AUTOSAVE.

        Always four entries. Empty, corrupt and future-version slots are
        all represented rather than omitted, so the load screen can draw
        a stable four-row table without any None handling.
        """
        slots: List[SaveSlot] = []
        for slot_id in SLOT_IDS:
            payload, error = self.__read_slot(slot_id)
            slots.append(SaveSlot(slot_id, payload, error))
        return slots

    def get_slot(self, slot_id: int) -> Optional[SaveSlot]:
        """One slot's view, or None for an invalid slot id."""
        if not is_valid_slot_id(slot_id):
            self.__last_error = f"invalid slot id: {slot_id!r}"
            return None
        payload, error = self.__read_slot(slot_id)
        return SaveSlot(slot_id, payload, error)

    # -- reading ----------------------------------------------
    def load(self, slot_id: int) -> Optional[Dict[str, Any]]:
        """
        Read one slot's state dict, or None.

        None means: invalid slot id, no file, unreadable file, JSON that
        is not an object, or a file written by a newer build. The reason
        is always in get_last_error().
        """
        if not is_valid_slot_id(slot_id):
            self.__last_error = f"invalid slot id: {slot_id!r}"
            return None
        payload, error = self.__read_slot(slot_id)
        self.__last_error = error
        return payload

    def __read_slot(self, slot_id: int) -> tuple:
        """
        (payload, error) for one slot. Never raises.

        Kept separate from load() so list_slots() can read all four
        without stamping over each other's error strings.
        """
        path = self.get_slot_path(slot_id)
        if not os.path.isfile(path):
            return (None, "")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError, UnicodeDecodeError) as error:
            # Truncated, empty or hand-edited files all land here.
            return (None, f"{slot_filename(slot_id)} is unreadable: {error}")

        if not isinstance(payload, dict):
            return (None, f"{slot_filename(slot_id)} is not a save object")

        version = payload.get("schema_version", 0)
        try:
            version = int(version)
        except (TypeError, ValueError):
            return (None, f"{slot_filename(slot_id)} has no usable "
                          f"schema_version")
        if version > SAVE_SCHEMA_VERSION:
            # Refusing is the safe move: a newer build may have changed
            # what a field means, and guessing corrupts a real save.
            return (None, f"{slot_filename(slot_id)} was written by a newer "
                          f"version (schema {version} > "
                          f"{SAVE_SCHEMA_VERSION})")
        return (payload, "")

    # -- writing ----------------------------------------------
    def save(self, slot_id: int, state: Dict[str, Any]) -> bool:
        """
        Write a state dict to a slot, atomically.

        `schema_version` and `saved_at` are stamped here rather than
        trusted from the caller, so neither can be forgotten or faked.
        The caller's dict is not mutated. Returns False on any problem,
        with the reason in get_last_error().
        """
        if not is_valid_slot_id(slot_id):
            self.__last_error = f"invalid slot id: {slot_id!r}"
            return False
        if not isinstance(state, dict):
            self.__last_error = "state must be a dict of primitives"
            return False
        if not self.__ensure_dir():
            return False

        payload = dict(state)
        payload["schema_version"] = SAVE_SCHEMA_VERSION
        payload["saved_at"] = utc_timestamp()
        payload.setdefault("playtime_seconds", 0)

        path = self.get_slot_path(slot_id)
        tmp_path = path + TMP_SUFFIX
        try:
            # Serialise to a string FIRST. A state dict holding an
            # object that will not serialise then fails before the temp
            # file is touched, instead of leaving a half-written one.
            text = json.dumps(payload, indent=2, sort_keys=True,
                              ensure_ascii=False)
        except (TypeError, ValueError) as error:
            self.__last_error = f"state is not JSON-serialisable: {error}"
            return False

        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        except OSError as error:
            self.__last_error = f"cannot write {path}: {error}"
            self.__discard(tmp_path)
            return False

        self.__last_error = ""
        return True

    def autosave(self, state: Dict[str, Any]) -> bool:
        """Write to the autosave slot. Same rules as save()."""
        return self.save(AUTOSAVE_SLOT_ID, state)

    def delete(self, slot_id: int) -> bool:
        """
        Remove a slot's file.

        Returns False for an invalid id or a slot that was already
        empty, so a caller can tell "deleted" from "there was nothing
        to delete". A stray temp file is cleared too.
        """
        if not is_valid_slot_id(slot_id):
            self.__last_error = f"invalid slot id: {slot_id!r}"
            return False
        path = self.get_slot_path(slot_id)
        self.__discard(path + TMP_SUFFIX)
        if not os.path.isfile(path):
            self.__last_error = f"{slot_filename(slot_id)} does not exist"
            return False
        try:
            os.remove(path)
        except OSError as error:
            self.__last_error = f"cannot delete {path}: {error}"
            return False
        self.__last_error = ""
        return True

    def __discard(self, path: str) -> None:
        """Delete a file if it is there, ignoring every failure."""
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass


def build_state(display_name: str = "", character_id: str = "",
                wallet_balance: float = 0.0, accumulated_credits: int = 0,
                current_semester: int = 1, has_graduated: bool = False,
                skills: Optional[Dict[str, int]] = None,
                time_pool_days: int = 80,
                registered_course_codes: Optional[List[str]] = None,
                completed_course_codes: Optional[List[str]] = None,
                backlog_course_codes: Optional[List[str]] = None,
                level_id: str = "", spawn_x: int = 0, spawn_y: int = 0,
                triggered_prop_uids: Optional[List[str]] = None,
                talked_npc_uids: Optional[List[str]] = None,
                dialogue_choices: Optional[Dict[str, int]] = None,
                return_positions: Optional[Dict[str, List[int]]] = None,
                global_career_clock_days: int = 0,
                playtime_seconds: int = 0) -> Dict[str, Any]:
    """
    Build a state dict in the documented shape, with every key present.

    This is a convenience for callers and for tests -- save() accepts any
    dict of primitives. Keeping the canonical shape in one function means
    the integration contract has a single executable definition rather
    than only a paragraph in a PHASELOG.
    """
    return {
        "schema_version": SAVE_SCHEMA_VERSION,
        "saved_at": "",
        "playtime_seconds": int(playtime_seconds),
        "player": {
            "display_name": display_name,
            "character_id": character_id,
            "wallet_balance": float(wallet_balance),
            "accumulated_credits": int(accumulated_credits),
            "current_semester": int(current_semester),
            "has_graduated": bool(has_graduated),
            "skills": dict(skills or {}),
        },
        "semester": {
            "number": int(current_semester),
            "time_pool_days": int(time_pool_days),
            "registered_course_codes": list(registered_course_codes or []),
        },
        "academic": {
            "completed_course_codes": list(completed_course_codes or []),
            "backlog_course_codes": list(backlog_course_codes or []),
        },
        "world": {
            "level_id": level_id,
            "spawn_x": int(spawn_x),
            "spawn_y": int(spawn_y),
            "triggered_prop_uids": list(triggered_prop_uids or []),
            "talked_npc_uids": list(talked_npc_uids or []),
            # Replies the player gave to branching dialogue, keyed
            # "<level>:<npc uid>:<chain id>". Absent from any save
            # written before branches existed, which loads as {}.
            "dialogue_choices": dict(dialogue_choices or {}),
            # Where the player was standing in each area when they last
            # left it, "<level_id>": [landing_x, landing_y, stood_x,
            # stood_y]. Additive in exactly the way dialogue_choices
            # above is: a save written without it loads as {} and every
            # area opens at its SET SPAWN cell, so SAVE_SCHEMA_VERSION
            # stays where it is.
            "return_positions": dict(return_positions or {}),
        },
        "clock": {
            "global_career_clock_days": int(global_career_clock_days),
        },
    }


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
# No pygame here: this layer is pure Python, so its stub is a
# console round-trip rather than a screen.
#
# It writes into a throwaway temporary directory, NEVER into the
# real saves/ folder, so running it can never touch a playthrough.
# -------------------------------------------------------------
if __name__ == "__main__":
    import shutil
    import tempfile

    workspace = tempfile.mkdtemp(prefix="cse_life_saves_")
    manager = SaveManager(workspace)
    print(f"save dir: {manager.get_save_dir()}\n")

    print("-- empty to begin with --")
    for slot in manager.list_slots():
        print(f"  {slot.get_label():9s} empty={slot.is_empty()}")

    print("\n-- writing slot 1 and the autosave --")
    state = build_state(display_name="Nangiba", character_id="student_01",
                        wallet_balance=48200.0, accumulated_credits=84,
                        current_semester=7, time_pool_days=46,
                        skills={"programming_language": 4, "dsa": 3},
                        registered_course_codes=["CSE101", "MAT120"],
                        completed_course_codes=["CSE100"],
                        level_id="campus_main", spawn_x=6, spawn_y=12,
                        global_career_clock_days=640, playtime_seconds=7325)
    print(f"  save(1)   -> {manager.save(1, state)}")
    print(f"  autosave  -> {manager.autosave(state)}")

    print("\n-- listing --")
    for slot in manager.list_slots():
        if slot.is_empty():
            print(f"  {slot.get_label():9s} EMPTY SLOT")
        else:
            print(f"  {slot.get_label():9s} {slot.get_player_name()} · "
                  f"Sem {slot.get_semester()} · "
                  f"{slot.get_credits()}/140 cr · "
                  f"{slot.get_days_remaining()}/80 d · "
                  f"{slot.get_wallet():,.0f} BDT · "
                  f"saved {slot.get_saved_at()}")

    print("\n-- round trip --")
    loaded = manager.load(1)
    print(f"  identical player block: "
          f"{loaded is not None and loaded['player'] == state['player']}")
    print(f"  schema stamped: {loaded['schema_version']}")
    print(f"  timestamp stamped: {bool(loaded['saved_at'])}")

    print("\n-- refusing bad input, never raising --")
    print(f"  save(99, ...)        -> {manager.save(99, state)}   "
          f"({manager.get_last_error()})")
    print(f"  save(2, 'not a dict')-> {manager.save(2, 'nope')}   "
          f"({manager.get_last_error()})")
    print(f"  save(2, {{unserialisable}}) -> "
          f"{manager.save(2, {'obj': object()})}   "
          f"({manager.get_last_error()})")
    print(f"  slot 2 written?      -> {manager.slot_exists(2)}")

    print("\n-- corrupt file --")
    with open(manager.get_slot_path(3), "w", encoding="utf-8") as handle:
        handle.write("{ this is not json")
    slot3 = manager.get_slot(3)
    print(f"  load(3)     -> {manager.load(3)}")
    print(f"  is_corrupt  -> {slot3.is_corrupt()}")
    print(f"  reason      -> {slot3.get_error()}")

    print("\n-- a save from a newer build --")
    future = dict(state)
    future["schema_version"] = SAVE_SCHEMA_VERSION + 5
    with open(manager.get_slot_path(2), "w", encoding="utf-8") as handle:
        json.dump(future, handle)
    print(f"  load(2)     -> {manager.load(2)}")
    print(f"  reason      -> {manager.get_last_error()}")

    print("\n-- delete --")
    print(f"  delete(1)   -> {manager.delete(1)}")
    print(f"  delete(1)   -> {manager.delete(1)}   "
          f"({manager.get_last_error()})")

    shutil.rmtree(workspace, ignore_errors=True)
    print(f"\ncleaned up {workspace}")

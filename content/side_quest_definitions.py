"""
content/side_quest_definitions.py
CSE Life: Compile & Conquer
Phase 12 — side quest definitions

The twelve side quests as static data. One per semester, each offered by
one named NPC, each teaching one skill-tree skill through the lecture
sheets Phase 11.5 converted.

Pure data, per the `content/` convention: no pygame, no `engine/`
imports, no `academic/` imports. The shape follows
`content/side_quest_lectures.py`, which follows `content/lectures.py` —
a module-level dict keyed by a stable id, accessors that never raise,
and a `validate()` that runs AT IMPORT.

    SIDE_QUEST_DEFINITIONS  quest_id -> {semester, npc_id, skill_id,
                                         day_cost, lecture_sheets}
    QUEST_ID_BY_SEMESTER    semester -> quest id

Nothing in this table was authored here. Every column was already in
the repository and is reproduced verbatim:

    semester, npc_id, quest_id   content/npc_quest_offers.py   (Phase 9)
    skill_id                     academic/side_quest_catalog.py
    lecture_sheets               content/side_quest_lectures.py (Phase 11.5)
    day_cost                     owner ruling, 2026-08-09: two days each

WHY validate() RUNS AT IMPORT. This table is only ever wrong because
someone edited it, and the failure it guards against is silent: a quest
pointing at a sheet id that does not exist reads as an empty lecture
rather than as an error, and a duplicated semester quietly drops a
quest out of the run. A game that refuses to start is the cheaper
outcome, and it is the rule `content/side_quest_lectures.py` already
set for exactly the same reason.

WHY THE npc_id IS THE SHORT TYPE ID. There are two NPC id spaces (recon
§9): the roster's long slugs (`warm_classmate_purnno`) and the level
registry's short type ids (`purnno`). The running interaction path —
`engine/states/exploration.py::__talk` — only ever holds an `NpcData`,
and an `NpcData` carries the short one, so `can_offer(npc_id, semester)`
can be called straight from the interaction. `get_npc_roster_id()` is
one hop away when the narrative data is wanted.

WHY THERE ARE TWO TABLES. `QUEST_ID_BY_SEMESTER` is written out rather
than derived from `SIDE_QUEST_DEFINITIONS`, for the reason Phase 11.5
kept `SHEET_IDS` separate from `SIDE_QUEST_SHEETS`: two tables can be
checked against each other, and a semester with no quest or a quest
filed under the wrong semester is invisible if one is generated from
the other.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from content.side_quest_lectures import DEFAULT_SHEET, get_sheet

# How many semesters the degree runs for, and therefore how many side
# quests there are: exactly one per term, no term without one. Mirrors
# content/level_registry.py::GATE_SEMESTER_MAX, spelled out here so this
# module stays importable on its own.
SEMESTER_MIN: int = 1
SEMESTER_MAX: int = 12
QUEST_COUNT: int = 12


# Table columns, per the brief: quest_id (the key), semester, npc_id,
# skill_id, day_cost, lecture_sheets.
#
# day_cost is 2 for every quest — uniform by owner ruling, the same way
# academic/side_quest_catalog.py made time_cost uniform. It is stored
# here rather than read from that catalog because content/ may not
# import academic/; validate() is what keeps a bad number out.
SIDE_QUEST_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "SQ_GIT_GITHUB": {
        "semester": 1,
        "npc_id": "purnno",
        "skill_id": "git",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_GIT_GITHUB_S1",
            "SQ_GIT_GITHUB_S2",
            "SQ_GIT_GITHUB_S3",
        ],
    },
    "SQ_OOP": {
        "semester": 2,
        "npc_id": "rahman",
        "skill_id": "oop",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_OOP_S1",
            "SQ_OOP_S2",
            "SQ_OOP_S3",
        ],
    },
    "SQ_DSA": {
        "semester": 3,
        "npc_id": "rafi",
        "skill_id": "dsa",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_DSA_S1",
            "SQ_DSA_S2",
            "SQ_DSA_S3",
        ],
    },
    "SQ_WEB_APP_DEV": {
        "semester": 4,
        "npc_id": "roya",
        "skill_id": "web_app_dev",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_WEB_APP_DEV_S1",
            "SQ_WEB_APP_DEV_S2",
            "SQ_WEB_APP_DEV_S3",
        ],
    },
    "SQ_AI_TOOLS": {
        "semester": 5,
        "npc_id": "hoque",
        "skill_id": "ai_tools",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_AI_TOOLS_S1",
            "SQ_AI_TOOLS_S2",
            "SQ_AI_TOOLS_S3",
        ],
    },
    "SQ_LINUX_CLI": {
        "semester": 6,
        "npc_id": "zayan",
        "skill_id": "linux_cli",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_LINUX_CLI_S1",
            "SQ_LINUX_CLI_S2",
            "SQ_LINUX_CLI_S3",
        ],
    },
    "SQ_DEBUGGING_TESTING": {
        "semester": 7,
        "npc_id": "kabir",
        "skill_id": "debugging_testing",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_DEBUGGING_TESTING_S1",
            "SQ_DEBUGGING_TESTING_S2",
            "SQ_DEBUGGING_TESTING_S3",
        ],
    },
    "SQ_TECH_COMMUNICATION": {
        "semester": 8,
        "npc_id": "purnno",
        "skill_id": "technical_communication",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_TECH_COMMUNICATION_S1",
            "SQ_TECH_COMMUNICATION_S2",
            "SQ_TECH_COMMUNICATION_S3",
        ],
    },
    "SQ_DATABASES_SQL": {
        "semester": 9,
        "npc_id": "rahman",
        "skill_id": "databases_sql",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_DATABASES_SQL_S1",
            "SQ_DATABASES_SQL_S2",
            "SQ_DATABASES_SQL_S3",
        ],
    },
    "SQ_NETWORKING": {
        "semester": 10,
        "npc_id": "roya",
        "skill_id": "networking",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_NETWORKING_S1",
            "SQ_NETWORKING_S2",
            "SQ_NETWORKING_S3",
        ],
    },
    "SQ_DOCKER": {
        "semester": 11,
        "npc_id": "hoque",
        "skill_id": "docker",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_DOCKER_S1",
            "SQ_DOCKER_S2",
            "SQ_DOCKER_S3",
        ],
    },
    "SQ_PROGRAMMING_LANGUAGE": {
        "semester": 12,
        "npc_id": "kabir",
        "skill_id": "programming_language",
        "day_cost": 2,
        "lecture_sheets": [
            "SQ_PROGRAMMING_LANGUAGE_S1",
            "SQ_PROGRAMMING_LANGUAGE_S2",
            "SQ_PROGRAMMING_LANGUAGE_S3",
        ],
    },
}


# The same twelve, read the other way round. Checked against the table
# above rather than built from it — see the module docstring.
QUEST_ID_BY_SEMESTER: Dict[int, str] = {
    1: "SQ_GIT_GITHUB",
    2: "SQ_OOP",
    3: "SQ_DSA",
    4: "SQ_WEB_APP_DEV",
    5: "SQ_AI_TOOLS",
    6: "SQ_LINUX_CLI",
    7: "SQ_DEBUGGING_TESTING",
    8: "SQ_TECH_COMMUNICATION",
    9: "SQ_DATABASES_SQL",
    10: "SQ_NETWORKING",
    11: "SQ_DOCKER",
    12: "SQ_PROGRAMMING_LANGUAGE",
}

# Quest ids in semester order — the order every list-returning accessor
# and the state machine's own report use, so "all twelve" always reads
# as a playthrough rather than as dictionary order.
QUEST_IDS: Tuple[str, ...] = tuple(
    QUEST_ID_BY_SEMESTER[semester]
    for semester in sorted(QUEST_ID_BY_SEMESTER))


class SideQuestDefinitionError(Exception):
    """Raised when the tables above do not agree, with each other or
    with the registries they name."""


# ── accessors ──────────────────────────────────────────────────

def get_quest_ids() -> List[str]:
    """The twelve quest ids in semester order. A copy, so a caller
    iterating it cannot edit the table."""
    return list(QUEST_IDS)


def is_quest_id(quest_id: Any) -> bool:
    """True when this names one of the twelve. Never raises."""
    return _key(quest_id) in SIDE_QUEST_DEFINITIONS


def get_definition(quest_id: Any) -> Optional[Dict[str, Any]]:
    """
    One quest's definition, or None for an id that is not one of the
    twelve.

    Returns None rather than a placeholder, unlike `get_sheet()` next
    door: a missing lecture sheet must still draw *something* on the
    reader's screen, but a missing quest definition is a caller bug and
    inventing a fake quest would hide it. This is the shape
    `academic/side_quest_catalog.py::get_side_quest_by_id()` already
    uses for the same reason. The returned dict is a copy.
    """
    entry = SIDE_QUEST_DEFINITIONS.get(_key(quest_id))
    if entry is None:
        return None
    definition = dict(entry)
    definition["quest_id"] = _key(quest_id)
    definition["lecture_sheets"] = list(entry["lecture_sheets"])
    return definition


def get_quest_for_semester(semester: Any) -> Optional[str]:
    """The quest id offered in this semester, or None outside 1-12."""
    try:
        number = int(semester)
    except (TypeError, ValueError):
        return None
    return QUEST_ID_BY_SEMESTER.get(number)


def get_semester(quest_id: Any) -> int:
    """The semester this quest belongs to, or 0 for an unknown id."""
    entry = SIDE_QUEST_DEFINITIONS.get(_key(quest_id))
    return int(entry["semester"]) if entry is not None else 0


def get_npc_id(quest_id: Any) -> str:
    """The short NPC type id that offers this quest, or ""."""
    entry = SIDE_QUEST_DEFINITIONS.get(_key(quest_id))
    return str(entry["npc_id"]) if entry is not None else ""


def get_skill_id(quest_id: Any) -> str:
    """The skill-tree skill this quest feeds, or ""."""
    entry = SIDE_QUEST_DEFINITIONS.get(_key(quest_id))
    return str(entry["skill_id"]) if entry is not None else ""


def get_day_cost(quest_id: Any) -> int:
    """Days this quest costs, or 0 for an unknown id. Nothing here
    deducts them — Phase 17 owns that."""
    entry = SIDE_QUEST_DEFINITIONS.get(_key(quest_id))
    return int(entry["day_cost"]) if entry is not None else 0


def get_lecture_sheets(quest_id: Any) -> List[str]:
    """This quest's sheet ids in reading order, or []. A copy."""
    entry = SIDE_QUEST_DEFINITIONS.get(_key(quest_id))
    return list(entry["lecture_sheets"]) if entry is not None else []


def _key(quest_id: Any) -> str:
    """Normalise a quest id the way `get_sheet()` normalises a sheet id,
    so the two agree on what counts as the same id."""
    return str(quest_id or "").strip().upper()


# ── validation ─────────────────────────────────────────────────

def _registry_npc_type_ids() -> Optional[Tuple[str, ...]]:
    """
    Every NPC type id the level registry knows, or None if it cannot be
    imported.

    None disables the two cross-registry checks below rather than
    failing, which is the idiom `content/level_registry.py` itself uses
    for `_MIN_SEMESTER_FALLBACK` and `_SKILL_IDS_FALLBACK`: this module
    stays importable standalone, and the checks that do not need the
    registry stay hard.
    """
    try:
        from content.level_registry import NPC_REGISTRY
    except ImportError:
        return None
    return tuple(NPC_REGISTRY)


def _registry_skill_ids() -> Optional[Tuple[str, ...]]:
    """The skill tree's twelve node ids, or None if unavailable."""
    try:
        from content.level_registry import SKILL_IDS
    except ImportError:
        return None
    return tuple(SKILL_IDS)


def _registry_npc_min_semester(npc_id: str) -> Optional[int]:
    """The first semester this NPC exists in, or None if unavailable."""
    try:
        from content.level_registry import get_npc_min_semester
    except ImportError:
        return None
    return int(get_npc_min_semester(npc_id))


def validate() -> None:
    """
    Raise SideQuestDefinitionError unless the table is complete and
    every id in it resolves.

    Checked, in order:
      * exactly twelve entries, and twelve semesters
      * semesters 1-12, each used exactly once
      * no duplicate skill_id (quest ids are dict keys, so a duplicate
        is structurally impossible and is not re-checked)
      * the two tables agree on which quest belongs to which semester
      * day_cost is a non-negative int
      * npc_id names a real NPC_REGISTRY type, and that NPC is already
        around in the semester their quest is offered in
      * skill_id names a real skill-tree node
      * lecture_sheets is a non-empty ordered list, every id of which
        resolves to real content and belongs to this quest

    Every problem is collected before raising, so one run reports the
    whole list instead of the first line of it.
    """
    problems: List[str] = []

    if len(SIDE_QUEST_DEFINITIONS) != QUEST_COUNT:
        problems.append("expected %d quests, found %d"
                        % (QUEST_COUNT, len(SIDE_QUEST_DEFINITIONS)))
    if len(QUEST_ID_BY_SEMESTER) != QUEST_COUNT:
        problems.append("expected %d semesters, found %d"
                        % (QUEST_COUNT, len(QUEST_ID_BY_SEMESTER)))

    npc_types = _registry_npc_type_ids()
    skill_ids = _registry_skill_ids()

    seen_semesters: Dict[int, str] = {}
    seen_skills: Dict[str, str] = {}

    for quest_id, entry in SIDE_QUEST_DEFINITIONS.items():
        if quest_id != _key(quest_id):
            problems.append("%s: quest id is not normalised (expected %s)"
                            % (quest_id, _key(quest_id)))

        # -- semester ------------------------------------------
        semester = entry.get("semester")
        if not isinstance(semester, int) or isinstance(semester, bool):
            problems.append("%s: semester is not an int (%r)"
                            % (quest_id, semester))
        elif not SEMESTER_MIN <= semester <= SEMESTER_MAX:
            problems.append("%s: semester %d outside %d-%d"
                            % (quest_id, semester, SEMESTER_MIN, SEMESTER_MAX))
        elif semester in seen_semesters:
            problems.append("%s: semester %d already used by %s"
                            % (quest_id, semester, seen_semesters[semester]))
        else:
            seen_semesters[semester] = quest_id
            if QUEST_ID_BY_SEMESTER.get(semester) != quest_id:
                problems.append(
                    "%s: says semester %d, but QUEST_ID_BY_SEMESTER[%d] is %r"
                    % (quest_id, semester, semester,
                       QUEST_ID_BY_SEMESTER.get(semester)))

        # -- npc -----------------------------------------------
        npc_id = entry.get("npc_id")
        if not isinstance(npc_id, str) or not npc_id.strip():
            problems.append("%s: npc_id is empty" % quest_id)
        elif npc_types is not None and npc_id not in npc_types:
            problems.append("%s: npc_id %r is not an NPC_REGISTRY type id"
                            % (quest_id, npc_id))
        elif isinstance(semester, int):
            available_from = _registry_npc_min_semester(npc_id)
            if available_from is not None and semester < available_from:
                problems.append(
                    "%s: %s is not around until semester %d, but the quest is "
                    "offered in semester %d"
                    % (quest_id, npc_id, available_from, semester))

        # -- skill ---------------------------------------------
        skill_id = entry.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id.strip():
            problems.append("%s: skill_id is empty" % quest_id)
        elif skill_id in seen_skills:
            problems.append("%s: skill_id %r already used by %s"
                            % (quest_id, skill_id, seen_skills[skill_id]))
        else:
            seen_skills[skill_id] = quest_id
            if skill_ids is not None and skill_id not in skill_ids:
                problems.append("%s: skill_id %r is not a skill tree node"
                                % (quest_id, skill_id))

        # -- day cost ------------------------------------------
        day_cost = entry.get("day_cost")
        if not isinstance(day_cost, int) or isinstance(day_cost, bool):
            problems.append("%s: day_cost is not an int (%r)"
                            % (quest_id, day_cost))
        elif day_cost < 0:
            problems.append("%s: day_cost %d is negative — every quest must "
                            "be configured before this file loads"
                            % (quest_id, day_cost))

        # -- lecture sheets ------------------------------------
        sheets = entry.get("lecture_sheets")
        if not isinstance(sheets, list) or not sheets:
            problems.append("%s: lecture_sheets is empty" % quest_id)
            continue
        for position, sheet_id in enumerate(sheets, start=1):
            if not isinstance(sheet_id, str) or not sheet_id.strip():
                problems.append("%s: lecture sheet %d has no id"
                                % (quest_id, position))
                continue
            sheet = get_sheet(sheet_id)
            if sheet is DEFAULT_SHEET:
                problems.append("%s: lecture sheet %r resolves to no content"
                                % (quest_id, sheet_id))
                continue
            if sheet.get("skill_id") != quest_id:
                problems.append(
                    "%s: lecture sheet %r belongs to %r"
                    % (quest_id, sheet_id, sheet.get("skill_id")))
        if len(set(sheets)) != len(sheets):
            problems.append("%s: the same lecture sheet is listed twice"
                            % quest_id)

    for semester, quest_id in QUEST_ID_BY_SEMESTER.items():
        if quest_id not in SIDE_QUEST_DEFINITIONS:
            problems.append("semester %s: no quest with id %r"
                            % (semester, quest_id))

    if problems:
        raise SideQuestDefinitionError(
            "side quest definitions are invalid:\n  " + "\n  ".join(problems))


validate()


# -------------------------------------------------------------
# STUB TEST -- print the whole table and re-run the checks that
# import already ran:
#
#     python -m content.side_quest_definitions
#
# Run as a module from the project root. Headless -- no pygame, no
# display, and nothing is written.
# -------------------------------------------------------------
if __name__ == "__main__":
    validate()
    print("%d quests, semesters %d-%d\n"
          % (len(SIDE_QUEST_DEFINITIONS), SEMESTER_MIN, SEMESTER_MAX))
    print("%-4s %-8s %-24s %-24s %-4s %s"
          % ("SEM", "NPC", "QUEST ID", "SKILL ID", "DAYS", "SHEETS"))
    for quest_id in QUEST_IDS:
        definition = get_definition(quest_id)
        print("%-4d %-8s %-24s %-24s %-4d %d"
              % (definition["semester"], definition["npc_id"], quest_id,
                 definition["skill_id"], definition["day_cost"],
                 len(definition["lecture_sheets"])))
    print("\nevery lecture sheet resolves: %s"
          % all(get_sheet(sheet_id) is not DEFAULT_SHEET
                for quest_id in QUEST_IDS
                for sheet_id in get_lecture_sheets(quest_id)))
    print("unknown quest id -> %r" % get_definition("NOPE"))
    print("semester 13       -> %r" % get_quest_for_semester(13))

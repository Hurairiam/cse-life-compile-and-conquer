# Phase 12 — Side Quests: Data Layer and State Machine

**Covers:** Prompt 1
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] add side quest definitions and state machine`

**Input:** the Phase 0 recon (`docs/recon.md`), and the ordered sheet id list Phase 11.5
handed over (`docs/phase-11.5-lecture-content-conversion.md`). The original
`side_quest_lectures.html` was not opened — Phase 11.5 already converted it and the engine
cannot render it.

---

## Step 1 — the report, made before anything was written

### The `content/` convention for data files

Same as Phase 11.5 found, re-confirmed: a **module-level dict literal in `content/`**, keyed
by a stable id, with `get_*()` accessors and a `validate()` that raises a module-specific
error and **runs at import**. No JSON content assets, no loader. `content/` modules import
stdlib and each other and nothing else.

`content/side_quest_lectures.py` is the shape copied here, down to `_key()` normalising an
id the same way `get_sheet()` does, so the two modules agree on what counts as the same id.

### Save serialization

`engine/save_manager.py::build_state()` is the single executable definition of the payload.
`SAVE_SCHEMA_VERSION = 1`, and **an older file is loaded as-is** — a file is only ever
refused for being *newer*. So every new key must be read with `.get(default)`.

Two keys were added this way before this phase and neither bumped the version:
`world.dialogue_choices` (branching dialogue) and `world.return_positions` (Phase 4). This
phase is the third and follows them exactly.

`engine/save_bridge.py::capture()` / `restore()` do the live-object half, and
`engine/return_points.py` is the pattern for a feature that owns its own slice of the
payload: a module-level `to_state(ctx)` / `from_state(saved)` pair that `save_bridge` calls
in one line each.

### Testing

**No pytest suite exists and pytest is not installed** on this machine (`py -3` is 3.14.6
with `pygame-ce` 2.5.7 and nothing else). The standing convention is a headless
`if __name__ == "__main__":` block run as `python -m <module>`.

Owner ruling: a **new pure-Python test module** following that convention, printing PASS or
FAIL per case and exiting non-zero on failure. `tests/test_quest_state.py` does that, and
its cases are named `test_*` so pytest collects the file unchanged if it is ever installed.

### What already existed

| File | What it has | Reached the game? |
|---|---|---|
| `academic/side_quest_catalog.py` | the twelve `SQ_*` ids, each with a skill-tree id, uniform 5 days / 15 EXP | no — `build_side_quest_catalog()` is never called |
| `content/npc_quest_offers.py` (Phase 9) | semester → NPC → `SQ_*`, with offer / accept / decline lines | yes, via `engine/dialogue_flow.py` |
| `content/side_quest_lectures.py` (Phase 11.5) | 36 sheets, `SHEET_IDS` keyed by `SQ_*` | not yet — Phase 15 |
| `engine/dialogue_flow.py:323` (Phase 9) | a **live** Accept / Decline that writes `ctx.unlocked_side_quests` and `ctx.decided_quest_semesters` | yes |

**The overlap was reported and deliberately left alone.** Phase 9's two sets are not in the
save file and are not a state machine — they cannot express Missed, cannot refuse an illegal
move and do not survive a reload. This phase's machine replaces them, but wiring the offer
onto it means editing the dialogue flow, which the brief puts out of scope. So the two run
side by side until **Phase 13**, and nothing in this phase reads Phase 9's sets. The
`AppContext` comment says so at the point where both are declared.

---

## Owner rulings

Reported first, then asked, then built. Four answers came back.

1. **The mapping table** is the one derived from the repository, below. Every column was
   already authored; nothing was invented here.
2. **`day_cost` = 2 for all twelve.** The brief contradicted itself — `-1` for "not yet
   configured" *and* `day_cost >= 0` validated as a loud startup failure. Confirmed with the
   team: a side quest takes **two days** out of the time pool. So the `-1` sentinel never
   ships, and the `>= 0` check stays a hard blocker with no exemption.
3. **`npc_id` is the short `NPC_REGISTRY` type id** (`purnno`), not the roster slug
   (`warm_classmate_purnno`) — recon §9's ruling. `engine/states/exploration.py::__talk`
   only ever holds an `NpcData`, and an `NpcData` carries the short id, so
   `can_offer(npc_id, semester)` can be called straight from the interaction. The roster id
   is one `get_npc_roster_id()` hop away.
4. **Tests: a new headless module**, as above.

---

## THE MAPPING TABLE

Nothing below was authored by this phase. Semester, NPC and quest come from
`content/npc_quest_offers.py`; skill ids from `academic/side_quest_catalog.py`; sheet ids
from Phase 11.5's handoff; day cost from ruling 2.

| Semester | NPC ID | Skill ID | Day cost | Lecture sheet IDs (ordered) |
|---|---|---|---|---|
| 1 | `purnno` | `git` | 2 | `SQ_GIT_GITHUB_S1`, `_S2`, `_S3` |
| 2 | `rahman` | `oop` | 2 | `SQ_OOP_S1`, `_S2`, `_S3` |
| 3 | `rafi` | `dsa` | 2 | `SQ_DSA_S1`, `_S2`, `_S3` |
| 4 | `roya` | `web_app_dev` | 2 | `SQ_WEB_APP_DEV_S1`, `_S2`, `_S3` |
| 5 | `hoque` | `ai_tools` | 2 | `SQ_AI_TOOLS_S1`, `_S2`, `_S3` |
| 6 | `zayan` | `linux_cli` | 2 | `SQ_LINUX_CLI_S1`, `_S2`, `_S3` |
| 7 | `kabir` | `debugging_testing` | 2 | `SQ_DEBUGGING_TESTING_S1`, `_S2`, `_S3` |
| 8 | `purnno` | `technical_communication` | 2 | `SQ_TECH_COMMUNICATION_S1`, `_S2`, `_S3` |
| 9 | `rahman` | `databases_sql` | 2 | `SQ_DATABASES_SQL_S1`, `_S2`, `_S3` |
| 10 | `roya` | `networking` | 2 | `SQ_NETWORKING_S1`, `_S2`, `_S3` |
| 11 | `hoque` | `docker` | 2 | `SQ_DOCKER_S1`, `_S2`, `_S3` |
| 12 | `kabir` | `programming_language` | 2 | `SQ_PROGRAMMING_LANGUAGE_S1`, `_S2`, `_S3` |

The quest id per row is the `SQ_*` id whose sheets are in the last column —
`SQ_GIT_GITHUB` for semester 1, and so on. **`quest_id` and `skill_id` are two different id
spaces and both are needed:** the `SQ_*` ids are quest ids (they key
`academic/side_quest_catalog.py` and `content/side_quest_lectures.py`), and the twelve
lower-case ids are skill-tree nodes (they key `SkillTree`, `SKILL_NODES` and
`save_bridge.TRACKED_SKILL_IDS`). Recon §12 settled that the lower-case set is the source of
truth for skills.

Five NPCs offer twice (Purnno 1 & 8, Rahman 2 & 9, Roya 4 & 10, Hoque 5 & 11, Kabir 7 & 12),
which is why `can_offer()` keys on the **pair**, not the NPC. Every offer semester is at or
after that NPC's `semester_available_from`, and `validate()` checks it.

---

## What was built

Four new files. Three existing files took a call site each, and nothing else was touched.

### `content/side_quest_definitions.py` *(new)*

```
SIDE_QUEST_DEFINITIONS  quest_id -> {semester, npc_id, skill_id, day_cost,
                                     lecture_sheets}
QUEST_ID_BY_SEMESTER    semester -> quest id
QUEST_IDS               the twelve, in semester order

get_definition(quest_id) -> dict | None      a copy, or None for an unknown id
get_quest_for_semester(semester) -> str | None
get_semester / get_npc_id / get_skill_id / get_day_cost / get_lecture_sheets
is_quest_id(quest_id) -> bool
validate() -> None      raises SideQuestDefinitionError; called at import
```

**`validate()` runs at import**, for the reason Phase 11.5 gave: this table is only ever
wrong because someone edited it, and every way it can be wrong is silent. A quest pointing
at a sheet id that does not exist reads as an empty lecture; a duplicated semester quietly
drops a quest out of the run. A game that refuses to start is the cheaper outcome. Every
problem is collected before raising, so one run reports the whole list.

What it checks: twelve entries and twelve semesters · semesters 1–12 each used once · no
duplicate `skill_id` · the two tables agree on which quest belongs to which semester ·
`day_cost` a non-negative int · `npc_id` a real `NPC_REGISTRY` type **whose NPC is already
around in that semester** · `skill_id` a real skill-tree node · `lecture_sheets` a non-empty
ordered list with no repeats, every id of which resolves to real content **and belongs to
that quest**.

**Two tables, checked against each other.** `QUEST_ID_BY_SEMESTER` is written out rather
than derived, for the reason Phase 11.5 kept `SHEET_IDS` separate from `SIDE_QUEST_SHEETS`:
a semester with no quest, or a quest filed under the wrong semester, is invisible if one
table is generated from the other.

**`get_definition()` returns `None` for an unknown id**, unlike `get_sheet()` next door.
That is not a break with the convention — a missing lecture sheet must still draw *something*
on the reader's screen, but a missing quest definition is a caller bug and inventing a fake
quest would hide it. It is the shape `academic/side_quest_catalog.py::get_side_quest_by_id()`
already uses.

The cross-registry checks import `content.level_registry` inside `try/except ImportError` and
degrade to skipping rather than failing, which is the idiom that module already uses for
`_MIN_SEMESTER_FALLBACK` and `_SKILL_IDS_FALLBACK` — so this file stays importable on its
own, and the checks that need nothing external stay hard.

### `engine/quest_state.py` *(new)*

```
STATE_UNOFFERED / STATE_DECLINED / STATE_MISSED / STATE_UNLOCKED / STATE_COMPLETED
QUEST_STATES · TERMINAL_STATES · LEGAL_TRANSITIONS (a frozenset of four pairs)
QuestStateError

class QuestStateMachine
    get_state · get_all_states · get_quest_for_semester · can_offer
    get_unlocked_quests · get_completed_quests · is_highly_skilled
    accept · decline · mark_completed · expire_unoffered_for_semester
    to_dict · load

to_state(ctx) -> dict          from_state(saved) -> QuestStateMachine
```

```
Unoffered ──accept()──────────> Unlocked ──mark_completed()──> Completed
    ├────── decline() ────────> Declined
    └── expire_unoffered_for_semester() ──> Missed
```

`LEGAL_TRANSITIONS` is the whole rulebook and `__transition()` is the only writer. Every
pair outside it raises `QuestStateError` — **including the identity pairs**, so accepting an
already-Unlocked quest is an error rather than a shrug, and the error names the legal moves
from where the quest actually is. An unknown quest id raises too: answering "unoffered" for
a typo would let the bug run for the rest of the playthrough.

**One method is allowed to do nothing, and it is not an exception to that rule.**
`expire_unoffered_for_semester()` is not a request to move a particular quest — it is "this
term is over". A quest that was accepted, declined or completed has had its answer and keeps
it; only a still-Unoffered one becomes Missed. It returns the quest id it expired, or `None`.

**States are plain strings, not an `Enum`.** They go straight into the save file, which
`save_manager.py` describes as "a dictionary of primitives", and a string survives a
hand-edited save and a debugger print with no decoding step. Every other closed set of
authored values in this repo does the same — `INTERACTION_KINDS`, `ON_COMPLETE_MODES`,
`FACINGS`.

**`load()` is deliberately tolerant while the mutators stay strict.** It is the one entry
point that reads a file a player could have hand-edited: a non-dict, an unknown quest id and
an unknown state name all fall back to Unoffered rather than raising. `accept()` and friends
are called by code, not by a file, so they throw.

**The API is transliterated to snake_case.** The brief spells it `GetState` / `CanOffer` /
`IsHighlySkilled`; every accessor in `core/`, `academic/` and `engine/` is `get_*`. The
mapping is written out in the module docstring.

The module lives on its own and holds no pygame, no screen state and no UI — recon hazard
#4, the rule `engine/menu_prop.py` and `engine/return_points.py` already set.

### `tests/test_quest_state.py` + `tests/__init__.py` *(new)*

29 cases, `py -3 -m tests.test_quest_state`, exit code 0 or 1. Headless; the only thing
written is a `tempfile.mkdtemp()` directory, so `saves/` is never touched — the same rule
`engine/save_manager.py`'s own stub follows.

Test states are reached **through the public API only** (`machine_in()` drives a quest into
each of the five), so no test can set up a state the game itself could not reach.

### The three call sites

| File | Change |
|---|---|
| `engine/save_manager.py` | `build_state()` gains a `quest_states` argument and a `"quests": {"states": {...}}` block |
| `engine/save_bridge.py` | `capture()` passes `quest_state.to_state(ctx)`; `restore()` rebuilds `ctx.quest_states` from `state["quests"]["states"]` |
| `engine/app_context.py` | `self.quest_states = QuestStateMachine()` |

**`SAVE_SCHEMA_VERSION` does not move.** The version handling the brief asks for is that a
save written before this feature loads with all twelve Unoffered, and it gets that from the
key simply being absent: `restore()` reads `state.get("quests") or {}`, `from_state(None)`
hands back a fresh machine. Bumping would only mean older builds refusing a file they can
read perfectly well — the same reasoning `dialogue_choices` and `return_positions` recorded.

---

## Verification

`py -3 -m tests.test_quest_state` — **29/29 passed**, exit 0.

| Requirement from the brief | Cases |
|---|---|
| each legal transition | `test_legal_unoffered_to_unlocked` · `_to_declined` · `_to_missed` · `test_legal_unlocked_to_completed` · `test_legal_transitions_are_exactly_four` |
| every illegal transition rejected | `test_illegal_transitions_all_rejected` — 5 states × 3 mutators, 3 legal, **12 must raise**, each asserted to leave the quest where it was · `test_illegal_terminal_states_are_final` · `test_illegal_expire_is_a_no_op_off_unoffered` · `test_illegal_unknown_quest_id_rejected` |
| save/load round-trip preserves all 12 | `test_round_trip_through_a_real_save_file` — a machine with **all five states represented** through `build_state()` → `SaveManager.save()` → disk → `load()` → `from_state()` · `test_round_trip_preserves_the_ending_gate` |
| `IsHighlySkilled` false at 11/12, true at 12/12 | `test_is_highly_skilled_false_at_eleven_of_twelve` — tried **twelve times, once per quest left out** · `_false_when_the_last_one_is_only_unlocked` · `_true_at_twelve_of_twelve` |
| a pre-existing save without quest data loads cleanly | `test_pre_phase_12_save_loads_all_unoffered` — a real file on disk with the key **deleted**, then asserted to load, read as twelve Unoffered, and still be a working machine · `test_a_hand_edited_save_never_raises` · `test_to_state_survives_a_context_without_a_machine` |
| definitions file validates | `test_definitions_*` — 8 cases, including `test_definitions_fail_loudly_on_a_bad_entry`, which breaks the table two ways and asserts the raise |

`py -3 -m content.side_quest_definitions` — the twelve rows print, every lecture sheet
resolves, unknown ids answer `None`.

`py -3 -m engine.quest_state` — **the acceptance criterion**: the state of all twelve quests
through the public API, after a run that exercises all four transitions.

```
SEM  NPC      QUEST ID                 STATE
1    purnno   SQ_GIT_GITHUB            completed
2    rahman   SQ_OOP                   completed
3    rafi     SQ_DSA                   completed
4    roya     SQ_WEB_APP_DEV           unlocked
5    hoque    SQ_AI_TOOLS              declined
6    zayan    SQ_LINUX_CLI             missed
7    kabir    SQ_DEBUGGING_TESTING     unoffered
...
refused: SQ_AI_TOOLS: illegal transition declined -> unlocked
         (legal moves from declined: none, terminal)
```

Against the **real** `AppContext`, headless with `SDL_VIDEODRIVER=dummy`: the machine is on
the context at boot with all twelve Unoffered, `capture()` emits the block, `restore()`
rebuilds it identically, a payload with `"quests"` deleted restores to twelve Unoffered, and
`new_game()` resets it.

`py -3 -m engine.save_manager` — the existing save round-trip stub still passes unchanged.

`git merge-tree` against `origin/main`: **0 conflict markers.** Three of the four new files
are in directories `main` does not have this content in; `tests/` is a new directory
entirely. The three edited files took one line each in `build_state()`'s signature, one
block in its return, two lines in `save_bridge`, and one field in `AppContext` — all
appends, per recon hazard #2.

---

## Out of scope — confirmed untouched

No dialogue file, no scene file, no UI, no day deduction, no PC object. `git status` for
this commit is four new files and three call sites; `engine/dialogue_flow.py`,
`engine/states/*`, `content/dialogues.py`, `content/npc_quest_offers.py` and every
`levels/*.json` are byte-identical.

`day_cost` is **stored and read back, never spent** — nothing in this phase calls
`GameClock.process_time_consumable()`. Phase 17 owns that.

---

## Notes for the phases downstream

**Phase 13 (the NPC offer).** `can_offer(npc_id, semester)` takes the short type id straight
off `NpcData.get_type_id()` and already returns False once the quest is answered — the check
`dialogue_flow.arm_offer()` currently does with `decided_quest_semesters`. Moving the offer
onto `accept()` / `decline()` retires **both** Phase 9 sets: `ctx.unlocked_side_quests`
becomes `get_unlocked_quests()` and `ctx.decided_quest_semesters` becomes "not Unoffered".
Do it in one change — leaving one behind means two stores disagreeing about the same quest.

**Where `expire_unoffered_for_semester()` goes.** `engine/states/exam.py::close_semester()`
is the one place a semester rolls over (recon §7). It is called once per term, before
`advance_semester()`, and recon §8 notes there is no side-quest hook in that path yet. That
is the call site, and the semester to pass is the one that is ending.

**Phase 15 (the reader).** `get_lecture_sheets(quest_id)` is the ordered list; feed each id
to `content.side_quest_lectures.get_sheet()`. Call `mark_completed()` only when the last
sheet is done — it raises if the quest was never accepted, which is the guard against
recording a completion for a quest the player does not have.

**Phase 16 (the ending gate).** `is_highly_skilled()` is `all twelve Completed`, deliberately
`all` rather than a threshold, so no later tuning of the number can happen here by accident.

**Phase 17 (the day lockout).** `get_day_cost(quest_id)` is 2 for every quest. Spending it
must go through `GameClock.process_time_consumable()` — recon §7 records the bug that arose
when that was skipped.

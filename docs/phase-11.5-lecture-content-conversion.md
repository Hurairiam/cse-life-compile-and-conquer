# Phase 11.5 — Convert Lecture Content to Engine Format

**Covers:** the lecture content for all 12 side quests
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] convert side quest lecture content into game data`

**Input:** `changes(8-8-26)/lecture_content.json` — 12 skills × 3 paragraphs, already
extracted and verified. The original HTML was not used as the source; it was only read to
confirm the extraction matched.

---

## Step 1 — the report, made before anything was written

### The `content/` convention

Every long-form text asset in this game is a **module-level dict literal in `content/`**.
There is no text-asset loader, no `assets/text/`, no JSON content file — the only JSON the
game reads is level files, save slots, `settings.json` and `tile_ids.json`. `content/`
modules import stdlib and each other, nothing else: no pygame, no `engine/`, no `academic/`.

`content/lectures.py` is the exact shape to copy:

```python
LECTURE_SCRIPTS: dict[str, dict] = {...}   # keyed by a stable id
DEFAULT_LECTURE: dict = {...}              # what a miss returns
def get_lecture(course_code) -> dict:      # never raises, never returns None
```

`engine/states/lecture.py` consumes it in two nested loops — outer: which course, inner:
which line — and hands `script["lines"]` to `DialogueManager.load_dialogue()` and
`script["title"]` to `set_speaker()`. That outer/inner shape is exactly a sheet sequence.

Recon §15 had already ruled this the best fit and named `content/side_quest_lectures.py` as
a new file that cannot conflict. Nothing found in the codebase contradicted that.

### The ids already exist

- `academic/side_quest_catalog.py::_SIDE_QUEST_DATA` owns the twelve `SQ_*` ids — it calls
  them `quest_id` — and pairs each with a skill-tree id (`git`, `dsa`, …).
- `content/npc_quest_offers.py` (Phase 9) already assigns semester → NPC → `SQ_*`.

So Phase 12's mapping table only ever needed its last column, which is what this phase
produces.

### Testing

No pytest suite exists in this repo. The standing convention is a headless
`if __name__ == "__main__":` block run as `python -m content.<module>`. This module follows
it.

---

## The fit problem, reported not solved

`ui/dialog_box.py::__wrap_line()` ends:

```python
return lines[:MAX_LINES]        # MAX_LINES = 3
```

Anything past the third wrapped row is **dropped silently** — no ellipsis, no warning.
Measured against the real `PressStart2P` at `BODY_SIZE = 13` on the shipped 1280px screen:

| | value |
|---|---|
| text column width | 976 px |
| character advance | 13 px → **75 characters per wrapped row** |
| rows drawn | 3 |
| **characters drawn per dialogue entry** | **~220** |

Against that ceiling:

| | chars | drawn today |
|---|---|---|
| an existing lecture line | 72–110 (mean 99) | all of it — 2 rows |
| one source paragraph | 308–557 | ~220, the rest dropped |
| one whole skill | ~1,300 | ~220, the rest dropped |

29 of the 78 sentences are themselves over 220 characters, so breaking only at sentence
boundaries would not have fitted either.

**Nothing was cut.** This is recorded here for Phase 15, which owns the layout. It is also
why the sheet carries a `lines` list — see the third ruling below.

---

## Owner rulings

Reported first, then asked, then built. Three answers came back.

1. **Format and location: `content/side_quest_lectures.py`**, a new pure-data module in the
   `content/lectures.py` shape. Not a JSON asset (the game has no loader for one), and not
   an extension of `content/lectures.py` (that file already differs from `main`, and course
   lectures and side quests are different content).
2. **Decision D2 = (b): one paragraph = one sheet.** 36 sheets, 3 per skill, ids
   `SQ_DSA_S1 … SQ_DSA_S3`.
3. **A sheet stores `text` *and* `lines`.** `text` is the paragraph verbatim; `lines` is the
   same characters split for the card. The split is machine-checked — see below — so
   "preserve the text exactly" is enforced rather than asserted.

---

## What was built

One new file. No existing file was touched, so this phase cannot conflict with anything.

### `content/side_quest_lectures.py`

```
SKILL_IDS          the twelve SQ_* topics, in source order
SIDE_QUEST_SHEETS  sheet id -> {skill_id, title, text, lines}
SHEET_IDS          skill id -> its sheet ids, in reading order   <- the Phase 12 handoff
DEFAULT_SHEET      what an unknown id resolves to

get_sheet(sheet_id) -> dict        never raises, never returns None
get_sheet_ids(skill_id) -> list    [] for an unknown skill; a copy, not the table
validate() -> None                 raises SideQuestLectureError; called at import
```

**`text` is byte-identical to the source.** Nothing reworded, summarised, reordered or cut.
All 15,700 characters of the 36 paragraphs ship.

**`lines` is that same string, split — not edited.** Cuts land on existing spaces at clause
boundaries, ranked: sentence end > `;` > `:` > `,` > a closing em dash > an opening em dash
> any space. Chunks are balanced across a paragraph rather than filled greedily, so no sheet
ends on a two-word orphan. Every line is ≤ 135 characters, which wraps to two rows in the
card — the same two rows the existing 72–110 character lecture lines occupy.

**The verbatim guarantee is a check, not a promise.** `validate()` asserts
`" ".join(lines) == text` on every sheet. A single character added, dropped or altered in
either field raises at import.

**`SHEET_IDS` is written out rather than derived** from `SIDE_QUEST_SHEETS`, so the two
tables can be checked against each other: an id listed with no sheet behind it and a sheet
no skill lists are both failures, and either would be invisible if one table were generated
from the other.

**`validate()` runs at import, deliberately.** This table is only ever wrong because someone
edited it, and a lecture that silently loses a paragraph is worse than a game that refuses
to start. It is the same reason `content/level_registry.py` derives `SKILL_IDS` at import
instead of trusting two lists to stay in step.

**`SKILL_IDS` is spelled out rather than imported** from `academic/side_quest_catalog.py`,
for the reason `content/map_directory.py` spells out `ROOT_LEVEL_ID`: `content/` does not
import outside itself. `validate()` fails the moment the table stops covering exactly those
twelve.

---

## Verification

`python -m content.side_quest_lectures` — 12 topics, 36 sheets, longest line 134 characters.

Checked independently against `lecture_content.json`, with the real font loaded:

| Check | Result |
|---|---|
| 36 sheets, 12 skills, 3 sheets each, ids `_S1.._S3` in order | pass |
| every `text` byte-identical to its source paragraph | pass |
| `" ".join(lines) == text`, all 36 | pass |
| total characters shipped vs. source | 15,700 = 15,700 |
| every line fits the card at ≤ 3 wrapped rows | pass (all at 2) |
| unknown / empty / `None` sheet id → `DEFAULT_SHEET` | pass |
| lower-case sheet id resolves | pass |
| `get_sheet_ids()` returns a copy | pass |

`validate()` was then made to fail, once per failure mode:

| Broken deliberately | Raises |
|---|---|
| a skill removed from `SHEET_IDS` | `SQ_OOP: skill missing from SHEET_IDS` |
| a skill given zero sheets | `SQ_OOP: skill has zero sheets` |
| a sheet id with no sheet behind it | `SQ_OOP_S9: no sheet with this id` |
| a sheet with empty text | `SQ_OOP_S1: sheet has no text` |
| a sheet with no lines | `SQ_OOP_S1: sheet has no lines` |
| one word dropped from `lines` | `SQ_OOP_S1: lines do not rejoin to text` |
| a sheet no skill lists | `SQ_OOP_S2: sheet no skill lists` |
| a sheet listed under two skills | `SQ_OOP_S1: sheet says skill_id 'SQ_OOP', listed under SQ_DSA` |
| a thirteenth topic | `SQ_MADE_UP: not one of the twelve topics` |

`git merge-tree` against `origin/main`: 0 conflict markers. The file does not exist in
`main`.

---

## HANDOFF — the ordered sheet id list per skill

Phase 12's `lecture_sheets` field. Every id below resolves to real text through
`get_sheet()`; `content.side_quest_lectures.SHEET_IDS` is this table in Python.

| Skill ID | Lecture sheet IDs (ordered) |
|---|---|
| `SQ_PROGRAMMING_LANGUAGE` | `SQ_PROGRAMMING_LANGUAGE_S1`, `SQ_PROGRAMMING_LANGUAGE_S2`, `SQ_PROGRAMMING_LANGUAGE_S3` |
| `SQ_DSA` | `SQ_DSA_S1`, `SQ_DSA_S2`, `SQ_DSA_S3` |
| `SQ_GIT_GITHUB` | `SQ_GIT_GITHUB_S1`, `SQ_GIT_GITHUB_S2`, `SQ_GIT_GITHUB_S3` |
| `SQ_LINUX_CLI` | `SQ_LINUX_CLI_S1`, `SQ_LINUX_CLI_S2`, `SQ_LINUX_CLI_S3` |
| `SQ_DATABASES_SQL` | `SQ_DATABASES_SQL_S1`, `SQ_DATABASES_SQL_S2`, `SQ_DATABASES_SQL_S3` |
| `SQ_NETWORKING` | `SQ_NETWORKING_S1`, `SQ_NETWORKING_S2`, `SQ_NETWORKING_S3` |
| `SQ_WEB_APP_DEV` | `SQ_WEB_APP_DEV_S1`, `SQ_WEB_APP_DEV_S2`, `SQ_WEB_APP_DEV_S3` |
| `SQ_DOCKER` | `SQ_DOCKER_S1`, `SQ_DOCKER_S2`, `SQ_DOCKER_S3` |
| `SQ_AI_TOOLS` | `SQ_AI_TOOLS_S1`, `SQ_AI_TOOLS_S2`, `SQ_AI_TOOLS_S3` |
| `SQ_DEBUGGING_TESTING` | `SQ_DEBUGGING_TESTING_S1`, `SQ_DEBUGGING_TESTING_S2`, `SQ_DEBUGGING_TESTING_S3` |
| `SQ_OOP` | `SQ_OOP_S1`, `SQ_OOP_S2`, `SQ_OOP_S3` |
| `SQ_TECH_COMMUNICATION` | `SQ_TECH_COMMUNICATION_S1`, `SQ_TECH_COMMUNICATION_S2`, `SQ_TECH_COMMUNICATION_S3` |

**Note, not a decision.** The mapping table's other columns are already authored:
`content/npc_quest_offers.py` (Phase 9) pairs each semester with an NPC and an `SQ_*` id,
and `academic/side_quest_catalog.py` carries a uniform 5-day `time_cost`. Whether Phase 12's
`day_cost` adopts that 5 or stays at the `-1` sentinel is still the team's call.

---

## Notes for the phases downstream

**Phase 12.** `SHEET_IDS` is the table to validate `lecture_sheets` against. Importing
`content.side_quest_lectures` runs `validate()` for you; `get_sheet(id) is DEFAULT_SHEET` is
the check for "this id resolves to nothing".

**Phase 14.** The sheet count for a skill is `len(get_sheet_ids(skill_id))` — 3 for every
topic today, but read it rather than hard-coding it.

**Phase 15.** A sheet is one screen. `lines` is ready to hand straight to
`DialogueManager.load_dialogue()`, and `title` to `set_speaker()`, exactly as
`engine/states/lecture.py` already does. Three to six lines per sheet and 11–14 per skill
(151 across all twelve topics), so one skill read start to finish is a dozen-odd SPACE
presses — the unbroken sitting D2 warned about is short.

If the reader ends up being a full-page card rather than a speech box, use `text` and do
your own wrapping; `lines` exists only because `ui/dialog_box.py` truncates at three rows.
Do not re-split `text` and store the result — that is the one thing `validate()` cannot
check for you.

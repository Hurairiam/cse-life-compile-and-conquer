# Phase 8 — NPC Semester Availability

**Covers:** Change 9 (presence and placement only)
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-08
**Commit:** `[Sprint 4] Hide NPCs in semesters where they are unavailable`

---

## Step 1 — what Ayesha's files actually say

The brief said to read `dev4-aysha-narrative` first, report which files define
per-semester availability and in what format, and wait. That report, verified before
anything was built:

`origin/dev4-aysha-narrative` is fully merged into both `origin/main` and this branch —
`git merge-base --is-ancestor` passes both ways and `git diff origin/main...origin/dev4-aysha-narrative`
is empty — so every file below was already in the working tree.

| Ayesha's file | Defines availability? |
|---|---|
| **`content/npc_roster.py`** | **Yes — the only source in the repo** |
| `content/npc_quest_offers.py` | No. A per-semester NPC→quest map, and **not in the recon's §13 table** — it landed after that survey |
| `content/dialogues.py` | No. Carries an `"unavailable"` section per NPC — see the rulings |
| `content/lectures.py`, `content/epilogue_text.py`, `engine/dialogue_manager.py`, `engine/states/cutscene.py` | No |

**The format** is one integer per NPC, `content/npc_roster.py:12`:

```python
"semester_available_from": 5,     # professor_hoque
```

`purnno 1 · rafi 1 · rahman 1 · zayan 2 · kabir 3 · roya 4 · hoque 5`

**A lower bound and nothing else.** No upper bound, no per-semester list, no gaps.
Nothing in the narrative data ever takes an NPC away again.

**The authored dialogue corroborates that reading independently.** Every placed NPC
carries exactly one chain per semester from their debut through semester 12 — which is
what `dialogue_flow.chain_index_for()` consumes:

| Level | uid | type | from | chains | covers |
|---|---|---|---|---|---|
| `cafeteria` | npc_0001 | purnno | 1 | 12 | sem 1–12 |
| `lecture_hall` | npc_0002 | rahman | 1 | 12 | 1–12 |
| `university_library` | npc_0002 | rafi | 1 | 14 | 1–12 **+ his two branch arms** `s1_yes` / `s1_no` |
| `campus_courtyard` | npc_0001 | zayan | 2 | 11 | 2–12 |
| `university_library` | npc_0001 | kabir | 3 | 10 | 3–12 |
| `campus_lobby` | npc_0001 | roya | 4 | 9 | 4–12 |
| `lecture_hall` | npc_0001 | hoque | 5 | 8 | 5–12 |
| `campus_main` | npc_0001 | purnno | 1 | **0** | — a second Purnno, no dialogue |

If the availability rule had an upper bound anywhere, one of those chain counts would be
short. None is.

### What the code did with it before this phase

The number already reached the runtime, through a chain the repo had built for the
editor's gate defaults:

```
content/npc_roster.py  semester_available_from
  └─ content/level_registry.py:621  _bind_roster_fields()   stamps min_semester
       └─ content/level_schema.py:1583  NpcData.get_effective_min_semester()
            = max(roster figure, this NPC's own editor gate)
```

and it was enforced in exactly one place, `engine/dialogue_flow.py:108`, **after E was
pressed**:

```python
if npc_data.get_effective_min_semester() > semester:
    ctx.message_popup.open("NOT YET", ["They are not around this semester."], SEVERITY_INFO)
```

So Prof. Hoque stood in the lecture hall from semester 1, advertised `[E] TALK`, blocked
his cell, and only then told the player he was not around. That is the behaviour this
phase replaces.

### Gaps reported before building

1. **Purnno is placed twice** — `campus_main` npc_0001 is a second Purnno with zero
   chains. Availability says nothing about her: she is available from semester 1.
2. **`professor_rahman`'s roster `location` is `classroom_a`**, a level that does not
   exist; he is placed in `lecture_hall`. Nothing reads that field, so it is noise —
   recorded because this phase sources from that file.
3. **Nobody is ever unavailable *after* appearing**, so only semesters 1–4 look any
   different from semester 12.
4. **The `"unavailable"` dialogue section** in `content/dialogues.py` is the only other
   thing in Ayesha's files shaped like an availability rule. It belongs to the dead
   0.75–1.00 window in `core/character/npc.py`, which no state module calls.

---

## Owner rulings

Reported first, then asked, then built. Four answers came back.

1. **The rule is the lower bound, exactly as written.** Zayan absent in semester 1;
   Kabir absent in 1–2; Roya absent in 1–3; Hoque absent in 1–4. From semester 5 on the
   whole cast is present. Nothing was invented, and no upper bounds were added.
2. **The editor keeps drawing every NPC, and gains a semester badge.** You cannot place,
   move, right-click or write dialogue for somebody you cannot see, and the editor has no
   current semester to hide them against.
3. **The second Purnno in `campus_main` is left exactly as she is.** She is out of this
   phase's scope: availability never hides her, and her silence is a dialogue-content
   problem, which is Phase 9.
4. **The `"unavailable"` dialogue section is ignored.** Wiring up an NPC who is present
   but declining is the opposite of this phase, and nobody asked for it.

---

## What was built

### `engine/npc_availability.py` — the rule (new file)

```
min_semester_of(npc_data)             the semester they first appear in
is_available(npc_data, semester)      the whole rule, one comparison
semester_of(ctx)                      the term, or 0 when there is none
hidden_in(document, semester)         who would go, without touching anything
apply_to_document(document, sem)      who goes, and takes them out
```

A new module for the reason `engine/menu_prop.py`, `engine/day_warning.py` and
`engine/final_exam.py` are: it cannot produce a merge conflict, and the alternative here
was **three** branches in three already-divergent shared files — one in `ui/map_screen.py`
to skip the sprite, one in `engine/states/exploration.py` to skip the `[E] TALK` chip and
the talk, and one wherever the collision grid is baked.

**The rule is not defined here.** It is read through
`NpcData.get_effective_min_semester()` — the roster figure widened by any gate the author
set — rather than off the roster directly, because that is the same method
`dialogue_flow.start_talk()` and `chain_index_for()` already use. An NPC delayed past
their roster debut by an author's gate is therefore hidden on exactly the semester they
would otherwise have been refused a conversation on. Reading the roster alone would have
recreated the inconsistency this phase exists to remove. No NPC in the repo carries a gate
today, so the two agree everywhere.

**`semester_of()` never raises**, and its `except` is deliberately broad — rare in this
repo, and justified because it runs inside `load_level()`: whatever a context does when
asked for a semester it has not got, the answer must be "no filtering", never an exception
that takes the map down with it. A semester of `0` means "no semester in hand" and filters
nobody, which is what the editor, the harnesses and every pre-existing caller get.

### Where it is applied — on the document, before the `Level` is built

```
read_level()  ->  LevelData  ->  validate()  ->  [FILTER]  ->  Level
```

`engine/level_loader.py::Level.__init__` bakes its NPC list, its `{cell: npc}` lookup
**and** its O(1) collision grid out of the document it is handed —
`content/level_schema.py::is_cell_walkable()` is what makes an NPC solid. So an NPC
removed from the document one step earlier is absent from all three at once:

| Brief's requirement | How it falls out | Consumer |
|---|---|---|
| not rendered | not in `level.get_npcs()` | `ui/map_screen.py:635` |
| not interactable | `get_npc_at()` returns `None` | `exploration.verb_for` / `__interact` |
| does not block movement | the cell was never marked solid | `Level.__walkable` |

**One filter, three requirements, and not one line of branching in the consumers.** That
is the whole reason the filter went on the document rather than on the `Level`: the
alternative was a semester argument threaded through `map_screen.render()`, two new
branches in `exploration.py`, and a way to re-open a baked collision cell.

**After `validate()`, never before.** A level is judged exactly as it was authored — the
same blockers, the same warnings, in semester 1 and in semester 12 — because which term
the player is in must never decide whether a map is well formed.

**Nothing is written back.** The document is the loader's own throwaway copy, built fresh
from the JSON on every load, and `engine/level_loader.py` is a one-way door. Verified:
all 12 level files are byte-identical after 144 filtered loads.

### Nothing needs to remember anything

*"A returning NPC reappears at its correct position with no manual intervention"* is free,
because the filter runs at load and **every** route into a new semester already drops the
loaded level:

```
engine/states/registration.py:72   ctx.level = None    every rollover
engine/save_bridge.py:167          ctx.level = None    every load
```

So the next `ensure_level()` rebuilds the map from the JSON against the new semester
number, and an NPC whose term has come is standing on the cell the file always gave them.
No state, no `ctx` field, no save key, no `SAVE_SCHEMA_VERSION` bump, and nothing to reset.

### `engine/level_loader.py` — one optional argument

```python
def load_level(level_ref, levels_dir=LEVELS_DIR, strict=True, semester=0) -> Level:
    ...
    if semester:
        from engine.npc_availability import apply_to_document
        apply_to_document(document, semester)
    return Level(document)
```

`semester=0` is the old behaviour exactly, so the editor, the harnesses and
`play_sandbox.py` still see the whole cast without being touched. Appended after `strict`,
so every existing positional call still means what it meant.

### The three in-game call sites

```python
engine/states/exploration.py   ensure_level()   load_level(..., semester=npc_availability.semester_of(ctx))
engine/states/exploration.py   __travel()       load_level(target, semester=...)
engine/states/teleport.py      __travel()       load_level(level_id, semester=...)
```

`exploration.py` is the file the recon names the busiest shared one in the repo, and its
share of this phase is one added import and two arguments — no new branch, no new
function, hazard #4's pattern followed exactly.

### `tools/level_editor.py` — the `S<n>` badge

`__render_npc_badges()` gained one chip: `S5` on Prof. Hoque, `S4` on Roya, `S3` on Kabir,
`S2` on Zayan. Semester 1 draws nothing — it is the default, most of the cast has it, and
a chip on everybody says nothing about anybody.

It reads `get_effective_min_semester()`, the same number the game hides them by, read the
same way — so the canvas cannot disagree with the map.

**Bottom-left of the cell, over the feet.** The first attempt put it top-left and it
landed squarely across Hoque's face: an NPC sprite hangs off the *top* of its cell
(`npc_blit_offset`), so `rect.y` is where the head is, and the face is the one part of the
art an author reads to see who they placed. The talk dot already owns the top right and
the lock badge the bottom right, which leaves the feet.

**The NPC itself is still drawn unconditionally** (ruling 2). The term is *reported*, not
simulated.

---

## Files changed

| File | Δ | Why |
|---|---|---|
| `engine/npc_availability.py` *(new)* | +323 | the rule, the filter, and the module's stub test |
| `tools/level_editor.py` | +37 −1 | the `S<n>` badge |
| `engine/level_loader.py` | +27 −1 | the `semester` argument and the filter call |
| `engine/states/exploration.py` | +9 −3 | one import, two arguments |
| `engine/states/teleport.py` | +5 −2 | one import, one argument |

**Not touched:** `content/` (every file — the rule is *read* from Ayesha's data, never
edited into it), `ui/`, `engine/app_context.py`, `engine/save_manager.py`,
`engine/save_bridge.py`, `engine/screen_manager.py`, `engine/dialogue_flow.py`,
`tools/editor_popups.py`, and **every `levels/*.json`**.

---

## Merge-conflict risk

**Phase 8 adds zero conflicts.** `git merge-tree --write-tree` against `origin/main`
produces a clean tree with and without this phase's commit — no conflict markers either
way.

The bulk of the work is in a new file, which cannot conflict. Of the four modified files:

- `engine/states/exploration.py` and `engine/states/teleport.py` — hazard #4's own
  mitigation, applied: the logic went into a new module and the state modules took the
  smallest possible call site. `teleport.py` is this branch's own Phase 5 file.
- `engine/level_loader.py` — Medium risk, +66 from main before this. The change is one
  optional keyword argument appended to one signature, plus a four-line guarded call. No
  existing line moved.
- `tools/level_editor.py` — **High** risk, +215 from main and the file Phases 10 and 11
  both land in. Its share here is one method body, deliberately the smallest thing that
  satisfied ruling 2, and it is a method nothing else calls.

The three hazards this phase could have hit, and did not:

- **Hazard #1, level JSON.** Nothing was placed and nothing was rewritten. The filter is
  a load-time view; the files on disk are byte-identical, and that is asserted.
- **Hazard #2, `content/level_registry.py`.** Not touched. The roster binding it already
  had was enough.
- **Hazard #3, `ScreenState` renumbering.** No new screen, so `engine/screen_manager.py`
  was not opened.

The uncommitted `levels/campus_main.json` map edit and the eight untracked
`assets/props/*.png` in the working tree are **not** this phase's and were left staged out
of the commit.

---

## Verification

Headless, `SDL_VIDEODRIVER=dummy`, on `pygame-ce 2.5.7` / Python 3.14.6.
**273 end-to-end checks plus 80 assertions in the module's own stub test — 353 total, all
passing.**

### Unit — `py -m engine.npc_availability`

Pure python, no pygame, no assets.

| Case | Result |
|---|---|
| A debut of *n* is absent at *n−1*, present at *n*, present at 12 | pass |
| Semester 0 / negative (tooling) filters nobody | pass |
| An NPC whose class cannot answer is left on the map, never hidden | pass |
| The shipped cast, filtered semester by semester, 1 through 12 | pass |
| Kept NPCs keep their exact cells; a hidden one's cell is empty | pass |
| A returning NPC is back on the same cell with nothing reset | pass |
| `semester_of()` on a context with no session returns 0 | pass |
| `semester_of()` on a context that *raises* returns 0 | pass |
| A hand-stacked cell is left alone rather than guessed at | pass |

### End to end — real level files, a real `AppContext`, the real loop order

| Group | Case | Result |
|---|---|---|
| Source | all seven roster figures reach `get_npc_min_semester()` | pass |
| | no semester was invented for an NPC the roster does not gate | pass |
| Rule | lower bound only, checked at every debut 1–5 | pass |
| Levels | **all 12 levels load and validate in semesters 0–12** (156 loads) | pass |
| **Cast** | **for every semester 1–12, every level holds exactly the NPCs the roster marks available** | pass |
| **Position** | **every present NPC is at its authored cell, every semester** | pass |
| **Absent** | **not in the draw list** (`get_npcs`) | pass |
| | **not interactable** (`get_npc_at` is `None`) | pass |
| | **does not block movement** (the cell is walkable) | pass |
| | all three flip back the semester they arrive | pass |
| Files | 12 level files byte-identical after 144 filtered loads | pass |
| Tooling | a default `load_level()` still shows the whole cast | pass |
| Editor | the badge reads `get_effective_min_semester()` and skips semester 1 | pass |
| | the NPC is still drawn unconditionally | pass |
| | the editor renders `lecture_hall`, `campus_lobby` and `player_room` without error | pass |
| **In game** | semester 1 lecture hall: Hoque absent, Rahman present | pass |
| | Hoque's cell is walkable and **the player can stand on it** | pass |
| | **no `[E] TALK` chip on his cell**, and `[E] TALK` still on Rahman | pass |
| | semesters 1–4 absent, 5 and 12 present — with only a rollover between | pass |
| | **Hoque returned to (12,5) with nobody resetting anything** | pass |
| | talking to him in semester 5 still works end to end | pass |
| | `campus_lobby`: Roya absent and her cell walkable in sem 3, back in sem 4 | pass |
| Ruling 3 | `campus_main`'s second Purnno is untouched in semesters 1, 6 and 12 | pass |
| Regression | 30 modules import, including `main`, `save_bridge`, `state_router`, `dialogue_flow`, both editor modules and `play_sandbox` | pass |
| | `day_warning` and `final_exam` stub tests still pass | pass |

**Visual acceptance** (the brief's own test), captured headless: the lecture hall in
semester 1 shows Prof. Rahman alone with bare floor where Prof. Hoque stands, and the same
room in semester 5 shows both of them, Hoque on the exact cell the file always gave him.

---

## What this phase deliberately did not do

- **Touched a single line of `content/`.** Availability is Ayesha's data. It is read, not
  edited, and not duplicated — there is no second copy of those seven numbers anywhere in
  this phase.
- **Added an upper bound.** Ruling 1. If an NPC should ever leave, the numbers have to
  come from the owner.
- **Filtered `play_sandbox.py`.** It is a standalone harness with no `GameSession`, so
  `semester_of()` returns 0 there anyway and it keeps showing the whole cast — which is
  what a sandbox is for.
- **Removed the `"NOT YET"` popup** in `engine/dialogue_flow.py`. It is now unreachable
  for a hidden NPC, but it still fires for one an author deliberately leaves visible, and
  deleting it would be a change to a shared file for no gain.
- **Anything about what an NPC *says*.** That is Phase 9. This phase only decides whether
  they are on the map at all.

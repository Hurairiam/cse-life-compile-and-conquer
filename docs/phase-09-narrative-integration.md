# Phase 9 — Narrative Dialogue Integration

**Covers:** Change 10, and the dialogue half of Change 9
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] integrate narrative dialogue and side quest data into NPCs`

---

## Step 1 — what is in `dev4-aysha-narrative`, and where it goes

The brief said to inventory every file on that branch, map each dialogue to its NPC,
semester and prerequisite conditions, and wait for the owner to verify before touching
anything. That report, verified before a line was written:

`origin/dev4-aysha-narrative` tips at `852c397` and is fully contained in `origin/main`
and in this branch. There was nothing to merge — every file below was already in the
working tree.

### The files

| Ayesha's file | Contains | Reached the player before this phase? |
|---|---|---|
| `content/npc_roster.py` | 7 NPCs; `semester_available_from`, `location`, portrait variants | **Yes** — the semester gate (Phase 8) |
| `content/dialogues.py` | `SEMESTER_INTROS` (12×3) · `CUTSCENES` (sem 1,3,4,5,6,9,12) · `has_cutscene()` · `NPC_DIALOGUES` (7 NPCs × greeting/offer/farewell/unavailable) | **Partly** — intros and cutscenes yes; `NPC_DIALOGUES` reaches nothing |
| `content/npc_quest_offers.py` | `SEMESTER_QUEST_OFFERS` — 12 terms, one NPC + `quest_id` + offer/accept/decline lines each. **Not in the recon's §13 table** — it landed after that survey | Yes, via `engine/dialogue_flow.py` |
| `levels/cafeteria · campus_courtyard · campus_lobby · lecture_hall · university_library .json` | **the per-semester dialogue itself** — 76 chains on 7 placed NPCs | Yes at HEAD; **no** in the working tree — see the conflict below |
| `engine/states/cutscene.py`, `engine/states/registration.py`, `engine/dialogue_manager.py`, `engine/screen_manager.py` | the cutscene screen and its route | Yes |
| `engine/app_context.py`, `engine/state_router.py`, `ui/popup.py` (`box_y`) | `quest_intro_popup`, `seen_quest_intro_semesters` | **Constructed and rendered, but nothing opens it** |
| `engine/states/dialogue.py`, `ui/choice_box.py` | the Accept / Decline reply list | Yes (rewritten into `dialogue_flow.py`) |
| `content/lectures.py` | per-course lecture scripts | Yes — out of scope |

### The mapping

The selection rule was already in the engine — `dialogue_flow.chain_index_for()`:
`index = semester − semester_available_from`, clamped at both ends. One chain per semester
of availability, so the last authored chain repeats rather than the conversation running
out.

| NPC | Level | Avail. from | Chains | Semester → chain id |
|---|---|---|---|---|
| Purnno | `cafeteria` | 1 | 12 | 1→`1`, 2→`2`, 3→`3`, 4→`chain_4` … 12→`chain_12` |
| Rahman | `lecture_hall` | 1 | 12 | 1→`semester_1` … 5→`semester_5`, 6→`sem_6` … 12→`sem_12` |
| Rafi | `university_library` | 1 | 12 (+2) | 1→`s1`, 2→`s2`, 3→`s3`, 4→`chain_4` … 12→`chain_12`; `s1_yes` / `s1_no` sit at indices 12–13 and are reachable **only** through `s1`'s choice |
| Zayan | `campus_courtyard` | 2 | 11 | 2→`sem2`, 3→`sem3`, 4→`chain_4` … 12→`chain_12` |
| Kabir | `university_library` | 3 | 10 | 3→`sem3`, 4→`sem4`, 5→`chain_5` … 12→`chain_12` |
| Roya | `campus_lobby` | 4 | 9 | 4→`c1`, 5→`chain_2` … 12→`chain_9` |
| Hoque | `lecture_hall` | 5 | 8 | 5→`sem05`, 6→`sem06`, 7→`sem7`, 8→`chain_8` … 12→`chain_12` |

Every count is exact — nobody runs short, nobody over-runs. All seven are `interactable`,
carry no `gate`, and use `on_complete: loop_last`, which is what the clamp already does.

### Prerequisite conditions found, and whether the codebase has an equivalent

| Condition | Source | Equivalent |
|---|---|---|
| NPC present from semester *n* | `npc_roster.semester_available_from` | **Yes** — `get_effective_min_semester()`; Phase 8 hides them, `dialogue_flow` gates the talk |
| Which chain plays this term | chain ordering in the level files | **Yes** — `chain_index_for()` |
| Cutscene before semester *n* | `has_cutscene()` | **Yes** — `registration.py:74` |
| Rafi's `s1` answer | level `choice` / `goto` | **Yes** — persisted to `ctx.dialogue_choices`; nothing reads it back yet |
| Offer only from the named NPC, once per term | `SEMESTER_QUEST_OFFERS` | Yes — `arm_offer()` / `decided_quest_semesters`. **Out of scope this phase** |
| **"the first 20 days of the term"** | `NPC_DIALOGUES["unavailable"]` + `npc.is_within_availability_window()` (0.75–1.00 of the 80-day pool) | **None** — dead code, no state module calls it. Listed and asked, not approximated |

---

## The conflict — Ayesha's dialogue was gone from the working tree

Three level files were modified and uncommitted, written at 23:34–23:37 on 2026-08-08,
after Phase 8's commit at 23:16. Two of them had **re-placed four NPCs with new uids and
zero chains** — the erase-and-re-place the recon warns about at §11 ("Move — NOT FOUND …
relocating a prop today means erasing it and re-placing it, which loses every
per-instance attribute").

| Level | At HEAD (Ayesha's) | In the working tree |
|---|---|---|
| `lecture_hall` | `npc_0001` hoque @12,5 — **8 chains**<br>`npc_0002` rahman @8,5 — **12 chains** | `npc_0003` hoque @11,3 — **0**<br>`npc_0004` rahman @8,4 — **0** |
| `university_library` | `npc_0001` kabir @12,6 — **10 chains**<br>`npc_0002` rafi @8,6 — **14 chains** (incl. the branch) | `npc_0003` kabir @12,2 — **0**<br>`npc_0004` rafi @9,9 — **0** |

**44 of the 76 authored chains — four of the seven NPCs — reached the player not at all.**
Validation said so: `EMPTY_DIALOG` ×2 on each file. In game, pressing **E** on Hoque,
Rahman, Kabir or Rafi played the error beep and nothing else, while the `[E] TALK` chip
still appeared over the cell. Cafeteria (Purnno), courtyard (Zayan) and lobby (Roya) were
untouched and still worked.

`campus_main.json` is a genuine map resize (30×16 → 35×18) with no NPCs in any revision.
It is not this phase's and was left out of the commit, the same way Phase 8 left it.

---

## Owner rulings

Reported first, then asked, then built. Three answers came back.

1. **Graft the chains onto the new placements.** The working tree's cells and uids
   (`npc_0003` / `npc_0004`) are kept exactly as the editor left them; only `dialog.chains`
   is written back, matched by `type_id` against the same NPC at HEAD. Nothing about the
   re-placement is undone.
2. **The `"unavailable"` section stays ignored**, as Phase 8 ruled. It describes an NPC
   who is present but declining, which is a different feature from per-semester dialogue,
   and wiring its 20-day window would change what every NPC says for 60 of every 80 days.
3. **The speaker name is bound from the roster**, rather than fixing two string literals
   or leaving it — see below.

---

## What was built

Nothing in this phase is new machinery. The dialogue system, the semester rule and the
branch all already existed and all already worked; what was missing was the data reaching
them. So the change is 20 lines of data restored to the two level files, and one existing
function taught to bind one more field.

### The graft — `levels/lecture_hall.json`, `levels/university_library.json`

Done through the schema's own API rather than by hand-editing JSON:

```
read_level()  ->  npc.to_dict()  ->  record["dialog"]["chains"] = HEAD's chains
              ->  level.replace_npc(uid, record)  ->  write_level()
```

`replace_npc()` keeps the uid, the type and the cell and swaps everything else
(`level_schema.py:2172`) — it is the dialog editor's own commit path, so the file lands in
exactly the shape the editor would have written. `write_level()` re-validates before
touching disk.

**Round-tripped first.** Reading and re-writing both files with no change produced
byte-identical output, so the diff below is the graft and nothing else.

**The final diff against HEAD is four uids and four cells.** Every layer, prop, zone and
line of dialogue is byte-identical to what Ayesha wrote — the restored chains cancel out
against HEAD exactly, which is the strongest available evidence that nothing was
paraphrased, reordered or dropped on the way through.

Rafi's branch survived intact: `s1` still carries the `WHAT DO YOU SAY?` prompt, both
replies, and gotos into `s1_yes` / `s1_no`, and those two arms are still last in his list
where the semester rule can never select them.

### `content/level_registry.py` — the speaker name

`NPC_REGISTRY`'s `name` is what `dialogue_flow.play_chain()` puts on the dialogue card.
Two of the seven disagreed with the roster: Ayesha wrote **Prof. Rahman** and **Ms. Roya**,
the card said *Rahman* and *Roya*. Hoque already carried his title in both files, which
makes this two entries that were missed rather than a decision.

`_bind_roster_fields()` already stamps `roster_id` and `min_semester` onto every registry
entry from the roster at import, for the stated reason that "a roster change cannot
silently disagree with the editor". `name` now binds the same way — three lines inside a
function that already reads that file:

```python
entry["name"] = str(
    roster_entry.get("display_name") or entry.get("name", type_id))
```

Chosen over editing the two literals because the literals could drift again. A registry
entry the roster has nothing to say about keeps its hand-written name, so a placeable NPC
with no narrative entry is unaffected. `get_npc_display_name()` was not touched; the
editor's dialog popup and `level_loader`'s NPC objects pick the corrected names up for
free.

### What was deliberately not done

- **No side quest mechanics.** The brief says to extract and report that content, not
  implement it. `SEMESTER_QUEST_OFFERS` was read, tabulated below, and left alone.
- **No parallel dialogue path.** The brief says to reuse the existing system. The level
  chains are the live path; `content/dialogues.py::NPC_DIALOGUES` is a second, unreachable
  source and wiring it would have been exactly the parallel path the brief forbids.
- **No new file, no new state, no save key, no `SAVE_SCHEMA_VERSION` bump.**
- **`content/npc_roster.py`, `content/dialogues.py` and `content/npc_quest_offers.py` were
  not edited.** Ayesha's data is read, never rewritten.

---

## Side quest source material — extracted, not implemented

From `content/npc_quest_offers.py`, for the Phase 0 mapping table the owner fills in:

| Sem | Offering NPC | Level | `quest_id` | Skill id |
|---|---|---|---|---|
| 1 | Purnno | cafeteria | `SQ_GIT_GITHUB` | `git` |
| 2 | Prof. Rahman | lecture_hall | `SQ_OOP` | `oop` |
| 3 | Rafi | university_library | `SQ_DSA` | `dsa` |
| 4 | Ms. Roya | campus_lobby | `SQ_WEB_APP_DEV` | `web_app_dev` |
| 5 | Prof. Hoque | lecture_hall | `SQ_AI_TOOLS` | `ai_tools` |
| 6 | Zayan | campus_courtyard | `SQ_LINUX_CLI` | `linux_cli` |
| 7 | Kabir | university_library | `SQ_DEBUGGING_TESTING` | `debugging_testing` |
| 8 | Purnno | cafeteria | `SQ_TECH_COMMUNICATION` | `technical_communication` |
| 9 | Prof. Rahman | lecture_hall | `SQ_DATABASES_SQL` | `databases_sql` |
| 10 | Ms. Roya | campus_lobby | `SQ_NETWORKING` | `networking` |
| 11 | Prof. Hoque | lecture_hall | `SQ_DOCKER` | `docker` |
| 12 | Kabir | university_library | `SQ_PROGRAMMING_LANGUAGE` | `programming_language` |

Each entry carries three `offer_lines`, one `decline_lines` and one `accept_lines`.

- All twelve `quest_id`s match `academic/side_quest_catalog.py` exactly, at a uniform
  5 days / 15 EXP.
- Every offering NPC is available in the term they offer in — no offer is stranded behind
  the semester gate.
- Every accept line points the player at **the PC in their room** ("check your PC back in
  your room", "I'll upload the set to your PC tonight", "the material will be waiting on
  your terminal"). That is the delivery mechanism the narrative assumes, and it is the
  strongest steer in Ayesha's files about how a side quest is meant to be collected.
- **Structure only.** No day cost, no state model, no expiry, no offer window, no
  acceptance deadline anywhere in her files.

---

## Contradictions between Ayesha's files and the game

Reported, not silently fixed.

1. **`professor_rahman`'s roster `location` is `classroom_a`** — a level that does not
   exist. Her own level file places him in `lecture_hall`, and that is where his twelve
   chains live. Nothing live reads the field; it would only surface in the quest-intro
   popup, which is dead (below). Left alone — editing it is a `content/` change for no
   in-game effect.
2. **The quest-intro popup is dead code.** `ctx.quest_intro_popup` is built in
   `app_context.py:106`, dispatched in `state_router.py:80` and rendered at `:137`, but
   the `exploration.__maybe_show_quest_intro()` that opened it did not survive the merge
   `2fad10c`. It told the player once per term who had something to offer and where.
   Reviving it is *offers* — out of scope — so it is flagged here for whoever owns that
   phase. Note it would print Rahman's location as "classroom a" until #1 is settled.
3. **`NPC_DIALOGUES` is unreachable** — 7 NPCs × greeting/offer/farewell/unavailable. A
   second, parallel source of NPC speech that no state module loads. The live dialogue is
   the level chains. Wiring it is the parallel path the brief forbids.
4. **Two speaker names disagreed with the roster** — fixed, ruling 3.
5. **Eight portrait PNGs are missing.** `NPC_REGISTRY` maps every NPC to
   happy / neutral / serious (Hoque: approving / neutral / strict), but
   `assets/npcs/npc_rafi_happy · npc_rafi_serious · npc_rahman_happy · npc_rahman_serious ·
   npc_zayan_happy · npc_zayan_serious · npc_kabir_happy · npc_purnno_serious` do not
   exist. `get_npc_portrait_path()` falls back to the NPC's default, so nothing crashes
   and no dialogue is lost — the face is just neutral where the author asked for a mood.
   Roya and Hoque are the only two whose art fully matches their script. This is art, not
   dialogue, and is left for the asset track.
6. **A third naming layer exists but is harmless.** `npc_roster.py` points portraits at
   `assets/portraits/`, `NPC_REGISTRY` at `assets/npcs/`. The registry is what the game
   reads; the roster paths are unused.

---

## Files changed

| File | Δ | Why |
|---|---|---|
| `levels/lecture_hall.json` | +5 −5 vs HEAD | Hoque's 8 and Rahman's 12 chains restored onto the new placements; the diff that remains is the two uids and cells |
| `levels/university_library.json` | +5 −5 vs HEAD | Kabir's 10 and Rafi's 14 restored, branch intact; same |
| `content/level_registry.py` | +12 −1 | `_bind_roster_fields()` binds `name` |

**Not touched:** every file under `content/` except `level_registry.py` — and Ayesha's
three data files in particular — all of `engine/`, all of `engine/states/`, all of `ui/`,
all of `tools/`, `levels/campus_main.json`, and the eight untracked `assets/props/*.png`,
which are not this phase's and stayed out of the commit.

---

## Merge-conflict risk

**Phase 9 adds zero conflicts.** `git merge-tree --write-tree HEAD origin/main` produces a
clean tree with and without this phase's commit.

- `levels/*.json` — hazard #1 calls these effectively unmergeable, and this phase does the
  least dangerous thing possible with them: no prop placed, no layer touched, no map
  rewritten. The two files differ from HEAD by twenty lines inside the `npcs` array.
- `content/level_registry.py` — hazard #2's shared choke point, already +103 from main.
  Its share here is one assignment plus a docstring, **inside an existing function**, with
  nothing reordered and no top-level table restructured. That is the appended-not-
  restructured shape hazard #2 asks for.
- `engine/states/exploration.py` — hazard #4's busiest file. **Not opened.** The whole
  phase turned out to be data plus one binding, which is the cheapest possible outcome for
  that file.

---

## Verification

Headless, `SDL_VIDEODRIVER=dummy`, `pygame-ce 2.5.7` / Python 3.14.6.
**638 end-to-end checks, all passing**, plus the three existing stub tests and a 24-module
import sweep.

| Group | Case | Result |
|---|---|---|
| Source | each NPC's chain count exactly covers their debut → semester 12 | pass |
| | 7 NPCs, 76 chains accounted for | pass |
| Files | all 12 levels validate; **`lecture_hall` and `university_library` now carry 0 warnings** (was `EMPTY_DIALOG` ×2 each) | pass |
| | `cafeteria`, `campus_courtyard`, `campus_lobby` byte-identical to HEAD | pass |
| Placement | all 7 roster NPCs placed, exactly once, in the level Ayesha authored them for | pass |
| | every NPC's chain id list matches HEAD's, in order | pass |
| **Selection** | **semester → chain id, every NPC, every semester of their availability (76 cases)** | pass |
| Gate | absent the semester before their debut, present on it and at 12 | pass |
| Branch | `s1` still branches; prompt, both labels and both gotos intact; `s1_yes` / `s1_no` resolve | pass |
| | the semester rule can never select a branch arm, semesters 1–12 | pass |
| **In game** | **a real `AppContext`, the real `dialogue_flow.start_talk()`, every available NPC in every semester 1–12: the conversation starts, the chain is the one the mapping names, and the first line on screen is Ayesha's own text** | pass |
| | every NPC speaks under their roster name | pass |
| | an unavailable NPC is not on the map to be talked to | pass |
| In game | **every line of all 76 chains reads out through `DialogueManager`, in order, complete** | pass |
| Branch in game | answering "Teach me how." continues into `s1_yes`; "I'll wing it." into `s1_no` | pass |
| | the answer is recorded under `university_library:npc_0004:s1` either way | pass |
| Reach | all 7 NPCs are solid, return from `get_npc_at()`, and have at least one walkable cell reachable from the level spawn to stand on and press E | pass |
| Regression | 24 modules import, including `main`, `play_sandbox`, `play_registration`, both editor modules, `save_bridge` and `map_directory` | pass |
| | `npc_availability`, `day_warning` and `final_exam` stub tests still pass | pass |

**Visual acceptance**, captured headless: Prof. Hoque's semester-5 card shows his strict
portrait, his corrected title and "Welcome to my class."; Rafi's semester-1 card shows his
last line with the two-reply branch docked above it.

---

## What this phase deliberately did not do

- **Implement any side quest mechanic.** The offer table is extracted and tabulated above
  and nothing else. `SEMESTER_QUEST_OFFERS` is untouched.
- **Revive the quest-intro popup.** It is dead, it is reported, and it is *offers*.
- **Wire `NPC_DIALOGUES`.** A parallel dialogue path, explicitly out of bounds.
- **Approximate the "first 20 days" window.** Listed and asked; the owner ruled it stays
  ignored.
- **Touch `engine/states/exploration.py`, `engine/dialogue_flow.py` or any state module.**
  The dialogue machinery was already correct — the data was the only thing missing.
- **Move an NPC.** The cells the editor left them on are the cells they are on. The one
  thing put back is what they say.

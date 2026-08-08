# Codebase Recon — Phase 0

Read-only survey of the repo as it stands. Paste the relevant sections at the top of
later side-quest sessions so the codebase does not get rediscovered every time.

- **Checkout surveyed:** `C:\Users\nanji\Downloads\github_repositories\cse-life-compile-and-conquer`
- **Branch:** `dev3-nangiba-gui-assets` @ `2c40bd3` (4 ahead / 1 behind `origin/main`)
- **Date:** 2026-08-08
- **Entry point:** `main.py` → `AppContext` + `StateRouter`, 1280×720, 60 FPS

Everything below is what *exists today*. "Not found" means the thing genuinely is not in
the repo, and that is a deliberate answer.

> **Amended 2026-08-08, after the recon**, by owner ruling in the same session. Three
> changes land on top of the survey below, and every affected section says so inline:
>
> 1. **Skill ids reconciled** onto Saif's canonical twelve (§12).
> 2. **Branching dialogue implemented** — `ctx.choice_options` is no longer dead (§10).
> 3. **Two content bugs fixed** — `campus_lobby` would not load, and Roya's dialogue was
>    orphaned on a malformed prop (§13).

> **Amended again 2026-08-08, after Phases 1 and 2 shipped.** The survey below described
> the repo *before* them, so two sections would now mislead a later session and say so
> inline:
>
> 1. **Phase 1 — player name entry** (`8f5bcc7`). `Character.set_display_name()` exists,
>    a `NAME_ENTRY` screen runs before the opening monologue, and `restore()` reads the
>    saved name back (§3).
> 2. **Phase 2 — manual save slots** (`d52272d`). SAVE GAME opens a slot picker instead
>    of writing the autosave; the quit-time autosave stays and is now silent (§1). The
>    student id is `8324782`, not `player_01` (§3).
>
> Neither phase changed the save payload or `SAVE_SCHEMA_VERSION`. The
> merge-conflict tables at the bottom are updated for both.

---

## Architecture in one paragraph

`main.py` builds one `AppContext` (`engine/app_context.py`) that owns every system and
every piece of shared screen state, then loops: apply pending transition → `router.sync()`
→ events → update → render. `engine/state_router.py` maps a `ScreenState` enum member to
`engine/states/<lowercase name>.py` by `importlib`, and calls whichever of
`enter/exit/handle_events/update/render` that module happens to define. A missing module
or missing hook is a silent no-op — **a new screen is added by dropping in one file plus
one enum member; the router is never edited.** `content/` is pure data (no pygame, no
engine imports), `academic/` and `core/` are pure logic, `engine/` orchestrates, `ui/`
only draws what it is handed.

---

## 1. Save system

**Format.** Plain JSON, one file per slot, written by `engine/save_manager.py`.

**Location.** `<project root>/saves/`, anchored to the module file rather than the working
directory. Currently contains only `autosave.json`.

**Slots.** Three manual (`slot_1.json`…`slot_3.json`) plus one autosave (`autosave.json`,
slot id `0`). Constants: `SAVE_SLOTS = 3`, `AUTOSAVE_SLOT_ID = 0`,
`SLOT_IDS = (1, 2, 3, 0)`, `SLOT_LABELS = {1:"SLOT 1", …, 0:"AUTOSAVE"}`.

**What is written.** `build_state()` (`save_manager.py:428`) is the single executable
definition of the payload shape:

```
schema_version, saved_at, playtime_seconds
player   { display_name, character_id, wallet_balance, accumulated_credits,
           current_semester, has_graduated, skills{} }
semester { number, time_pool_days, registered_course_codes[] }
academic { completed_course_codes[], backlog_course_codes[] }
world    { level_id, spawn_x, spawn_y, triggered_prop_uids[], talked_npc_uids[],
           dialogue_choices{} }
clock    { global_career_clock_days }
```

`skills` is `{skill_id: level}` over the twelve tracked ids (see §12).
`triggered_prop_uids` / `talked_npc_uids` are stored as `"<level_id>:<uid>"` strings.

**`world.dialogue_choices` was added by the 2026-08-08 amendment** — `{"<level>:<npc
uid>:<chain id>": reply index}`, the answers the player gave to branching dialogue (§10).
`schema_version` was **not** bumped: the key is additive, `restore()` reads it with a
`.get()` and an `int()` guard, and a save written before branches existed loads to `{}`.
Bumping would have made every existing save unreadable for no gain.

**Writing.** `SaveManager.save(slot_id, state)` serialises to a string *first* (so an
unserialisable payload fails before touching disk), writes `<file>.tmp`, `flush` + `fsync`,
then `os.replace()` — atomic on Windows and POSIX. `schema_version` and `saved_at` are
stamped by `save()` itself, never trusted from the caller. **Nothing in this module ever
raises**; failures return `False`/`None` with a reason in `get_last_error()`.

**Loading.** `SaveManager.load(slot_id)` returns the dict or `None`.
`engine/save_bridge.py::restore(ctx, state)` rehydrates: it builds a **fresh**
`build_course_catalog()`, `GameSession`, `GameClock`, `RegistrationManager` and
`SemesterCatalogBuilder`, then replays saved facts through public mutators only. A fresh
catalog is deliberate — `Course` objects carry completed/backlogged flags and are reused
for the whole run. `ctx.level` is set to `None` so exploration reloads from `ctx.level_id`.

**Version handling.** `SAVE_SCHEMA_VERSION = 1`. On read, a file whose `schema_version` is
**greater** than the current one is *refused* (returned as empty + an error string) rather
than guessed at. There is **no migration path for older versions** — an older file is
simply loaded as-is, so any new key must be tolerant of absence (`.get(..., default)`).

**How the "save game" button reaches a slot — ⚠ REPLACED BY PHASE 2.** What the survey
found was this, and it is no longer true:

> Exactly one path, ending at the autosave. `ACTION_QUIT_TO_MENU` called the same
> `__save(ctx)` before leaving. **There was no UI anywhere that wrote to slots 1–3** —
> `SaveManager.save()` accepted them, `list_slots()` displayed them, `load_game` could
> delete them, but nothing offered the player a "save to slot N" choice.

The path today:

```
ui/pause_menu.py              ACTION_SAVE_GAME (button index 4, label "SAVE GAME")
engine/progression.py:70      resolve_pause() reads pause_menu.take_result()
engine/progression.py:96        elif action == ACTION_SAVE_GAME:
                                    ctx.return_state = here
                                    ctx.go(ScreenState.SAVE_GAME)
engine/states/save_game.py    the picker. ENTER or SAVE on a row:
                                empty slot -> ctx.saves.save(id, capture(ctx))
                                occupied   -> ctx.popup "OVERWRITE SLOT n?",
                                              then the same save() on CONFIRM
```

The picker lists **the three manual slots only** — `list_slots()` filtered by
`is_autosave()`. The autosave is not a slot the player controls: `ACTION_QUIT_TO_MENU`
still writes it on the way out (`progression.__autosave`), so a save placed there by hand
would not survive the next quit. That quit-time autosave is **silent on success** now — it
used to open a "GAME SAVED" popup on top of the title screen — but still opens
`SAVE FAILED` when the write fails.

The picker *is* `ui/load_game_screen.py`: `render()` gained `title` and `confirm_label`
arguments that default to the load screen's own wording, so LOAD GAME is untouched and
still lists all four rows. `format_slot_summary()` next to `format_slot_row()` builds the
one short line the confirmation popup shows.

`ctx.pending_save_slot` now carries the slot an *overwrite* confirmation refers to as well
as the *delete* one it already did. The two screens never run at once, so they cannot
collide; the picker's row highlight is a module-level `__selected` rather than
`ctx.load_selected`, for the same reason in reverse.

**Phase 2 changed no payload field and did not bump `SAVE_SCHEMA_VERSION`** — a save
written before it loads exactly as it did, which was checked against a hand-written
pre-branch save with no `dialogue_choices` key.

---

## 2. Settings

`ui/settings_screen.py` draws exactly **four** controls; `engine/states/settings.py` wires
them. No other option exists.

| Control | Widget | Values | Runtime home | Consumer |
|---|---|---|---|---|
| MUSIC volume | slider | 0–100 | `ctx.music_volume` | `ctx.audio.set_music_volume()` |
| SFX volume | slider | 0–100 | `ctx.sfx_volume` | `ctx.audio.set_sfx_volume()` |
| Display mode | two chips | WINDOWED / FULLSCREEN | `ctx.is_fullscreen` | `settings_store.apply_display()` re-opens the window |
| TEXT SPEED | three chips | SLOW / NORMAL / FAST (15 / 30 / 60 cps) | `ctx.text_speed` | `settings_store.apply_text_speed()` |

**Is anything written to disk?** Yes — this already exists. `engine/settings_store.py`
reads and writes `<project root>/settings.json` (a real file, currently
`{"music_volume": 35, "sfx_volume": 35, "fullscreen": true, "text_speed": "FAST"}`).
It is explicitly *not* a save slot; it survives across playthroughs.

- Load: `AppContext.__init__` STAGE 2 calls `settings_store.load()` and then `apply_all()`.
  Any read failure returns a full `DEFAULTS` copy.
- Save: only the **APPLY** button persists (`settings.py:68` →
  `apply_display` → `apply_all` → `save(capture(ctx))`).
- BACK / ESC calls `__revert(ctx)`, restoring the snapshot taken in `enter()`.
- Live-edit model: sliders and chips write straight into `ctx`, so the change is audible
  immediately even before APPLY.

**Gotcha already documented in the module:** text speed must be rebound in **both**
`ui.dialog_box.TYPEWRITER_CPS` and `engine.dialogue_manager.TYPEWRITER_CPS`, because
`dialogue_manager` does `from ui.dialog_box import TYPEWRITER_CPS`, which copies the value
into its own namespace.

---

## 3. Player identity

**Storage.** `core/character/base.py::Character` holds three private fields —
`__character_id`, `__display_name`, `__current_location_id`. The id and the location are
getters only; **the display name gained a setter in Phase 1** (`set_display_name()`, which
trims and refuses a blank without changing state). `core/character/player.py::Player.__init__`
hardcodes:

```python
character_id=STUDENT_ID, display_name="CSE Student", current_location_id="campus_main"
```

**⚠ CHANGED BY PHASE 2:** `STUDENT_ID` is a module constant in `player.py`, currently
`"8324782"` — the number `play_registration.py` has always drawn on the registration
screen. It was the literal `"player_01"` when this survey was written. It is fixed rather
than generated because `save_bridge.restore()` rebuilds the Player from the constant, so a
generated id would have to be persisted or it would change on every load. `restore()` does
**not** read `player.character_id` back out of the save, so an old file naming `player_01`
still displays the current constant.

**⚠ CHANGED BY PHASE 1:** the survey said *"there is no way to change the player's name at
runtime — no setter, no name-entry screen, no prompt"*. There is now: `ScreenState.NAME_ENTRY`
(`engine/states/name_entry.py` + `ui/name_entry_screen.py`) runs between START GAME and
the opening monologue, 16 characters, letters and spaces, and a blank submit keeps the
default `"CSE Student"`. `GameSession.__init__` still constructs `Player()` with no
arguments, and the name is written onto the Player after `new_game()` rebuilds the session.

**The save file's slot for it is now read back.** `build_state(display_name=...)` writes
`player.display_name`, `save_bridge.capture()` fills it from `player.get_display_name()`,
and `SaveSlot.get_player_name()` reads it back for the slot rows. The survey found that
`save_bridge.restore()` **never applied it to the Player**, so a loaded game reverted to
the default; **Phase 1 fixed that** — it replays the saved name through
`set_display_name()`, and a save written before name entry existed carries `""`, which the
setter refuses, leaving the default intact.

**Every place identity is displayed:**

| Where | Field | Source |
|---|---|---|
| `ui/registration_screen.py:585` right panel | name + `ID: <character_id>` | `engine/states/registration.py:132` |
| `ui/stats_screen.py:260` identity block | `display_name`, `ID` | `engine/states/stats.py:32` |
| `ui/certificate_screen.py:479` | name (uppercased, falls back to `"UNNAMED STUDENT"`), `STUDENT ID` | `engine/states/certificate.py:47` |
| `ui/load_game_screen.py:140` slot row | `slot.get_player_name()`, truncated to `MAX_NAME_CHARS` | the save payload |
| HUD | **not shown** | — |

---

## 4. Scenes, areas, portals

**Level files.** `levels/*.json`, one per area. Current set: `cafeteria`,
`campus_courtyard`, `campus_library`, `campus_lobby`, `campus_main`, `field`,
`lecture_hall`, `outdoor_cafeteria`, `outdoor_lecturehall`, `outdoor_library`,
`player_room`, `university_library`. Top-level keys: `schema_version`, `meta`, `layers`,
`props`, `npcs`, `zones`.

**Two representations, one-way door.**

```
content/level_schema.py   LevelData   editable, serialisable, validated  (editor writes)
        │  engine/level_loader.py::load_level()
        ▼
engine/level_loader.py    Level       read-only view + O(1) collision grid (game reads)
```

`load_level(level_ref)` accepts an id (`"campus_main"`) or a path. In `strict` mode
(default) a file carrying §7 **blockers** is refused with `LevelLoadError`; warnings never
block.

**Loading in game.** `engine/states/exploration.py::ensure_level(ctx)` is the only entry:
if `ctx.level is None` it loads `ctx.level_id`, picks a spawn, and places the walker.

**Spawn points — three sources, in this precedence:**

1. `ctx.pending_spawn` — set by `save_bridge.restore()` from `world.spawn_x/y`, or `None`.
2. `portal.get_target_spawn()` — per-portal override set in the editor.
3. `level.get_spawn()` — the level's own SET SPAWN cell, stored in `meta`.

Each is validated with `level.is_walkable(*spawn)` and falls back to `level.get_spawn()` if
the cell is blocked. After registration, `engine/states/registration.py:17` forces
`START_LEVEL_ID = "player_room"` and clears `ctx.level` / `ctx.pending_spawn` — every term
begins in the player's own room by owner ruling.

**Two ways to travel:**

- **Portal prop** (`type_id == "portal"`, `PropData.is_portal()`) — fires the moment the
  player *steps onto* the cell, from `__check_cell_transition()`.
- **Travel interaction** (`interaction.kind == "travel"` + a `target_level_id`,
  `PropData.travels_on_interact()`) — fires on **E**. A door you open rather than a
  threshold you cross.

Both carry the same `target_level_id` / `target_spawn` fields and both go through
`exploration.__travel()`, which loads the level, places the walker, plays `page_turn`, and
re-applies the soundtrack and ambient (the router's per-screen music hook does not fire,
because portal travel stays inside `EXPLORATION`).

**Where the prompts are generated.** `engine/states/exploration.py::verb_for(ctx, cell)`
(line 168) decides the label; `ui/interaction_prompt.py` only draws it. The four labels are
constants in `ui/interaction_prompt.py:64`:

```python
LABEL_TALK    = "[E] TALK"
LABEL_ENTER   = "[E] ENTER"
LABEL_EXAMINE = "[E] EXAMINE"
LABEL_LOCKED  = "[E] LOCKED"
```

**Precedence is deliberately identical in `verb_for()` and `__interact()`** so the chip
never promises something E will not do:

```
gate (if not cleared)  ->  NPC (if interactable)  ->  portal  ->  interactable prop
```

`[E] ENTER` is produced by a portal **and** by a travel prop; `[E] EXAMINE` by any other
interactable prop. The chip is drawn in `exploration.render()` above the *facing* cell
(`walker.get_facing_cell()`), bobbing, clamped to the viewport, outlined red when locked.

---

## 5. HUD

`ui/hud.py`, drawn by `engine/state_router.py::render_overlays()` **above every state
except** `HUD_HIDDEN` (`MAIN_MENU, ENDGAME, MONOLOGUE, SETTINGS, LOAD_GAME, CERTIFICATE,
SKILL_TREE, STATS, EXAM_RESULT`).

A 44 px tan strip across the top. Left to right, packed (each helper returns the next `x`):

1. **Days** — icon, an 84×16 bar filled `time_pool / 80`, then `"{days}/80"`.
   Bar colour: green `> 30`, amber `16–30`, **red `<= 15`** (the firewall threshold).
2. **Wallet** — icon + `"{wallet:,.0f} BDT"`
3. **Semester** — icon + `"Sem {n}"`
4. **Credits** — icon + `"{credits}/140"`
5. **Location** — right-aligned, clipped to whatever gap is left after the stats; a bare
   slug like `campus_library` is de-underscored and title-cased. Dropped entirely below
   `LOCATION_MIN_W = 40` px of free space.

Call site (`state_router.py:110`) passes exactly five kwargs: `time_pool`, `wallet`,
`semester`, `credits`, `location`.

**Where a new persistent indicator would go.** The clean insertion is a **fifth stat in the
left run**, after credits, in `HUD.render()` — add a `self.__draw_stat(...)` call with its
own icon key and let it return the new `x`, then pass the new value through
`state_router.render_overlays()`. The left row is explicitly designed for this (`GAP`
between stats, each helper returns the next `x`). The right-hand slot is already taken by
the location label, and that label *already* gives way as the numbers widen — adding a
sixth left stat squeezes it further, so a long indicator is better placed left with a short
label. `HUD.__init__` loads icons from `assets/ui/icon_*.png` with a `None` fallback that
draws a placeholder square, so a missing PNG will not crash.

---

## 6. Menus / UI

**Framework.** There is no base "Screen" class. Each screen is a pair: a **stateless
drawing class** in `ui/` that owns geometry and exposes `get_*_rect()` getters, and a
**state module** in `engine/states/` that owns input and decisions. The `ui/` class never
fetches its own data (UI Style Guide §6.1). Screens are cached in a module-level
`__screen` global and built lazily by a `__ui(ctx)` helper.

**Shared widget library — `ui/ui_widgets.py`** (the palette and layout constants are also
the canonical copy):

- `Button` — `take_clicked()`, `set_enabled()`, 44 px tall
- `Slider` — `value_from_x()`, `nudge()`, `take_changed()`
- `ChipRow` — mutually exclusive chips, `get_value()` / `set_value()` / `cycle()`
- `RowTable` — **the list/scroll widget**: `set_rows()`, `get_selected()`, `get_scroll()`,
  `row_at(pos)`, `get_row_rect(i)`, internal `__clamp_scroll()` / `__scroll_into_view()`,
  and a `__draw_scrollbar()` (8 px, only when content overflows)

Editor widgets are a **separate, deliberately un-unified** set in `tools/editor_widgets.py`
(`Stepper`, `Cycler`, `TextInput`, `ChipRow`, `Slider`).

**Two list/scroll patterns in use:**

1. **Caller-owned scroll integer** — `engine/states/registration.py`. The state owns
   `ctx.reg_scroll`, the screen exposes `clamp_scroll(offset, total)`,
   `get_visible_row_count()`, `get_row_index_at(pos, scroll, total)`, and
   `get_scroll_up_rect()` / `get_scroll_down_rect()`. **The screen windows the list itself —
   the caller never slices.** Bound to ↑/↓, PageUp/PageDown, mouse wheel and the arrow
   buttons.
2. **Fixed short list, no scroll** — `engine/states/load_game.py` (always exactly 4 rows),
   `main_menu`, `activity`. Index arithmetic with `%` for wraparound (menu) or `min`/`max`
   clamping (load game).

**Modals.** `ui/popup.py` gives `Modal` (base), `MessagePopup` (one OK) and `ConfirmPopup`
(CONFIRM / CANCEL). Geometry: 600×224 centred, dim overlay `(25,18,12,160)`, ALL-CAPS
title in the severity colour, **max 3 centred body lines** (`MAX_BODY_LINES = 3` — hard
constraint), 44 px buttons.

Severity constants: `SEVERITY_INFO` (brown), `SEVERITY_WARNING` (amber), `SEVERITY_DANGER`
(red). Result codes: `RESULT_OK`, `RESULT_CONFIRM`, `RESULT_CANCEL`.

Usage pattern:

```python
ctx.message_popup.open("TITLE", ["line 1", "line 2"], SEVERITY_INFO)   # fire and forget
ctx.popup.open("DELETE SAVE?", [...], SEVERITY_DANGER)                 # then, next frame:
result = ctx.popup.take_result()                                       # None until decided
if result == RESULT_CONFIRM: ...
```

**Modal precedence** is fixed in `state_router.__modals()` — highest first:
`gate_notice` → `message_popup` → `popup` → `pause_menu`. An open modal eats every event
before the active state sees it; `exploration.__blocked(ctx)` additionally freezes movement
and hides the interaction chip.

**Pause menu** (`ui/pause_menu.py`) is an *overlay*, not a screen: six buttons —
`resume, skill_tree, stats, settings, save_game, quit_to_menu`. Callers match the **index
against the `ACTIONS` tuple**, never a label string. Opened by ESC in exploration
(`progression.open_pause`), resolved every frame by `progression.resolve_pause`.

---

## 7. Time system

| Quantity | Value | Owner |
|---|---|---|
| Semester time pool | **80 days** | `academic/semester.py::_DEFAULT_TIME_POOL_DAYS` and `Player.__time_pool_days` |
| Semesters in the degree | 12 | `content/level_registry.py::GATE_SEMESTER_MAX` |
| Global career cap | **960 days** | `GameSession.__GLOBAL_YEAR_CAP_DAYS` |
| Graduation threshold | 140 credits | `GameClock`, `EndgameEvaluationManager`, `progression.CREDIT_GOAL` |
| **Side-activity day floor** | **15 days** | `GameClock.__MIN_MAIN_QUEST_TIME_BORDER` |

**Two independent day counters exist.** `Player.__time_pool_days` and
`Semester.__time_pool_days` are separate ints. `TimeConsumable.execute_action()` deducts
only the **Player's** copy; `GameClock.process_time_consumable()` is the single place that
deducts the **Semester's** copy as well:

```python
# engine/game_clock.py:51
days_cost = action.get_time_cost()
action.execute_action(player)                    # deducts Player's pool
self.__session.increment_global_clock(days_cost) # global career clock
self.__current_semester.deduct_time(days_cost)   # deducts Semester's pool
```

**Anything that costs days must go through `GameClock.process_time_consumable()`** — this
is stated as the single entry point for all time-costing actions, and the module docstring
records the bug that arose when step 3 was skipped. The HUD and the firewall both read the
**Semester's** counter.

**The limit on days spent on side quests — the actual number is 15.**

```python
# engine/game_clock.py:93
def is_eligible_for_side_activities(self) -> bool:
    remaining = self.__current_semester.get_time_pool_days()
    return remaining > self.__MIN_MAIN_QUEST_TIME_BORDER   # 15
```

Called the "15-Day Borderline Firewall". It is enforced in exactly **one** place today:

```python
# engine/states/exploration.py:100 — inside update(), every frame
if not ctx.game_clock.is_eligible_for_side_activities():
    ctx.go(ScreenState.EXAM)
    return
```

That is a hard bounce: at ≤ 15 days the player is yanked out of exploration into the exam
screen the next frame. Nothing else consults it — NPC talk, prop triggers, the activity
card and the skill tree all run without checking. `SideQuest.execute_action()` explicitly
documents that it does *not* re-check the threshold itself. The HUD's red bar (`<= 15`)
is a separate literal in `ui/hud.py:148`, not read from `get_min_border()`.

**Where a semester rolls over.** `engine/states/exam.py::close_semester(ctx)` (line 113),
reached when every registered course has been attempted and the player presses SPACE:

```
game_clock.check_semester_end_state()   # backlog incomplete courses; freeze on 140 cr or 960 d
reset ctx.exam bookkeeping
if session.get_is_frozen():  -> ScreenState.ENDGAME
game_clock.advance_semester()           # terminate old, player.advance_semester(), fresh Semester(n+1)
ctx.gates_cleared = set()
ctx.prop_trigger_counts = {}
monologue.start_semester(...) -> ScreenState.MONOLOGUE -> ScreenState.REGISTRATION
```

`GameClock.advance_semester()` is the only mutator: it calls `Semester.terminate()` (clears
registered courses and the quest pool), `player.advance_semester()` (increments the counter
**and** resets the 80-day pool), then constructs a fresh `Semester(n)` and sets it active.
Note that `ctx.talked_npc_uids` and `ctx.triggered_prop_uids` are **not** cleared here —
only `prop_trigger_counts` and `gates_cleared` are.

---

## 8. Exams

**Trigger — three routes into `ScreenState.EXAM`:**

1. **The firewall**, automatically, from `exploration.update()` at ≤ 15 days.
2. **The activity card** — a prop with `interaction.kind = "menu"` and
   `menu_id = "activity"` opens `ScreenState.ACTIVITY`; "START EXAM" goes to `EXAM`
   (`engine/states/activity.py:61`).
3. **The `X` key** in exploration (`exploration.py:74`) — an undocumented direct jump.

**Per course** (`engine/states/exam.py`): `ExamSession(course, skill_tree)` → `start()` →
three timed questions (easy/medium/hard, `QUESTION_TIME_LIMIT_SECONDS`) answered with
A/B/C/D or by clicking → `MainQuest.attempt_qa_optimization(answers)` →
`GameClock.process_time_consumable(quest)` — **the only charge** — → `EXAM_RESULT`.

`MainQuest` costs **10 days if optimised, 14 if not** (`get_time_cost()` overrides the base
so the global clock and the player pool cannot drift). Pass ⇔ all three answers correct.
On pass: `history.record_completion()` + `player.add_credits()`. On fail:
`mark_course_incomplete()` + `add_backlog()`. A course with no question set goes straight
through with `{}` answers.

**What happens immediately after the final exam of a semester.**
`__current_course(ctx)` returns `None` once `course_index` runs past the registered list.
`render()` then draws `"ALL EXAMS ATTEMPTED — PRESS SPACE TO CONTINUE"` and
`handle_events` waits for SPACE, which calls `close_semester(ctx)` (see §7). So the
sequence is:

```
last EXAM_RESULT card --(any key)--> EXAM (empty) --(SPACE)--> close_semester()
    -> ENDGAME                         if frozen (140 credits, or 960-day cap)
    -> MONOLOGUE (semester beat) -> REGISTRATION -> [CUTSCENE if authored] -> EXPLORATION
```

There is **no side-quest hook, no "days you didn't spend" reckoning, and no NPC expiry**
anywhere in this path. `NPCManager.expire_all_for_semester()` exists and is documented as
"called when the exploration phase ends" — **nothing calls it.**

---

## 9. NPCs

**There are two parallel NPC identity systems, and they do not use the same ids.** This is
the single most important thing to get right before Phase 8/13.

### System A — the roster (narrative data)

`content/npc_roster.py::NPC_ROSTER`, keyed by a long descriptive slug:

```
warm_classmate_purnno, overachiever_classmate_rafi, struggling_friend_zayan,
late_bloomer_kabir, professor_rahman, professor_hoque, career_advisor_roya
```

Each entry: `display_name`, `location`, `role`, `personality`,
`semester_available_from`, `sprite_file`, `portrait_file`, `portrait_variants`.
`NPC_IDS` is the key list. These same keys are the top-level keys of
`content/dialogues.py::NPC_DIALOGUES`, and they are what
`DialogueManager.load_npc_dialogue(npc_id, section)` and `NPCManager.get_npc(npc_id)`
expect. `engine/npc_manager.py` builds one `core.character.npc.NPC` object per roster
entry with `character_id = <roster key>`.

### System B — the placement (level data)

`content/level_schema.py::NpcData`, one per *placed instance*, with two ids:

- `type_id` — a `content/level_registry.py::NPC_REGISTRY` key: **short** —
  `hoque, roya, kabir, zayan, purnno, rafi, rahman`
- `uid` — a stable per-file instance id assigned by the editor

`_ROSTER_ID_BY_TYPE` (`level_registry.py:600`) is the bridge:
`{"hoque": "professor_hoque", "roya": "career_advisor_roya", …}`. `_bind_roster_fields()`
runs at import and stamps `roster_id` and `min_semester` onto every `NPC_REGISTRY` entry by
reading `NPC_ROSTER`, with `_MIN_SEMESTER_FALLBACK` used only if the roster cannot be
imported.

### Which one `npc_id` must match

**The running game's NPC interaction path uses System B only.**
`exploration.__talk(ctx, npc_data)` receives an `NpcData` off the level and reads
`get_type_id()`, `get_uid()`, `get_effective_min_semester()` and `get_chains()`. It does
**not** touch `NPCManager` at all — `ctx.npc_manager` is constructed in `AppContext` and
then never used by any state module.

So: **if a later phase wants to key a side quest off "the NPC the player just talked to",
`npc_id` must be a short `NPC_REGISTRY` `type_id`** (`"rafi"`, `"hoque"`, …), because that
is what the interaction actually has in hand. Use `get_npc_roster_id(type_id)` to reach the
roster key if the narrative data is needed. Keying off `uid` would bind the quest to one
placement in one level file, which breaks the moment the editor re-places the NPC.

**Placement.** NPCs live in a level's `npcs` array. `NpcData` fields: `uid`, `type_id`,
`x`, `y`, `facing` (down/left/right/up), `interactable` (false = scenery), `dialog.chains`,
`dialog.on_complete` (`loop_last` / `loop_all` / `silent`), optional `gate`. The editor
places them with the NPC palette tool (`__apply_tool` → `level.add_npc(type_id, x, y)`) and
edits them via right-click → `NpcDialogPopup`. `Level.__npc_at` is a `{(x,y): NpcData}`
dict — **one NPC per cell**, unlike props which stack.

### Availability / visibility gating that already exists

Three separate mechanisms, only one of which actually runs:

1. **Semester gate — live.** `NpcData.get_effective_min_semester()` returns
   `max(roster's semester_available_from, this NPC's gate min_semester)` — the stricter of
   the two, so an author can delay an NPC but never pull them earlier than the narrative
   allows. Enforced in `exploration.__talk`:

   ```python
   if npc_data.get_effective_min_semester() > current_semester:
       ctx.message_popup.open("NOT YET", ["They are not around this semester."], SEVERITY_INFO)
       return
   ```

   The NPC is still **drawn and still shows `[E] TALK`** — the refusal happens after the
   player presses E. There is no visibility gating.

2. **`GateData` on the NPC — partially live.** `NpcData.get_gate()` exists and
   `Level.get_gate_at()` resolves prop-gate → zone-gate for *cells*, but
   `exploration.verb_for` / `__interact` look up gates by cell, not by NPC, so an NPC's own
   gate is only consulted through `get_effective_min_semester()`.

3. **The 0.75–1.00 availability window — dead code.**
   `core/character/npc.py::is_within_availability_window(player)` computes
   `player.get_time_pool_days() / 80.0` and returns True only in `[0.75, 1.00]` (i.e. the
   first 20 days of an 80-day term). `NPCManager.get_dialogue_lines()` uses it to pick the
   `"unavailable"` dialogue section. **Neither is called from any state module.**
   `NPC_SEMESTER_EXPIRY_DAY = 20` in `level_loader.py` is stamped onto objects built by
   `Level.build_npc_characters()`, which is also never called by the game.

**Dialogue chain selection** — moved by the 2026-08-08 amendment into
`engine/dialogue_flow.py::chain_index_for(npc_data, semester)`, behaviour unchanged:

```python
start = npc_data.get_effective_min_semester()
return max(0, min(semester - start, len(chains) - 1))
```

One chain per semester of availability, clamped at both ends — so the last chain repeats
forever. `dialog.on_complete` is stored but **not consulted** by this code path.
`ctx.talked_npc_uids.add("%s:%s" % (level_id, uid))` records the conversation.

Worked example: Roya's `min_semester` is 4 and she has 9 chains, so semesters 4–12 map to
chains 0–8 exactly, and semester 13+ would repeat the last.

---

## 10. Dialogue

**Manager.** `engine/dialogue_manager.py::DialogueManager` — the only file in the narrative
layer that imports pygame, and even then it delegates all drawing to `ui/dialog_box.py`.

Core API: `load_dialogue(lines, portrait_path=None)`, `advance() -> bool` (False = done),
`is_active()`, `get_current_line()`, `render(screen)`, `set_speaker(name)`.
Additions: `update(dt)`, `skip_reveal()`, `is_reveal_complete()`, `get_progress() ->
(current, total)`, `set_typewriter_enabled(flag)`, `load_npc_chain(chain, portrait, name)`,
`load_npc_dialogue(npc_id, section)`.

**Typewriter.** Opt-in. `__elapsed` starts as `None`, meaning "never ticked", and
`__visible_count()` then returns the whole line — so a caller that never calls `update(dt)`
sees complete lines. `skip_reveal()` jumps the clock forward rather than setting a flag.
Speed comes from the module-level `TYPEWRITER_CPS`, rebound by the settings screen (§2).

**The dialogue state.** `engine/states/dialogue.py` owns input and the return route only:

- `ctx.dialogue_return` — the `ScreenState` to go back to (default `EXPLORATION`)
- SPACE/RETURN/click → `skip_reveal()` first, then `advance()`; when `advance()` returns
  False, leave
- ESC leaves immediately

**Choice-prompt system — LIVE as of the 2026-08-08 amendment.** It used to be a dead hook
(*"Nothing sets it today"*). It is now implemented end to end.

- **Authoring.** A `DialogChain` may carry an optional `choice`, serialised into the level
  file and omitted entirely when absent, so pre-existing levels round-trip byte for byte:

  ```json
  "choice": {
    "prompt": "WHAT DO YOU SAY?",
    "options": [{"label": "Teach me how.", "goto": "s1_yes"},
                {"label": "I'll wing it.", "goto": "s1_no"}]
  }
  ```

  `goto` names another chain on the **same NPC**; `""` ends the conversation, which is what
  makes a bare accept/decline pair work without authoring a dead arm. Clamped to
  `CHOICE_OPTIONS_MAX = 4` (`content/level_registry.py`), which must stay equal to
  `ui/choice_box.py::MAX_OPTIONS` — both files carry the matching comment.

- **Runtime.** All of it lives in **`engine/dialogue_flow.py`** (a new file, so it cannot
  conflict). `engine/states/exploration.py::__talk` is now a two-line delegation to
  `dialogue_flow.start_talk()`, which also absorbed the semester gate and the chain-index
  arithmetic that used to sit inline there — that file got **smaller**, not bigger.

- **The branch opens while the last line is still on screen**, not after. `advance()` past
  the end deactivates `DialogueManager`, and an inactive manager renders nothing, so the
  reply list would otherwise float over an empty screen. `engine/states/dialogue.py`
  checks `get_progress()` and opens the choice *instead of* advancing.

- **A branch cannot be skipped.** While one is open the ChoiceBox consumes every event.
  This fixed two real bugs: SPACE/RETURN both confirm a reply *and* advance a line, and a
  click that missed a reply row used to fall through and advance past the question. ESC is
  deliberately not an escape hatch here.

- **Answers persist** in `ctx.dialogue_choices` → `world.dialogue_choices` in the save
  (§1). Read one back with `dialogue_flow.get_answer(ctx, npc, chain)`.

- **Live content:** Rafi's semester-1 chain `s1` in `levels/university_library.json` ends
  in a two-reply branch into `s1_yes` / `s1_no`. Reachable in a fresh game:
  `player_room → campus_lobby → campus_main → campus_library → university_library`.

- **Validation:** a `goto` naming a chain that does not exist is a **warning**
  (`DANGLING_CHOICE_GOTO`), not a blocker — the conversation just ends, and a typo in one
  reply must never stop a level loading.

- **Editor authoring.** `tools/editor_popups.py::NpcDialogPopup` gained an **`EDITING:
  LINES | REPLIES` toggle** on its right column. There was no room to grow the card — it is
  1080×604 centred on a 1280×720 editor — so the two lists share one table, one button row
  and one text field, which is honest anyway: a chain's lines and its replies are never
  edited at the same time.

  The REPLIES tab gives `+ REPLY / - REPLY / UP / DOWN`, a **REPLY TEXT** field, a **THIS
  REPLY JUMPS TO** cycler listing `(end talk)` plus every chain on that NPC, and a
  **PROMPT** field. Adding the first reply creates the branch; removing the last clears it,
  and no empty `choice` block is serialised. `+ REPLY` greys out at four
  (`CHOICE_OPTIONS_MAX`). The CHAINS list marks a branching chain — `s1 (3 lines,
  branches)`.

  Because the goto cycler is rebuilt from the live chain list on every refresh, it can only
  ever offer a real target — a dangling goto has to be hand-written into the JSON.

  ⚠ **A text field must never be refreshed from the model while it is being typed into.**
  `set_choice()` and `set_chain_id()` both `.strip()`, so writing the stored value back on
  each keystroke deletes a space as fast as it is typed, and the empty-label guard makes
  the last character impossible to backspace away. Both were live bugs during this work.
  Commit on every keystroke, but refresh **only the table rows** — the pattern the LINES
  side already used.

**How content is authored and stored — two independent sources:**

| Source | Shape | Consumed by | Status |
|---|---|---|---|
| **Level `DialogChain`** (`content/level_schema.py:1189`) | per-NPC-instance, `{chain_id, lines[], emotion}`, ordered list, authored in the level editor's `NpcDialogPopup`, serialised into `levels/*.json` under `npcs[].dialog.chains` | `exploration.__talk` → `load_npc_chain()` | **live — this is what plays in game** |
| **`content/dialogues.py::NPC_DIALOGUES`** | `{roster_id: {greeting[], offer[], farewell[], unavailable[]}}`, hand-written Python | `NPCManager`, `DialogueManager.load_npc_dialogue()` | **not reached by any state module** |

`content/dialogues.py` also holds `SEMESTER_INTROS` (12 entries, 3 lines each),
`DEFAULT_SEMESTER_INTRO`, `CUTSCENES` (semesters 1, 3, 4, 5, 6, 9, 12 — each
`{title, lines[]}`) and `has_cutscene(semester)`.

Note the `"offer"` section already exists in `NPC_DIALOGUES` for every NPC and is
deliberately unused — `npc_manager.py:41` explains that showing an offer line with no quest
behind it would be misleading.

---

## 11. Level editor

`tools/level_editor.py` (~95 KB) + `editor_popups.py` (~79 KB) + `editor_widgets.py`,
`editor_assets.py`, `editor_theme.py`. Run it directly; it writes `levels/<level_id>.json`.

### Prop data model — `content/level_schema.py::PropData`

Per-instance fields (registry supplies art and the *default* passthrough only):

```
uid, type_id, x, y                     identity + placement (bottom-left corner)
passthrough, pass_behind,              collision, three-way (see below)
behind_transparency, speed_modifier
interactable                           bool
kind                                   "none" | "money" | "skill" | "menu" | "travel"
amount, skill_id, menu_id              kind-specific payload
rotation                               0/90/180/270, purely visual
triggers_per_semester                  1..5
target_level_id, target_spawn          travel / portal
gate                                   GateData (omitted from JSON when open)
__extra                                unknown keys, re-emitted verbatim on save
```

`get_footprint_rect()` returns `(x, y - h + 1, w, h)` — position is the **bottom-left**
corner and the footprint runs upward. Rotation is ignored by collision on purpose.

Collision is three-way, not two toggles: `blocking` / `passthrough` / `pass behind`.
`set_pass_behind(True)` forces `passthrough = True`; `set_passthrough(False)` clears
`pass_behind`. Both invariants are enforced in the setters so older readers that only know
the `passthrough` flag still get the right answer.

### How attributes are attached

Right-click a placed prop → `LevelEditorApp.__open_entity_settings(cell)` (line 1208) →
`PropSettingsPopup(prop)`. NPCs sit above props on a shared cell, so `get_npc_at()` is
tried first.

`PropSettingsPopup` edits a **detached copy** (`PropData.from_dict(prop.to_dict())`), so
CANCEL genuinely changes nothing and OK is exactly one undo step. The result payload is the
edited prop's dict, applied by `LevelData.replace_prop(uid, dict)` in
`__consume_modal()` (line 1255), preceded by `self.__record()` (the undo snapshot).

Widgets in the popup: collision `ChipRow`, speed `Slider`, transparency `Stepper`,
interactable `ChipRow`, interaction-kind `ChipRow` over `INTERACTION_KINDS`, amount
`Stepper`, triggers `Stepper`, skill `Cycler` over `SKILL_IDS`, menu `Cycler` over
`MENU_REGISTRY`, travel `TextInput` + spawn mode. The kind chip swaps which sub-panel is
live.

### How props are moved / placed / saved

- **Place** — select a prop in the palette, click a cell. `__apply_tool()` →
  `level.add_prop(type_id, x, y)`, then `set_rotation(self.__rotation)`.
- **Erase** — eraser tool or held `X`. `__erase()` is strictly top-down: NPC → prop →
  overlay tile → ground reset to `DEFAULT_GROUND_TILE`. Ground can never be empty.
- **Re-layer** — `[` / `]` on the canvas act on the prop under the cursor
  (`__layer_target()` → `__reorder_hovered()` → `level.reorder_prop(uid, action)`), and the
  popup stages the same move via `take_layer_action()`. Actions: `back`, `backward`,
  `forward`, `front`. Status line reports "layer 2 of 3".
- **Move — NOT FOUND.** `PropData.set_position(x, y)` exists in the schema and is fully
  implemented (rejects negatives), but **the editor never calls it.** There is no drag, no
  cut/paste, no arrow-key nudge for a placed prop. Relocating a prop today means erasing it
  and re-placing it, which loses every per-instance attribute. (`NpcData.set_position()` is
  in the same position — implemented, uncalled.) Zones have a drag (`__begin_zone_drag` /
  `__finish_zone_drag`) but that creates a rectangle, it does not move an entity.
- **Save** — `__save()` (line 363): `write_level(level, level_path(level_id))` returns a
  `ValidationReport`. **Blockers abort the write** and open a `ValidationPopup`; warnings
  save and then list. Undo is a full-document snapshot stack (`UndoStack`, `UNDO_LIMIT`),
  recorded by `__record()` before every mutation, with `discard()` for a no-op move.

### How "interactable functions" are registered

There is no callback registry. A prop's behaviour is **data**: `interaction.kind` picks one
of five hardcoded branches.

```
INTERACTION_KINDS = ("none", "money", "skill", "menu", "travel")   # level_registry.py:661
```

Dispatch lives in `engine/states/exploration.py::__trigger_prop(ctx, prop)` (line 252),
in this order:

1. `menu_prop.trigger(ctx, prop)` — **before** the trigger cap, because a menu prop is a
   door, not a payout
2. `prop.travels_on_interact()` → `__travel()`
3. the per-semester trigger cap (`ctx.prop_trigger_counts[level:uid]` vs
   `get_triggers_per_semester()`), refusing with a "NOTHING LEFT" popup
4. `kind == "money"` → `player.deposit_funds(amount)`
5. `kind == "skill"` → `player.get_skill_tree().increment_skill(skill_id, amount)`
6. anything else → "There is nothing here to take."

**The one extension seam is `MENU_REGISTRY`** (`content/level_registry.py:687`):

```python
MENU_REGISTRY = {
    "registration": {"name": "Course Registration", "state": "REGISTRATION"},
    "skill_tree":   {"name": "Skill Tree",          "state": "SKILL_TREE"},
    "stats":        {"name": "Player Stats",        "state": "STATS"},
    "certificate":  {"name": "Certifications",      "state": "CERTIFICATE"},
    "exam":         {"name": "Exam",                "state": "EXAM"},
    "exam_result":  {"name": "Exam Results",        "state": "EXAM_RESULT"},
    "settings":     {"name": "Settings",            "state": "SETTINGS"},
    "load_game":    {"name": "Load Game",           "state": "LOAD_GAME"},
    "main_menu":    {"name": "Main Menu",           "state": "MAIN_MENU"},
    "activity":     {"name": "Exam / Lecture",      "state": "ACTIVITY"},
}
```

`state` is a **string naming a `ScreenState` member**, not an import — `content/` may not
import `engine/`. `engine/menu_prop.py::resolve_state()` does `getattr(ScreenState, name,
None)` and reports an unroutable id to the player rather than raising.

**Adding a new screen a prop can open is three edits and no editor change:** one
`ScreenState` member, one `MENU_REGISTRY` row, one file in `engine/states/`. The editor's
dropdown reads `MENU_REGISTRY` directly. `engine/menu_prop.py` exists specifically because
it is a new file that cannot produce a merge conflict.

**Live example:** `levels/player_room.json` already has `prop_0023` (`computer_desk_4`) and
`prop_0024` (`computer_desk_3`) with `interactable: true`, `kind: "menu"`,
`menu_id: "skill_tree"` — a working PC in the player's room.

---

## 12. Existing side quest / skill / lecture code

Substantially more exists than "nothing". None of it is wired to an NPC or a state machine.

| File | What it is | Reached by the game? |
|---|---|---|
| `academic/quest.py::Quest` (ABC) → `MainQuest`, `SideQuest` | Quest hierarchy; both implement `TimeConsumable` | `MainQuest` yes (exams); **`SideQuest` never instantiated at runtime** |
| `academic/side_quest_catalog.py` | `_SIDE_QUEST_DATA` — **the 12 topics**, `build_side_quest_catalog()`, `get_side_quest_by_id()` | **`build_side_quest_catalog()` is never called** |
| `core/skill_tree.py::SkillTree` | `{skill_id: int}`, `increment_skill`, `get_skill_level`, `is_skill_unlocked` | yes — props, exams, skill tree screen |
| `content/skill_tree_layout.py::SKILL_NODES` | 12 nodes with `display_name`, `column`, `row`, `max_level`, `requires[]`, `description` | yes — skill tree screen, `progression.py` |
| `engine/progression.py` | **derived** skill points: `completed_courses * 2` minus invested; `invest()` respects `requires` and `max_level` | yes |
| `content/lectures.py::LECTURE_SCRIPTS` | per-**course-code** `{title, lecturer, emotion, skill_id, lines[]}` | yes, via `ACTIVITY` → `LECTURE` |
| `engine/states/lecture.py` | one lecture per registered course, back to back, in the dialogue box | yes |
| `engine/states/skill_tree.py`, `ui/skill_tree_screen.py` | the tree screen | yes |
| `academic/semester.py` `add_quest()` / `get_active_quest_pool()` | per-term quest pool | **nothing ever calls `add_quest()`** |
| `core/character/npc.py` `offer_quest()`, `__quest_pointer_array` | NPC quest offering | **the array is never populated** |

`SideQuest` today: `quest_id`, `time_cost`, `title`, `description`, `exp_reward` (default
10), `academic_gate_dependency_flag` (the skill id it feeds). `execute_action()` deducts
time, `increment_skill(skill_id or "general", exp_reward)`, sets `_is_completed = True`.
There is **no state field beyond a completed bool** — the five canonical states
(Unoffered/Declined/Missed/Unlocked/Completed) have nowhere to live yet.

The catalog's twelve `quest_id`s are exactly the twelve `SQ_*` ids in the phase brief, at
a uniform **5 days / 15 EXP** each.

### Skill ids — RECONCILED by the 2026-08-08 amendment

**Saif's twelve are the source of truth.** They are what
`academic/side_quest_catalog.py` (his), `engine/endgame_manager.py` (his),
`engine/save_bridge.py` and `content/skill_tree_layout.py::SKILL_NODES` all use:

```
programming_language, dsa, git, linux_cli, databases_sql, networking,
web_app_dev, docker, ai_tools, debugging_testing, oop, technical_communication
```

**What was wrong.** `content/level_registry.py::SKILL_IDS` was a *separate* 9-entry
authoring list — `programming, algorithms, mathematics, hardware, networking, databases,
software_engineering, communication, general` — overlapping the real set on `networking`
alone. It validates both a skill prop's `skill_id` and a gate's `required_skill_id`, so
anything authored against it named a node the skill tree never draws, the save file never
stores and the endgame never counts. Three modules carried comments calling the split
"deliberate" and "owner-ruled", to be reconciled by the lead at integration.

**What changed.** `SKILL_IDS` is now **derived** from `SKILL_NODES` at import — the same
trick `_bind_roster_fields()` uses on `npc_roster`, so the tree and the editor cannot
silently disagree. `_SKILL_IDS_FALLBACK` mirrors it only so the module stays importable
standalone. `"general"` is deliberately **not** offered: `SideQuest.execute_action()` and
`exploration.__trigger_prop()` still fall back to it in code when nothing is set, but it
is not a tree node and nothing counts it, so an author must never be able to pick it.

The stale comments in `content/skill_tree_layout.py`, `engine/exam_session.py` and
`engine/gate_evaluator.py` were rewritten to match.

**Migration cost: none.** No level in the repo had a single `kind: "skill"` prop or a gate
with a skill requirement, so nothing needed rewriting. All 12 levels still validate.

**Editor labels.** `get_skill_display_name()` was added to `content/level_registry.py` and
both editor cyclers now show the tree's own node names ("Databases & SQL") instead of raw
ids, the same way the menu picker already did.

`content/lectures.py` still uses these ids plus a `"general"` bucket for non-CSE courses;
that field is a lecture attribute and is not validated against `SKILL_IDS`.

---

## 13. `dev4-aysha-narrative`

**Branch status:** `origin/dev4-aysha-narrative` is **fully merged into `origin/main`**
(`git merge-base --is-ancestor` confirms; `git diff origin/main...origin/dev4-aysha-narrative`
is empty). It is also merged into the current working branch (`2c40bd3`). There is nothing
to integrate — the files below are already present in the working tree.

Ayesha's files, all pure-data Python (no pygame, no engine imports) except
`dialogue_manager.py`:

| File | Format | Contains |
|---|---|---|
| `content/npc_roster.py` | `dict[str, dict]` + `NPC_IDS: list[str]` | 7 NPCs. Per entry: `display_name`, `location`, `role`, `personality`, **`semester_available_from`**, `sprite_file`, `portrait_file` (with an `{emotion}` placeholder), `portrait_variants[]`. **This is the semester-gating source** — `_bind_roster_fields()` in `level_registry.py` reads it at import. Values: purnno 1, rafi 1, rahman 1, zayan 2, kabir 3, roya 4, hoque 5. |
| `content/dialogues.py` | four module-level dicts | `SEMESTER_INTROS: dict[int, list[str]]` (12 × 3 lines) · `DEFAULT_SEMESTER_INTRO` · `CUTSCENES: dict[int, {title, lines[]}]` (semesters 1, 3, 4, 5, 6, 9, 12) · `has_cutscene(semester)` · `NPC_DIALOGUES: dict[roster_id, dict[section, list[str]]]` with sections `greeting`, **`offer`**, `farewell`, `unavailable` |
| `content/lectures.py` | `LECTURE_SCRIPTS: dict[course_code, dict]` | Per course: `title`, `lecturer` (a roster id), `emotion`, `skill_id`, `lines[]` (4–5 lines). Plus `get_lecture()`, which never raises and never returns None. |
| `content/epilogue_text.py` | `EPILOGUE_TEXT: Dict[str, List[str]]` | **Placeholder written by Saif, not Ayesha.** Four keys matching `ui/endgame_screen.py`'s `THEMES`: `"TOP GRADUATE"`, `"AVERAGE GRADUATE"`, `"DROP OUT Strong Skills"`, `"DROP OUT Weak Skills"`. The docstring names this the intended drop-in point for the real narrative. |
| `engine/dialogue_manager.py` | class | Ayesha's original six public methods are byte-identical; everything since is additive (see §10). |
| `engine/states/cutscene.py` | state module | Renders `CUTSCENES[semester]` through `MonologueScreen` over a blurred snapshot of the map. Reached from `registration.__confirm()` when `has_cutscene()` is true. |

**Prerequisite conditions present:** only `semester_available_from` (per NPC) and
`has_cutscene(semester)`. **Side quest structure: not found** — there is no quest data, no
day cost, no accept/decline text, and no per-semester NPC→quest mapping anywhere in
Ayesha's files. The `"offer"` dialogue section is the only thing shaped like a quest offer,
and it is 2–4 lines of flavour with no mechanics attached.

### ⚠ Two content bugs found and fixed (2026-08-08 amendment)

Both were in `levels/campus_lobby.json`, and they were the same bug seen from two sides:

1. **The level would not load at all.** `prop_0076` sat at (12,20) on a 20×14 grid, which
   is an `OUT_OF_BOUNDS` blocker, and `load_level()` runs strict — so the lobby refused to
   open. It is the **only exit from `player_room`**, which registration forces every term,
   so *the game could not leave the bedroom*. Every other level validated clean, which is
   why this went unnoticed.
2. **Roya had no dialogue.** `npc_0001` (roya, min_semester 4) carried zero chains, and the
   level warned `EMPTY_DIALOG`.

`prop_0076` was typed `"flower1"` but carried a full nine-chain `dialog` block — Roya's
entire career-advisor script, written by Ayesha, saved onto a prop record instead of onto
her NPC. `PropData` keeps unrecognised keys in a private `__extra` and re-emits them, which
is why the text survived in the file while being invisible to the game.

**Fix:** the nine chains were grafted onto `npc_0001` via `replace_npc()`, then the
malformed prop was deleted, and the file was rewritten through `write_level()`. The lobby
now validates with 0 blockers and 0 warnings. The chain count is exactly right — nine
chains for semesters 4 through 12, which is what `chain_index_for()` expects.

**Deleting the prop without reading it first would have destroyed authored narrative.**
Anything that removes a prop flagged `OUT_OF_BOUNDS` should dump its raw JSON first.

---

## 14. Tests

**Not found.** There is no test suite in this repository.

- No `tests/` or `test/` directory, no `test_*.py` / `*_test.py` anywhere
- No `conftest.py`, no `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `Makefile`
- No `.github/` workflows
- `requirements-dev.txt` is two lines: `pygame`, `pytest` — so pytest is the *intended*
  framework, and nothing has been written against it

**What stands in for tests today:** a "stub test" convention. Most `ui/` and several
`engine/` modules end with an `if __name__ == "__main__":` block that opens a pygame window
and exercises the module interactively — `ui/hud.py`, `ui/interaction_prompt.py`,
`ui/popup.py`, `ui/pause_menu.py`, `ui/dialog_box.py`, `ui/stats_screen.py`,
`content/skill_tree_layout.py` and others. `engine/save_manager.py`'s block is a headless
console round-trip that writes into `tempfile.mkdtemp()` and never touches `saves/`.
`play_sandbox.py` and `play_registration.py` are standalone harnesses.

Several modules' docstrings refer to assertions "the tests" make (e.g.
`level_registry.py:612`: *"these mirror it and are asserted equal by the tests"*). Those
tests do not exist in this checkout.

**Practical note for later phases:** on this machine `requirements-dev.txt` will not
install — `pygame` publishes no Python 3.14 wheels. `pygame-ce` is a drop-in (it still
imports as `pygame`). Headless runs need `SDL_VIDEODRIVER=dummy`.

---

## 15. Long-form text display

The engine renders no HTML. Every existing long-form format:

| # | Format | Files | Data shape | Paging | Typewriter |
|---|---|---|---|---|---|
| A | **Dialogue box** | `ui/dialog_box.py` + `engine/dialogue_manager.py`, state `engine/states/dialogue.py` | `list[str]`, one line = one screen | SPACE / click, `advance()` returns False at the end | yes, `TYPEWRITER_CPS`, `skip_reveal()` |
| B | **Lecture** | `engine/states/lecture.py` + `content/lectures.py` | `{title, lines[]}` per course code; iterates courses then lines | SPACE / click, two-stage (finish line, then advance) | yes — reuses A wholesale |
| C | **Monologue card** | `ui/monologue_screen.py`, state `engine/states/monologue.py` | `(title, subtitle, lines[])`, **the whole block on one card** | any key; first press completes the reveal, second advances | yes, block-level `get_revealed_chars()` |
| D | **Cutscene** | `engine/states/cutscene.py` | `{title, lines[]}` over a blurred map snapshot; `textwrap.wrap(line, width=72)` | SPACE / RETURN / ESC / click | yes, via C |
| E | **Modal body** | `ui/popup.py` | `list[str]`, **hard max 3 lines**, centred | button | no |
| F | **Endgame / certificate** | `ui/endgame_screen.py`, `ui/certificate_screen.py` + `content/epilogue_text.py` | `Dict[str, List[str]]` keyed by ending title | terminal screen | no |

**How content assets are stored and loaded.** Every one of these is a **Python dict or list
literal in `content/`** — there is no text-asset loader, no JSON content file, no
`assets/text/`. `content/` is pure data by convention (no pygame, no engine imports), and
modules import the dict directly (`from content.lectures import get_lecture`). The only
JSON the game reads is level files, save slots, `settings.json` and `tile_ids.json`.

**Best fit for side quest lecture sheets: format B, the lecture pattern
(`engine/states/lecture.py` + a `content/` dict).** Reasons:

- It is the closest existing analogue — it already means "a body of teaching text, paged
  through one screen at a time, with a title".
- It reuses the dialogue box, so typewriter, text-speed settings, skip-on-first-press and
  the SPACE/click contract all come for free.
- Its two-level loop (outer: which course; inner: which line) maps directly onto
  outer: which sheet; inner: which paragraph — the shape a sheet sequence needs.
- `content/lectures.py` already establishes the storage convention: a module-level dict
  keyed by a stable id, with a `get_*()` accessor that never raises and never returns None.
  A `content/side_quest_lectures.py` alongside it is a **new file**, so it cannot conflict.
- The state module is ~90 lines and is copied, not modified — a new `ScreenState` member
  plus a new file in `engine/states/` is the whole wiring cost (§11).

Format C is the runner-up if a sheet should read as a full-screen page rather than a
speech box, but it draws a fixed `LINE_PITCH = 32` column with no wrapping of its own and
no scroll, so it caps out at roughly 9 short lines per card. Format E is unusable — three
lines maximum.

**Source-material status.** `side_quest_lectures.html` is **not in this repo**. It was
located after the survey at:

    C:\Users\nanji\OneDrive\Desktop\side_quest_lectures.html

Confirmed contents: 12 `<section class="topic">` blocks, each with an `id` equal to its
`SQ_*` quest id, an `<h2>` title, and **exactly three `<p>` paragraphs** — 36 paragraphs
total, matching the extraction below. It defines no sheet boundaries of any kind, so
Decision D2 is still genuinely open.

A pre-made extraction also exists in the handover folder
`C:\Users\nanji\Downloads\changes(8-8-26)\`:

- `lecture_content.json` — `{source, note, skills[]}`, where each of the 12 entries is
  `{skill_id, title, paragraphs[3]}`. `skill_id` values are the twelve `SQ_*` ids. The
  `note` field reads: *"Engine-agnostic extraction. Sheet boundaries are NOT decided here —
  see Decision D2."*
- `lecture_content.md` — the same content as Markdown, headed *"12 skills, 3 paragraphs
  each, 36 paragraphs total"*.

⚠ The `.md` file has mis-encoded punctuation (`â€"` where an em dash belongs) — it was
written as UTF-8 and re-read as cp1252. The `.json` is clean. **Prefer the JSON** as the
Phase 11.5 input, or the mojibake will end up on screen.

Nothing has been converted. Sheet boundaries remain Decision D2.

---

## Merge-conflict risk against `main`

**Current state: clean.** `git merge-tree HEAD origin/main` produces a tree with no
conflict markers — re-checked after the 2026-08-08 amendment. The branch is 4 ahead /
1 behind; the single commit behind (`f71f429`) is main's merge of `dev4-aysha-narrative`,
which this branch already merged directly.

### Files the 2026-08-08 amendment touched

One new file, thirteen modified. All still merge clean against `origin/main`.

| File | Why |
|---|---|
| **`engine/dialogue_flow.py`** *(new)* | the whole talk-and-branch flow |
| `content/level_schema.py` | `DialogChain` choice + `NpcData.find_chain()` + validation |
| `content/level_registry.py` | `SKILL_IDS` derived, `get_skill_display_name()`, `CHOICE_OPTIONS_MAX` |
| `content/skill_tree_layout.py` | stale divergence comment |
| `engine/states/dialogue.py` | branch handling, input fixes |
| `engine/states/exploration.py` | `__talk` delegates — **net −36 lines** |
| `engine/app_context.py` | `dialogue_npc`, `dialogue_chain`, `dialogue_choices`, `choice_prompt` |
| `engine/save_manager.py`, `engine/save_bridge.py` | persist answers |
| `engine/exam_session.py`, `engine/gate_evaluator.py` | stale divergence comments |
| `tools/editor_popups.py` | skill cyclers show display names; **LINES / REPLIES tab in `NpcDialogPopup`** |
| `ui/choice_box.py` | comment tying `MAX_OPTIONS` to the schema constant |
| `levels/campus_lobby.json` | Roya's dialogue rehomed, malformed prop removed |
| `levels/university_library.json` | Rafi's authored branch |

`engine/states/exploration.py` was the file hazard #4 below warns about, and the change
followed that advice: the logic went into a new module and the state module lost a
branch rather than gaining one.

**Branch positions:** `origin/dev2-saif-academic` is 1 ahead of main;
`origin/dev3-nangiba-gui-assets` is 4 ahead; `dev1`, `dev4` and `nangiba-temp-01` are all
fully contained in main.

### Files this branch already diverges on — touch with care

These 65 files differ from `origin/main` right now. Editing one for a side-quest phase
stacks a second set of changes on top of an already-divergent file:

| File | Δ vs main | Risk |
|---|---|---|
| `content/level_schema.py` | +294 | **High** — the prop/NPC data model. Phases 10/11 land here. |
| `tools/level_editor.py` | +215 | **High** — Phase 10 (prop move) and Phase 11 (pass days) both land here. |
| `ui/map_screen.py` | +174 | Medium |
| `tools/editor_popups.py` | +160 | **High** — Phase 11 adds a prop attribute popup field. |
| `tools/editor_assets.py` | +114 | Medium |
| `content/level_registry.py` | +103 | **High** — `MENU_REGISTRY`, `SKILL_IDS`, `INTERACTION_KINDS` all live here. |
| `content/asset_scanner.py` | +71 | Low |
| `engine/level_loader.py` | +66 | Medium |
| `academic/course_catalog.py` | +34 | Low (dev2's change, already merged in) |
| `levels/*.json` | thousands of lines | **Very high** — see below |
| `content/tile_ids.json` | +17 | Low, but append-only by design |
| `tools/editor_widgets.py` | +6 | Low |

### Specific hazards

1. **Level JSON files are effectively unmergeable.** `campus_lobby.json` (±2835),
   `field.json` (±3029), `campus_main.json` (±2439), `cafeteria.json` (±1827),
   `campus_courtyard.json` (+1989) have been substantially rewritten. `lakeside.json` was
   **deleted** and `outdoor_cafeteria.json`, `outdoor_lecturehall.json`,
   `outdoor_library.json` were added. Git cannot merge these meaningfully — a conflict here
   means hand-reconciling a map. **If a phase needs a prop placed in a level, place it with
   the editor and commit that level file alone, and expect to re-do it rather than merge it
   if main also touches the same map.**

2. **`content/level_registry.py` is a shared choke point.** Phase 11 (editor pass-days),
   Phase 14 (the PC prop) and any new `MENU_REGISTRY` entry all edit it, and it is already
   +103 from main. Mitigate by **appending** to `MENU_REGISTRY` / `SKILL_IDS` rather than
   reordering or reformatting — a pure append conflicts far less than a restructure.

3. **`engine/screen_manager.py::ScreenState` uses `auto()`.** The comment at line 38 warns
   that inserting a member renumbers everything after it. **Always append.** The file is
   currently identical to main, so an append is a one-line clean merge.

4. **`engine/states/exploration.py` is the busiest shared file** even though it currently
   matches main — it owns the interaction precedence, the firewall bounce and prop
   dispatch. Phases 4, 5, 8, 13 and 17 all want a piece of it. The repo already has a
   documented mitigation pattern: `engine/menu_prop.py` exists *specifically* because a new
   module cannot conflict, and `exploration.py` carries a two-line call instead of a
   branch. **Follow that pattern** — put new logic in a new `engine/*.py` module and add
   the smallest possible call site.

5. **`whitetile1_border.png` sits in the repository root** (a stray copy of
   `assets/tiles/whitetile1_border.png`). Harmless, but it is a tracked file that differs
   from main and will show up in every diff.

6. **`docs/` did not exist before this file.** Creating it cannot conflict.

### Files that are still identical to main and are the safest to extend

*(Updated after the 2026-08-08 amendment — the table above lists what it moved out of this
set.)*

`engine/screen_manager.py` (append-only), `engine/state_router.py`,
`engine/progression.py`, `engine/menu_prop.py`, `engine/settings_store.py`,
`engine/game_clock.py`, `academic/quest.py`, `academic/side_quest_catalog.py`, `core/*`,
`content/dialogues.py`, `content/lectures.py`, `content/npc_roster.py`, all of `ui/`
except `map_screen.py` and `choice_box.py`, and every module under `engine/states/`
except `dialogue.py` and `exploration.py`.

### What Phases 1 and 2 moved out of that set

Both phases still merge clean — `git merge-tree` against `origin/main` reports no conflict
at `d52272d` — but these files now carry changes, so a later phase editing one is stacking
on top of them rather than starting from main:

| File | Phase | Change |
|---|---|---|
| `engine/screen_manager.py` | 1, 2 | `NAME_ENTRY`, then `SAVE_GAME` — **appended**, per hazard #3 |
| `engine/state_router.py` | 1, 2 | both appended to `HUD_HIDDEN`, nothing else |
| `engine/progression.py` | 2 | `ACTION_SAVE_GAME` routes to the picker; `__save` became `__autosave` |
| `engine/save_bridge.py` | 1 | `restore()` replays the saved display name |
| `engine/states/main_menu.py` | 1 | START GAME routes to `NAME_ENTRY` |
| `core/character/base.py` | 1 | `set_display_name()` |
| `core/character/player.py` | 2 | the `STUDENT_ID` constant |
| `ui/load_game_screen.py` | 2 | `title` / `confirm_label` render arguments, `format_slot_summary()` |
| **`engine/states/name_entry.py`**, **`ui/name_entry_screen.py`** *(new, Phase 1)* | 1 | — |
| **`engine/states/save_game.py`** *(new, Phase 2)* | 2 | — |

Both phases followed hazard #4's pattern: the new logic went into new modules that cannot
conflict, and the shared files took the smallest possible call site.

**Lowest-risk shape for the side-quest work overall:** new files in `content/`
(quest data, lecture sheets), new files in `engine/` (the state machine, the offer service),
new files in `engine/states/` (the reader screen), and append-only edits to
`ScreenState` and `MENU_REGISTRY`.

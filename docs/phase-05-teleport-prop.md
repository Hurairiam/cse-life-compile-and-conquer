# Phase 5 — Teleport Prop and Menu

**Covers:** Change 7
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-08
**Commit:** `[Sprint 4] Add teleport prop with destination menu`

---

## What the recon found

### There is no registry of map locations, and adding one would have been wrong

An area **is** a file in `levels/`. `content/level_schema.py::list_level_files()` is the
only enumeration that exists, and each file's `meta` block carries `level_id`,
`level_name` and one SET SPAWN cell. Nothing lists the areas anywhere in Python — not the
HUD, which prints whatever `Level.get_level_name()` returns, and not the editor, which
opens a file picker over the folder.

The one thing joining two areas is a prop carrying a `target_level_id`: a step-on portal
(`type_id == "portal"`) or any prop given the `travel` interaction kind. So the campus is
already a **directed graph the level files describe**, and the twelve maps split into two
groups on it:

| Reachable on foot from `player_room` (9) | Nothing walks into (3) |
|---|---|
| `player_room` → `campus_lobby` → `campus_main` | `outdoor_cafeteria` *(no portals at all)* |
| `campus_main` → `cafeteria`, `campus_library`, `field`, `lecture_hall` | `outdoor_lecturehall` *(no portals at all)* |
| `campus_library` → `university_library` | `outdoor_library` *(portals out, none in)* |
| `field` → `campus_courtyard` | |

Four of the twelve still carry a bare slug in `meta.level_name` (`campus_library`,
`field`, `outdoor_cafeteria`, `outdoor_lecturehall`), and `player_room` carries
`Player_Room`.

### The "new interactable function" seam already existed

`INTERACTION_KINDS` is five hardcoded branches in `exploration.__trigger_prop`, but that
is not where a new prop behaviour goes. `MENU_REGISTRY` (`content/level_registry.py`) is,
and the recon says so outright: *"Adding a new screen a prop can open is three edits and
no editor change."* `engine/menu_prop.py` resolves `menu_id → ScreenState` by name, and
the editor's picker is a `Cycler` built from `get_menu_ids()` / `get_menu_display_name()`
(`tools/editor_popups.py:617`) — it reads the dict, so a new row appears in the dropdown
on its own.

### The list widget existed too, and nothing had ever used it

`ui/ui_widgets.py::RowTable` is the shared game-side scroll control — 38 px rows on a
44 px pitch, wheel and up/down, an 8 px scrollbar drawn only on overflow. It is fully
implemented, has its own stub test, and is referenced by **no screen in `ui/`**. Every
screen so far either hand-rolled a scroll integer (`registration.py`) or had a list short
enough not to need one (`load_game`, `main_menu`, `activity`).

---

## Owner rulings

Two questions were put before anything was written, both answered:

1. **The nine walk-reachable areas** — *"and any new levels created and added in the
   future that will be walk-reachable as well."* That turned the destination list from a
   constant into something that has to be **derived**, which is the shape of the whole
   phase.
2. **Phase 4's remembered position**, falling back to the area's SET SPAWN on a first
   visit.

Stated rather than asked, and not contradicted: teleporting costs **no days** and no
trigger budget.

---

## What was built

Three new files and two one-line appends. Nothing else was opened.

### `content/map_directory.py` — the destinations, derived

```
walk_reachable()  ->  [(level_id, display_name), ...]
```

Reads every map through `content/level_schema.py`, collects each one's
`target_level_id`s, and walks the graph breadth-first out from `ROOT_LEVEL_ID`
(`player_room`, which `engine/states/registration.py` forces at the top of every term).
Nine areas come back, in the order the player learned them:

```
Player Room · Campus Lobby · Campus Main · Cafeteria · Campus Library
Field · Lecture Hall · University Library · Campus Courtyard
```

**A map wired to an existing one appears with no Python to edit.** A map nothing leads
into does not, because teleport would then be its only door in *and* its only door out —
which reads as a broken level, not a feature.

`display_name()` de-underscores and title-cases a bare slug exactly the way
`ui/hud.py:205` already does for the location strip, so `outdoor_library` reads as
"Outdoor Library" in both places instead of one of them shouting a filename. An authored
name always wins.

Gates are ignored on purpose: a locked door still *joins* two areas, and whether the
player may pass it is `engine/gate_evaluator.py`'s ruling, made at the door.

Pure data — no pygame, no engine imports — reading the levels folder the way
`content/asset_scanner.py` reads the assets folder. Rebuilding the graph costs ~11 ms
across twelve maps, so it is cached against a **fingerprint of the folder's paths and
mtimes**: cheap enough to recheck on every menu open, and a map saved by the editor is
picked up rather than cached out of existence.

### `ui/teleport_screen.py` — the card

A card over a dimmed map, the relationship `ui/activity_choice_screen.py` already has
with the world, because the player is answering the thing they are standing next to.
`WHERE TO GO?`, a subtitle naming where they are, the list, `GO` / `BACK`, and the hint
line.

The list is **`RowTable`**, imported rather than reimplemented. A fifth hand-rolled
scroll offset is exactly what the shared widget library exists to prevent. The palette
and card geometry are still this file's own copies (Build Plan §0.5) — a widget is
imported, a screen's colours never are.

The table is **five rows tall against nine destinations**, so the scrollbar is a live
part of the design rather than something that only appears if somebody adds enough
levels. The area the player is standing in is filled `ROW_GREEN` and suffixed
`· YOU ARE HERE`.

One thing worth naming: the card is centred on whatever surface it is drawn onto, so the
table's rect is not known until then. `__sync()` parks it before **every** public entry
point, not just `render()` — a hit test run against last frame's rect after a resize
would select the wrong row.

### `engine/states/teleport.py` — the decisions

Input, refusals and the level swap. Selection and scroll live in the widget; the two
module-level globals are the screen and the current destination list, kept off `ctx` the
way `engine/states/save_game.py` keeps its row highlight — **`engine/app_context.py` was
not touched at all**, which matters more than usual this week (see below).

`__travel()` is deliberately **not** a call into `exploration.__travel()`. That one is
driven by a portal prop it reads a target and a spawn override off, and there is no prop
here; `exploration.py` is also the file the recon names the busiest shared one in the
repository. The dozen lines it would have taken to generalise it live in a new file that
cannot conflict with anybody — the same ruling `engine/menu_prop.py` and
`engine/return_points.py` were both made under.

Music and ambient are **not** set there. Handing control back to `EXPLORATION` fires its
`enter()`, which calls `soundtrack.apply_for_level()` and `play_ambient()` off the level
that is loaded by then. Doing it twice would only restart the loop.

Both refusals say why rather than doing nothing, matching what `activity.py` does with a
greyed entry: `GO` is already drawn muted in both cases, and a muted button the player
presses anyway is a question.

### The two appends

```python
# engine/screen_manager.py
TELEPORT = auto()                                    # appended, per hazard #3

# content/level_registry.py
"teleport": {"name": "Teleport", "state": "TELEPORT"},   # appended, per hazard #2
```

`engine/state_router.py` needed **no** edit: `ScreenState.TELEPORT.name.lower()` resolves
to `engine/states/teleport.py` on its own, and the card sits over the map, so the HUD
stays up the way it does on the `ACTIVITY` card.

---

## Arriving, and the one thing that does not happen

`return_points.arrival(ctx, level, level.get_spawn())` — read-only. An area the player
has been in before opens where they left it; a first visit opens at its SET SPAWN. A
remembered cell that no longer works falls through Phase 4's own two-step chain to the
spawn. Arriving by teleport is therefore indistinguishable from arriving on foot, which
is the point.

**Teleporting *away* records nothing, and that is a real consequence worth stating.**
Phase 4 files a return point when the player steps through a doorway; this is not one,
because there is no threshold to step back from. So an area still remembers the last time
it was *walked* out of, and an area only ever *teleported* out of keeps opening at its
SET SPAWN. Making teleport file its own entry means writing into Phase 4's table from
outside the module that owns it — which is Phase 4's work, not this phase's, and the
brief puts it out of scope.

---

## Merge-conflict risk

**Phase 5 adds zero conflicts.** `git merge-tree --write-tree` against `origin/main`
produces the *byte-identical* conflict set with and without this phase's changes.

- The three new files cannot conflict.
- `content/level_registry.py` and `engine/screen_manager.py` **auto-merge silently** —
  neither appears in the merge output at all. Both are pure appends at the end of a
  block, which is what hazards #2 and #3 ask for, and the merged result reads correctly
  with main's own entries intact.

⚠ **`origin/main` had moved 10 commits since Phase 4's log was written, and HEAD
conflicted with it in three files this phase never opened** — `engine/app_context.py`,
`engine/states/dialogue.py`, `engine/states/exploration.py`, all from
`#23 dev2-saif-academic` and `#24 dev4-aysha-narrative`. Those conflicts existed at
`819a068` before any Phase 5 change and were unchanged by it.

**They were resolved in a follow-up merge commit, on the owner's instruction** — see
"Integrating `origin/main`" below.

`levels/cafeteria.json` was already modified in the working tree when this phase started
and was **left untouched and uncommitted** throughout, including across the merge.

---

## Files changed

| File | Δ | Why |
|---|---|---|
| `content/map_directory.py` *(new)* | +193 | the derived destination list |
| `ui/teleport_screen.py` *(new)* | +372 | the card, the list, the buttons |
| `engine/states/teleport.py` *(new)* | +227 | input, refusals, the level swap |
| `content/level_registry.py` | +3 | one `MENU_REGISTRY` row |
| `engine/screen_manager.py` | +3 | one `ScreenState` member |

No level file was touched — the prop is placed in the editor, by hand, which is the whole
point of registering the function rather than hardcoding it.

---

## Verification

Headless, `SDL_VIDEODRIVER=dummy`. **63 checks, all passing.**

### Unit — the derived list

| Case | Result |
|---|---|
| Nine areas reachable on foot | pass |
| Breadth-first walking order out from `player_room` | pass |
| The three orphan maps excluded | pass |
| Slug `level_name` title-cased; authored name kept; `Player_Room` → `Player Room` | pass |
| `display_name` falls back to the id, leaves mixed case alone, and handles blank | pass |
| Repeat call identical; the caller cannot mutate the cache | pass |
| **A new map wired to an existing one is listed automatically** | pass |
| **A new map nothing walks into is not listed** | pass |
| A new map's name derived from its id | pass |
| An mtime change re-derives instead of serving the cache | pass |
| An unparseable map is skipped, not raised on | pass |
| An unknown root degrades to the whole folder, sorted | pass |
| An empty folder is an empty list; the real folder is unaffected throughout | pass |

### Unit — the registration seam

| Case | Result |
|---|---|
| `teleport` in `MENU_REGISTRY`, and last — appended, not inserted | pass |
| The editor dropdown offers it, labelled "Teleport" | pass |
| `menu_prop.resolve_state("teleport")` is `ScreenState.TELEPORT` | pass |
| `TELEPORT` appended to the enum; all 18 earlier members kept their number | pass |
| The router resolves `TELEPORT` to a real module | pass |
| All 12 maps still load and still validate | pass |
| `tools/level_editor.py` and `tools/editor_popups.py` still import | pass |

### End to end — a real `AppContext` on the real maps

| Case | Result |
|---|---|
| A `kind: menu` / `menu_id: teleport` prop is handled by `menu_prop` and opens `TELEPORT` | pass |
| `return_state` points back at the map | pass |
| The menu lists the nine areas; exactly one row is labelled `YOU ARE HERE`, and it is the current one | pass |
| Selection opens off the current area, so ENTER is never a refusal | pass |
| Subtitle names where the player is | pass |
| Content overflows the table; selecting the last row scrolls it; the wheel scrolls it back | pass |
| Picking the current area is refused and says why, and moves nobody | pass |
| Picking elsewhere travels and hands control back to the map | pass |
| **First visit lands on the area's SET SPAWN** | pass |
| **Return lands on Phase 4's remembered cell** — `(12, 7)`, not the spawn | pass |
| A blocked remembered cell falls back through Phase 4's chain | pass |
| `last_cell` follows the walker | pass |
| ESC and BACK leave without moving; GO travels; a row click selects without travelling | pass |
| UP / DOWN step the highlight | pass |
| The card renders over the map without raising | pass |
| **Teleporting costs no days** — semester pool and global career clock both unchanged | pass |
| No per-semester trigger is consumed | pass |
| A destination whose file is gone reports and moves nobody | pass |

**Manual acceptance** (the brief's own test): set a prop's interaction kind to `menu` and
its menu to **Teleport** in the level editor, save, then press **E** on it in game — the
`WHERE TO GO?` card opens over the map with a scrollable list of the nine areas, and
picking one puts the player there.

---

## Integrating `origin/main`

Done after Phase 5 shipped, on the owner's instruction, as a separate merge commit so the
teleport work stays reviewable on its own.

### The maps were never at risk

Recon hazard #1 calls level JSON effectively unmergeable, so the merge was rehearsed in a
throwaway `git worktree` first. It touched **no level file at all** — `git diff HEAD --
levels/` after the trial merge was empty. This branch's maps already descend from main's,
so there was nothing to reconcile; the enormous `git diff HEAD origin/main` over `levels/`
is one-sided evolution, not divergence.

### The real conflict was one feature written twice

Both branches built dialogue branching, independently, on the same widget:

| | this branch (`dev3`) | `origin/main` (`#24`) |
|---|---|---|
| Lives in | `engine/dialogue_flow.py` | inlined in `exploration.__talk` + `dialogue.py` |
| What opens the reply list | an authored per-chain `choice` block with `goto` targets | one fixed Accept / Decline per semester, from `content/npc_quest_offers.py` |
| Persisted | yes, `ctx.dialogue_choices` → the save | `ctx.unlocked_side_quests` / `decided_quest_semesters` |
| Shared | `ctx.choice_options`, `ui/choice_box.py` | same |

Main had **re-inlined into `exploration.__talk` the ~36 lines the 2026-08-08 amendment
took out of it**, and built the quest offer on top. Taking either side wholesale would
have deleted a shipped feature, so both were kept.

### How it was resolved

- **`engine/states/exploration.py` → ours verbatim, zero net change.** Main's inlined
  semester gate, chain pick and portrait lookup are what `dialogue_flow.start_talk()`
  already does. The quest-offer arming moved into `dialogue_flow` instead, so the busiest
  shared file in the repo still carries a two-line call and no branch.
- **`engine/dialogue_flow.py`** gained the offer as a second, clearly separated section:
  `arm_offer()`, `open_offer()`, `is_offer_open()`, `resolve_offer()` and the
  `OFFER_*` constants. It now owns the whole conversation flow, both reasons the reply
  list can open.
- **`engine/app_context.py`** — union. `choice_prompt` (ours) and main's five quest fields
  both survive, plus one new `quest_offer_open` flag, because two things can now dock the
  same widget and the answer routes differently for each.
- **`engine/states/dialogue.py`** — both advance paths, in a defined order:

  ```
  last line still on screen  ->  authored branch      (open_choice)
  chain has actually run out  ->  semester offer      (open_offer)
  ```

  An authored branch is asked first because it is part of the chain being told. The offer
  is second because it *replaces* the chain with its own lines — which is also why our
  "ask before `advance()` deactivates the box" rule does not apply to it.

Two behaviours were reconciled rather than merged:

- **ESC during a choice.** Main let it leave; ours swallows it, deliberately and with the
  reasoning in the docstring. Ours kept — it also stops ESC skipping a quest offer, which
  is strictly better for main's feature than what main shipped.
- **An offer left unanswered.** Only `resolve_offer()` writes `decided_quest_semesters`,
  so walking out mid-conversation re-asks next time instead of silently burning the term's
  one offer.

**No collision exists in the shipped content:** semester 3's offer is Rafi's, and Rafi's
only authored branch is on his semester-**1** chain, so the two never contend for the
widget. The order above is what would happen if they ever did.

### Verification — 63 further checks, all passing

| Group | Cases |
|---|---|
| Context | all eight fields from both sides present; `quest_intro_popup` is a real modal and the router dispatches it; roster bridge intact |
| **Authored branch (ours)** | Rafi's `s1` plays; the branch docks at the last line and is *not* the offer; the authored prompt is used; ESC cannot skip it; the answer lands in `ctx.dialogue_choices`; the `goto` jumps to the follow-up chain |
| **Quest offer (main)** | arms only for the named NPC; docks once the chain runs out; offer lines replace the chain with the box still up; Accept unlocks the quest id and plays `accept_lines`; Decline unlocks nothing but still decides; re-talking does not re-ask; leaving mid-talk re-arms next time |
| **Both together** | in semester 3 Rafi arms an offer while off his branching chain, and only one reply list is ever open |
| Regression | all 12 maps load and validate; `main`, both editor modules, `save_bridge`, `state_router`, `teleport` and `map_directory` all import; the save still carries `dialogue_choices` *and* `return_positions` at `schema_version` 1 |

Phase 5's own 63 checks were re-run after the merge and are still green — **126 in total**.

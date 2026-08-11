# Phase 10 — Level Editor: Move Props Without Losing Attributes

**Covers:** Change 11
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] preserve prop attributes when moving props`

---

## Step 1 — the current move / place code path, reported before anything was written

### Placing

```
__handle_mouse_down   tools/level_editor.py:1146
  → __begin_stroke    tools/level_editor.py:950
    → __apply_tool    tools/level_editor.py:696
      → LevelData.add_prop(type_id, x, y)   content/level_schema.py:2025
        → PropData(uid, type_id, x, y)      content/level_schema.py:707
```

The `PropData` constructor takes **four arguments**. Every other field is set to a
default — the registry's `default_passthrough`, `pass_behind=False`, the default
transparency, `speed_modifier=1.0`, `interactable=False`, `kind="none"`, `amount=0.0`,
`skill_id=None`, `menu_id=""`, `rotation=0`, the default trigger cap,
`target_level_id=""`, `target_spawn=None`, an open `GateData()`, an empty `__extra`.
`__apply_tool` then stamps the brush rotation on, and nothing else.

### Erasing

```
__begin_stroke → __erase                   tools/level_editor.py:721
  → LevelData.remove_prop_at(x, y)         content/level_schema.py:2043
    → get_prop_at(x, y); self.__props.remove(prop)
```

The configured object is dropped and left unreferenced. No copy, no clipboard, no stash.

### There was no move path at all

`__apply_tool` and `__erase` were the **only** two writers of prop placement.

- `PropData.set_position()` (`level_schema.py:745`) is fully implemented and rejects
  negatives. **The editor never called it** — `set_position` had zero hits anywhere under
  `tools/`. `NpcData.set_position()` (`level_schema.py:1424`) was in the same state.
- `LevelData.replace_prop()` (`level_schema.py:2120`), the settings-popup commit path,
  **explicitly pins the cell back**: `merged["x"], merged["y"] = prop.get_position()`. So
  even the right-click popup could not relocate anything.
- `[` / `]` → `__reorder_prop` (`level_editor.py:772`) reorders the list. It never touched
  coordinates.
- The only drag in the editor was `__begin_zone_drag` / `__finish_zone_drag`
  (`level_editor.py:817` / `:833`), which draws a rectangle — it does not move an entity.

### Why the attributes were lost — yes, a move destroyed and recreated the prop

The only way to relocate a prop was erase-then-place: `remove_prop_at()` discarded the
configured `PropData`, then `add_prop()` built a **brand-new** one from the four-argument
constructor. **Three** things were lost, not one:

1. **Every per-instance attribute**, because the new object came from registry defaults.
2. **The uid** — `add_prop` calls `__next_uid("prop")`, so `prop_0023` came back as
   `prop_0081`. Saves key `triggered_prop_uids` and `prop_trigger_counts` on
   `"<level_id>:<uid>"`, so an existing save lost that prop's trigger history.
3. **The layer** — the new prop is appended, so it reappeared on top of whatever stack it
   had been layered into.

This was never theoretical. Recon §11 records it, and the Phase 9 log records four NPCs
re-placed exactly this way, silently dropping 44 authored dialogue chains.

### Every attribute that must survive a move

Complete, from `PropData.__init__` (`level_schema.py:707`) and `to_dict` (`:1087`):

| Attribute | Serialised as |
|---|---|
| `uid` | `uid` — identity; saves key trigger history on it |
| `type_id` | `type_id` |
| `passthrough` | `passthrough` |
| `pass_behind` | `pass_behind` (omitted when false) |
| `behind_transparency` | `behind_transparency` (written with `pass_behind`) |
| `speed_modifier` | `speed_modifier` |
| `interactable` | `interactable` |
| **the interactable function** (`kind`) | `interaction.kind` — none / money / skill / menu / travel |
| `amount` | `interaction.amount` |
| `skill_id` | `interaction.skill_id` |
| `menu_id` | `interaction.menu_id` (omitted when unset) |
| `triggers_per_semester` | `interaction.triggers_per_semester` |
| `rotation` | `rotation` (omitted when 0) |
| `target_level_id` | `target_level_id` (travel / portal only) |
| `target_spawn` | `target_spawn` |
| `gate` | `gate` (omitted when open) — min semester, required skill + level, min credits, min days, min wallet, required courses, graduation flag, day/money cost, locked title and lines |
| **`__extra`** — unknown keys read from the file | re-emitted verbatim |
| **list position** = the layer | array order inside `props` |

**Assigned dialogue is not a prop attribute.** Dialogue lives on `NpcData.dialog.chains`.
The only dialogue ever found on a prop was the `campus_lobby` bug (recon §13), and it
survived purely because of `__extra`, which is on the list above.

**NPCs additionally carry:** `facing`, `interactable`, `dialog.chains` (each with its
lines, emotion and optional `choice` branch), `dialog.on_complete`, `gate`, `__extra`.

---

## Owner rulings

Reported first, then asked, then built. Two answers came back.

1. **The gesture is a MOVE tool in the palette**, beside the existing ERASE slot, rather
   than a modifier key, a no-tool drag, or coordinate steppers in the settings popup.
2. **NPCs move too, not props only.** `NpcData.set_position()` was implemented and
   uncalled in exactly the same way, and an NPC carries far more that a re-place destroys.
   Phase 9's loss was NPCs.

A third question was **not** asked, because the answer turned out to be "no change":
the brief says to ask before touching the prop data model or the level file format.
Neither needed touching. `PropData.set_position()` already existed, `x` / `y` already
serialised, and `LevelData.get_prop_by_uid()` hands back the live object — so the whole
feature fits inside one file.

---

## What was built

**One file changed: `tools/level_editor.py`.** No `content/` edit, no schema method added,
no JSON key added or moved, no `SCHEMA_VERSION` bump.

### The tool

`TOOL_MOVE` / `MOVE_KEY` join `TOOL_ERASER` / `ERASER_KEY`. `__rebuild_palette` adds a
`move` item to the **PROPS and NPCS** palettes — not TILES, because a tile is a cell of
the grid, not a placed entity, so there is nothing there to pick up. Selection is shared
across every tab already, so the tool stays live after switching away from the tab it was
picked from.

The slot draws its own four-way-arrow glyph (`__move_glyph`), the way the eraser draws its
own X. Falling through to the generic placeholder square would have left the two tool
slots looking identical, and "the tool with no art" is not something an artist can fix.
It is marked `[ICON PLACEHOLDER: assets/ui/icon_move.png]` per Style Guide §5.2.

### The drag

| Step | Where |
|---|---|
| press | `__begin_stroke` → `__begin_move` — records the uid, the origin cell and the grab offset. **The document is not touched** |
| hold | `__render_move_hover` ghosts the entity over the destination |
| release | `MOUSEBUTTONUP` → `__finish_move` — one `__record()`, one `set_position()` |
| ESC mid-drag | `__cancel_move`, keeping the MOVE tool selected |

**What it picks up:** NPC first, then the topmost prop — the same top-down order
`__erase` and `__open_entity_settings` already use, so what you can grab is exactly what
you can see and right-click.

**Coverage, not anchor.** `get_prop_covering()` answers for a prop's whole footprint, so a
2×3 vending machine can be grabbed by its canopy as well as its base. The eraser
deliberately keeps using the anchor, because peeling a stack one layer at a time needs a
precise cell; a drag needs whatever is under your hand. The grab offset is kept, so a prop
dropped by its canopy does not jump two cells up the screen on release.

### Why nothing is lost

`set_position()` moves the **object**. Its uid, every per-instance attribute and its index
in the prop list — which *is* the draw order — are all untouched, because none of them is
rebuilt. That is the entire fix.

The drag is held as a **uid, not an object reference**, so a Ctrl+Z mid-drag re-resolves
against whatever document the drop lands in rather than writing into a `LevelData` the
editor has already thrown away.

### Refusals

| Case | Behaviour |
|---|---|
| drop would put the anchor outside the grid | refused, `"Outside the grid — nothing moved"`, no undo step |
| an NPC dropped on a cell that already holds one | refused, `"An NPC is already on that cell"`, no undo step |
| press and release on the same cell | nothing happens, and **no undo step is recorded**, so Ctrl+Z still undoes whatever came before |
| press on an empty cell | `"Nothing here to move"` |
| release with the cursor off the canvas | the drag is dropped harmlessly |

The NPC refusal is deliberate and is the same class of bug this phase exists to fix:
`add_npc()` resolves the one-NPC-per-cell rule (Spec §4.3) by **deleting** the sitting
tenant, and silently destroying an authored NPC — dialogue chains and all — is exactly
what must not happen. Props stack freely, so they have no such rule.

### On-canvas feedback

- **Idle**, the tool outlines the whole **footprint** of the entity under the cursor in
  green. A single-cell outline would lie about which prop a click on a tree's canopy picks
  up.
- **Dragging**, it ghosts the entity at 50 % alpha over the destination and outlines it
  green (legal) or red (refused). The original stays drawn where it is until the button
  comes up, so the move reads as a from-and-to rather than as the prop teleporting under
  the hand.
- The panel footer reads `DRAG A PLACED PROP OR NPC` / `KEEPS UID, SETTINGS, LAYER`, in
  the eraser's two-line help slot.
- The status line names the prop and, for props, the layer it landed on —
  `computer desk 4 moved to (9,0) — layer 1 of 1` — the same readout `__reorder_prop`
  already prints.

### Interactions with what was already there

- **Held `X` still wins.** The move branch sits *after* the eraser check in
  `__begin_stroke`, so X+LMB erases whatever tool is selected, exactly as documented.
- **`__painting` is never set** by a move: it is one gesture with one result, not a stroke
  over cells, so `__continue_stroke` is untouched.
- **ESC** cancels a drag in flight instead of clearing the selection, because dropping the
  MOVE tool as well would mean re-selecting it to retry the same move. With no drag in
  flight ESC still clears the selection as before, and `__clear_selection` cancels any
  drag, so opening a file or switching tools mid-drag cannot strand one.
- **`__layer_uid`** is pointed at a moved prop, so `[` and `]` keep acting on the piece
  just dropped.

---

## What this phase deliberately did not do

- **No data model change and no file format change.** Not one line of
  `content/level_schema.py` or `content/level_registry.py` was opened.
- **No new schema method.** A `LevelData.move_prop()` helper was considered and rejected:
  `get_prop_by_uid()` already returns the live object, so the helper would have bought
  nothing and would have put this phase into the highest-risk shared file on the branch.
- **No new interactable function.** Phases 5 and 11 own those.
- **No prop rendering change.** The ghost and the outlines are drawn by the hover layer,
  which already existed for the placement preview; `__render_entities` was not opened.
- **`levels/campus_main.json` and the eight untracked `assets/props/*.png`** are the asset
  track's, not this phase's, and stayed out of the commit — the same way Phases 8 and 9
  left them.

---

## A pre-existing bug found in passing, reported and not fixed

`PropSettingsPopup` rewrites an EXP `amount` that sits below `MONEY_MIN`. Its amount
`Stepper` is **constructed** on the money range (`MONEY_MIN = 50.0`) and re-ranged to the
EXP one (`EXP_MIN = 1`, `EXP_MAX = 10`) by `__retune_amount()` afterwards, so a stored
value of `5.0` is clamped up to `50.0` and then down to `10.0` on the way through. Opening
a `kind: "skill"` prop and pressing OK is enough to change its payout.

Reproduced with `PropData` + `PropSettingsPopup` alone, touching none of this phase's
code, and left alone: it is a widget-ordering bug in `tools/editor_popups.py`, on a path
Phase 10 does not open, and fixing it would be scope creep into a file Phase 11 also
wants. It is asserted in the harness so it cannot be mistaken for a move regression.

---

## Merge-conflict risk

**Phase 10 adds no conflicts.** `git merge-tree --write-tree HEAD origin/main` produces a
clean tree with and without this phase's commit. The branch is 19 ahead / 0 behind.

- `tools/level_editor.py` — recon hazard: already +215 from main and named as Phase 10's
  and Phase 11's landing site. This phase's share is **312 added lines, 3 changed**: new
  constants appended beside the existing tool constants, four fields appended to
  `__init__`, one new private section, and single-line insertions into
  `__rebuild_palette`, `__palette_sprite`, `__clear_selection`, `__tool_readout`,
  `__begin_stroke`, `__handle_key`, the `MOUSEBUTTONUP` arm, `__render_hover` and the
  palette footer. Nothing was reordered, renamed or restructured — the
  appended-not-restructured shape hazard #2 asks for.
- `content/level_schema.py` — recon calls it **High** risk and already +294 from main.
  **Not opened.**
- `content/level_registry.py` — the shared choke point. **Not opened.**
- `tools/editor_popups.py` — Phase 11's landing site. **Not opened.**
- `levels/*.json` — hazard #1 calls these effectively unmergeable. **None written.**
- `engine/states/exploration.py` — hazard #4's busiest file. **Not opened.** The game
  reads a moved prop's new `x` / `y` with no engine change at all, because the level
  loader already read them.

---

## Verification

Headless, `SDL_VIDEODRIVER=dummy`, `pygame-ce 2.5.7` / Python 3.14.6.
**121 checks, all passing.** The harness drives the **real `LevelEditorApp`** with real
`pygame` events through a temporary levels directory, so the repo's `levels/` are never
written.

The fixture is one level carrying: a fully configured prop (walk-behind at 60 %, speed
0.5, interactable, `kind: "skill"`, amount, skill id, 4 triggers, rotation 180, a gate
with every requirement, cost and locked message filled in) plus a hand-planted unknown
JSON key; a travel prop with a destination and a custom spawn; a deliberate two-prop
stack; a 2×3 multi-cell prop; and an NPC with two dialogue chains, a two-reply `choice`
branch, a facing and a gate.

| Group | Case | Result |
|---|---|---|
| Tool | MOVE is in the PROPS and NPCS palettes and **not** in TILES | pass |
| | ERASE is still in all three; select / unselect / readout / glyph | pass |
| **Attributes** | **prop dragged 6 times across the map: every one of the 12 serialised fields identical in memory** | pass |
| | **the same after SAVE and re-READ from disk** | pass |
| | the hand-planted unknown JSON key survived six moves and a save | pass |
| | `x` / `y` are the **only** difference from the pre-move dict | pass |
| | uid unchanged after six moves | pass |
| Travel | `target_level_id`, `target_spawn` and the whole `interaction` block survived | pass |
| **NPC** | **moved 3 times: both dialogue chains, every line, the `choice` prompt and both replies, facing, gate, `on_complete` and uid all survived a save and reload** | pass |
| Layer | moving a prop does not reorder the prop list | pass |
| | the **top** prop of a stack is the one grabbed | pass |
| Multi-cell | a 2×3 prop can be grabbed by its canopy | pass |
| | the grab offset is kept — the footprint lands where the ghost showed it | pass |
| Undo | one move = exactly one undo step; undo restores the cell **and** the attributes; redo re-applies | pass |
| | a press-and-release with no drag records **no** undo step | pass |
| Refusals | a drop that pushes the anchor off the grid is refused, and records no undo step | pass |
| | an NPC dropped on an occupied NPC cell is refused; the sitting NPC is **not** deleted | pass |
| | dragging from an empty cell changes nothing and records nothing | pass |
| | ESC mid-drag cancels and keeps the MOVE tool selected | pass |
| Files | the moved level saves, reloads and validates with **0 blockers** | pass |
| Regression | placing, erasing and painting still work | pass |
| | right-click still opens `PropSettingsPopup`; OK still commits without moving the prop, and keeps the gate, travel fields, rotation, collision and unknown keys | pass |
| | render survives every move state — idle over a prop, idle over nothing, dragging legal, dragging refused, on all five tabs | pass |
| Control | erase-and-re-place really does lose the attributes **and** change the uid | pass |
| Regression | all 12 `levels/*.json` still validate with no blockers | pass |
| | 14 modules import, including `main`, `play_sandbox`, `play_registration`, all four editor modules, `save_bridge`, `dialogue_flow` and `map_screen` | pass |

**Visual acceptance**, captured headless on the real `levels/player_room.json`: the MOVE
slot draws its arrow glyph and reads `move`; hovering `prop_0023` (the `computer_desk_4`
that opens the skill tree) outlines its footprint green; dragging ghosts it over the
destination with a green outline while the original stays put; and the drop reports
`computer desk 4 moved to (9,0) — layer 1 of 1` with `uid`, `interactable`, `kind: menu`
and `menu_id: skill_tree` all unchanged. On `levels/lecture_hall.json`, dragging Prof.
Hoque onto Prof. Rahman's cell draws the ghost with a **red** outline and the drop is
refused. Both level files were left unmodified.

---

## Acceptance

> I can configure a prop, move it repeatedly, save, reload the level, and every attribute
> is exactly as I set it.

Covered by the "Attributes" rows above: a prop carrying all 12 serialised fields plus an
unknown authored key was dragged six times, saved, and re-read from disk, and its
serialised form differed from the original in `x` and `y` and in nothing else.

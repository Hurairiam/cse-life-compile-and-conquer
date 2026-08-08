# Phase 4 — Portal Prompt and Return Position

**Covers:** Changes 5 and 8
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-08
**Commit:** `[Sprint 4] Remove enter prompt and restore pre-portal position`

---

## What the recon found

### The two prompts come from one function

There is a single decision point and a single drawing class, and they are already
separated:

- **`engine/states/exploration.py::verb_for(ctx, cell)`** picks the label.
- **`ui/interaction_prompt.py`** draws it. Four label constants and the chip geometry;
  no game logic at all, which is why that file was never opened for this phase.

The real strings are `[E] ENTER` and `[E] EXAMINE`, not "to enter" and "to interact".

`verb_for()` and `__interact()` share one precedence — **gate → NPC → portal →
interactable prop** — and the module docstring said so explicitly: the chip must never
promise something E will not do.

### `[E] ENTER` had two producers, not one

| Branch | Source | Fires when |
|---|---|---|
| `level.get_portal_at(cell)` | the step-on portal prop, `type_id == "portal"` | the frame the player **walks onto** the cell, from `__check_cell_transition()` |
| `prop.travels_on_interact()` | any interactable prop with `kind == "travel"` and a target level | **only on E** |

That asymmetry decided TASK A. A portal's chip is decorative — the doorway opens by
itself and E is only ever a spare route to the same place. A travel prop's chip is the
door's *only* advertisement; deleting it would hide the door rather than tidy it away.

### Only one way in and out of a level

`exploration.__travel()` is the single funnel for both kinds of doorway, and it took the
arrival cell from `portal.get_target_spawn() or level.get_spawn()`. Those are fixed
per-portal and per-level, which is exactly the inconsistency TASK B describes: every
return trip landed on the same tile no matter where the player had been standing.

---

## Owner rulings

Four questions were put before anything was written, and all four were answered:

1. **Remove the portal chip only.** Travel-prop doors keep `[E] ENTER`. `[E] EXAMINE` is
   untouched.
2. **"2 cells next to it" means the doorway plus two.** Walk up onto a portal at (10, 5)
   from (10, 6) and you come back at (10, 7) — one cell further back than where you were
   standing, so the threshold is never underfoot on arrival.
3. **The positions go in the save file**, as an additive `world` key.
4. **Three-step fallback** when the recorded cell no longer works: recorded landing cell →
   the cell actually stood on → the level's existing spawn.

---

## What was built

### A new module, not a new branch in `exploration.py`

Recon hazard #4 names `engine/states/exploration.py` the busiest shared file in the
repository — it owns the interaction precedence, and Phases 5, 8, 13 and 17 all want a
piece of it. The documented mitigation is `engine/menu_prop.py`: put the logic in a new
file, because a new file cannot conflict, and let the state module carry a call rather
than a branch.

**`engine/return_points.py`** (new, 118 lines) follows that. Pure Python — no pygame, no
level loading, no screen state — with four functions:

| Function | Does |
|---|---|
| `record(ctx, doorway, origin)` | files the way out under the level being left |
| `arrival(ctx, level, fallback)` | resolves the landing cell on the way in |
| `to_state(ctx)` / `from_state(saved)` | the save payload, with the guards |

### The geometry

One entry per level id, overwritten every time the player leaves:

```
ctx.return_positions["campus_main"] = (12, 7, 12, 6)
                                       ^^^^^  ^^^^^
                                       landing  the cell they
                                       cell     actually stood on
```

The landing cell is the doorway plus `STEP_BACK = 2` along the way the player came. The
direction is taken as a **per-axis sign**, so a diagonal cell change reads back as a
diagonal return instead of being flattened onto one axis — cell transitions really can be
diagonal here, because `PlayerMover` moves two float axes separately rather than
grid-stepping.

The cell actually stood on is kept as the second chance. Both were walkable when the
player left; they only diverge if a level was edited since, and then the one nearer the
door is the likelier survivor.

`record()` returns without writing anything when the direction works out to (0, 0) — the
player standing on the doorway itself with nothing to step back along. Recording that
cell would bounce them straight out again on arrival.

### Where it plugs in

Three call sites, all in `__travel()` and `__check_cell_transition()`:

- `__travel()` gained an optional `origin` argument. Only the step-on portal has to
  supply it (`previous`, the cell the player held a frame ago); everything else fires on
  E, so the walker is already standing beside the doorway and `ctx.walker.get_cell()` is
  the right answer.
- `record()` is called **after** the two failure returns and **before** `ctx.level_id`
  moves. After, so a doorway with no destination does not rewrite the way back; before,
  because the entry is filed under the level being left.
- `arrival()` is called **after** the existing `is_walkable` fallback, so the value it
  receives has already been validated and can be returned untouched on a first visit.

`ensure_level()` was left alone. Its `ctx.pending_spawn` comes from `world.spawn_x/y`,
which is already the exact cell the player was standing on when they saved, so a load
lands where it always did.

---

## The regression the acceptance test caught

Deleting the portal branch from `verb_for()` outright did **not** silence the chip. It
labelled all sixteen portals `[E] EXAMINE`.

Every authored portal prop in the repository carries `interactable = True`:

```
campus_courtyard  (20, 11)  portal.interactable=True   interactable_at=portal
campus_courtyard  (20, 10)  portal.interactable=True   interactable_at=portal
campus_library    (17, 12)  portal.interactable=True   interactable_at=portal
...                                                    16 of 16
```

With the portal step gone, the cell fell through to `get_interactable_at()` and found the
portal itself. Worse than cosmetic: `__interact()` still checks portals *before* props,
so the chip would have offered a poke that E answered by teleporting the player — the
exact thing the shared precedence exists to prevent.

**Fix:** the portal step stays in the chain and returns a **blank** label instead of being
removed. `render()` already returns early on an empty label, so nothing is drawn, and the
precedence is still honoured.

---

## Save format

One additive key in `world`:

```json
"return_positions": {"campus_courtyard": [20, 13, 20, 12]}
```

`SAVE_SCHEMA_VERSION` stays at **1**. This is the precedent `world.dialogue_choices` set
in the 2026-08-08 amendment and Phase 2 followed: the key is additive, `restore()` reads
it through a guard, and a save written before it loads as `{}` — which only means every
area opens at its SET SPAWN cell, exactly as it used to. Bumping the version would make
every existing save unreadable for no gain.

`from_state()` drops any entry that is not four coercible ints rather than letting a
hand-edited file reach `walker.place()`.

---

## What was deliberately left alone

- **`ui/interaction_prompt.py`.** It has no logic and is still byte-identical to `main`.
  `LABEL_ENTER` is still in use for travel-prop doors, so nothing there is dead.
- **How portals trigger.** `__check_cell_transition()` is unchanged apart from passing
  `previous` through. `__interact()`'s portal branch is untouched, so E on a facing portal
  still travels — silently now, which the module's one-directional invariant allows.
- **`play_sandbox.py`.** It carries its own copy of `__verb_for()` that also returns
  `LABEL_ENTER` for portals, but it is a standalone dev harness not reachable from
  `main.py`, so it is outside this phase's scope. It remains identical to `main`.
- **Teleporting and the level editor** — Phase 5 and Phase 10/11 respectively.
- **`ensure_level()`'s spawn precedence**, per above.

---

## Files changed

| File | Δ | Why |
|---|---|---|
| `engine/return_points.py` *(new)* | +118 | the whole feature |
| `engine/states/exploration.py` | +46 / −9 | portal chip silenced, `origin` threaded through `__travel()`, two calls into the new module |
| `engine/save_manager.py` | +8 | the `return_positions` parameter and the `world` key |
| `engine/save_bridge.py` | +6 | capture and restore |
| `engine/app_context.py` | +4 | `ctx.return_positions` in STAGE 5 |

No level file was touched, so hazard #1 (unmergeable maps) does not apply.

---

## Merge-conflict risk

**Zero.** `git merge-tree` against `origin/main` with these changes applied produces 0
conflict markers.

- `engine/return_points.py` is new — it cannot conflict.
- `engine/states/exploration.py` was already divergent (Phase 0's amendment took −36
  lines out of `__talk`). This phase's edits are in `verb_for()`, `__travel()` and
  `__check_cell_transition()`, none of which that amendment went near.
- `engine/save_manager.py` and `engine/save_bridge.py` were both touched by the
  amendment, and both edits here are appends immediately after the `dialogue_choices`
  lines it added — the same append-don't-restructure mitigation hazard #2 asks for.
- `engine/app_context.py` diverges from main only in STAGE 4; the new line is in STAGE 5.

---

## Verification

Headless, `SDL_VIDEODRIVER=dummy`. Two scripts: unit checks on `return_points` in
isolation, and an end-to-end run driving the real `exploration` module against the real
level files.

### Unit — 24 checks, all passing

| Case | Result |
|---|---|
| Walk up onto a portal at (10, 5) from (10, 6) → `(10, 7, 10, 6)` | pass |
| Walk right onto a portal at (10, 5) from (9, 5) → `(8, 5, 9, 5)` | pass |
| Diagonal exit keeps both axes | pass |
| Origin equals the doorway → nothing recorded | pass |
| Blank level id, or `origin` of `None` → nothing recorded | pass |
| First visit → the caller's fallback | pass |
| Return → the landing cell | pass |
| Landing cell blocked → the cell actually stood on | pass |
| Both blocked → the fallback | pass |
| Landing cell off a shrunk grid → the fallback | pass |
| `build_state()` carries the key; default `{}`; `schema_version` still 1 | pass |
| `to_state` → `from_state` round trip | pass |
| Malformed entries dropped: missing key, non-dict, wrong length, non-int, bare string | pass |
| Floats coerced to ints | pass |
| A `world` dict with the key deleted → empty table | pass |
| All 12 level files still load; all 16 portals still found | pass |

### End-to-end — 14 checks, all passing

Built a real `AppContext`, loaded `campus_courtyard`, and used its authored portal at
(20, 11) → `field`.

| Case | Result |
|---|---|
| `verb_for()` on a portal cell returns an empty label | pass |
| `verb_for()` on an interactable prop still returns `[E] EXAMINE` | pass |
| Travel through the portal reaches `field` | pass |
| `campus_courtyard` remembered as `(20, 13, 20, 12)` after leaving from (20, 12) | pass |
| First visit to `field` still lands on its spawn, (10, 1) | pass |
| Return through `field`'s portal reaches `campus_courtyard` | pass |
| Landing cell is (20, 13) — where we left, not the SET SPAWN, not the portal | pass |
| `capture()` writes the key; `restore()` reads it back identically | pass |
| A save with the key deleted restores cleanly, with an empty table | pass |

No level authored a `travels_on_interact` prop, so that branch has no live case to assert
against; it was left in place and unmodified.

**Manual acceptance** (the brief's own test, on a real display): walk up to a portal — no
`[E] ENTER` chip appears, and stepping on still travels. Walk up to a bookshelf or a
vending machine — `[E] EXAMINE` still appears and still works. Leave an area from one
corner, come back, and you arrive two cells back from the door you used rather than at the
area's original spawn point.

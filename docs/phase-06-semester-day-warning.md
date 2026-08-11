# Phase 6 — Semester Day Warning and HUD Counter

**Covers:** Change 3
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-08
**Commit:** `[Sprint 4] Add end-of-semester day warning popup and HUD counter`

---

## What the recon found

### The limit is 15, and it was already a hard bounce

```python
# engine/game_clock.py:43
__MIN_MAIN_QUEST_TIME_BORDER: int = 15

# engine/game_clock.py:93
def is_eligible_for_side_activities(self) -> bool:
    remaining = self.__current_semester.get_time_pool_days()
    return remaining > self.__MIN_MAIN_QUEST_TIME_BORDER
```

Called the "15-Day Borderline Firewall", owned by the clock since Sprint 2 and read
back through `get_min_border()`. It was enforced in exactly one place, and not gently:

```python
# engine/states/exploration.py:104 — inside update(), every frame
if not ctx.game_clock.is_eligible_for_side_activities():
    ctx.go(ScreenState.EXAM)
    return
```

At 15 days the player was yanked out of the world into the exam screen on the next
frame. **That is what made the brief impossible as written** — a popup saying "utilize
them wisely" and a HUD counter that "stays visible until the next semester" have
nowhere to live if the player is removed from the map the instant they could be shown.

Reported before writing anything. The ruling came back:

> "When there's exactly 15 days left in the time pool, the popup warning is issued.
> After that, the player can explore as much as they want to (because exploration does
> not cost any time), they just can't interact with any NPCs that have side quests
> ready for them."

So the threshold stays at 15 and **the bounce goes**. Exploring costs no days, so there
was nothing to protect the player from; what the threshold costs them from now on is
*new side quests*, which is Phase 17's job. `GameClock` itself is untouched —
`is_eligible_for_side_activities()` still answers exactly what it always did.

### Days do not tick, they come off in blocks

The brief asked to confirm the "fires once, on first crossing" reading if the time code
suggested otherwise. It does not suggest otherwise — it rules out the alternative.
There is **no daily tick anywhere in the game**. Days leave the pool in whole chunks
(10 or 14 for an exam, 5 for a side quest, whatever a gate toll costs), every one of
them through `GameClock.process_time_consumable()`, which is the single entry point for
all time-costing actions. "The first frame the pool is at or below the threshold" is
the only reading the time system supports, so no question was raised.

### The HUD was already designed for this

Recon §5 names the insertion point outright: a fifth entry in the left run, each helper
returning the next `x`, with the location label already built to give way as the numbers
widen. That is exactly where the chip went.

---

## Owner rulings

Three, all answered before any code was written:

1. **Threshold 15, and the firewall bounce is removed** (above).
2. **The teleport lock moves off the zone and into the menu** — see below.
3. Stated in the same message rather than asked: **moving between areas must never
   require a key press.**

---

## What was built

### `engine/day_warning.py` — the rule (new file)

```
threshold(ctx)   the 15, read back from GameClock.get_min_border()
remaining(ctx)   days left in the active semester
is_low(ctx)      True at or below the threshold        <- Phase 17 reads this
hud_days(ctx)    the number for the chip, or None      <- state_router reads this
check(ctx)       fires the popup once per semester     <- exploration calls this
```

A new module for the reason `engine/menu_prop.py` is one: it cannot produce a merge
conflict, and the alternative was another branch inside `engine/states/exploration.py`,
which the recon names the busiest shared file in the repository. That file carries a
one-line call.

**The threshold is not declared here.** The brief asks for one named constant in one
place, and one already existed — `GameClock.__MIN_MAIN_QUEST_TIME_BORDER`. Writing a
second `15` into this module would have been two numbers claiming to be one rule. What
this module adds is a single *front door*: Phases 11 and 17 call `threshold(ctx)` and
`is_low(ctx)` rather than reaching into the clock, so the day rule has one read point
even though the number lives with the system that spends days.

`is_low()` is the complement of `is_eligible_for_side_activities()` and is phrased
positively because that is how the phases reading it think: *days are low, so do not
offer this*. The two are asserted to always disagree in the verification below.

**State is one module-level int** — the semester the popup has been shown for. Kept off
`ctx` the way `engine/states/save_game.py` keeps its row highlight, because
`engine/app_context.py` is a shared, already-divergent file and this is one bookkeeping
integer. Keying it to the semester **number** means a rollover or a new game re-arms it
without anybody having to call a reset.

**Nothing was added to the save payload**, so `SAVE_SCHEMA_VERSION` stays at 1 and every
existing save loads unchanged. The HUD half needs no memory at all — it is derived from
the day count every frame, so it survives save/load for free and clears itself when
`advance_semester()` refills the pool. Only the once-per-semester popup is session
state, and re-showing it after a load is a smaller cost than a schema change.

### `ui/hud.py` — the counter

One optional argument, `low_days`, and one private helper. Every existing caller
(`play_sandbox.py`, the module's own stub test) keeps working untouched.

`low_days` is **None-or-a-number, not a plain int**: a semester can genuinely run down
to zero days, and that is the moment the chip matters most, so `0` has to mean "no days
left" and never "nothing to say".

The chip is a filled terracotta pill reading `15 DAYS LEFT`, in the same red the day
bar already turns, so the two read as one statement rather than two warnings. It is not
a fifth icon-and-number stat because the four stats are things that are always true and
this is an alarm; it carries no icon because `assets/ui/` has none for it and a
PLACEHOLDER square inside an alarm chip reads as a bug.

**Whether the count is low enough to show is not decided here.** Like every other number
on the strip it is handed in — `engine/day_warning.py` decides, `engine/state_router.py`
passes it, `ui/hud.py` draws it (UI Style Guide §6.1).

The bar's own `<= 15` colour literal was left alone. It is a colour ramp, not the rule,
and it already agrees.

### `engine/state_router.py` — one kwarg

`low_days=day_warning.hud_days(ctx)` on the existing `hud.render()` call. Derived every
frame rather than remembered, so the chip follows the day count down and disappears by
itself at the rollover — **nothing in `engine/states/exam.py` needed touching**, which
keeps this phase out of Phase 7's file entirely.

### `engine/states/exploration.py` — the bounce out, the call in

```python
-    if not ctx.game_clock.is_eligible_for_side_activities():
-        ctx.go(ScreenState.EXAM)
-        return
+    day_warning.check(ctx)
```

The two other routes into the exam are untouched: the activity card's **START EXAM**
and the `X` key both still work, so the semester can still be closed. The player is now
told the term is ending instead of being moved when it does.

---

## The two fixes asked for in the same message

Both turned out to be the same bug seen from two sides.

### Walking between areas never needs a key

Every link between two maps in the repo is already a step-on portal, and they do fire
on entry — that was verified by simulation before anything was changed. What actually
stopped the player leaving their own room was **the teleport zone**: it covered
(7,7)–(8,8), the door portal is at (7,9), and so the gated cell sat directly in the
walking path to the door. Walking at it bounced the player back with a locked notice
and left the doorway reachable only by a detour through (6,9).

It was also **the only live gate in the entire game.** Every other zone in `levels/`
carries a `locked_title` and flavour text with no actual requirement, so
`has_requirements()` is false and `get_gate_at()` already returns None for all of them.

Two changes:

- **The zone is gone** and the rule moved into the menu (below), so nothing on the floor
  of the player's room stops anybody.
- **`__check_cell_transition()` now crosses a travel prop on entry too**, not just a
  portal — so the rule is "walking between areas needs no key press" rather than "the
  portals we happen to have authored need no key press". E still works on one, the way
  it already did on a portal. It sits **below** the gate check rather than above it: a
  travel prop is a door somebody may have locked, and a lock that opens because you
  walked at it is not a lock. (The portal step's position above the gate check is
  pre-existing behaviour and was left exactly as it was.)

The `[E] ENTER` chip stays on a travel prop. Unlike a portal it is a visible object the
player can stand beside and face, so the label answers *what is this* rather than
advertising a key they must press.

### No zone outlines in game

`ui/map_screen.py::__draw_gates` outlined **every** gated cell and badged a zone's
top-left one. A zone is an authoring rectangle: it has no art, no edge and nothing in
the world that corresponds to it, so its outline put a coloured grid on the floor the
player could see but never explain.

Zones now draw **nothing at all** in game — verified pixel-for-pixel, below.
`tools/level_editor.py` draws its own zone rectangles on its own canvas
(`level_editor.py:1341`), which is where that shape belongs and where it is still
visible, so the editor is unaffected and was not opened.

A gated **prop** keeps both its outline and its lock badge. It is a real object an
artist placed, so "this one is locked" reads as a property of a thing rather than as a
stripe on the ground.

### `engine/states/teleport.py` — the semester lock, rehomed

`MIN_SEMESTER = 5`, named once, in the file that owns the menu. The copy that used to
live in the zone's gate is gone with the zone.

`enter()` refuses before the card is ever built: one popup, and control handed straight
back to the map. `handle_events()` and `render()` both return early while refused —
a transition is applied at the *top* of the next loop iteration, so this state renders
exactly one more frame, and that frame must not flash a card the player was just told
they cannot have.

The prop is walkable, the doorway beside it is walkable, and nothing bounces anybody.
**A restriction on a menu is not a restriction on a floor.**

---

## Files changed

| File | Δ | Why |
|---|---|---|
| `engine/day_warning.py` *(new)* | +228 | the rule, the popup, the read points for Phases 11/17 |
| `ui/hud.py` | +64 −4 | the `low_days` argument and the warning chip |
| `engine/states/exploration.py` | +36 −6 | bounce removed, `check()` called, travel props cross on entry |
| `engine/states/teleport.py` | +50 −1 | the semester lock, moved off the zone |
| `ui/map_screen.py` | +23 −17 | zones draw nothing; gated props still marked |
| `engine/state_router.py` | +5 −1 | one kwarg to the HUD |
| `levels/player_room.json` | −20 | the teleport zone removed |

`engine/game_clock.py` was **not** touched — the threshold and the firewall predicate
are still exactly where they were.

---

## Merge-conflict risk

**Phase 6 adds zero conflicts.** `git merge-tree --write-tree` against `origin/main`
produces the same clean result with and without this phase's changes: no conflict
markers either way.

Three of the seven files were already divergent from main before this phase
(`ui/map_screen.py`, `engine/states/teleport.py`, `levels/player_room.json`); the other
four are small, local edits. `engine/day_warning.py` is new and cannot conflict, which
is where the bulk of the work is by design.

`levels/player_room.json` was rewritten through `content/level_schema.py::write_level()`
rather than by hand, so the file is byte-identical to what the editor would produce —
the diff is the removed `zones` block and nothing else, checked by comparing the parsed
JSON with and without that key.

---

## Verification

Headless, `SDL_VIDEODRIVER=dummy`. **57 end-to-end checks plus 13 unit assertions in the
module's own stub test — 70 total, all passing.**

### Unit — `py -m engine.day_warning`

| Case | Result |
|---|---|
| 80 days and 16 days warn nobody | pass |
| 15 days warns, and the line carries the real count | pass |
| Repeat calls inside one semester never warn twice | pass |
| A lower count in the same semester does not re-warn | pass |
| The next semester re-arms, with its own count | pass |
| `1 day left` is singular; `0` still shows the chip | pass |

### End to end — a real `AppContext` on the real maps

| Group | Case | Result |
|---|---|---|
| Content | all 12 levels load and validate | pass |
| | `player_room` carries no zones | pass |
| **Walking out** | **the whole route to the door raises no gate notice** | pass |
| | **stepping onto the doorway travels to the lobby with no key pressed** | pass |
| | the player can stand on the old zone's cells | pass |
| **Teleport** | the rug is a `menu` / `teleport` prop and carries no gate | pass |
| | E on it routes to `TELEPORT` | pass |
| | semester 1 refuses, names semester 5, moves nobody, draws no card | pass |
| | semester 5 opens the card | pass |
| **The warning** | threshold is the clock's own 15, not a second copy | pass |
| | 80 and 16 days show nothing at all | pass |
| | **15 days fires the popup, with the count and the exam line** | pass |
| | **the HUD indicator turns on at 15 and follows the count down to 9** | pass |
| | it never fires a second time | pass |
| | a day cost charged through `GameClock` trips it the same way | pass |
| **Below it** | **no bounce to `EXAM` — the player is still in `EXPLORATION`** | pass |
| | movement still works at 9 days | pass |
| | the clock still reports them ineligible for side activities | pass |
| | `is_low()` and `is_eligible_for_side_activities()` always disagree | pass |
| **Rollover** | the pool refills, the chip clears, no popup on the fresh term | pass |
| | **the next semester re-arms the warning with its own count** | pass |
| HUD | the old five-argument call still works | pass |
| | the chip draws beside a full 12th-semester strip, and at zero days | pass |
| **Zones** | **a gated zone changes not one pixel of the rendered map** | pass |
| | a gated **prop** is still marked | pass |
| Travel props | one crosses on entry with no key pressed | pass |
| | a **locked** travel prop still holds | pass |
| Regression | `main`, `save_bridge`, `state_router`, `exam`, `activity`, both editor modules, `play_sandbox` and `map_directory` all import | pass |

**Manual acceptance** (the brief's own test): spend the semester down to 15 days — the
`WARNING` popup opens once saying how many days are left, the HUD then carries a red
`15 DAYS LEFT` chip that counts down as more days are spent, the player keeps the run of
the campus instead of being thrown into the exam, and the chip is gone the moment the
next semester starts.

---

## What this phase deliberately did not do

- **Blocking side quests below the threshold** — Phase 17, which reads `is_low(ctx)`.
- **The pass-days prop** — Phase 11, which reads `threshold(ctx)` and gets the popup and
  the chip for free by spending days through `GameClock` like everything else.
- **The exam flow** — Phase 7. Removing the bounce means the exam is now entered only by
  choice (the activity card, or `X`), which is the state Phase 7's "free roam after the
  final exam" already assumes.

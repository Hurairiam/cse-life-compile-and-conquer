# Phase 11 — Level Editor: "Pass Remaining Days" Interactable

**Covers:** Change 13
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] add pass-remaining-days interactable function`

---

## Step 1 — what the time system does at zero, reported before anything was written

The brief asked for this before implementation, and the answer decided the shape of the
phase.

### Deduction refuses, it does not clamp

```python
# academic/semester.py:57                     # core/character/player.py:71
def deduct_time(self, days: int) -> bool:     def deduct_time_pool_days(self, days):
    if days < 0:        return False              if days < 0:  return False
    if self.__time_pool_days >= days:             if self.__time_pool_days >= days:
        self.__time_pool_days -= days                 self.__time_pool_days -= days
        return True                                   return True
    return False                                  return False
```

Both return `False` and change nothing when asked for more days than are left. A drain
must therefore charge **exactly** the remaining count — a round number would silently do
nothing at all.

### Nothing watches the counter

- `Semester.is_semester_complete()` (True at ≤ 0) exists and is **called by nothing** —
  grep across the repo returns only its definition.
- There is **no daily tick**. Days leave in blocks, every one of them through
  `GameClock.process_time_consumable()`, the single entry point.
- Phase 6 removed the one automatic reaction a low pool ever had: `exploration.update()`
  used to bounce the player into `ScreenState.EXAM` the frame
  `is_eligible_for_side_activities()` went False.

### Zero is read in exactly two places

| Where | What it decides |
|---|---|
| `engine/final_exam.py::may_roam()` | *after the last exam*: days > 0 → congratulate and hand the campus back; days ≤ 0 → congratulate and `close_semester()` |
| `engine/day_warning.py` | the warning already fired at 15; the HUD chip reads `0 DAYS LEFT` |

So reaching zero **before** the exams triggers nothing on its own today. The cost surfaces
later: `MainQuest.execute_action()` aborts with no side effects when the pool is short, so
`exam.py:100` sets `NOT ENOUGH TIME LEFT THIS SEMESTER` and `check_semester_end_state()`
backlogs every course that was never sat.

### The registration seam, unchanged since Phase 5

`MENU_REGISTRY` row + appended `ScreenState` member + one file in `engine/states/`. The
editor needs no edit — its menu `Cycler` is built from `get_menu_ids()` /
`get_menu_display_name()` (`tools/editor_popups.py:617`). `engine/states/end_semester.py`
(Phase 7) is the precedent for what this phase needs specifically: a menu prop whose whole
screen is a `ConfirmPopup` over the map, refusing in `enter()` and resolving in `update()`.

Spending through `ctx.game_clock.process_time_consumable()` gets Phase 6's warning popup
and HUD chip **for free**. `GateEntryAction` (`engine/gate_evaluator.py:393`), run through
the clock by `engine/gate_service.py`, is the precedent for a `TimeConsumable` that is not
a `Quest`.

---

## Owner rulings

Reported first, then asked, then built. Two answers came back.

1. **Stop short of the exam trigger and the rollover.** The drain deducts through
   `GameClock` and hands the player straight back to the map at zero days. It does not
   open `EXAM` — that would reinstate for one prop the bounce Phase 6 deleted — and it
   does not roll the term over, which is still only ever `exam.close_semester()`, reached
   through the exam screen or an `end_semester` prop.
2. **No exam gate on the prop.** It works at any point in the term; the confirmation names
   the cost and CANCEL is always there. A term drained before its finals backlogs whatever
   is never sat, exactly as a term that runs out of days already does.

---

## What was built

Two new files and two one-line appends. No shared file gained a branch.

### `engine/day_drain.py` — the action and the rule

```
PassDaysAction(TimeConsumable)   cost fixed at construction, deducts and returns
    .for_semester(ctx)           the action for the term, or None when spent
remaining(ctx)                   delegated to day_warning, not read a second time
passable(ctx)                    the days the drain may actually charge
can_pass(ctx)                    True while there is at least one left
drain(ctx) -> int                spend them; returns how many actually went
```

A new module for the reason `engine/menu_prop.py`, `engine/day_warning.py` and
`engine/final_exam.py` are: it cannot produce a merge conflict.

**Named beside `day_warning.py` rather than after the screen.** The screen has to be
`engine/states/pass_days.py`, because the router resolves `ScreenState.PASS_DAYS` to that
path by name; two modules sharing a basename in different packages import fine and read as
a mistake. "Drain" is also the one verb here that cannot be misread — in a game with exams,
"pass" already means something else.

**`PassDaysAction` is the phase's one real design decision.** Every other `TimeConsumable`
in the game exchanges days for something — credits, EXP, a door. This one buys nothing:
the days *are* the effect, so `execute_action()` deducts and returns. The cost is fixed at
construction the way `GateEntryAction` fixes a toll, because `GameClock` reads
`get_time_cost()` **before** calling `execute_action()` and advances the global career
clock by it; a cost that recomputed itself between those two calls is precisely the drift
`MainQuest.get_time_cost()` was overridden to stop.

`for_semester()` returns **None** rather than a zero-day action on a spent term, for the
reason `GateEntryAction.for_gate()` refuses a free gate: a zero-cost item pushed through
the clock advances the global counter by nothing and reads, in every log, as an action
that happened.

**`remaining()` delegates to `engine/day_warning.py`.** Phase 6 built that module to be the
single front door for the day rule and named this phase as one of its two callers. Reading
`ctx.semester()` here would have been a second place to change when the rule moves. The
threshold is never mentioned in this phase at all — asserted below.

**`passable()` takes the min of the two day pools.** `Player.__time_pool_days` and
`Semester.__time_pool_days` are independent ints kept in step by `GameClock` deducting the
same number from each. One place still parts them: `save_bridge.restore()` rebuilds the
Player with a full 80 days and replays the term's spend onto the Semester only, so a loaded
game has a player pool at or above the term's. The term's count is therefore the smaller
one in every reachable state — which is exactly what the brief asks to drain, so the `min`
changes no number in practice. What it buys is a guarantee: the cost `GameClock` reads, the
days `execute_action()` takes off the player and the days `GameClock` takes off the
semester are **one number** and cannot disagree, whatever a save file turns out to hold.

**`drain()` measures, it does not report intent.** The days passed are computed from the
semester's counter before and after, because `process_time_consumable()` does nothing at
all on a frozen session and a caller that trusted the action's cost would report a spend
that never happened.

### `engine/states/pass_days.py` — the question

`end_semester.py`'s shape, because it is the same shape of thing: `enter()` refuses or
asks, `update()` resolves, `render()` draws the map underneath and lets the router put the
popup over it. There is nothing to draw of its own — the map **is** the screen.

```
title    PASS REMAINING DAYS?
body     "40 days left in this term."
         "All of them go to the main quest."
         "They will not come back."
buttons  PASS DAYS / CANCEL              severity: WARNING
```

Three lines is `ui/popup.py`'s hard ceiling and all three are used. The count is real and
singular at one day. The confirm button is named with the act rather than "CONFIRM", the
way `END TERM` is, so a player who read only the buttons still knows what they pressed.

**CANCEL changes nothing** — the action is not built, let alone run, until `RESULT_CONFIRM`
comes back. A refusal (`NO DAYS LEFT`) opens one popup and hands control straight back, so
the player presses E, reads why, and is still standing on the map.

The warning popup and the HUD chip are **not** fired from here. `exploration.update()`
runs `day_warning.check()` every frame and `state_router` derives the chip every frame, so
both land on the frame after the drain off the count it just changed — identical to
crossing the threshold by sitting an exam. That is the brief's "reuse, do not duplicate",
and it cost zero lines.

### The two appends

```python
# engine/screen_manager.py
PASS_DAYS = auto()                                          # appended, per hazard #3

# content/level_registry.py
"pass_days": {"name": "Pass Remaining Days", "state": "PASS_DAYS"},   # per hazard #2
```

`engine/state_router.py` needed **no** edit: `ScreenState.PASS_DAYS.name.lower()` resolves
to `engine/states/pass_days.py` on its own, and the HUD stays up because the card sits over
the map — which is right here more than anywhere, since the day count is the subject.

`tools/` was **not opened**. The editor's menu dropdown reads `MENU_REGISTRY`, so the new
function appears in it on its own.

---

## Files changed

| File | Δ | Why |
|---|---|---|
| `engine/day_drain.py` *(new)* | +287 | the action, the rule, its own stub test |
| `engine/states/pass_days.py` *(new)* | +127 | the confirmation, the refusal, the one call |
| `content/level_registry.py` | +6 | one `MENU_REGISTRY` row |
| `engine/screen_manager.py` | +5 | one `ScreenState` member |

No level file was touched — the prop is assigned in the editor, by hand, which is the whole
point of registering the function rather than hardcoding it. `engine/game_clock.py`,
`engine/day_warning.py`, `engine/states/exploration.py`, `engine/states/exam.py`,
`engine/final_exam.py`, `ui/hud.py` and `engine/state_router.py` were all **left alone**.

---

## Merge-conflict risk

**Phase 11 adds no conflicts.** `git merge-tree --write-tree HEAD origin/main` produces a
clean tree with and without this phase's commit — no conflict markers either way. The
branch is 21 ahead / 0 behind.

- The two new files cannot conflict, which is where all 414 lines of behaviour live.
- `content/level_registry.py` — recon hazard #2's shared choke point, already +103 from
  main. This phase's share is **one appended row and a comment**, at the end of the dict,
  which is what the hazard asks for.
- `engine/screen_manager.py` — hazard #3. One member appended at the end of the enum; every
  earlier member kept its `auto()` number, asserted below.
- `tools/level_editor.py`, `tools/editor_popups.py`, `content/level_schema.py`,
  `engine/states/exploration.py`, `levels/*.json` — the four High-risk files and the
  unmergeable maps. **None opened.**

`levels/campus_main.json` and the eight untracked `assets/props/*.png` are the asset
track's, not this phase's, and stayed out of the commit — the same way Phases 8, 9 and 10
left them.

---

## Verification

Headless, `SDL_VIDEODRIVER=dummy`, `pygame-ce 2.5.7` / Python 3.14.6.
**90 end-to-end checks plus 30 assertions in the module's own stub test — 120 total, all
passing.** The harness drives a **real `AppContext`**, the real `GameClock`, `Semester` and
`Player`, the real `ConfirmPopup` through real pygame events, and the real level files.

### Unit — `py -m engine.day_drain`

Runs against the real `GameClock`, `Semester` and `Player`, so what it proves is the
pipeline rather than a mock of it.

| Case | Result |
|---|---|
| A spent term offers nothing, builds no action, and drains 0 | pass |
| A full term costs 80, drains both pools, and moves the global clock by 80 | pass |
| A part-spent term costs exactly what is left (32 of 80) | pass |
| One day drains; a second drain on a spent term does nothing | pass |
| **A loaded save (player 80 / semester 20) drains 20 and takes it off the right pool** | pass |
| **A player pool below the term's caps the cost, so the two never disagree** | pass |
| **A frozen session spends nothing and `drain()` reports 0, not the intent** | pass |
| The drain crosses `day_warning.is_low()` and turns the chip on | pass |

### The registration seam

| Case | Result |
|---|---|
| `pass_days` in `MENU_REGISTRY`, **last** — appended, not inserted | pass |
| All 12 earlier menu ids kept their place | pass |
| `menu_prop.resolve_state("pass_days")` is `ScreenState.PASS_DAYS` | pass |
| `PASS_DAYS` appended to the enum; **all 20 earlier members kept their number** | pass |
| The router resolves it to a real module | pass |
| All 12 maps still load and validate; 18 modules still import | pass |

### The level editor — the acceptance criterion

| Case | Result |
|---|---|
| **The prop settings popup's menu dropdown offers it, labelled "Pass Remaining Days"** | pass |
| **OK commits `kind: menu` / `menu_id: pass_days` onto the prop** | pass |
| The committed dict loads back as a prop carrying the function | pass |
| CANCEL commits nothing | pass |
| A prop carrying it round-trips through the level file format | pass |

### In game — a real `AppContext` on `player_room`

| Group | Case | Result |
|---|---|---|
| Prop | `menu_prop` handles it and **E opens `PASS_DAYS`** | pass |
| | `return_state` points back at the map | pass |
| | no per-semester trigger is consumed | pass |
| **Warns first** | a confirmation opens, titled `PASS REMAINING DAYS?` | pass |
| | the body carries the **real count**, where the days go, and that they do not return | pass |
| | three lines, warning severity, `PASS DAYS` / `CANCEL` | pass |
| | singular at one day | pass |
| | **asking spends nothing** | pass |
| **Cancelling** | **the day count, the player pool and the global clock are all untouched** | pass |
| | control goes back to the map; no warning is fired | pass |
| | ESC cancels too; a resultless close still leaves, term intact | pass |
| **Confirming** | **the semester pool drains to 0, and so does the player pool** | pass |
| | **the global career clock advanced by exactly 52** | pass |
| | control goes back to the map | pass |
| | **it did not open the exam** | pass |
| | **it did not roll the semester over** | pass |
| | a whole untouched term, one day, and ENTER all drain | pass |
| **Pipeline** | the action is a `TimeConsumable`; its cost is the term's remaining days | pass |
| | `execute_action()` deducts **exactly** `get_time_cost()` | pass |
| | a spent term builds no action and reports no spend | pass |
| | a frozen session spends nothing and does not claim otherwise | pass |
| **Refusal** | a spent term refuses, says why, draws no confirmation, hands control back | pass |
| | `update()` does nothing while refused | pass |
| **Phase 6 reuse** | 60 days shows no chip; the drain crosses the threshold | pass |
| | **the HUD chip turns on, derived from the count this phase changed** | pass |
| | **the drain itself opens no warning — the next exploration frame does, once** | pass |
| | carrying the real count | pass |
| | **a drained crossing and a normally-spent crossing behave identically** | pass |
| | `is_low()` and the clock's firewall still always disagree | pass |
| | **this phase declares no threshold constant of its own** | pass |
| **Below it** | the player is still on the map, not bounced to the exam, and stays there | pass |
| | the clock still reports them ineligible for side activities | pass |
| **Rollover** | the next term starts full, the chip clears, the prop is offered again | pass |
| | and it drains the new term too | pass |
| Render | the card and the refusal frame both draw over the map without raising | pass |

**Manual acceptance** (the brief's own test): in the level editor, right-click a prop, set
INTERACTABLE to yes, the interaction kind to **menu** and the menu to **Pass Remaining
Days**, then save. In game, press **E** on it — `PASS REMAINING DAYS?` opens over the map
naming how many are left; **CANCEL** leaves the count exactly as it was; **PASS DAYS**
spends every one of them through the clock, the end-of-semester warning opens on the next
frame and the red HUD chip appears, and the player is left standing on the campus.

---

## What this phase deliberately did not do

- **The exam flow** — out of scope, and the first owner ruling keeps it that way: nothing
  new routes into `EXAM` and nothing new closes a term.
- **The side quest lockout** — Phase 17, which reads `day_warning.is_low(ctx)`. Draining
  makes that True, which is the whole hook it needs, and no more.
- **Any change to `engine/game_clock.py`.** The threshold, the firewall predicate and the
  single-pipeline rule are all exactly where they were.
- **No save payload change**, so `SAVE_SCHEMA_VERSION` stays at 1 and every existing save
  loads unchanged. The drain leaves nothing to remember — the day count already persists.

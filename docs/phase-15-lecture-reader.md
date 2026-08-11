# Phase 15 — Side Quests: Lecture Reader, Day Cost, Completion

**Covers:** Prompt 4
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] add lecture reader with day cost and completion`

**Input:** the Phase 0 recon (`docs/recon.md`), Phase 12's state machine
(`engine/quest_state.py`) and definitions (`content/side_quest_definitions.py`),
Phase 11.5's sheets (`content/side_quest_lectures.py`), and Phase 14's PC and
list (`engine/side_quest_list.py`, `engine/states/side_quests.py`) — all read
first and used entirely through their public API.

**The state machine was not modified.** `git diff` on `engine/quest_state.py` is
empty: five states, four transitions, exactly as Phase 12 left them. Asserted,
not just claimed — `test_flow_the_state_machine_was_not_modified`.

**No lecture content was touched.** `content/side_quest_lectures.py` is
byte-identical. Nothing was re-split, re-parsed or re-worded; the reader loads
sheets by id and pages the `lines` Phase 11.5 already sized for the card.

---

## Step 1 — the report, made before anything was written

The session opened blocked: both `>>> FILL IN` markers were still in the brief.
Two facts were reported before the questions were asked, because both changed
what the answers could mean.

### R1(b) collides with the prompt

The prompt says *"Do not modify the state machine's transition rules."* A
ONE-SHOT quest needs a sixth state and a fifth transition in
`engine/quest_state.py`, plus a new state name in the save payload.

R1(a) needs **zero** state-machine change. A quest in a sitting never leaves
`Unlocked` in the first place, so "returns to Unlocked" is a fact about the
machine rather than a move through it. That was reported, and (a) was chosen.

### "Walking away from the PC" is not a third case

The reader is a full-screen `ScreenState`. The walker cannot move while it is
open, so walking away is closing the panel under another name.

---

## Owner rulings

Reported first, then asked, then built. Two questions, two answers.

1. **R1 — RETRYABLE.** Leaving early leaves the quest **Unlocked**. Days already
   spent are **not** refunded. The player may pay the full `day_cost` again, and
   the day gate is re-checked on every attempt because `start()` is the only way
   in. No new terminal state, and `LEGAL_TRANSITIONS` is untouched.

2. **R2 — leaving early is exactly two things:**

   | Counts as leaving early | Does not |
   |---|---|
   | closing the lecture panel (ESC) | quitting the game |
   | saving and reloading | a lecture sheet failing to load |

   Both selected cases end at the same function, `lecture_reader.end()`. The two
   unselected ones are handled below and their handling follows from the ruling,
   not around it.

---

## What was built

Two new files, one new test module. Three existing files took a call site each.
`engine/quest_state.py`, `content/side_quest_lectures.py`,
`content/side_quest_definitions.py`, `engine/side_quest_list.py`,
`ui/side_quest_screen.py`, `engine/states/exploration.py`,
`engine/app_context.py` and every `levels/*.json` are **untouched**.

### `engine/lecture_reader.py` *(new, 651 lines)*

```
LectureDayCost(TimeConsumable)  the price of one sitting, and nothing else
skill_reward(quest_id)          EXP, read from the catalog rather than declared

blocker(ctx, quest_id)          why a sitting cannot open — (title, lines) | None
can_start(ctx, quest_id)        the same rule, as a bool
start(ctx, quest_id)            re-check, charge, open. None on success

is_open / is_finished           where the sitting is
get_quest_id / get_sheet_number / get_sheet_count / get_day_cost
current_sheet()                 the sheet on screen
topic() / skill_name() / progress_label()
advance(ctx)                    next sheet; False completes the quest
completion_notice(ctx)          the card shown for a topic just finished

exit_warning()                  the question any player exit must ask
abandon()                       R1: end it, keep nothing
end()                           forget the sitting, however it ended
```

**Why a new module.** Recon hazard #4 and the precedent `engine/menu_prop.py`,
`engine/day_warning.py`, `engine/day_drain.py`, `engine/quest_offer.py` and
`engine/side_quest_list.py` all set. No pygame, no screen state, no UI, so the
day charge and the completion are testable headless. They are.

**`LectureDayCost` is deliberately not `academic/quest.py::SideQuest`.** That
class deducts the time, grants the EXP and marks itself completed inside one
`execute_action()` — precisely the thing this phase has to split. The brief
charges on **open** and applies the skill on the **last sheet**, and a player who
leaves partway must have paid the first without collecting the second. Running
`SideQuest` here would hand out the skill on the way in.
`engine/day_drain.py::PassDaysAction` is the precedent for a `TimeConsumable`
that buys nothing but the time.

**The sitting is module-level and transient**, the way `engine/states/teleport.py`
keeps its destinations. Not for tidiness: *a sitting that could be stored is a
sitting that could be resumed.* R2 says there is no resume point, so there is
nowhere for a sheet index to be written down. This is that "nowhere".

### `engine/states/side_quest_lecture.py` *(new, 229 lines)*

The screen. Recon §15 surveyed every long-form text format in the engine and
named `engine/states/lecture.py` + a `content/` dict as the best fit for these
sheets; Phase 11.5 then split all 36 paragraphs into `lines` sized for
`ui/dialog_box.py`'s three-row card **on that basis**. So this module is that
one's shape — same dialogue box, same two-stage SPACE, same typewriter, same
TEXT SPEED setting — with a sheet loop around it instead of a course loop.

**No new UI file.** `engine/states/lecture.py` has none either, and the header is
two centred lines over a flat fill, drawn the way that module draws its own. A
seventh long-form reader with its own card geometry would be a new pattern in a
repo that already has six.

Three details worth naming:

- **ENTER is not bound.** ENTER is CONFIRM on every `ConfirmPopup` in the game,
  so binding it to "next sheet" would let a player mashing through a lecture
  answer the leave question by accident — with two days and a whole topic on it.
  SPACE and left-click only. Covered by a test.
- **`exit()` ends any sitting**, so no path off this screen can leave one
  half-alive. It is a no-op on both real exits, which have already cleared it.
- **`update()` is guarded on `__leaving`, not on the popup.** `ctx.popup` is
  shared; reading a result this screen did not ask for would throw away a lecture
  off somebody else's question. Covered by a test.

### The three call sites

| File | Change |
|---|---|
| `engine/screen_manager.py` | `SIDE_QUEST_LECTURE = auto()` — **appended**, per hazard #3 |
| `engine/states/side_quests.py` | the confirm branch now charges and hands over |
| `engine/save_bridge.py` | `lecture_reader.end()` in the transient-state block |

**Not in `MENU_REGISTRY`, on purpose.** No prop routes to the reader — only
`engine/states/side_quests.py`, after the charge lands. Putting it in the
registry would offer the level editor a screen that opens with no days paid.

`tools/` needed no edit at all. `engine/states/exploration.py` — hazard #4's
busiest file — **was not opened.**

---

## The flow, as the brief spells it

```
1. re-check remaining >= day_cost, abort with no side effects  blocker()
2. deduct day_cost, ONCE, on open, not per sheet               start()
3. open on the first sheet                                     start()
4. every sheet for that quest, in order                        advance()
5. on the LAST sheet: mark_completed() and apply the skill      __complete()
```

Step 2 goes through `GameClock.process_time_consumable()` — recon §7's single
entry point for every time-costing action — so all three counters move together:
the player's pool, the semester's pool and the global career clock. The charge is
**measured** before and after rather than assumed from the action's cost, the way
`day_drain.drain()` measures, because `process_time_consumable()` does nothing at
all on a frozen session and a caller that trusted the intent would open a reader
it never paid for.

Step 5 happens once per quest and cannot happen twice: `mark_completed()` refuses
anything that is not `Unlocked`, and `Completed` is terminal.

---

## THE SKILL REWARD IS 15, AND IT WAS NOT INVENTED HERE

"Apply the skill" needed a number. It was **derived from the repository, in two
independent places that already agree**, not chosen:

1. `academic/side_quest_catalog.py` sets `exp_reward = 15` for all twelve.
2. `engine/endgame_manager.py` documents its two ending thresholds as
   *"TOP_GRADUATE 30.0 … STRONG_SKILLS_DROPOUT 15.0 — these line up with
   SideQuest's exp_reward of 15 per attempt: level 30 ≈ every tracked skill
   attempted twice on average, level 15 ≈ every tracked skill attempted once."*

So `skill_reward()` **reads the catalog** rather than declaring a second 15. A
smaller grant (one level, say) would have put the STRONG SKILLS DROPOUT ending
out of reach through side quests entirely, silently. This is also the first
caller `build_side_quest_catalog()` has ever had — recon §12 recorded it as dead.

**One interaction to flag, not fixed here.** `engine/progression.py` derives
spendable skill points as `completed_courses * 2 - total_invested`, and
`total_invested` sums levels across `SKILL_NODES`. A +15 grant therefore reduces
the points available to spend by hand on the skill tree screen (floored at 0 by
`max(0, …)`). That is a pre-existing property of the derived-points model shared
with every `kind: "skill"` prop in the game, and `SideQuest.execute_action()` was
always going to do exactly this. It is reported rather than tuned: changing the
economy is not this phase's, and Saif's endgame thresholds are calibrated to 15.

**Two names for one topic, both kept.** The PC's list calls semester 1 "Version
Control" (the skill tree's node name); the sheets call themselves "Git & GitHub"
(the lecture's own title). The reader shows the sheet's title, and the completion
notice names both — which makes it the one place the two are tied together.

---

## THE EDGE CASES — each one, and how

### 1. Deducting days crosses a semester boundary or ends the game

**Reused, not re-written.** The charge goes through
`GameClock.process_time_consumable()`, so Phase 6's threshold is crossed exactly
the way passing days or sitting an exam crosses it, and the HUD chip falls out of
the semester counter every frame with not one line of either repeated.

Phase 6's popup normally fires from `exploration.update()`, which does not run on
the PC's card. So `engine/states/side_quests.py::__open_reader()` calls
`day_warning.check(ctx)` itself on the same frame — a call, not a second copy —
and then **waits**: `__hand_over()` refuses to transition while any modal is
open, so the warning is read and dismissed *over the room*, and the router only
moves to the reader once the screen is clear. That is both halves of the brief's
requirement: resolved fully **before** the reader opens, and no time event can
land **on top of** an open one.

**A charge cannot roll a semester or end a run.** `advance_semester()` is called
only by `exam.close_semester()`, and the 960-day freeze only by
`check_semester_end_state()` in that same path (recon §7, §8). Phase 11 already
ruled that reaching zero days triggers nothing on its own. So the only two
boundaries a deduction can cross are the 15-day threshold and zero — and Phase 6
owns both. Asserted: a term at exactly `day_cost` charges to zero and the reader
still runs to completion without interruption.

### 2. The game is saved while the reader is open, then reloaded

**The save cannot be taken.** `progression.open_pause()` is called from exactly
one place — `engine/states/exploration.py` — so SAVE GAME and QUIT TO MENU are
both unreachable while the reader is open. `main.py` has no quit-time autosave;
the only one is `progression.__autosave` on QUIT TO MENU. Asserted structurally:
the reader's source contains no route to any of them.

**And a payload made one anyway carries nothing.** Per-sheet progress is never
written, so `capture()` taken mid-sitting contains no sheet id and nothing
sheet-shaped — proved on a real file through `SaveManager` in a
`tempfile.mkdtemp()`. `restore()` calls `lecture_reader.end()`, so a reload lands
on the map with the quest still Unlocked and the days already gone: exactly R2.

**No save payload change, and `SAVE_SCHEMA_VERSION` does not move.** This phase
adds no key. The quest states were already in the file from Phase 12.

### 3. `day_cost` is still -1 (unconfigured)

**Blocked with an explicit error — "LECTURE NOT CONFIGURED" — and never treated
as free.** Two locks:

- `content/side_quest_definitions.py::validate()` already refuses a negative
  `day_cost` **at import**, so the sentinel cannot ship: the game would not start.
- `blocker()` checks it anyway, and **before the day gate, deliberately.** `-1`
  satisfies `remaining >= cost` for every pool there is, including an empty one,
  so a day check running first would wave it straight through as free. That
  ordering is asserted at 80, 40, 2 and 0 days.

`get_definition()` returning `None` for an unknown id is caught first, because
`get_day_cost()` answers `0` for an unknown id and `0` looks free. Non-integer
costs (`None`, `"2"`, `2.0`, `True`) block the same way.

### 4. A lecture sheet fails to load mid-sequence

**Per R2, this is not leaving early: it is one unreadable card, and the sitting
still completes.** `get_sheet()` never raises and never returns `None` — an
unknown id comes back as `DEFAULT_SHEET`, which reads *"These notes are not on
this PC."* The sequence does not stop, no day is charged again, and the last
sheet still marks the quest Completed and applies the skill.

`start()` therefore keeps **every listed sheet id**, including a bad one.
Filtering it out would silently shorten the lecture and still pay out. The one
thing that does block is a quest with **no sheets at all**, which is a different
fault and costs nothing.

Unreachable in this build regardless: `validate()` checks all 36 ids against the
sheet table at import.

---

## The exit warning

Any player-initiated exit asks first and needs an explicit yes.

> **LEAVE THE LECTURE?**
> The 2 days you spent are gone.
> Nothing you have read is kept.
> You would start again from sheet 1.
> `[ LEAVE ]  [ KEEP READING ]`

Three lines exactly, the popup's hard maximum. The first two are what the brief
requires stated plainly; the third is R1 said out loud, because "you lose it" and
"you lose it forever" are different games and the player is owed the difference.
ESC on the question maps to CANCEL, so a second ESC backs out rather than
confirming.

The reminder is also on screen the whole time — `THIS TOPIC ONLY COUNTS ONCE THE
LAST SHEET IS READ` — because a player who has to be warned on the way out was
not told in time.

---

## ⚠ ONE PRE-EXISTING BUG HAD TO BE FIXED

`engine/save_bridge.py::restore()` built `GameClock` **before** installing the
restored `Semester`:

```python
ctx.session = GameSession()
ctx.game_clock = GameClock(ctx.session)     # caches Semester A
...
ctx.session.set_active_semester(Semester(target))   # session now holds B
```

`GameClock.__init__` caches `session.get_active_semester()` in its own
`__current_semester` and only ever replaces it in `advance_semester()`. So every
charge through `process_time_consumable()` deducted from an orphaned object,
while `ctx.semester()`, the HUD, the 15-day firewall and `engine/day_warning.py`
all read the live one. **`restore()` runs on every load AND on `new_game()`, so
this was true of every run.** It is the same class of bug `game_clock.py`'s own
BUG FIX note records, one object further out.

Measured before the fix: `process_time_consumable(PassDaysAction(5))` after a
restore left `ctx.semester()` at 80 and the orphan at 75.

**Fixed by moving one statement** to after `set_active_semester()` — nothing
between the two lines used `ctx.game_clock`. Out of this phase's scope, but the
phase's acceptance criterion ("deducts days exactly once") is false in the real
game without it, and so is every exam charge and Phase 11's prop. Reported here
rather than fixed silently.

---

## ⚠ ONE PHASE 14 TEST NOW ASSERTS THE OPPOSITE

`tests/test_side_quest_list.py::test_screen_confirming_logs_the_quest_and_closes`
asserted *"no day spent"* and *"back to the map"* — the Phase 14 contract, at the
call site Phase 14's own log named as **"the seam"** for Phase 15. Renamed to
`…_and_opens_the_reader` and updated: the id is still logged and the quest still
does not move, but the days now leave and the destination is the reader. The
docstring records what changed and why.

---

## Verification

```
py -3 -m tests.test_lecture_reader     55/55 passed, exit 0
py -3 -m tests.test_side_quest_list    46/46 passed  (1 case updated, above)
py -3 -m tests.test_quest_offer        33/33 passed, unchanged by this phase
py -3 -m tests.test_quest_state        29/29 passed, unchanged by this phase
py -3 -m engine.lecture_reader         the module's own stub, all checks passed
```

Headless (`SDL_VIDEODRIVER=dummy`). The only thing written anywhere is a
`tempfile.mkdtemp()` directory for the save round-trip, so `saves/` is never
touched — the rule `engine/save_manager.py`'s own stub already follows.

The rule half runs against the **real** `GameSession`, `GameClock`, `Player`,
`Semester` and `SkillTree` rather than mocks, because "the days came off" is a
claim about that pipeline and a fake pool would prove nothing. The screen half
drives the **real** `engine/states/side_quest_lecture.py` and
`engine/states/side_quests.py` through a **real** `AppContext` with real popups
and real `pygame.KEYDOWN` events.

| Requirement from the brief | Cases | Result |
|---|---|---|
| **re-check days on open, abort with no side effects** | a term drained under an open question | pass |
| **deduct once, on open, not per sheet** | semester + player + global clock, then re-checked after every sheet | pass |
| **open on the first sheet** | all 12 topics | pass |
| **every sheet, in order** | read back against `get_lecture_sheets()` for all 12 | pass |
| **last sheet marks Completed** | all 12 | pass |
| **…and applies the skill** | all 12, level 0 → 15 | pass |
| **nothing applied before the last sheet** | state and level checked at every step | pass |
| **the state machine is not modified** | 5 states, 4 transitions, exact set | pass |
| **only `mark_completed()` is called** | a whole run moves one quest one step | pass |
| **R1: quest returns to Unlocked** | after leaving at each sheet | pass |
| **R1: days not refunded** | all three counters | pass |
| **R1: full cost payable again** | second sitting starts at sheet 1, charges again | pass |
| **R1: day gate re-checked per attempt** | a term with room for one sitting refuses the second | pass |
| **no partial credit** | stopping after 0, 1 and 2 sheets are byte-identical | pass |
| **R2: closing the panel** | ESC through the real screen | pass |
| **R2: saving and reloading** | real file, real `SaveManager`, no sheet id in the payload | pass |
| **R2: no route to a mid-sitting save** | structural, on the reader's own source | pass |
| **exit warning states the loss** | days gone, nothing kept, restarts at sheet 1 | pass |
| **exit needs explicit confirmation** | CANCEL keeps the reader on the same sheet | pass |
| edge 1: warning answered before hand-over | 16 days → charge → WARNING on the card → then the reader | pass |
| edge 1: charge to zero, reader uninterrupted | a term at exactly `day_cost` | pass |
| edge 2: reload drops the sitting | mid-read `capture()` → disk → `restore()` | pass |
| edge 3: `day_cost = -1` blocks | at 80, 40, 2 and 0 days; plus non-int costs | pass |
| edge 3: the table refuses it at import | `validate()` raises | pass |
| edge 4: a broken sheet does not stop the run | 3 cards shown, topic still completes | pass |
| edge: a quest with no sheets blocks | nothing charged | pass |
| edge: a frozen run blocks | rather than reading for free | pass |
| edge: a short player pool blocks | rather than parting the two counters | pass |
| edge: no quest machine | refuses, never raises | pass |
| edge: somebody else's popup | leaves the other screen's result unread | pass |
| ENTER does not advance a sheet | `RETURN`, `KP_ENTER`, `E` all inert | pass |
| every popup fits 3 lines | every message this phase can produce | pass |
| every popup fits the box | measured in **pixels** through the real PressStart2P | pass |
| every popup is plain ASCII | no missing-glyph boxes | pass |
| regression | all 12 levels load strict; 23-module import sweep incl. `main`, `play_sandbox`, `tools.level_editor`, `save_bridge` | pass |
| | `quest_state`, `quest_offer`, `day_warning`, `day_drain`, `final_exam`, `menu_prop`, `side_quest_list`, `side_quest_definitions`, `side_quest_lectures`, `level_registry`, `save_manager` stub tests | pass |

**Visual acceptance**, captured headless at 1280×720: the reader mid-reveal on
sheet 1 with the HUD already showing `78/80`; the exit warning over it with both
buttons fitting their labels; and the completion notice, using the longest title
in the set ("Object-Oriented Programming (OOP)") to prove the box holds it.

```
days before      : 80
days after open  : 78
  SHEET 1 OF 3   Git & GitHub
  SHEET 2 OF 3   Git & GitHub
  SHEET 3 OF 3   Git & GitHub
state            : completed
skill            : Version Control = 15
days after read  : 78          <- not charged per sheet
```

---

## Merge-conflict risk

**Phase 15 adds zero conflicts.** `git merge-tree --write-tree HEAD origin/main`
produces a clean tree with and without this phase's commit — 0 conflict markers.

| File | Δ | Risk |
|---|---|---|
| `engine/lecture_reader.py` *(new)* | +651 | none — `main` has no such file |
| `engine/states/side_quest_lecture.py` *(new)* | +229 | none — `main` has no such file |
| `tests/test_lecture_reader.py` *(new)* | +1199 | none — `main` has no `tests/` directory |
| `engine/screen_manager.py` | +5 | low — a pure append, per hazard #3 |
| `engine/states/side_quests.py` | +73 −16 | none — the file is Phase 14's, new to `main` |
| `tests/test_side_quest_list.py` | +21 −8 | none — new to `main` |
| `engine/save_bridge.py` | +21 −2 | low — one moved statement and two appended lines |

`levels/campus_main.json` was modified in the working tree before this session
and is not this phase's; it is left out of the commit, the same way Phases 8, 9,
13 and 14 left it. The eight untracked `assets/props/*.png` are left alone for
the same reason.

---

## Out of scope — confirmed untouched

- **The ending gate.** `is_highly_skilled()` is not called anywhere in this
  phase. Phase 16's.
- **`engine/quest_state.py` is byte-identical.** No new state, no new transition.
- **`content/side_quest_lectures.py` is byte-identical.** No sheet was re-split,
  re-parsed or re-worded, and no sheet boundary moved.
- **The 15-day firewall.** `is_eligible_for_side_activities()` is still consulted
  by nothing on this path, exactly as Phases 13 and 14 left it — so Phase 17
  still has one place to land.
- **`engine/states/exploration.py`, `engine/app_context.py`,
  `content/level_registry.py`, every `levels/*.json`, and everything under
  `tools/`, `ui/`, `academic/` and `core/`** — not opened.
- **No save payload change and no `SAVE_SCHEMA_VERSION` bump.**
- **No new UI file, widget, card geometry or modal.** `ui/dialog_box.py`,
  `ConfirmPopup` and `MessagePopup` are the existing ones.

---

## Notes for the phases downstream

**Phase 16 (the ending gate).** `is_highly_skilled()` is now reachable for real:
`mark_completed()` finally has a caller, so twelve Completed is a state a
playthrough can actually arrive at. Nothing else changed for it.

**Phase 17 (the day lockout).** `engine/side_quest_list.py::refusal()` is still
the single day rule, and `engine/lecture_reader.py::blocker()` calls it — so the
15-day firewall lands in **one** function and covers the list, the confirmation,
the re-check after the answer, and the charge itself. Note the one ordering
constraint: the unconfigured-cost check in `blocker()` must stay **above** that
call, for the reason edge case 3 records.

**Anyone touching `restore()`.** The `GameClock` construction is now
order-dependent — it must stay below `set_active_semester()`. The comment there
says so.

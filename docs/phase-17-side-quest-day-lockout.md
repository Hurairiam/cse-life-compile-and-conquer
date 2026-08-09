# Phase 17 — Lock Out New Side Quests When Days Run Low

**Covers:** Change 4
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] block new side quests when semester days run low`

**Input:** the Phase 0 recon (`docs/recon.md`), Phase 6's threshold module
(`engine/day_warning.py`), Phase 12's state machine (`engine/quest_state.py`),
and the three paths Phases 13–15 built — all read first and used entirely
through their public API.

**Runs last, and gates every path built in Phases 13–15.** It defines no
threshold of its own: the number is still `GameClock.__MIN_MAIN_QUEST_TIME_BORDER`,
read through the one front door Phase 6 built for it.

---

## Step 1 — every path to a new side quest, reported before anything changed

### The two live ones

**① The NPC offer (Phase 13).** The only place `QuestStateMachine.accept()` is
ever called in the game.

```
exploration.__interact  ->  __talk  ->  dialogue_flow.start_talk
  arm_offer(ctx, npc)          quest_offer.offered_quest_id()
  ...the chain plays out...
dialogue.__advance      ->  dialogue_flow.open_offer()      the reply list
dialogue.__answer       ->  dialogue_flow.resolve_offer(index)
                            quest_offer.resolve()  ->  accept() / decline()
```

**② The PC in the player's room (Phases 14 + 15).** Where an unlocked quest is
started and days are actually spent.

```
prop kind="menu", menu_id="side_quests"  ->  ScreenState.SIDE_QUESTS
states/side_quests.__select  ->  side_quest_list.refusal() / is_startable()
                             ->  confirmation popup -> side_quest_list.confirm()
                             ->  lecture_reader.start()  -> blocker() re-checks,
                                 then charges day_cost through GameClock
                             ->  ScreenState.SIDE_QUEST_LECTURE
                             ->  mark_completed() + the skill grant
```

### The pre-existing ones recon turned up — all still dead

| Route | Status |
|---|---|
| `academic/quest.py::SideQuest.execute_action()` | never instantiated at runtime. `build_side_quest_catalog()` has one caller, `lecture_reader.skill_reward()`, which only *reads* `exp_reward` |
| `academic/semester.py::add_quest()` / `get_active_quest_pool()` | `add_quest()` is called by nothing |
| `core/character/npc.py::offer_quest()` | `__quest_pointer_array` is never populated; `engine/npc_manager.py` names the method only in its own design notes, explaining why it is unused |
| `engine/states/activity.py` START LECTURE | the **main quest** lecture over registered courses (`content/lectures.py`). Not a side quest |
| `exploration.py` `X` key, `kind: "skill"` props | neither touches the quest machine |

Blocking any of those would have been blocking dead code. That claim is not left
as prose — `test_paths_the_dead_side_quest_routes_are_still_dead` **parses** every
`.py` under `engine/`, `academic/`, `core/`, `content/`, `ui/` and `tools/` with
`ast` and fails the day a real call to either appears.

---

## Owner rulings

Reported first, then asked, then built. Two questions, two answers.

1. **Decision D1 — (a): the offer is unaffected.** It is still presented and can
   still be accepted below the threshold; only *starting* a quest is blocked. So
   **Phase 13's files were not opened at all** — `engine/quest_offer.py` and
   `engine/dialogue_flow.py` are byte-identical to what Phase 13 shipped.

2. **The NOTES reading, confirmed — and it extends to starting.** A quest already
   `Unlocked` keeps its state, stays on the PC's list, and is startable again next
   term. What it may not do below the threshold is open a **new sitting**, because
   a sitting spends days. "Taking on a new side quest" is any new lecture sitting.

---

## What was built

**One function, in one file.** Phases 14, 15 and 16 each recorded that
`engine/side_quest_list.py::refusal()` was the single place this phase would land.
It landed there.

### `engine/side_quest_list.py` — the rule

| Added | What it is |
|---|---|
| `threshold(ctx)` | the day count, delegated to `day_warning.threshold()`; `NO_THRESHOLD` (-1) when a context has no clock |
| `is_locked_out(ctx)` | the verdict, delegated to `day_warning.is_low()` |
| `NO_THRESHOLD` | the quiet answer for a context with no clock |
| one branch in `refusal()` | the block, above the cost check and below the state checks |

**No number is written down.** Both functions delegate to Phase 6, whose own
docstring names this phase as its caller, and which reads
`GameClock.get_min_border()`. There is still exactly one `15` in the codebase.
Asserted structurally off the **code object** rather than the source text —
`test_rule_no_second_number_is_written_down` fails if either function compiles
with any numeric constant at all, which a hand-written `<= 15` would.

**`day_warning` is imported lazily**, inside both functions, for the reason
`engine/dialogue_flow.py` imports `ui.popup` lazily: `day_warning` reaches
`ui/popup.py` for a severity constant, and this module's whole point is that it
loads with no pygame and no display. The import lands in `sys.modules` on the
first call and costs a dict lookup after that.

**A context with no clock locks nothing out.** The editor, the standalone
harnesses and the stub contexts the day rules are tested against have no
`game_clock`; the honest reading of "there is no clock" is that there is no
end-of-term rule, not that everything is shut. This is the same going-quiet that
`machine_of()` and `days_left()` already do, and it is why the 46 pre-existing
`test_side_quest_list` cases against stub contexts were unaffected.

**Where the check sits, and why.**

```
not on this list        ->  NOTHING SELECTED
already Completed       ->  ALREADY READ
not Unlocked            ->  NOTHING SELECTED
the term has run out    ->  TOO LATE IN THE TERM     <-- this phase
costs more than is left ->  NOT ENOUGH DAYS
```

Below the state checks, so a finished topic still reads `ALREADY READ` — the term
running out is not why *that* one is shut. Above the cost check, because it is the
wider of the two rules: below the threshold nothing new starts whatever it costs,
so a topic the player could otherwise afford is refused for the right reason.

The message states both figures, the way the cost refusal already did:

```
TOO LATE IN THE TERM
  Only 15 days left before the exams.
  No new lecture may be started
  with 15 days or fewer.
```

Three lines, the popup's hard maximum, phrased as one sentence across the last two
the way `day_warning.check()`'s own popup is. Measured against the real font: the
widest line is inside the 552px the 600px card allows, and every string is ASCII.

### `engine/states/side_quests.py` — the standing notice

The card's subtitle becomes `15 DAYS LEFT - NO NEW LECTURES` below the threshold.
START is already drawn muted there — `is_startable()` has driven `can_start` since
Phase 14 — and a muted button with no explanation beside it reads as a bug. The
rule is *asked for*, never restated.

### Nothing else was touched

`engine/quest_state.py`, `engine/quest_offer.py`, `engine/dialogue_flow.py`,
`engine/lecture_reader.py`, `engine/day_warning.py`, `engine/game_clock.py` and
`engine/states/side_quest_lecture.py` were **not opened**. The reader is gated
because `lecture_reader.blocker()` already defers to `refusal()` rather than
re-deciding — the seam Phase 15 left on purpose.

### `tests/test_day_lockout.py` *(new, 36 cases)*

`py -3 -m tests.test_day_lockout`, exit 0 or 1. Headless (`SDL_VIDEODRIVER=dummy`),
and nothing is written anywhere — this phase adds no save key and holds no state.

**The number 15 appears nowhere in the file.** Every case reads the threshold back
through `side_quest_list.threshold()`, so re-tuning `GameClock`'s constant re-aims
the whole suite instead of breaking it — which is itself one of the things tested.

The rule half runs over the **real** `GameSession`, `GameClock`, `Player`,
`Semester` and `SkillTree`; the last section drives the **real**
`engine/states/side_quests.py` through a **real** `AppContext` with real popups and
real pygame `KEYDOWN` events, because "the player is told why" is a claim about the
screen.

---

## Seven pre-existing tests were updated, and why

Phases 14 and 15 exercised the **cost** rule by driving the term to 0–3 days —
which is below the threshold, so the lockout now answers first. Each was updated
to the new reality rather than worked around, and each says so in its docstring:

| Test | Change |
|---|---|
| `test_screen_blocks_a_quest_that_costs_more...` → `..._blocks_a_start_when_the_term_has_run_out` | asserts the lockout at 1 day |
| `test_screen_a_stale_confirmation_is_refused...` | same, title only |
| `test_flow_the_day_gate_is_rechecked_on_open` | same, title only |
| `test_r1_the_day_gate_is_rechecked_on_the_retry` | term set to `threshold + 2` instead of `cost + 1`, so one sitting is granted and the next refused — the shape the test wanted |
| `test_block_not_enough_days_names_both_numbers` → `..._the_day_refusal_is_reused_and_names_both_numbers` | keeps the identity that proves the refusal is reused, asserts the lockout's two numbers |
| `test_edge_the_charge_can_take_the_term_to_zero` → `..._the_last_start_of_the_term_is_one_day_above_the_threshold` | **rewritten** — see the consequence below |
| `test_handover_a_stale_confirmation_charges_nothing` | title only |

**A consequence worth naming.** With every quest costing 2 days against a
threshold of 15, `NOT ENOUGH DAYS` is no longer reachable from the PC: it needs
`days_left < 2` **and** `days_left > 15` at once. The branch is kept — it is
correct the moment either number changes — and the cost rule is still covered
directly, against a clockless stub context, by
`test_day_blocks_a_quest_that_costs_more_than_the_term_has_left`.

The same arithmetic gives the feature a floor: the last day a sitting may open is
`threshold + 1`, so the lowest a lecture can leave the term is `14`. A lecture can
no longer take the term to zero, which is what the rewritten edge case now asserts.

---

## Verification

```
py -3 -m tests.test_day_lockout       36/36 passed, exit 0
py -3 -m tests.test_side_quest_list   46/46 passed
py -3 -m tests.test_lecture_reader    55/55 passed
py -3 -m tests.test_quest_offer       33/33 passed, unchanged by this phase
py -3 -m tests.test_quest_state       29/29 passed, unchanged
py -3 -m tests.test_ending_gate       37/37 passed, unchanged
                                     236/236
```

Regression: all 12 levels load strict **and round-trip byte-identically**; a
32-module import sweep including `main`, `play_sandbox`, `play_registration`,
`tools.level_editor` and `save_bridge`; the `note_prop`, `day_warning`,
`side_quest_list`, `quest_state`, `quest_offer` and `ending_gate` stubs all pass.

| Requirement from the brief | Cases | Result |
|---|---|---|
| **ACCEPTANCE: above the threshold, Phase 15 behaviour is unchanged** | opens, charges, completes, pays the skill; through the real screen too | pass |
| **ACCEPTANCE: at or below, no new side quest through any path** | the list, `is_startable`, `refusal`, `lecture_reader.blocker`, `start`, and the real PC screen | pass |
| …every day from the threshold down to an empty term | 16 checks, one per day | pass |
| **ACCEPTANCE: the player is told why** | title, both numbers, ≤3 lines, fits the card, ASCII; plus the standing subtitle | pass |
| **ACCEPTANCE: quests already unlocked still work** | state untouched, still listed, startable again after a real `advance_semester()` | pass |
| **blocking changes no quest state** | all five states present, every path attempted, all twelve compared before/after | pass |
| **the threshold is Phase 6's, not a second one** | equals `get_min_border()`; equals `day_warning.threshold()`; the verdict equals `day_warning.is_low()`; complement of `is_eligible_for_side_activities()` | pass |
| …and cannot be re-hardcoded | neither deciding function compiles with any numeric constant | pass |
| the boundary is `<=`, not `<` | `threshold+1` allowed, `threshold` and `threshold-1` refused | pass |
| a context with no clock is quiet | `object()`, `None`, a half-built context | pass |
| **D1 (a): the offer is unaffected** | offered and acceptable at 0 days; declinable; all twelve semesters | pass |
| …structurally | neither `quest_offer` nor `dialogue_flow` mentions `day_warning`, `side_quest_list`, `is_locked_out`, `get_min_border` or `is_eligible_for_side_activities` | pass |
| a sitting already open is not interrupted | the charge crosses the threshold and the reader still reads through | pass |
| **there is no other path to block** | the two dormant routes have no callers (parsed, not grepped); one menu id routes to the list; `refusal()` is the only gate | pass |
| the state machine was not modified | five states, four transitions | pass |

### The debug view

```
py -3 -m engine.side_quest_list
```

```
16 days left in the term
TOPIC                      DAYS   SHEETS  START?
OOP                        2      3       yes

15 days left in the term   -- LOCKED OUT (threshold 15)
TOPIC                      DAYS   SHEETS  START?
OOP                        2      3       no  (TOO LATE IN THE TERM)
```

`py -3 -m tests.test_day_lockout` prints the same boundary day by day, plus the
threshold read off the real clock.

---

## Also in this commit — the level editor's NOTE prop

Not part of Change 4. Requested alongside it: **a prop that shows text of the
author's own choosing when the player interacts with it.**

### What it is

A sixth interaction kind, `"note"`, beside `none / money / skill / menu / travel`.
A prop wearing it opens the game's ordinary message popup with a title and up to
three lines the author typed in the level editor — a sign, a poster, a page left
on a desk. It grants nothing.

```
tools/editor_popups.py     PropSettingsPopup — the NOTE panel (author writes it)
content/level_registry.py  the kind + the three caps (what the card can hold)
content/level_schema.py    PropData note fields, serialisation, validation
engine/note_prop.py        NEW — the runtime behaviour
engine/states/exploration.py   one import line, one call
```

### Decisions

**Read every time, like a menu and unlike a payout.** `note_prop.trigger()` is
called from `__trigger_prop()` in the same band as `menu_prop.trigger()` and the
travel check — *above* the per-semester trigger cap. A doorway usable three times
a term would be nonsense, and so would a notice that stops being readable in
March. Nothing is recorded: no trigger spent, no uid in `ctx.triggered_prop_uids`,
no day charged, nothing in the save file. Anything that should restrict *who* may
read one goes on the prop's gate, which `__interact()` has already evaluated.

**Separate fields per line, not one box the runtime wraps.** `ui/popup.py` neither
wraps nor truncates — it draws the lines it is handed at a fixed pitch — so where
the break falls is the author's decision, and the editor is where they make it.
The gate popup's locked-message editor is laid out the same way. Blank fields are
dropped rather than kept: an empty line is a visible hole in a centred card.

**The caps are measured, not guessed.** The 600px card holds 50 body characters at
`SIZE_BODY` and 34 title characters at `SIZE_TITLE`; the fields cap at 44 and 28.

**Existing levels round-trip byte for byte.** `note_title` and `note_lines` are
written into the prop's `interaction` block **only when something was typed** —
the same rule `menu_id`, `rotation`, `pass_behind` and `gate` already follow. All
12 level files re-serialise identically, checked.

**A note with nothing on it is a warning, never a blocker.** `NOTE_NO_TEXT` at
save time; at runtime `shows_note()` is False and the prop falls through to the
ordinary "there is nothing here to take" line rather than opening an empty card.
An author part-way through writing a sign must still be able to save.

**The kind chip row was widened 330 → 450.** Six chips where there were five;
at 330 the row's auto-shrinking font made TRAVEL and NOTE hard to tell apart.

`INTERACTION_KINDS` was **appended to, never reordered** — the rule `MENU_REGISTRY`
already states for the same reason.

### Verified

`py -3 -m engine.note_prop` — 11 checks: the card opens with the author's own
words, opens again five times over, falls through when empty or non-interactable
or any other kind, defaults a cleared title, drops blank lines, clamps to three,
survives a round trip through the level file format, and never raises on something
that is not a prop.

Driven through the **real** `exploration.__trigger_prop()` on a real `AppContext`:
the popup opens with the authored title and lines, four times running, spending no
trigger and recording no uid. The editor panel was driven headless end to end —
click a field, type, press OK, read the resulting dict back through
`PropData.from_dict()`.

The `[E] EXAMINE` chip needs no change: `verb_for()` already labels any
interactable non-travel prop that way, which is what a sign should read as.

---

## Merge-conflict risk

**`git merge-tree --write-tree HEAD origin/main` produces a clean tree — 0 conflict
markers**, with and without this phase's commit.

| File | Δ | Risk |
|---|---|---|
| `engine/note_prop.py` *(new)* | +207 | none — `main` has no such file |
| `tests/test_day_lockout.py` *(new)* | +751 | none — `main` has no `tests/` directory |
| `engine/side_quest_list.py` | +146 −25 | none — the file itself is new on this branch (Phase 14) |
| `engine/states/side_quests.py` | +13 | none — new on this branch (Phase 14) |
| `tests/test_lecture_reader.py`, `tests/test_side_quest_list.py` | +118 −36 | none — both new on this branch |
| `content/level_registry.py` | +27 | low — a pure append to `INTERACTION_KINDS` plus a new constant block; already divergent from `main` on this branch |
| `content/level_schema.py` | +113 | low — new accessors and two conditional serialisation keys; nothing renamed or reordered; already divergent |
| `tools/editor_popups.py` | +112 | low — one new panel and one widened rect inside `PropSettingsPopup`; already divergent |
| `engine/states/exploration.py` | +18 −6 | **the one to watch** — one import line and one call in `__trigger_prop`; the recon names this the busiest shared file, which is exactly why the behaviour is in `engine/note_prop.py` and not here |

`levels/cafeteria.json`, `levels/campus_lobby.json`, `levels/campus_main.json`,
`levels/field.json` and `levels/lecture_hall.json` were modified in the working
tree by level-editor work running alongside this session — `field.json` appeared
mid-session — and are **left out of this commit**, the same way Phases 8, 9, 13,
14, 15 and 16 left `campus_main.json` out of theirs. The untracked
`assets/props/*.png` are left alone for the same reason.

---

## Out of scope — confirmed untouched

- **The state machine's transition rules.** `engine/quest_state.py` is
  byte-identical: five states, four transitions, and this phase calls no mutator.
- **The Phase 6 warning popup and HUD.** `engine/day_warning.py` and `ui/hud.py`
  are byte-identical. This phase only *reads* `threshold()` and `is_low()`.
- **Phase 13's offer path.** `engine/quest_offer.py` and `engine/dialogue_flow.py`
  are byte-identical — Decision D1 (a), asserted structurally.
- **No save payload change and no `SAVE_SCHEMA_VERSION` bump.** The lockout holds
  no state; it is derived from the day count every frame. The note prop is level
  data, not save data.
- **`play_sandbox.py` was not opened.** It is byte-identical to `origin/main` and
  carries its own prop dispatch; the level editor has no link to it, so a note is
  previewed by running the game rather than the sandbox. Worth wiring up if the
  sandbox is ever used for authoring again.

---

## Notes for whoever comes next

**On balance.** Twelve completed side quests now have to fit inside twelve terms
whose last 15 days are closed to them — 65 usable days a term against a 2-day
lecture, so the budget is not tight, but Phase 16 already flagged that nobody has
played a full run against the finished chain. That is still a playtest question.

**On the cost rule.** `NOT ENOUGH DAYS` is unreachable through the PC today and
will stay so while `day_cost` is under the threshold. If a longer quest is ever
authored it becomes live again with no code change — which is why it was kept.

**On the note prop.** `INTERACTION_KINDS` is now six long and the chip row is
sized for six. A seventh kind needs the row widened again, or split.

# Phase 16 — Side Quests: Highly-Skilled Ending Gate

**Covers:** Prompt 5
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] gate highly skilled ending on all 12 side quests`

**Input:** the Phase 0 recon (`docs/recon.md`), Phase 12's state machine
(`engine/quest_state.py`) and definitions (`content/side_quest_definitions.py`),
and Phase 15's completion path (`engine/lecture_reader.py`) — all read first and
used entirely through their public API.

**The state machine was not modified.** `git diff` on `engine/quest_state.py` is
empty: five states, four transitions, exactly as Phase 12 left them. Asserted,
not just claimed — `test_untouched_five_states_and_four_transitions` and
`test_untouched_no_mutator_appears_in_the_module`. This phase only ever *reads*
the machine; `test_untouched_the_gate_writes_nothing` proves the whole report
leaves all twelve states where it found them.

---

## Step 1 — the integration point, shown before anything was changed

### One function decides the ending

`engine/endgame_manager.py::determine_ending_title(player)` — nothing else in the
repo picks between the four endings. Two inputs, two axes:

```python
graduated = player.get_accumulated_credits() >= 140                    # academic
average   = calculate_average_skill_level(player.get_skill_tree())     # SKILL
if graduated:  return "TOP GRADUATE" if average >= 30.0 else "AVERAGE GRADUATE"
else:          return "DROP OUT Strong Skills" if average >= 15.0 else "DROP OUT Weak Skills"
```

**"Highly skilled" is not a spare flag in this game — it is that second axis, and
it already names two of the four endings.** So the prompt landed on a rule that
existed and worked, which is why it says *show me before changing it*.

### The call chain, one caller at each hop

```
engine/states/exam.py::close_semester()          the only route to an ending
  quest_offer.expire_semester(ctx)               Phase 13 — books closed first
  game_clock.check_semester_end_state()          freezes at 140 cr / 960 d
  if session.get_is_frozen(): go(ENDGAME)
engine/states/endgame.py:11-13  enter()
  manager = ctx.session.trigger_endgame_evaluation()      game_session.py:113
  ctx.endgame_result = manager.evaluate(ctx.player())     ← THE SEAM
ui/endgame_screen.py             themes off the title
engine/states/certificate.py:16  reads the same title back
```

Phase 13's ruling matters here: expiry runs **above** the freeze check, so by the
time the ending is evaluated no quest can still be Unoffered. The gate reads a
closed book.

### The mechanical obstacle

`evaluate()` takes a `Player` and nothing else. `is_highly_skilled()` hangs off
`ctx.quest_states`, and a `Player` has no route to the `AppContext`. So the
verdict has to enter at `engine/states/endgame.py:13`, the single caller.

### Merge position

`engine/endgame_manager.py`, `engine/states/endgame.py`, `engine/game_session.py`,
`ui/endgame_screen.py`, `content/epilogue_text.py` and
`engine/states/certificate.py` were all **byte-identical to `origin/main`**. This
is the first phase to touch any of them.

---

## THREE MEASUREMENTS THAT DECIDED THE SHAPE

Reported with the integration point, because they changed what the answer could
mean. None of them was assumed; each was run.

**1. `SkillTree` levels come from three places, of which two are live.**
`progression.invest()` (+1, capped at `max_level`), a `kind: "skill"` prop
(+amount, uncapped) and Phase 15's completion grant (+15, uncapped). **Not one
`kind: "skill"` prop exists in the twelve level files** — recon §12 recorded that
and it is still true.

**2. Twelve completed quests average exactly 15.0.** Twelve grants of 15 EXP onto
twelve *distinct* skills (`validate()` forbids a duplicate `skill_id`), so
12 × 15 / 12 = 15.0 — landing precisely on `STRONG_SKILLS_DROPOUT_THRESHOLD`.
n quests give 15n/12.

**3. The ceiling on average skill level in the shipped game is 15.0, so TOP
GRADUATE was unreachable.** `invest()` refuses a node already at its `max_level`
of 10, and a completed quest puts its node at 15 — so completing a quest
permanently locks hand-investment out of the skill it feeds. `sum(max_level)`
over `SKILL_NODES` is 120 across 12 nodes, an average of 10.0 from investment
alone. Best case overall is twelve nodes at 15 → average 15.0, against a
threshold of 30.0. **Every graduating player got AVERAGE GRADUATE, whatever they
did.**

So the old rule broke the brief in **both** directions: on the dropout row the
15.0 threshold coincided with the 12/12 gate only by arithmetic accident, sitting
exactly on the boundary; on the graduate row it made the highly-skilled outcome
impossible even at 12/12. And a single `kind: "skill"` prop authored in the level
editor tomorrow would have opened an alternative route to the outcome — the thing
the brief forbids.

---

## Owner rulings

Reported first, then asked, then built. Two questions, two answers.

1. **Replace both rows.** The skill axis becomes `is_highly_skilled()`:
   TOP GRADUATE ⇔ graduated **and** 12/12; DROP OUT Strong Skills ⇔ not graduated
   **and** 12/12. The two threshold constants stop deciding anything. This is the
   literal "if and only if", and it makes TOP GRADUATE reachable for the first
   time.

2. **The debug command is a module stub** — `py -3 -m engine.ending_gate`, the
   repo's standing convention (recon §14, and what `py -3 -m engine.quest_state`
   already is). No change to the running game's surface.

---

## What was built

One new file, one new test module. Two existing files took a change each, and
nothing else was touched.

### `engine/ending_gate.py` *(new, 289 lines)*

```
machine_of(source)          the QuestStateMachine behind a ctx or a bare machine
is_highly_skilled(source)   THE GATE — all twelve Completed, or False
completed_count(source)     reporting only, never the gate

quest_rows(source)          twelve rows: semester, npc, quest, skill, state
report_lines(source, title) the debug report as lines
print_report(source, title) the debug command's whole body
```

**Why a new module.** Recon hazard #4, and the precedent `engine/menu_prop.py`,
`engine/quest_offer.py`, `engine/side_quest_list.py` and
`engine/lecture_reader.py` all set: new logic goes in a new file, and the shared
modules carry a call rather than a branch. No pygame, no screen state, no UI — so
the verdict and the report are testable headless. They are.

**`is_highly_skilled()` is total.** Every shape of "there is no quest machine" — a
context built before Phase 12, a test double, a half-restored save, `None`, a
bare `object()` — answers **False**, never an exception. False is the safe
default in both directions: the ending it withholds is the good one, and a crash
on the last screen of the game would lose the whole run.

**The four ending titles are not restated here.** `report_lines()` asks
`EndgameEvaluationManager.title_for()` for them, so the report cannot drift from
the endings the game actually shows. Asserted structurally: no title string is a
literal anywhere below this module's docstring.

**The report prints both columns of the 2×2** — the ending if graduated *and* the
ending if not. The gate decides one axis, and printing only one would read as if
the quests alone chose the ending.

### `engine/endgame_manager.py` — the decision

| Change | Why |
|---|---|
| **`title_for(graduated, highly_skilled)`** *(new)* | the 2×2, split out so both axes can be read, tested and reported without a `Player` to hand |
| `determine_ending_title(player, highly_skilled)` | second argument, **no default** |
| `evaluate(player, highly_skilled)` | same, passed straight through |
| `TOP_GRADUATE_SKILL_THRESHOLD`, `STRONG_SKILLS_DROPOUT_THRESHOLD` | kept, marked **RETIRED — read by nothing** |
| `calculate_average_skill_level()` | kept, marked retired from the decision |
| module docstring | the three measurements above, written down where the next person will look |

**`highly_skilled` deliberately has no default.** A default would have to be
either a guess or the retired average-level rule, and both are a silently wrong
ending on the last screen of the game. A caller that forgets gets a `TypeError`
at the one call site instead — loud and immediate. `test_title_the_verdict_has_no_default`
asserts the raise, which is the structural guarantee that no second rule is
hiding behind a default value.

**The retired pieces were kept rather than deleted.** Nothing reads them —
asserted, not asserted-in-a-comment: `test_no_alternative_route_the_decision_never_reads_the_average`
reads the source of both deciding functions and fails if either name appears
below the docstring. Deleting public API off a teammate's class, in a file
otherwise identical to `origin/main`, buys nothing and costs merge surface.

### `engine/states/endgame.py` — the one call site

One import and one argument:

```python
ctx.endgame_result = manager.evaluate(
    ctx.player(), ending_gate.is_highly_skilled(ctx))
```

`engine/states/exam.py`, `engine/states/certificate.py`, `ui/endgame_screen.py`,
`content/epilogue_text.py` and `engine/game_session.py` were **not opened**.

### `tests/test_ending_gate.py` *(new, 37 cases)*

`py -3 -m tests.test_ending_gate`, exit 0 or 1. Headless (`SDL_VIDEODRIVER=dummy`);
the only thing written is a `tempfile.mkdtemp()` directory, so `saves/` is never
touched — the rule `engine/save_manager.py`'s own stub already follows.

Test states are reached **through the public API only** (`machine()` drives quests
into each state with `accept` / `decline` / `mark_completed` /
`expire_unoffered_for_semester`), so no case can set up a state the game itself
could not reach.

---

## Verification

```
py -3 -m tests.test_ending_gate      37/37 passed, exit 0
py -3 -m engine.ending_gate          the debug command — all scenarios correct
py -3 -m tests.test_lecture_reader   55/55 passed, unchanged by this phase
py -3 -m tests.test_side_quest_list  46/46 passed, unchanged
py -3 -m tests.test_quest_offer      33/33 passed, unchanged
py -3 -m tests.test_quest_state      29/29 passed, unchanged
```

Regression: all 12 levels load strict; a 28-module import sweep including `main`,
`play_sandbox`, `play_registration`, `tools.level_editor`, `save_bridge` and every
endgame module; the `quest_state`, `quest_offer`, `save_manager` and
`side_quest_definitions` stubs still pass.

| Requirement from the brief | Cases | Result |
|---|---|---|
| **ACCEPTANCE: 12 Completed → highly skilled** | `test_acceptance_twelve_completed_*`, both as a bare machine and on a context | pass |
| **ACCEPTANCE: 11 Completed + 1 Missed → not** | tried **twelve times, once per quest left out** | pass |
| **ACCEPTANCE: 11 Completed + 1 Declined → not** | tried **twelve times, once per quest left out** | pass |
| eleven is eleven however the twelfth got left behind | + 1 Unlocked and + 1 Unoffered, twelve times each | pass |
| **no partial tiers** | 0 through 11 completed all answer no; only 12 answers yes | pass |
| **no alternative route** | every tracked skill at 999 — far past both retired thresholds — still AVERAGE GRADUATE / DROP OUT Weak Skills at 11/12 | pass |
| …and the reverse | an **empty** skill tree still gets TOP GRADUATE / Strong Skills at 12/12 | pass |
| …structurally | neither deciding function's body names the average or either threshold | pass |
| …at the call site | `endgame.py` fills the verdict from `ending_gate` and calls `evaluate()` exactly once | pass |
| the verdict cannot be defaulted | omitting it raises `TypeError` on both entry points | pass |
| **the integration point is really wired** | the REAL `endgame.enter()`, a REAL `AppContext`, `GameSession`, `Player` and `SkillTree` | pass |
| the four endings, end to end | 12/12 + 140 cr → TOP GRADUATE · 12/12 + 0 cr → Strong Skills · 11/12 → AVERAGE / Weak | pass |
| the academic axis is unchanged | 140 credits, `>=` not `>` | pass |
| every reachable title is a real theme and epilogue | checked against `THEMES` and `EPILOGUE_TEXT` | pass |
| the certificate reads the same title | the real `certificate.enter()` off the same `ctx.endgame_result` | pass |
| the result is computed once | re-entering does not re-evaluate | pass |
| the session still freezes on entry | unchanged, asserted so a refactor cannot drop it | pass |
| the screen still turns the page | SPACE → `CERTIFICATE` through the real router | pass |
| **the verdict survives a save** | 12/12 through a real file via `SaveManager` → `from_state()` | pass |
| …and one short stays short | twelve times, once per quest left out | pass |
| a pre-quest save is not highly skilled | the `quests` block **deleted** from a real payload | pass |
| a hand-edited save cannot forge it | `"COMPLETED!"`, `"complete"`, `"finished"`, `""`, `None`, `12` all fall back to Unoffered | pass |
| **the state machine was not modified** | 5 states, 4 transitions, exact set; no mutator in the module; the report writes nothing | pass |
| **the debug command** | run for real in a subprocess: exit 0, all twelve quest ids present, both verdicts present | pass |
| the report is plain ASCII | a Windows console is cp1252 and a stray em dash there is a crash | pass |

### The debug command

```
py -3 -m engine.ending_gate
```

```
FORCED: ALL TWELVE COMPLETED
----------------------------
SEM  NPC      QUEST ID                 SKILL ID                 STATE
1    purnno   SQ_GIT_GITHUB            git                      completed
2    rahman   SQ_OOP                   oop                      completed
3    rafi     SQ_DSA                   dsa                      completed
4    roya     SQ_WEB_APP_DEV           web_app_dev              completed
5    hoque    SQ_AI_TOOLS              ai_tools                 completed
6    zayan    SQ_LINUX_CLI             linux_cli                completed
7    kabir    SQ_DEBUGGING_TESTING     debugging_testing        completed
8    purnno   SQ_TECH_COMMUNICATION    technical_communication  completed
9    rahman   SQ_DATABASES_SQL         databases_sql            completed
10   roya     SQ_NETWORKING            networking               completed
11   hoque    SQ_DOCKER                docker                   completed
12   kabir    SQ_PROGRAMMING_LANGUAGE  programming_language     completed

completed              : 12/12
HIGHLY SKILLED         : YES
ending if graduated    : TOP GRADUATE
ending if not graduated: DROP OUT Strong Skills
```

It then prints a mixed run (all five states on screen at once) and drives the
brief's three scenarios — 1 + 12 + 12 checks, plus the two non-terminal ways to
fall short, a fresh run and a context with no machine at all — exiting non-zero
if any comes out wrong. That is the whole acceptance criterion without a
twelve-semester playthrough.

### Visual acceptance

Captured headless at 1280×720 through the real `endgame.enter()` and
`endgame.render()`:

```
ending_12of12_graduated  completed=12  skilled=True   -> TOP GRADUATE
ending_11of12_graduated  completed=11  skilled=False  -> AVERAGE GRADUATE
ending_12of12_dropout    completed=12  skilled=True   -> DROP OUT Strong Skills
ending_11of12_dropout    completed=11  skilled=False  -> DROP OUT Weak Skills
```

The TOP GRADUATE card — dark background, gold accent,
`FINAL EVALUATION -- WITH DISTINCTION` — renders correctly. **It had never been
reachable before this change**, so its theme had never been drawn by a real run.

---

## Merge-conflict risk

**Phase 16 adds zero conflicts.** `git merge-tree --write-tree HEAD origin/main`
produces a clean tree with and without this phase's commit — 0 conflict markers.

| File | Δ | Risk |
|---|---|---|
| `engine/ending_gate.py` *(new)* | +289 | none — `main` has no such file |
| `tests/test_ending_gate.py` *(new)* | +707 | none — `main` has no `tests/` directory |
| `engine/endgame_manager.py` | +94 −25 | **the one to watch** — see below |
| `engine/states/endgame.py` | +9 −1 | low — one import, one argument |

`engine/endgame_manager.py` was identical to `origin/main` and is Saif's file, so
this phase moves it out of recon's "safest to extend" set. The mitigation was to
keep the change *additive where possible*: `title_for()` is a new method,
`determine_ending_title()` lost eleven lines of branching and gained one
delegation, and nothing was renamed, reordered or reformatted. `TRACKED_SKILL_IDS`
— which `engine/exam_session.py` and `ui/stats_screen.py` both read — was not
touched.

`levels/campus_main.json` was modified in the working tree before this session and
is not this phase's; it is left out of the commit, the same way Phases 8, 9, 13,
14 and 15 left it. The sixteen untracked `assets/props/*.png` are left alone for
the same reason.

---

## Out of scope — confirmed untouched

- **`engine/quest_state.py` is byte-identical.** No new state, no new transition,
  and not one call to `accept()`, `decline()`, `mark_completed()` or
  `expire_unoffered_for_semester()` outside the debug block's throwaway machines.
- **No save payload change and no `SAVE_SCHEMA_VERSION` bump.** The gate holds no
  state of its own — it reads the quest machine, whose persistence Phase 12
  already built.
- **No new UI file, no new screen, no new `ScreenState`, no `MENU_REGISTRY`
  entry.** The four ending titles, their four themes and their epilogue text are
  exactly as they were; only *which* one a run reaches has changed.
- **`content/epilogue_text.py`, `ui/endgame_screen.py`,
  `engine/states/certificate.py`, `engine/game_session.py`,
  `engine/states/exam.py`, `engine/app_context.py`, `engine/save_bridge.py`,
  every `levels/*.json`, and everything under `tools/`, `academic/` and `core/`**
  — not opened.
- **The 15-day firewall.** `is_eligible_for_side_activities()` is still consulted
  by nothing on the side-quest path, exactly as Phases 13, 14 and 15 left it — so
  Phase 17 still has one place to land.

---

## Notes for the phases downstream

**Phase 17 (the day lockout).** Unaffected. This phase reads the machine and never
writes to it, and it consults no day counter at all.
`engine/side_quest_list.py::refusal()` is still the single day rule.

**Anyone touching the ending.** `EndgameEvaluationManager.title_for()` is now the
2×2, and it is the only place the four title strings are chosen. If a fifth
ending is ever added, it goes there, plus a `THEMES` entry and an `EPILOGUE_TEXT`
entry — `test_title_every_ending_is_a_real_theme_and_epilogue` will fail until
all three agree.

**Anyone tempted to re-wire the average.** The two retired thresholds are still in
`endgame_manager.py` and still look live. They are not, and
`test_no_alternative_route_the_decision_never_reads_the_average` fails the moment
either name reappears in a deciding function. Read the three measurements in the
module docstring first — the numbers do not mean what they look like they mean.

**A consequence worth naming, not fixed here.** TOP GRADUATE now requires all
twelve side quests *and* 140 credits. Phase 15 recorded that each completion
costs 2 days and grants 15 EXP, and that the grant reduces
`engine/progression.py`'s derived spendable points. Twelve completions is 24 days
across twelve semesters — comfortably inside the budget — but nobody has played a
full run against the finished chain yet. The gate is the rule the brief asked
for; whether the run is *balanced* around it is a playtest question, not this
phase's.

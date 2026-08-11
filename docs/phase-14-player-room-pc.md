# Phase 14 — Side Quests: Player's Room PC and Quest List

**Covers:** Prompt 3
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] add player room PC with side quest list`

**Input:** the Phase 0 recon (`docs/recon.md`), Phase 12's state machine
(`engine/quest_state.py`) and definitions (`content/side_quest_definitions.py`),
and Phase 13's offer path (`engine/quest_offer.py`) — all read first and used
entirely through their public API. **The state machine was not modified** —
`git diff` on `engine/quest_state.py` is empty, and nothing in this phase calls
`accept()`, `decline()`, `mark_completed()` or `expire_unoffered_for_semester()`.

---

## Step 1 — the report, made before anything was written

### The PC already existed, and it was already doing something

Recon §11 records it under "Live example", and it is still there:

| Prop | Type | Cell | Interaction | Before this phase |
|---|---|---|---|---|
| `prop_0023` | `computer_desk_4` | (6, 2) | `menu` | `menu_id: "skill_tree"` |
| `prop_0024` | `computer_desk_3` | (5, 2) | `menu` | `menu_id: "skill_tree"` |

Those are the two lower tiles of the 2×2 computer desk in
`levels/player_room.json` — one object as far as the player is concerned, two
prop records as far as the file is concerned. The brief says extend the PC
rather than add a second one, so the question was not *where to put a PC*, it
was *what happens to the skill tree the PC currently opens*. That was reported
and asked before anything was edited.

### What the rest of the machinery already gave us

| Piece | Where | State before this phase |
|---|---|---|
| The five quest states | `engine/quest_state.py` | live, written only by Phase 13 |
| `get_unlocked_quests()` / `get_completed_quests()` | same | live, **no caller** |
| `day_cost`, `lecture_sheets`, `skill_id` per quest | `content/side_quest_definitions.py` | live, uniform 2 days / 3 sheets |
| Skill display names | `content/level_registry.py::get_skill_display_name()` | live, used by the editor |
| The list widget | `ui/ui_widgets.py::RowTable` | live |
| Prop → screen routing | `engine/menu_prop.py` + `MENU_REGISTRY` | live; a new screen is three appends |
| The remaining-days counter | `Semester.get_time_pool_days()` | live, the one the HUD draws |

So "follow the existing UI/menu patterns" was satisfied by writing no new
patterns at all. The card is `ui/teleport_screen.py`'s shape, the table is the
shared `RowTable`, the confirmation is the shared `ConfirmPopup`, and the prop
reaches the screen through the same `menu_id` path a noticeboard uses.

---

## Owner rulings

Reported first, then asked, then built. One question, one answer.

1. **Both desk tiles re-point to the side quest list.** `prop_0023` and
   `prop_0024` now carry `menu_id: "side_quests"`. No third interactable was
   added to a ten-by-ten room, and the two halves of one desk do not do two
   different things. The skill tree did not lose a door — it is on the pause
   menu, one ESC away, where it has always been (recon §6).

---

## What was built

Three new files. Two shared files took one append each, and one level file took
two changed strings.

### `engine/side_quest_list.py` *(new, 341 lines)*

```
LOG_PREFIX                  what a confirmed selection writes
machine_of(ctx)             ctx.quest_states, or None
days_left(ctx)              the SEMESTER's pool, or 0
listed_ids(ctx)             the quest ids this PC may show
entry(ctx, quest_id)        title / day_cost / sheets / completed / affordable
entries(ctx)                every row, in the order it is drawn
is_startable(ctx, quest_id) the one gate
refusal(ctx, quest_id)      why not — (title, lines) — or None
confirmation(ctx, quest_id) the question — (title, lines)
confirm(quest_id)           log it, and stop
get_last_confirmed()        the id, for Phase 15
```

**Why a new module.** Recon hazard #4, and the precedent `engine/menu_prop.py`,
`engine/day_drain.py`, `engine/final_exam.py` and Phase 13's
`engine/quest_offer.py` all set. It also keeps the visibility rule in exactly
one place: `engine/states/side_quests.py` draws and takes input, and has no
filtering step of its own to get wrong. No pygame, no screen state, no UI — so
it is tested headless, and it is.

**`listed_ids()` cannot enumerate a hidden quest.** It reads
`get_unlocked_quests()` and `get_completed_quests()` — the two *positive* lists
— rather than walking the twelve and skipping some. There is no code path in
this module that has a Declined or Missed quest in hand, so nothing downstream
can accidentally count one.

### `ui/side_quest_screen.py` *(new, 448 lines)*

The "SELF STUDY" card, drawn over the room behind a dimming veil, the way
`ui/teleport_screen.py` and `ui/activity_choice_screen.py` already are. Four
columns — `TOPIC / DAYS / SHEETS / status` — on the shared `RowTable`, five rows
visible with the scrollbar the widget provides, and START / CLOSE at 44 px.

`format_quest_row()` is module-level and outside the class, the way
`format_destination()` and `format_slot_row()` are: the screen is handed cells,
and never reaches into a quest (§6.1).

Column offsets are sized off the longest label the skill tree can produce
("Version Control", "Data Structures", "Databases & SQL" — 15 characters) and
the longest status ("COMPLETE"), so nothing that can appear here is truncated by
`RowTable`'s per-column clip. Checked by rendering the all-twelve-completed case.

### `engine/states/side_quests.py` *(new, 244 lines)*

`enter` rebuilds the list, `handle_events` gives the table first refusal on every
event, `update` resolves the confirmation, `render` draws the room and then the
card. The same four hooks `teleport.py` and `pass_days.py` define, in the same
order, for the same reasons — including redrawing exploration underneath,
because the router renders only the active state.

Two details worth naming:

- **`update()` is guarded on `__pending`, not on the popup.** `ctx.popup` is
  shared; reading a result this screen did not ask for would start a lecture off
  somebody else's question. Covered by a test.
- **The answer is re-checked before it is acted on.** Nothing in the engine can
  drain the term while a modal is up — the router runs one state and the popup
  eats every event — but an answer landing on a quest the rules no longer allow
  refuses rather than being honoured. One comparison, and it turns "cannot
  happen" into "cannot be made to happen". Also covered.

### The three appends

| File | Change |
|---|---|
| `engine/screen_manager.py` | `SIDE_QUESTS = auto()` — **appended**, per recon hazard #3 |
| `content/level_registry.py` | `"side_quests": {"name": "Side Quests", "state": "SIDE_QUESTS"}` — **appended**, per hazard #2 |
| `levels/player_room.json` | `prop_0023` and `prop_0024`: `menu_id` `"skill_tree"` → `"side_quests"` |

`tools/` needed no edit at all — the editor's menu dropdown reads `MENU_REGISTRY`
directly, so the new destination is already in it.

---

## The visibility rule

    Unlocked   shown, selectable
    Completed  shown, marked complete, not selectable
    Unoffered  HIDDEN entirely
    Declined   HIDDEN entirely
    Missed     HIDDEN entirely

**Nothing on the card counts the twelve.** No numbering, no "n of 12", no
placeholder slot, no greyed row standing in for something absent. The subtitle
shows the days left in the term instead of a total, deliberately — a count of
rows beside a count of quests would say out loud how many the player did not
take, which is Phase 16's ending to reveal and not this screen's.

The empty card reads `NOTHING SAVED ON THIS PC YET.` — worded as an absence of
study material, not an absence of quests.

The strongest form of the rule is a test rather than an argument:
**a run that declined all twelve, a run that missed all twelve, and a fresh run
produce byte-identical card contents.** So does a run that took semester 1 and
refused semester 2, against one that took semester 1 and was never asked.

---

## The day rule

`remaining >= day_cost` allows the confirmation; `remaining < day_cost` blocks
it. The block is total: the confirmation is never opened, nothing is deducted,
nothing is recorded, and there is no argument, flag or second call anywhere in
the module that says yes. The refusal names both figures —

> **NOT ENOUGH DAYS**
> This lecture needs 2 days.
> You have 1 day left in this term.

— because "not enough" without the two numbers is a wall rather than an answer.

An unaffordable quest is still a **visible row**. It is Unlocked, so it is shown;
only starting it is refused, and START draws muted while it is highlighted. That
is a fact about the player's own term, not evidence of a quest they never saw.

**This is not the 15-day firewall.** `GameClock.is_eligible_for_side_activities()`
is never consulted here, exactly as Phase 13's ruling 3 left it, so Phase 17 still
has one place to land. A term at 16 days and a term at 3 days differ only by the
`day_cost` comparison — asserted.

---

## Verification

```
py -3 -m tests.test_side_quest_list    46/46 passed, exit 0
py -3 -m tests.test_quest_offer        33/33 passed, unchanged by this phase
py -3 -m tests.test_quest_state        29/29 passed, unchanged by this phase
py -3 -m engine.side_quest_list        the module's own stub test, all checks passed
```

The `test_screen_*` cases drive a **real `AppContext`**, the real popups and real
`pygame.KEYDOWN` events through the real `engine/states/side_quests.py`, because
"blocked with a clear reason and no state change" is a claim about the screen,
not about a helper. Headless (`SDL_VIDEODRIVER=dummy`); nothing is written to
disk at all — this phase adds no save key, so there is not even a temp directory
to clean up.

| Requirement from the brief | Cases | Result |
|---|---|---|
| **an interactable PC in the Player's Room** | routes through `menu_prop`; both desk props carry the id; the room still validates | pass |
| **extend it, do not add a second one** | every interactable computer prop in the room is one of the two pre-existing uids | pass |
| **Unlocked → shown, selectable** | the mixed run; all twelve unlocked | pass |
| **Completed → shown, marked, not selectable** | marked in the last cell, refused with `ALREADY READ`, tinted | pass |
| **Unoffered / Declined / Missed → hidden** | exhaustive: all 5 states × all 12 quests, one at a time | pass |
| **no evidence of a declined or missed quest** | declined-all / missed-all / fresh produce identical cards; no cell or message names a hidden quest or its skill | pass |
| **no counter, no gap in numbering** | the subtitle counts days, not quests; nothing drawn contains a total | pass |
| **each row shows skill name, day cost, sheets** | read back against `side_quest_definitions` for all twelve | pass |
| **confirmation states the day cost** | all twelve, and it fits the popup's three-line maximum | pass |
| **…and warns about one sitting** | asserted in the body text | pass |
| **remaining >= cost allows confirm** | above the cost, and exactly at it | pass |
| **remaining < cost blocks** | one short, and zero | pass |
| **the block shows why** | title plus both figures, through the real popup | pass |
| **the block deducts nothing** | whole machine and day counter compared before/after | pass |
| **no override** | every listed quest at every day count below the cost | pass |
| **confirming logs the id and closes** | the id is recorded, no state moves, no day is spent, the map comes back | pass |
| edge: cancel | nothing logged, the player stays on the list | pass |
| edge: a stale confirmation | forced by draining the term under an open question — refused, not honoured | pass |
| edge: somebody else's popup | `update()` with nothing pending leaves the other screen's result unread | pass |
| edge: an empty list | opens, draws and refuses without hinting anything was ever there | pass |
| edge: no quest machine | the editor / harness context lists nothing and never raises | pass |
| regression | `quest_state`, `quest_offer`, `final_exam`, `day_drain`, `day_warning`, `menu_prop`, `side_quest_definitions`, `side_quest_lectures`, `level_registry` stub tests | pass |
| | 15-module import sweep including `main`, `play_sandbox`, `play_registration`, `tools.level_editor`, `save_bridge` | pass |
| | all 12 level files still load in strict mode | pass |

**Visual acceptance**, captured headless: the card with a mixed run (two topics
complete, three to read, seven invisible), the same card with the all-twelve
case to prove no column truncates, the empty card, the confirmation, and the
block with START muted behind it.

```
TOPIC              DAYS   SHEETS  STATUS    QUEST ID
Version Control    -      3       COMPLETE  SQ_GIT_GITHUB
OOP                2      3       -         SQ_OOP
Web App Dev        -      3       COMPLETE  SQ_WEB_APP_DEV
Linux CLI          2      3       -         SQ_LINUX_CLI
Tech Writing       2      3       -         SQ_TECH_COMMUNICATION

5 rows shown; 7 quests are invisible to this card and nothing on it says so
```

---

## Merge-conflict risk

**Phase 14 adds zero conflicts.** `git merge-tree --write-tree HEAD origin/main`
produces a clean tree with and without this phase's commit.

| File | Δ | Risk |
|---|---|---|
| `engine/side_quest_list.py` *(new)* | +341 | none — `main` has no such file |
| `ui/side_quest_screen.py` *(new)* | +448 | none — `main` has no such file |
| `engine/states/side_quests.py` *(new)* | +244 | none — `main` has no such file |
| `tests/test_side_quest_list.py` *(new)* | +782 | none — `main` has no `tests/` directory |
| `engine/screen_manager.py` | +4 | low — a pure append, per hazard #3 |
| `content/level_registry.py` | +4 | low — a pure append to `MENU_REGISTRY`, per hazard #2 |
| `levels/player_room.json` | +2 −2 | low — two changed strings, no re-serialisation |

Hazard #1 says level JSON is effectively unmergeable, so `player_room.json` was
edited **in place by hand** rather than round-tripped through `write_level()`:
the diff is the two `menu_id` strings and nothing else, which is a conflict git
can actually resolve if `main` touches the same map.

`engine/states/exploration.py` — hazard #4's busiest file — **was not opened.**
Neither was `engine/app_context.py`, `engine/save_bridge.py`,
`engine/save_manager.py`, `engine/state_router.py`, `engine/quest_state.py`, any
other `levels/*.json`, or anything under `tools/`, `academic/` or `core/`.

`levels/campus_main.json` was modified in the working tree before this session
and is not this phase's; it is left out of the commit, the same way Phases 8, 9
and 13 left it. The eight untracked `assets/props/*.png` are left alone for the
same reason.

---

## Out of scope — confirmed untouched

- **`engine/quest_state.py` is byte-identical.** Nothing here transitions a
  quest. The list reads `get_unlocked_quests()`, `get_completed_quests()` and
  `get_state()`, and writes nothing.
- **Lecture content.** No sheet is loaded, `content/side_quest_lectures.py` is
  read only for its sheet *count*, and `ScreenState.LECTURE` is never reached.
- **Day deduction.** `GameClock.process_time_consumable()` is not called on this
  path, and `days_left()` is a read. Confirming spends nothing.
- **Completion logic.** `mark_completed()` still has no caller.
- **The 15-day firewall.** Not consulted, by design — Phase 17's.
- **No new UI framework.** No new widget, no new card geometry system, no new
  modal. `RowTable`, `ConfirmPopup` and `MessagePopup` are the existing ones.
- **No save payload change and no `SAVE_SCHEMA_VERSION` bump.** The confirmed id
  is transient; the quest states were already in the file from Phase 12.

---

## Notes for the phases downstream

**Phase 15 (the reader).** `engine/side_quest_list.py::confirm()` is the seam.
It logs the id and returns it, and `engine/states/side_quests.py::update()` calls
it on the line where the reader should be opened — one call site, already guarded
by `is_startable()`. `get_lecture_sheets(quest_id)` is the reading order, and
`mark_completed()` is still uncalled, so the reader owns both the sheets and the
transition. Note that `mark_completed()` raises unless the quest is Unlocked,
which is the guard against recording a completion the player never earned.

**Phase 17 (the day lockout).** The cost check is `is_startable()`, and it is the
only day rule in this phase. If the 15-day firewall is to apply to starting a
lecture, `refusal()` is the single function to extend — every path into the
confirmation goes through it, including the re-check after the question is
answered. Deducting the days belongs next to the reader, not here: confirming
still spends nothing.

**Phase 16 (the ending gate).** Unaffected. `is_highly_skilled()` reads the
machine, and this phase does not write to it.

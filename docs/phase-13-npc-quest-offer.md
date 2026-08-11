# Phase 13 — Side Quests: NPC Dialogue Hook and the Offer

**Covers:** Prompt 2
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-09
**Commit:** `[Sprint 4] offer side quests through NPC dialogue`

**Input:** the Phase 0 recon (`docs/recon.md`), Phase 12's state machine
(`engine/quest_state.py`) and data file (`content/side_quest_definitions.py`), both
read first and used entirely through their public API. **The state machine was not
modified** — `git diff` on `engine/quest_state.py` is empty.

---

## Step 1 — the report, made before anything was written

### What already existed, and why this phase is mostly a re-pointing

Phase 9 built a live Accept / Decline offer inside `engine/dialogue_flow.py`, backed by
two sets on `AppContext`. Phase 12 built the five-state machine and left a note saying
Phase 13 must retire **both** of those sets in one change, because two stores for one
quest is two answers that can disagree.

| Piece | Where | Before this phase |
|---|---|---|
| The two-reply widget | `ui/choice_box.py` | live, shared with authored branches |
| The offer's own lines | `content/npc_quest_offers.py` | live, 12 terms × offer/accept/decline |
| Offer arming and answering | `engine/dialogue_flow.py:269-357` | live, on `ctx.unlocked_side_quests` + `ctx.decided_quest_semesters` |
| The five states | `engine/quest_state.py` | live, but nothing called `accept()` / `decline()` |
| The expiry hook | — | **not found** — `expire_unoffered_for_semester()` had no caller |

So the constraint "reuse the existing dialogue and choice-prompt systems, do not build a
parallel dialogue path" was satisfied by *not* writing a dialogue path at all. The
conversation, the reply list, the order things appear in and the two-stage SPACE contract
are Phase 9's and are untouched. What changed is what an answer *means*.

### The three edge cases, and what the codebase says about each

Reported before a line was written, and each is now a named test.

**A — the player talks to the semester's NPC on the exact day the semester rolls over.**
A term does not roll over on a day counter in this game: `engine/day_drain.py` records that
reaching zero days triggers nothing, `Semester.is_semester_complete()` is called by nobody,
and Phase 6 removed the one automatic reaction a low pool ever had. `close_semester()` is
the only rollover, reached from the exam screen, from `final_exam.check()` and from the
`end_semester` prop. A conversation is `ScreenState.DIALOGUE`, and the router runs exactly
one state — so a talk and a rollover **cannot interleave**, and the ordering is always
total.

**B — a conversation is interrupted or cancelled before the dialogue concludes.**
Arming an offer already wrote nothing; only the answer did. So this case was about keeping
that true, not about adding a check.

**C — the semester's assigned NPC is absent, unavailable, or unreachable that semester.**
`content/side_quest_definitions.py::validate()` runs at import and refuses to boot if a
quest's NPC is not around in its offer semester, so for the shipped twelve "absent" cannot
happen — and Phase 8's filter is what would have made it happen. "Unreachable" is the
ordinary case and always was: the player never walks to that map.

---

## Owner rulings

Reported first, then asked, then built. Three answers came back.

1. **Delete both Phase 9 sets now.** `ctx.unlocked_side_quests` and
   `ctx.decided_quest_semesters` are gone from `engine/app_context.py`, not mirrored and not
   shadowed. `engine/dialogue_flow.py` was their only reader, so the retirement is complete
   in one commit — Phase 12's handoff asked for exactly that.
2. **The expiry fires before the freeze check** in `close_semester()`. A run that ends on
   `ENDGAME` (140 credits, or the 960-day cap) still closes its books, so the final term's
   quest is Missed rather than left Unoffered forever where Phase 16's ending gate would
   read it.
3. **Decision D1: no day gating in this phase.** The offer is put whenever the machine says
   it can be, including on a term drained to zero days. The 15-day threshold and the quest's
   own `day_cost` are Phase 17's, and two places deciding whether a side quest may start is
   one too many.

---

## What was built

One new module, one new test module. Four existing files took a call site or a deletion
each, and nothing else was touched.

### `engine/quest_offer.py` *(new, 368 lines)*

```
PROMPT / REPLIES / ACCEPT_INDEX     the two fixed replies and which one is yes
SEMESTER_NONE                       no semester in hand — offer nothing

machine_of(ctx)                     ctx.quest_states, or None
semester_of(ctx)                    the current semester, or SEMESTER_NONE
lines_for(quest_id)                 the authored offer/accept/decline lines, or None
offered_quest_id(ctx, npc_data)     the quest this NPC owes right now, or None
is_still_offerable(ctx, quest_id)   the guard resolve() runs before it writes
resolve(ctx, quest_id, accepted)    the ONE place the machine is touched
expire_semester(ctx, semester=None) the term ended: Missed if never put
```

**Why a new module.** Recon hazard #4, and the precedent `engine/menu_prop.py`,
`engine/day_warning.py`, `engine/final_exam.py`, `engine/npc_availability.py` and
`engine/day_drain.py` all set: a new file cannot produce a merge conflict, and the
alternative was quest knowledge spread across `dialogue_flow.py` **and** the semester
rollover inside `engine/states/exam.py`. That file carries a one-line call instead.

It also keeps the seam honest. `dialogue_flow` knows how to run a conversation and nothing
about the five states; `quest_offer` knows the five states and nothing about pygame, screens
or the choice box. Neither imports the other's concerns.

**`npc_id` needs no translation.** `offered_quest_id()` takes the `NpcData` the interaction
is already holding and passes `get_type_id()` straight into `can_offer()` — the short
`NPC_REGISTRY` id is exactly what Phase 12's ruling 3 chose for that reason. The roster slug
never appears on this path.

**Everything is tolerant, and nothing is silent about being wrong.** A context with no quest
machine, no semester, or an NPC object that cannot answer `get_type_id()` all produce "no
offer" rather than an exception — the offer path runs inside an interaction and the expiry
path inside a semester rollover, and neither is a place where a conversation should take the
game down. `QuestStateError` is caught in `resolve()` even though the guard above it makes
it unreachable.

### `engine/dialogue_flow.py` — the offer section re-pointed *(+48 −38)*

The five offer functions keep their names, their order and their place in
`engine/states/dialogue.py`'s event loop. What changed inside them:

| Function | Before | After |
|---|---|---|
| `pending_offer` | `SEMESTER_QUEST_OFFERS[ctx.pending_quest_npc]` | `quest_offer.lines_for(ctx.pending_quest_id)` |
| `arm_offer` | roster-slug compare + `decided_quest_semesters` | `quest_offer.offered_quest_id()` |
| `open_offer` | unchanged | unchanged |
| `is_offer_open` | unchanged | unchanged |
| `resolve_offer` | wrote to two sets | `quest_offer.resolve()`, re-validated |
| `end_talk` | cleared `pending_quest_npc` | clears `pending_quest_id` |

`OFFER_PROMPT`, `OFFER_REPLIES` and `OFFER_ACCEPT` are now aliases of the constants in
`quest_offer`, so the two modules cannot drift on which index means yes.

**`resolve_offer()` re-asks before it writes.** The offer is armed at the start of a talk
against the semester in hand at that moment, and answered some seconds later.
`quest_offer.resolve()` re-derives the quest from the context and refuses unless it is still
this term's and still Unoffered. Nothing in the engine can make that check fail — see edge
case A — but it costs one comparison and turns "cannot happen" into "cannot be made to
happen". A refusal ends the conversation with the quest exactly where it was, rather than
putting an accept line on screen that nothing behind it agrees with.

### `engine/app_context.py` — the retirement *(+11 −11)*

```diff
-        self.unlocked_side_quests = set()
-        self.decided_quest_semesters = set()
         self.quest_states = QuestStateMachine()
-        self.pending_quest_npc = None
+        self.pending_quest_id = None
```

`pending_quest_npc` held a semester number despite its name; `pending_quest_id` holds the
quest id and says so. It is transient by design — an unanswered offer is not a decision, so
it is never saved.

### `engine/states/exam.py` — the one call *(+14 −3)*

```python
def close_semester(ctx):
    """Every course attempted: close the term and route onward."""
    quest_offer.expire_semester(ctx)          # <- the whole of it
    ctx.game_clock.check_semester_end_state()
```

The first statement, above the freeze check, per ruling 2. The ending semester is read off
`ctx` inside `expire_semester()`, which is correct here because `advance_semester()` has not
run yet at this point. Recon §7 and §8 both record `close_semester()` as the single place a
term rolls over and note there was no side-quest hook in that path; this is it.

### `engine/save_bridge.py` — two lines in a block that already did this *(+6)*

`restore()` already dropped `dialogue_npc`, `dialogue_chain` and the choice fields as
transient screen state. `quest_offer_open` and `pending_quest_id` join them, so a save loaded
while the question was on screen comes back with the quest Unoffered and the offer put again
next time — edge case B for the save/load path, as a property rather than an argument.

### `tests/test_quest_offer.py` *(new, 802 lines, 33 cases)*

`py -3 -m tests.test_quest_offer`, exit 0 or 1, the convention `tests/__init__.py` sets.

**Most of it drives the real thing.** A real `AppContext`, the real level files, the real
`DialogueManager`, and real `pygame.KEYDOWN` events pushed through the real
`engine/states/dialogue.py` event loop. Nothing about the conversation is mocked, because the
behaviour under test is precisely that the offer appears in the middle of the real dialogue
path and nowhere else. Headless (`SDL_VIDEODRIVER=dummy`); the only thing written is a
`tempfile.mkdtemp()` directory, so `saves/` is never touched.

`run_to_offer()` asserts on **every** press that the offer has not opened while the chain
still has lines to give — "after the normal dialogue concludes" is half the requirement, so
it is checked continuously rather than only at the end.

---

## The edge cases — how each was handled

### A · The exact day the semester rolls over

**Handled by ordering that cannot be violated, plus a guard that makes it structural.**

A conversation is `ScreenState.DIALOGUE`; a rollover happens on the exam screen or at the
`end_semester` prop. The router runs one state, so only two orders exist and both are
already right:

- **Answer, then close.** The quest is Unlocked or Declined, so
  `expire_unoffered_for_semester()` finds it not-Unoffered and leaves it exactly where the
  player put it. Phase 12 documented that method as the one that is allowed to do nothing,
  and this is the case it was written for.
  *→ `test_edge_a_answer_then_rollover_keeps_the_answer`*
- **Close, then talk.** The quest is Missed, so `can_offer()` is False, and the semester has
  moved on to a quest belonging to a different NPC. The NPC plays unchanged dialogue.
  *→ `test_edge_a_rollover_then_talk_offers_nothing`*

On top of that, `resolve()` re-derives the quest from the context instead of trusting what
was armed, so an answer can only ever land on the term the game is actually in. The test
forces the situation by hand — restoring a semester-2 context under an open semester-1
offer — and asserts nothing moves.
*→ `test_edge_a_a_stale_offer_is_refused_rather_than_written`*

**On the "day" reading specifically:** a term drained to zero days still puts the offer, per
ruling 3. Accepting on the last day is legal; what it costs is Phase 17's.
*→ `test_edge_a_zero_days_left_still_offers`*

### B · A conversation interrupted or cancelled before the dialogue concludes

**Handled by where the write is, not by a check.** `arm_offer()` sets one transient field
and touches nothing else; the machine is written in exactly one place, `resolve()`, which
runs only after the player has picked a reply. Every way out before that leaves the quest
Unoffered and the offer is put again next time.

| Interruption | What happens |
|---|---|
| ESC on the first line | `end_talk()` clears the arm; quest Unoffered *→ `test_edge_b_escape_before_the_offer_...`* |
| ESC on the **last** line, one press from the question | same *→ `test_edge_b_escape_on_the_last_line_...`* |
| Three walk-aways in a row, then a real answer | the question comes back each time and the fourth talk answers it *→ `test_edge_b_an_interrupted_talk_is_offered_again`* |
| Loading a save with the question on screen | `restore()` drops both offer fields; quest Unoffered, offered again *→ `test_edge_b_a_load_mid_offer_...`* |

**One asymmetry, on the record.** Once the Accept / Decline prompt is actually on screen,
ESC cannot skip it — `engine/states/dialogue.py::__handle_choice_event` swallows every event
while a choice is open. That is Phase 9's deliberate rule for authored branches ("a branch is
a question the player was asked"), and the offer inherits it rather than carving out an
exception. The only way past the question is to answer it.
*→ `test_edge_b_the_open_offer_cannot_be_escaped` — five ESC presses, still open*

### C · The assigned NPC is absent, unavailable, or unreachable

**All three land on the same path, and that path is `Missed`.**

- **Absent / unavailable cannot happen for the shipped twelve.**
  `side_quest_definitions.validate()` runs at import and refuses to boot if a quest's NPC is
  not around in its offer semester. Re-checked here against the *placements* as well, which
  `validate()` does not read: every offering NPC is on the map, with
  `get_effective_min_semester() <= semester`, in all twelve terms.
  *→ `test_edge_c_no_offer_is_stranded_behind_the_semester_gate`*
- **The one way it could become real** is an editor `gate` raising a placement's
  `min_semester` above the roster's — `validate()` checks the roster figure, not per-placement
  gates. Nothing in the repo does it today, so the test builds it: Purnno gated to semester 9,
  confirmed hidden by `npc_availability` in semester 1, and the term ends with
  `SQ_GIT_GITHUB` Missed. No crash, no fallback offer from another NPC, no stuck quest.
  *→ `test_edge_c_an_npc_gated_out_of_their_own_term_is_never_asked`*
- **Unreachable is the ordinary case** — the player never walks to that map, never presses E,
  or skips the term. Nothing special happens: the quest was never offered, so the term's
  close marks it Missed and it is gone for good. This is what
  `expire_unoffered_for_semester()` exists for.
  *→ `test_edge_c_an_unreachable_npc_ends_the_term_missed`*
- **Phase 8's filter, from this side:** Hoque is genuinely not in `lecture_hall` at semester
  4 and is at semester 5, so in a term he is hidden there is nobody to press E on.
  *→ `test_edge_c_a_hidden_npc_is_not_on_the_map_at_all`*
- A context with no quest machine at all — the editor, the harnesses, a half-built
  `AppContext` — answers "no offer" and never raises.
  *→ `test_edge_c_a_context_with_no_quest_machine_never_raises`*

---

## Verification

`py -3 -m tests.test_quest_offer` — **33/33 passed**, exit 0.
`py -3 -m tests.test_quest_state` — **29/29 passed**, unchanged by this phase.
`py -3 -m engine.quest_offer` — the module's own stub test, all checks passed.

Every case below runs against a real `AppContext` and the real level files unless marked.

| Requirement from the brief | Cases | Result |
|---|---|---|
| **the offer appears after the dialogue concludes** | all twelve semesters, real chain played to its end, prompt / labels / first offer line asserted | pass |
| **it reuses the existing choice prompt** | the same `ui/choice_box.py`, the same `ctx.choice_options` hook, flagged as the offer not a branch | pass |
| **Accept → `Accept(quest_id)`** | all twelve, state read back through `get_state()` / `get_unlocked_quests()` | pass |
| **Accept starts nothing else** | no completion, no days spent, no skill level, no credits | pass |
| **Decline → `Decline(quest_id)`** | all twelve | pass |
| **the conversation ends either way** | the matching authored reply lines play, then the talk closes and every per-conversation ref is dropped | pass |
| **re-interacting produces no second offer** | after accepting **and** after declining, all twelve; the second conversation's first line is asserted identical to a fresh player's | pass |
| **"never again under any circumstance"** | ten further conversations from each terminal state | pass |
| **only the assigned NPC offers anything** | every other placed NPC, every semester — nothing armed, nothing offered, machine byte-identical to a fresh one afterwards | pass |
| **only the right semester** | the five NPCs who offer twice, asked in every term that is not theirs | pass |
| edge A | 4 cases, above | pass |
| edge B | 5 cases, above | pass |
| edge C | 5 cases, above | pass |
| **`ExpireUnofferedForSemester` on the term that just ended** | through the real `exam.close_semester()`; the term rolls and only its own quest is Missed | pass |
| | an accepted, declined **or completed** quest keeps its answer | pass |
| | the expiry runs above the freeze check — a frozen semester-12 run still marks its quest Missed | pass |
| | twelve terms in a row with nobody talked to: twelve Missed, in order, never one ahead of itself | pass |
| persistence | all twelve answered and round-tripped through a **real save file on disk**, then confirmed still not offered after loading | pass |
| | `SAVE_SCHEMA_VERSION` still 1; the transient offer is not in the payload | pass |
| retirement | both Phase 9 sets absent from a live `AppContext`; a repo-wide grep finds no remaining attribute access or `getattr` string in `engine/`, `content/`, `ui/`, `academic/`, `core/`, `tools/` | pass |
| regression | `engine.quest_state`, `engine.final_exam`, `engine.npc_availability`, `engine.day_drain`, `engine.day_warning`, `engine.return_points`, `engine.menu_prop`, `content.side_quest_definitions`, `content.side_quest_lectures` stub tests | pass |
| | 16-module import sweep including `main`, `play_sandbox`, `play_registration`, `tools.level_editor`, `save_bridge` | pass |

**Visual acceptance**, captured headless: Purnno's semester-1 card shows his first offer
line, with `YOUR DECISION` and the Accept / Decline rows docked above it in the existing
dialog panel. (His portrait draws as the placeholder box — one of the eight missing PNGs
Phase 9 reported, not a regression from this phase.)

**The acceptance run**, twelve semesters through the real dialogue path — accepted, declined
and ignored in rotation:

```
SEM  NPC      QUEST ID                 STATE
1    purnno   SQ_GIT_GITHUB            unlocked
2    rahman   SQ_OOP                   declined
3    rafi     SQ_DSA                   missed  (ignored)
4    roya     SQ_WEB_APP_DEV           unlocked
5    hoque    SQ_AI_TOOLS              declined
6    zayan    SQ_LINUX_CLI             missed  (ignored)
...
12   kabir    SQ_PROGRAMMING_LANGUAGE  missed  (ignored)
```

---

## Merge-conflict risk

**Phase 13 adds zero conflicts.** `git merge-tree --write-tree HEAD origin/main` produces a
clean tree with and without this phase's commit.

| File | Δ | Risk |
|---|---|---|
| `engine/quest_offer.py` *(new)* | +368 | none — `main` has no such file |
| `tests/test_quest_offer.py` *(new)* | +802 | none — `main` has no `tests/` directory |
| `engine/dialogue_flow.py` | +48 −38 | none — the file itself does not exist on `main` |
| `engine/app_context.py` | +11 −11 | low — inside the STAGE 4 block Phase 12 already edited |
| `engine/states/exam.py` | +14 −3 | low — one import and one first statement |
| `engine/save_bridge.py` | +6 | low — two appends inside an existing reset block |

`engine/states/exploration.py` — hazard #4's busiest file — **was not opened**. Neither was
any `levels/*.json` (hazard #1), `content/level_registry.py` (hazard #2),
`engine/screen_manager.py` (hazard #3), or any file under `ui/`, `content/`, `academic/`,
`core/` or `tools/`.

`levels/campus_main.json` was modified in the working tree before this session and is not
this phase's; it is left out of the commit, the same way Phases 8 and 9 left it.

---

## Out of scope — confirmed untouched

- **`engine/quest_state.py` is byte-identical.** The brief says do not modify the state
  machine, and `git diff` on it is empty. Everything goes through `can_offer`, `accept`,
  `decline`, `get_state` and `expire_unoffered_for_semester`.
- **The PC, the quest list, lectures and day costs.** No `MENU_REGISTRY` row, no
  `ScreenState` member, no new screen, no prop placed. Accepting a quest unlocks it and does
  nothing else — no lecture is loaded and `GameClock.process_time_consumable()` is never
  called on this path.
- **No parallel dialogue path.** No new dialogue class, no second reply widget, no separate
  offer screen. `content/dialogues.py::NPC_DIALOGUES` and its unused `"offer"` section stay
  unreached, as Phase 9 ruled.
- **No save payload change and no `SAVE_SCHEMA_VERSION` bump.** The offer is transient; the
  quest states were already in the file from Phase 12.
- **The quest-intro popup stays dead.** `ctx.quest_intro_popup` and
  `ctx.seen_quest_intro_semesters` are still built and still opened by nothing — Phase 9
  flagged them and they are not this phase's.

---

## Notes for the phases downstream

**Phase 14 (the PC).** `ctx.quest_states.get_unlocked_quests()` is the list a PC would read;
it replaces the retired `ctx.unlocked_side_quests` exactly. `get_completed_quests()` is
beside it.

**Phase 15 (the reader).** Nothing here loads a lecture, and `mark_completed()` still has no
caller — it raises unless the quest is Unlocked, which is the guard against recording a
completion for a quest the player never accepted.

**Phase 16 (the ending gate).** `is_highly_skilled()` now has a full run behind it: every
term either answers its quest or expires it, so no quest can still be Unoffered at the end
of a playthrough. The expiry sits above the freeze check specifically so the frozen ending
sees a closed book.

**Phase 17 (the day lockout).** `engine/quest_offer.py` consults no day counter by ruling 3,
so the threshold has exactly one place to land. If the *offer* is to be suppressed rather
than the *starting*, `offered_quest_id()` is the single function to gate — every path into
the offer goes through it.

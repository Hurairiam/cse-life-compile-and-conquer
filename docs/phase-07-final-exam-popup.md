# Phase 7 — Final Exam Completion Popup and Free Roam

**Covers:** Change 12
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-08
**Commit:** `[Sprint 4] Add final exam completion popup and free roam`

---

## What the recon found

### The end of a term was unwalkable

The brief asked me to report the current post-final-exam flow before writing anything,
and to ask if the game forced a transition there. It does. Traced in code, not taken
from the recon:

1. The last course grades out (`engine/states/exam.py:103`) → `EXAM_RESULT`, the
   PASS/FAIL card.
2. Any key or click (`engine/states/exam_result.py:46`) pushes `course_index` past the
   end and goes back to `EXAM`.
3. `__current_course()` is now `None`, so `render()` fills the screen tan and draws one
   centred line: `ALL EXAMS ATTEMPTED — PRESS SPACE TO CONTINUE`. `update()` returns
   immediately. The HUD strip still draws — `EXAM` is not in `HUD_HIDDEN` — and nothing
   else does.
4. **Input there was two keys.** `ESC` → `ctx.quit()`, which sets `running = False` and
   exits the whole game. `SPACE` → `close_semester()`. **There was no route back to
   `EXPLORATION` at all.**
5. `close_semester()` backlogs incompletes, freezes on 140 credits or the 960-day cap,
   then `advance_semester()` and `MONOLOGUE` → `REGISTRATION` → (`CUTSCENE`) →
   `EXPLORATION`, forced to `player_room`.

So the player never got to stand on the campus with the finals behind them. Free roam
only ever resumed in the *next* term, in the bedroom, three screens later. Movement was
not "locked" so much as absent — there was no walker, because there was no map.

That is the transition the brief said to report, and it is the one thing in the way of
the acceptance criterion: *dismissing the popup leaves the player free to move and
explore* cannot be true while dismissing it lands on a screen whose only key rolls the
semester over.

### The 15-day firewall was already out of the way

Phase 6 removed the bounce that yanked the player into `EXAM` at 15 days, and its log
notes that this leaves the exam enterable only by choice — the activity card's
**START EXAM** and the `X` key. That is exactly the state this phase's free roam needs:
if the firewall still dragged the player back to the exam every frame, handing them the
map after the finals would have lasted one frame.

---

## Owner rulings

Reported first, then asked, then built. Four answers came back.

1. **Dismissing the popup returns the player to `EXPLORATION` on the map they left** —
   free to walk and to take side quests for the rest of the term.
2. **Only when days remain.** If the finals end with no days left in the pool, the new
   semester begins, as it always did.
3. **The term is ended by a prop.** A player who wants to move on while they still have
   days does it by interacting with an object — *"a prop of my choosing"* — so this
   phase adds **a new interactable function to the level editor** and places nothing.
4. **The copy**, drafted and approved before it was written down:

   ```
   EXAMS DONE
     Congratulations on completing the
     final exams for this semester!
     Go breathe — the campus is yours.
   ```

   and, because ruling 2 sends the player somewhere else entirely, one alternate
   closing line for that branch: `The term is over — next one begins.` The first two
   lines never change — the finals are over either way.

5. **The term that ran dry is left exactly as it is.** An exam costs 10–14 days and the
   warning fires at 15, so a semester often runs out partway through the exams and the
   remaining courses are never sat. Congratulating somebody who never sat two of their
   exams would be a lie, and that path is exam logic, which the brief puts out of scope.

---

## What was built

### `engine/final_exam.py` — the rule (new file)

```
days_left(ctx)         days in the active semester's pool
registered_count(ctx)  how many courses this term put up
is_finished(ctx)       every registered course attempted     <- end_semester.py reads this
may_roam(ctx)          the days-left-above-zero test
check(ctx)             fires the popup once per semester     <- exam.py calls this
forget()               re-arm, for tests
```

A new module for the reason `engine/menu_prop.py` and `engine/day_warning.py` are: it
cannot produce a merge conflict, and the alternative was another branch inside a shared
state module. `engine/states/exam.py` carries a one-line call.

**The rollover is not touched.** `close_semester()` still does precisely what it did —
backlog, freeze check, `advance_semester()`, the monologue. This module moves *when* it
is called and never *what* it does, and in the no-days branch it does not even move
that. The brief puts semester rollover rules out of scope and they stayed there.

**`is_finished()` is the same condition `exam.py` already expresses** as
`__current_course(ctx) is None` — its `course_index` has run past the registered list —
written down once here so `end_semester.py` and any later phase can ask it without
reaching for a private helper. It refuses a term with nothing registered: a player who
walks into the exam having registered for no courses has not completed any finals.

**State is one module-level int**, the semester the popup has been shown for, exactly as
`engine/day_warning.py` keeps its own. Off `ctx` because `app_context.py` is a shared,
already-divergent file and this is one bookkeeping integer; out of the save file because
the payload then gains no key, `SAVE_SCHEMA_VERSION` stays at 1 and every existing save
still loads. Keying it to the semester **number** means a rollover or a new game re-arms
it with nobody calling a reset.

**The dry term consumes its slot and opens nothing.** Without that, clearing
`ctx.exam["message"]` would let the popup appear a frame later — the one way ruling 5
could have leaked.

**Why the popup lands on the map rather than the map landing after the popup.** The
message popup is a router-level overlay drawn above whatever state is active, and
`exploration.__blocked()` freezes the walker while one is open. So opening it and going
to `EXPLORATION` in the same frame gives the acceptance criterion literally: the popup
is over the campus, and dismissing it is the thing that frees the player to move.

### `engine/states/end_semester.py` — the way out (new file)

The door ruling 3 asked for. Reached through the ordinary menu-prop path, so which
object it hangs on is an authoring decision.

- **It refuses until the exams are done** (`final_exam.is_finished`). A prop that could
  end a term mid-semester would skip every unsat exam and `close_semester()` would
  dutifully backlog all of them — a way to throw a whole semester away by walking into a
  rug. This was the one place a new door could have changed the rollover rules, and it
  is shut. The refusal opens one popup and hands control straight back, the way
  `engine/states/teleport.py` handles its semester lock.
- **It asks before it acts.** The remaining days do not carry over —
  `player.advance_semester()` resets the pool to 80 — so this is destructive in exactly
  the way `OVERWRITE SLOT n?` is, and it takes the same `ConfirmPopup`, with the button
  named `END TERM` and the body naming the days being thrown away.
- **It draws the map underneath**, like `activity.py` and `teleport.py`, because the
  router renders only the active state and a popup on a stale frame is a bug.
- **CONFIRM calls `close_semester()`** and nothing else. There is no second copy of the
  rollover anywhere.

### The editor seam — two appended lines, and no `tools/` edit

```python
# engine/screen_manager.py     appended, never inserted (hazard #3)
END_SEMESTER = auto()

# content/level_registry.py    appended to MENU_REGISTRY (hazard #2)
"end_semester": {"name": "End Semester", "state": "END_SEMESTER"},
```

That is the whole cost. `tools/editor_popups.py` builds its **OPENS MENU** picker from
`get_menu_ids()` with `get_menu_display_name()` labels, so **End Semester** appears in
the prop settings popup on its own; `content/level_schema.py::set_menu_id()` already
validates against `MENU_REGISTRY`, so the new id is accepted, round-trips through JSON
and passes `validate_level` with no schema change. The recon's "three edits and no
editor change" seam did the whole job.

**Both files are shared choke points and both edits are pure appends** — `auto()`
renumbers everything after an inserted member, and `MENU_REGISTRY` is named in the
recon as a place a reorder conflicts and an append does not.

**Nothing was placed.** The prop is the owner's to choose, so no `levels/*.json` was
touched — which is also the file class the recon calls effectively unmergeable.

### `engine/states/exam.py` — one call and one line of text

```python
     if __current_course(ctx) is None:
+        final_exam.check(ctx)
         return                                  # waiting on SPACE, see render
```

and the prompt on that screen:

```
- ALL EXAMS ATTEMPTED — PRESS SPACE TO CONTINUE
+ ALL EXAMS ATTEMPTED — PRESS SPACE TO END THE SEMESTER
```

SPACE used to be the only way off that screen, so what it continued *to* was obvious.
Now the player is handed back to the campus when the exams end and only returns here on
purpose, so the key has to say what it costs them. **That route still works** — it is
the second way to close a term, and it matters, because no level in the repo carries an
`end_semester` prop until the owner places one.

`close_semester()` itself is byte-for-byte unchanged.

---

## Files changed

| File | Δ | Why |
|---|---|---|
| `engine/final_exam.py` *(new)* | +268 | the rule, the popup, the roam/rollover decision |
| `engine/states/end_semester.py` *(new)* | +117 | the prop that ends a term early |
| `engine/states/exam.py` | +21 −3 | one call, the reworded prompt, a docstring note |
| `engine/screen_manager.py` | +6 | `END_SEMESTER`, appended |
| `content/level_registry.py` | +6 | the `end_semester` menu row, appended |

`engine/game_clock.py`, `engine/state_router.py`, `engine/states/exploration.py`,
`engine/states/exam_result.py`, `ui/`, `tools/` and every `levels/*.json` were **not**
touched. Two of the five files here are new, which is where the bulk of the work is by
design.

---

## Merge-conflict risk

**Phase 7 adds zero conflicts.** `git merge-tree --write-tree` against `origin/main`
produces the same clean result with and without this phase's commit — no conflict
markers either way.

Three of the five files are ones the recon lists as safest to extend
(`engine/screen_manager.py` append-only, `engine/states/exam.py`, and the two new
modules); `content/level_registry.py` is the one already-divergent file, and it took a
pure append for exactly the reason hazard #2 gives.

The two hazards this phase could have hit, and did not:

- **Hazard #3, `ScreenState` renumbering.** `END_SEMESTER` is appended. All nineteen
  pre-existing members hold their original `auto()` values — asserted in the harness.
- **Hazard #1, level JSON.** Nothing was placed, so no map was rewritten.

---

## Verification

Headless, `SDL_VIDEODRIVER=dummy`. **95 end-to-end checks plus 21 unit assertions in the
module's own stub test — 116 total, all passing.**

### Unit — `py -m engine.final_exam`

| Case | Result |
|---|---|
| Silent before the last exam is sat | pass |
| Silent for a term with nothing registered | pass |
| Exams over with days left → popup, campus line, `EXPLORATION`, no rollover | pass |
| Never congratulates twice in one semester | pass |
| Exams over with no days → popup, term line, `close_semester()`, no `go()` | pass |
| A term that ran dry is never congratulated, and not a frame later either | pass |
| The next semester re-arms | pass |
| An overspent pool still counts as no days | pass |

### End to end — a real `AppContext` driven through the real loop order

| Group | Case | Result |
|---|---|---|
| Editor seam | `end_semester` is in `MENU_REGISTRY`, and is the **last** row | pass |
| | the editor's dropdown offers it, with a human label | pass |
| | `menu_prop` routes it to `ScreenState.END_SEMESTER` | pass |
| | every pre-existing menu still routes | pass |
| | **no `ScreenState` member was renumbered** | pass |
| | `END_SEMESTER` keeps the HUD — it draws the map | pass |
| Authoring | a prop takes the new menu id and survives a JSON round-trip | pass |
| | a bogus menu id is still refused | pass |
| | all 12 levels still load and validate | pass |
| Copy | every line fits the 600 px card; body is exactly 3 lines | pass |
| **Days left** | **the popup opens with the approved copy and the campus line** | pass |
| | **it routes to `EXPLORATION`, not the rollover** | pass |
| | the semester did not roll over and the days were not refilled | pass |
| | movement is blocked while it is up | pass |
| | **dismissing it unblocks the walker, and the player actually walks** | pass |
| | a second visit to the exam does not re-congratulate | pass |
| | SPACE there still ends the term and reaches the monologue | pass |
| **No days left** | the popup opens with the *term is over* line | pass |
| | the semester rolled over and the pool refilled | pass |
| | the popup is still readable over the monologue, and dismisses cleanly | pass |
| **Ran dry** | no congratulations, no free roam, the notice still drawn | pass |
| | SPACE closes the term exactly as it did before | pass |
| **The prop** | refuses before the exams are done, and asks nothing | pass |
| | asks once they are, naming the days and the `END TERM` button | pass |
| | CANCEL returns to the map with the term untouched | pass |
| | CONFIRM rolls it over, refills the pool, reaches the monologue | pass |
| | a fresh term re-locks it | pass |
| | `1 day left` is singular | pass |
| Phase 6 | the day warning still fires, and its HUD chip still turns on | pass |
| | the exams-done popup fires under it and still hands back the map | pass |
| Regression | `main`, `save_bridge`, `state_router`, `exam`, `exam_result`, `exploration`, `activity`, `teleport`, `end_semester`, `final_exam`, `day_warning`, `menu_prop`, both level modules, `map_directory`, both editor modules and `play_sandbox` all import | pass |

**Manual acceptance** (the brief's own test): sit the last exam of a semester with days
still in the pool — the `EXAMS DONE` popup opens over the campus, and dismissing it
leaves the player standing on the map, free to walk anywhere. The term ends when they
decide it does.

---

## What this phase deliberately did not do

- **Placed the `end_semester` prop.** Which object carries it is the owner's choice
  (ruling 3). Until one is placed, the term is still closed from the exam screen with
  SPACE, which is why that route was kept and its label rewritten rather than removed.
- **Touched the exam logic or the rollover rules** — both out of scope, and the dry-term
  path is untouched by ruling 5.
- **Blocked side quests below the day threshold** — Phase 17, which reads
  `day_warning.is_low(ctx)`.
- **Anything in `ui/` or `tools/`.** The popup is `ui/popup.py` used as-is, and the
  editor picked the new interaction up from `MENU_REGISTRY` on its own.

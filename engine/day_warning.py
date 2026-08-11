"""
engine/day_warning.py
The end-of-semester day warning: one popup, then a HUD counter.

WHY THIS IS ITS OWN FILE
────────────────────────
The same reason engine/menu_prop.py is: a new module cannot produce a
merge conflict, and the alternative was another branch inside
engine/states/exploration.py, which the recon names the busiest shared
file in the repository. That file carries a one-line call instead.

THE THRESHOLD IS NOT DEFINED HERE
─────────────────────────────────
It is `GameClock.__MIN_MAIN_QUEST_TIME_BORDER` — 15 days, the
"15-Day Borderline Firewall" the clock has owned since Sprint 2 — read
back through its own `get_min_border()`. Declaring a second 15 in here
would be two numbers claiming to be one rule, and the brief asks for
one named constant in one place. Phases 11 and 17 read `threshold(ctx)`
rather than the clock, so the day rule has a single front door even
though the number lives with the system that spends days.

WHAT CHANGED IN THE CLOCK'S BEHAVIOUR (owner ruling, Phase 6)
─────────────────────────────────────────────────────────────
`exploration.update()` used to bounce the player into ScreenState.EXAM
the frame `is_eligible_for_side_activities()` went False — a hard yank
out of the world at 15 days. That is gone. The player now keeps the run
of the campus below the threshold; exploring costs nothing, so there is
nothing to protect them from. What the threshold now costs them is
*new side quests*, which is Phase 17's job, and this module is where
that phase asks the question (`is_low`).

The clock itself is untouched: `is_eligible_for_side_activities()` still
answers exactly what it always did, and is still the one place the rule
is expressed.

STATE
─────
One module-level int — the semester the popup has already been shown
for. It is deliberately NOT on ctx and NOT in the save file:

  * app_context.py is a shared, already-divergent file, and this is one
    bookkeeping int (engine/states/save_game.py keeps its row highlight
    the same way);
  * the save payload gains no key, so SAVE_SCHEMA_VERSION stays at 1
    and every existing save still loads.

The HUD half needs no memory at all — it is derived from the day count
every frame, so it appears the moment days drop, survives a save/load
for free, and clears itself when advance_semester() refills the pool.
Only the once-per-semester popup needs remembering, and keying it to
the semester NUMBER means a new game or a rollover re-arms it without
anybody having to call a reset.
"""
from __future__ import annotations

from ui.popup import SEVERITY_WARNING

# The semester whose warning has already been shown, or None. See STATE.
__warned_semester = None


# ── the rule ───────────────────────────────────────────────────

def threshold(ctx) -> int:
    """
    Days remaining at or below which the semester counts as running out.

    The single read point for Phases 11 and 17. Sourced from the clock
    so there is still only one 15 in the codebase.
    """
    return ctx.game_clock.get_min_border()


def remaining(ctx) -> int:
    """Days left in the active semester's own pool."""
    return ctx.semester().get_time_pool_days()


def is_low(ctx) -> bool:
    """
    True once the semester has run down to the threshold.

    The complement of GameClock.is_eligible_for_side_activities(), and
    phrased positively because that is how the phases that read it think
    about it: "days are low, so do not offer this".
    """
    return remaining(ctx) <= threshold(ctx)


def hud_days(ctx):
    """
    The number the HUD's warning chip shows, or None to draw nothing.

    None rather than 0 — a semester can legitimately run down to zero
    days, and that is exactly when the chip matters most.
    """
    return remaining(ctx) if is_low(ctx) else None


# ── the popup ──────────────────────────────────────────────────

def check(ctx) -> None:
    """
    Fire the warning the first time this semester crosses the threshold.

    Called every frame from exploration.update(). Cheap: two getters and
    an int compare, and it is the only place the popup can come from.

    ONCE PER SEMESTER, NOT ONCE PER DAY. There is no daily tick in this
    game to hang a per-day check on — days leave the pool in blocks
    (10 or 14 for an exam, 5 for a side quest, whatever a gate toll
    costs), all of them through GameClock.process_time_consumable(), so
    "the first time it is at or below the threshold" is the only reading
    the time system supports.
    """
    global __warned_semester
    number = ctx.semester().get_semester_number()
    if __warned_semester == number:
        return
    if not is_low(ctx):
        return
    __warned_semester = number
    days = remaining(ctx)
    ctx.play_sfx("error")
    ctx.message_popup.open("WARNING", [
        "You only have %d day%s left!" % (days, "" if days == 1 else "s"),
        "Utilize them wisely and",
        "prepare for the exams!",
    ], SEVERITY_WARNING)


def forget(ctx=None) -> None:
    """
    Re-arm the popup. Nothing in the game needs this — the semester
    number does the re-arming on its own — but the stub test below and
    any later test that runs two semesters in one process does.
    """
    global __warned_semester
    __warned_semester = None


# -------------------------------------------------------------
# STUB TEST — the repo's convention for a module with no suite.
# Runs headless: no window, no assets, just the rule.
#     py -m engine.day_warning
# (as a module, so the project root stays on the import path)
# -------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    class _Semester:
        def __init__(self, number, days):
            self.number, self.days = number, days

        def get_time_pool_days(self):
            return self.days

        def get_semester_number(self):
            return self.number

    class _Clock:
        @staticmethod
        def get_min_border():
            return 15

    class _Popup:
        def __init__(self):
            self.opened = []

        def open(self, title, lines, accent):
            self.opened.append((title, list(lines)))

    class _Ctx:
        def __init__(self, number, days):
            self.__sem = _Semester(number, days)
            self.game_clock = _Clock()
            self.message_popup = _Popup()

        def semester(self):
            return self.__sem

        def play_sfx(self, key):
            pass

    forget()
    ctx = _Ctx(1, 80)
    check(ctx)
    assert ctx.message_popup.opened == [], "warned far too early"
    assert hud_days(ctx) is None and not is_low(ctx)

    ctx = _Ctx(1, 16)
    check(ctx)
    assert ctx.message_popup.opened == [], "warned one day early"

    ctx = _Ctx(1, 15)
    check(ctx)
    assert len(ctx.message_popup.opened) == 1, "did not warn at 15"
    assert "15 days left" in ctx.message_popup.opened[0][1][0]
    assert hud_days(ctx) == 15 and is_low(ctx)

    check(ctx)
    check(ctx)
    assert len(ctx.message_popup.opened) == 1, "warned more than once"

    later = _Ctx(1, 9)
    check(later)
    assert later.message_popup.opened == [], "re-warned inside one semester"
    assert hud_days(later) == 9, "chip must follow the day count down"

    rolled = _Ctx(2, 80)
    check(rolled)
    assert rolled.message_popup.opened == [] and hud_days(rolled) is None
    spent = _Ctx(2, 12)
    check(spent)
    assert len(spent.message_popup.opened) == 1, "next semester must re-arm"
    assert "12 days left" in spent.message_popup.opened[0][1][0]

    one = _Ctx(3, 1)
    check(one)
    assert "1 day left" in one.message_popup.opened[0][1][0], "plural at one"

    zero = _Ctx(4, 0)
    check(zero)
    assert hud_days(zero) == 0, "zero days must still show the chip"

    forget()
    print("day_warning: all checks passed")

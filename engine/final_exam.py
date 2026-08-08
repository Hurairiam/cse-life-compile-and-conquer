"""
engine/final_exam.py
The end of the exams: one popup, then the campus.

WHY THIS IS ITS OWN FILE
────────────────────────
The same reason engine/menu_prop.py and engine/day_warning.py are: a
new module cannot produce a merge conflict, and the alternative was
another branch inside engine/states/exam.py. That file carries a
one-line call instead.

WHAT IT REPLACES
────────────────
Finishing the last exam used to drop the player on a bare tan screen
whose only non-quit key rolled the semester straight over — monologue,
registration, and back to the bedroom for a new term. The end of a term
was unwalkable: there was no route from the exam back to EXPLORATION at
all, so the player never got to stand on the campus with the finals
behind them.

THE RULE (owner ruling, Phase 7)
────────────────────────────────
Every registered course attempted, and then:

    days left > 0   ->  popup, then EXPLORATION. The player roams and
                        takes side quests for the rest of the term, and
                        ends it when they choose by interacting with an
                        "end_semester" menu prop (engine/states/
                        end_semester.py).
    days left <= 0  ->  popup, then the term rolls over exactly as it
                        always did. No days, no roaming.

Only the CLOSING LINE of the popup changes between the two, because
only the closing line makes a promise about where the player is going.

SEMESTER ROLLOVER IS NOT TOUCHED. `exam.close_semester()` still does
precisely what it did — backlog, freeze check, advance_semester(), the
monologue. This module only moves WHEN it is called, never what it
does, and in the days<=0 branch it does not even move that.

THE TERM THAT RAN DRY IS LEFT ALONE
───────────────────────────────────
An exam costs 10-14 days and the warning fires at 15, so a semester
often runs out partway through the exams and the remaining courses are
never sat — exam.py sets ctx.exam["message"] and the player presses
SPACE twice. That path is untouched by owner ruling: congratulating
somebody who never sat two of their exams would be a lie, and the exam
logic itself is out of this phase's scope. check() consumes its
once-per-semester slot in that case and opens nothing, so clearing the
message with SPACE cannot make the popup appear a frame later.

STATE
─────
One module-level int — the semester the popup has already been shown
for — exactly as engine/day_warning.py keeps its own. Deliberately not
on ctx and not in the save file:

  * app_context.py is a shared, already-divergent file and this is one
    bookkeeping int;
  * the save payload gains no key, so SAVE_SCHEMA_VERSION stays at 1
    and every existing save still loads.

Keying it to the semester NUMBER means a rollover or a new game re-arms
it without anybody having to call a reset.

READ POINTS FOR LATER PHASES
────────────────────────────
`is_finished(ctx)` answers "are this term's exams behind the player?"
— which is what engine/states/end_semester.py asks before offering to
close the term, and what a side-quest phase would ask to know it is in
the post-exam stretch of a semester.
"""
from __future__ import annotations

from engine.screen_manager import ScreenState
from ui.popup import SEVERITY_INFO

# The semester whose popup has already been shown, or None. See STATE.
__done_semester = None

# Copy, approved by the owner before it was written down. Three centred
# lines is the hard ceiling (ui/popup.py MAX_BODY_LINES), and the first
# two never change — the finals are over either way.
TITLE = "EXAMS DONE"
BODY = ("Congratulations on completing the",
        "final exams for this semester!")
LINE_ROAM = "Go breathe — the campus is yours."
LINE_OVER = "The term is over — next one begins."


# ── the rule ───────────────────────────────────────────────────

def days_left(ctx) -> int:
    """Days remaining in the active semester's own pool."""
    return ctx.semester().get_time_pool_days()


def registered_count(ctx) -> int:
    """
    How many courses this term put in front of the player.

    Zero means there is nothing to have finished, which is why
    is_finished() refuses it: a player who walks into the exam having
    registered for nothing has not completed any finals.
    """
    try:
        return len(ctx.semester().get_registered_courses())
    except (AttributeError, TypeError):
        return 0


def is_finished(ctx) -> bool:
    """
    True once every registered course has been attempted.

    The same condition engine/states/exam.py expresses as
    `__current_course(ctx) is None` — its course_index has run past the
    registered list — written once here so end_semester.py and any
    later phase can ask it without importing a private helper.
    """
    count = registered_count(ctx)
    if count <= 0:
        return False
    return int(ctx.exam.get("course_index", 0)) >= count


def may_roam(ctx) -> bool:
    """
    True when finishing the exams hands the campus back rather than
    ending the term (owner ruling: days left > 0).
    """
    return days_left(ctx) > 0


# ── the popup ──────────────────────────────────────────────────

def check(ctx) -> bool:
    """
    Fire the congratulations the first time this semester's exams end.

    Called every frame from exam.update(), from the branch that already
    knows there is no course left to sit. True when it acted.

    ONCE PER SEMESTER. The player can come back to the exam screen for
    the rest of the term — the activity card's START EXAM and the X key
    both still work — and it must read as "press SPACE to end the
    semester" on every visit after the first, not as a fresh round of
    applause.
    """
    global __done_semester
    number = ctx.semester().get_semester_number()
    if __done_semester == number:
        return False
    if not is_finished(ctx):
        return False

    if ctx.exam.get("message"):
        # The term ran dry mid-exams. Consume the slot and say nothing,
        # so clearing the message with SPACE cannot open the popup on
        # the next frame. See THE TERM THAT RAN DRY, above.
        __done_semester = number
        return False

    __done_semester = number
    roam = may_roam(ctx)
    ctx.play_sfx("confirm")
    ctx.message_popup.open(
        TITLE, [BODY[0], BODY[1], LINE_ROAM if roam else LINE_OVER],
        SEVERITY_INFO)

    if roam:
        # The popup is a router-level overlay, drawn above whatever
        # state is active — so it lands on the map, and exploration's
        # __blocked() freezes the walker until it is dismissed. That is
        # the acceptance criterion exactly: dismissing it leaves the
        # player free to move.
        ctx.go(ScreenState.EXPLORATION)
        return True

    # Imported here rather than at module scope: engine/states/exam.py
    # imports THIS module, and close_semester() itself reaches for
    # engine.states.monologue the same way for the same reason.
    from engine.states.exam import close_semester
    close_semester(ctx)
    return True


def forget(ctx=None) -> None:
    """
    Re-arm the popup. Nothing in the game needs this — the semester
    number re-arms it on its own — but the stub test below and any
    later test running two semesters in one process does.
    """
    global __done_semester
    __done_semester = None


# -------------------------------------------------------------
# STUB TEST — the repo's convention for a module with no suite.
# Runs headless: no window, no assets, just the rule.
#     py -m engine.final_exam
# (as a module, so the project root stays on the import path)
# -------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    class _Semester:
        def __init__(self, number, days, courses):
            self.number, self.days, self.courses = number, days, courses

        def get_time_pool_days(self):
            return self.days

        def get_semester_number(self):
            return self.number

        def get_registered_courses(self):
            return self.courses

    class _Popup:
        def __init__(self):
            self.opened = []

        def open(self, title, lines, accent):
            self.opened.append((title, list(lines)))

    class _Ctx:
        def __init__(self, number, days, courses=3, index=3, message=None):
            self.__sem = _Semester(number, days, ["c"] * courses)
            self.message_popup = _Popup()
            self.exam = {"course_index": index, "message": message}
            self.went = []
            self.closed = 0

        def semester(self):
            return self.__sem

        def play_sfx(self, key):
            pass

        def go(self, state):
            self.went.append(state)

    # close_semester() is reached by a late import inside check(), so it
    # is swapped on the module object rather than passed in.
    import sys
    import types
    fake = types.ModuleType("engine.states.exam")

    def _close(ctx):
        ctx.closed += 1
    fake.close_semester = _close
    sys.modules["engine.states.exam"] = fake

    forget()
    mid = _Ctx(1, 40, courses=3, index=1)
    assert not check(mid), "fired before the last exam was sat"
    assert not is_finished(mid) and mid.message_popup.opened == []

    forget()
    none_reg = _Ctx(1, 40, courses=0, index=0)
    assert not check(none_reg), "fired for a term with nothing registered"
    assert not is_finished(none_reg)

    forget()
    roam = _Ctx(1, 40)
    assert check(roam), "did not fire when the exams ended with days left"
    assert is_finished(roam) and may_roam(roam)
    title, lines = roam.message_popup.opened[0]
    assert title == "EXAMS DONE" and len(lines) == 3
    assert lines[2] == LINE_ROAM, "days left must promise the campus"
    assert roam.went == [ScreenState.EXPLORATION], "did not hand back the map"
    assert roam.closed == 0, "rolled the semester over with days left"

    assert not check(roam), "congratulated twice in one semester"
    assert len(roam.message_popup.opened) == 1

    forget()
    over = _Ctx(2, 0)
    assert check(over), "did not fire when the exams ended with no days"
    assert not may_roam(over)
    assert over.message_popup.opened[0][1][2] == LINE_OVER
    assert over.closed == 1, "no days left must begin the next semester"
    assert over.went == [], "went somewhere other than close_semester()"

    forget()
    dry = _Ctx(3, 5, message="NOT ENOUGH TIME LEFT THIS SEMESTER")
    assert not check(dry), "congratulated a term that ran dry"
    assert dry.message_popup.opened == [] and dry.went == []
    dry.exam["message"] = None                 # the player presses SPACE
    assert not check(dry), "popped up a frame after the message cleared"
    assert dry.message_popup.opened == []

    forget()
    rolled = _Ctx(4, 80, courses=3, index=0)
    assert not check(rolled), "fired on a fresh term"
    rolled.exam["course_index"] = 3
    assert check(rolled), "the next semester must re-arm"
    assert rolled.message_popup.opened[0][1][2] == LINE_ROAM

    forget()
    negative = _Ctx(5, -2)
    assert check(negative) and not may_roam(negative), "overspent still ends"
    assert negative.closed == 1

    del sys.modules["engine.states.exam"]
    forget()
    print("final_exam: all checks passed")

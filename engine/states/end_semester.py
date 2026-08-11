"""
The "end the semester now?" question an end_semester prop opens.

Reached through the normal menu-prop path: a prop whose interaction
kind is "menu" and whose menu id is "end_semester" routes here, so the
door out of a term hangs on whichever object the author picks in the
level editor rather than being hardcoded. Adding it cost one appended
ScreenState member and one appended MENU_REGISTRY row — the editor's
dropdown reads that dict, so tools/ needed no edit at all.

WHY THIS EXISTS
───────────────
Finishing the exams with days left now hands the campus back instead of
rolling the term over (engine/final_exam.py, owner ruling). That is the
whole point — the player roams and takes side quests with the finals
behind them — but it leaves the term with no ending, so this is the
ending: a prop they walk up to when they are done.

IT REFUSES UNTIL THE EXAMS ARE DONE
───────────────────────────────────
`final_exam.is_finished(ctx)` is the gate. Letting a prop end a term
mid-semester would skip every unsat exam, and close_semester() would
dutifully backlog all of them — a way to throw a whole semester away by
walking into a rug. The semester rollover rules are out of this phase's
scope, and this is the one place a new door could have changed them.

IT ASKS BEFORE IT ACTS
──────────────────────
The remaining days do not carry over — player.advance_semester() resets
the pool to 80 — so this is destructive in exactly the way OVERWRITE
SLOT n? is, and it takes the same ConfirmPopup, named with what it
costs. The question is asked here rather than in a screen of its own
because there is nothing to draw: the map underneath IS the screen.

NOTHING ABOUT THE ROLLOVER LIVES HERE. CONFIRM calls
engine/states/exam.py::close_semester(), unchanged and still the only
thing in the game that closes a term.
"""
from engine import final_exam
from engine.screen_manager import ScreenState
from ui.popup import RESULT_CONFIRM, SEVERITY_INFO, SEVERITY_WARNING

# Module-level rather than on ctx, the way engine/states/save_game.py
# keeps its own row highlight: nothing outside this file reads it, and
# app_context.py is a shared file worth not touching for one bool.
__refused = False


def enter(ctx):
    """
    Ask the question, or refuse before anything is drawn.

    A refusal opens one popup and hands control straight back, so the
    player presses E, reads why, and is still standing on the map.
    """
    global __refused
    __refused = not final_exam.is_finished(ctx)
    if __refused:
        ctx.play_sfx("error")
        ctx.message_popup.open(
            "NOT YET",
            ["You still have exams to sit.",
             "Come back once they are done."], SEVERITY_INFO)
        ctx.go(ctx.return_state or ScreenState.EXPLORATION)
        return

    days = final_exam.days_left(ctx)
    ctx.popup.open(
        "END THE SEMESTER?",
        ["%d day%s left in this term." % (days, "" if days == 1 else "s"),
         "They will not carry over."],
        SEVERITY_WARNING, confirm_label="END TERM")


def update(ctx, dt):
    """
    Resolve the question. This state has no input of its own — the
    popup is a modal and eats every event before a state sees one.
    """
    if __refused:
        return
    result = ctx.popup.take_result()
    if result is None:
        # A popup that closed without recording anything would strand
        # the player on a screen with no keys. Not reachable through
        # ConfirmPopup, which always sets a result — but being wrong
        # about that should cost a wasted frame, not the run.
        if not ctx.popup.is_open():
            __leave(ctx)
        return
    if result == RESULT_CONFIRM:
        ctx.play_sfx("confirm")
        # The one call. Imported late for the same reason
        # close_semester() reaches for engine.states.monologue late:
        # state modules are loaded by the router, not by each other.
        from engine.states.exam import close_semester
        close_semester(ctx)
        return
    __leave(ctx)


def __leave(ctx):
    """Hand control back to the map, term untouched."""
    ctx.play_sfx("cancel")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def render(ctx, screen):
    """
    Draw the map. The router draws the question over it.

    Redrawn here rather than left over from the previous frame because
    the router only renders the ACTIVE state — without this the popup
    would sit on whatever was last flipped to the screen. Exploration's
    render is pure drawing, so calling it is safe, and it is what
    engine/states/activity.py and teleport.py both do.
    """
    from engine.states import exploration
    if getattr(ctx, "level", None) is not None:
        exploration.render(ctx, screen)

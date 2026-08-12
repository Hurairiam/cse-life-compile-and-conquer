"""
The three-choice question an end_semester prop opens (Task 7).

Reached through the normal menu-prop path: a prop whose interaction
kind is "menu" and whose menu id is "end_semester" routes here, so the
door out of a term hangs on whichever object the author picks in the
level editor rather than being hardcoded. In the shipped levels that
prop is the bed in levels/player_room.json.

WHAT CHANGED, AND WHAT THE BRIEF GOT WRONG
──────────────────────────────────────────
Task 7 describes replacing an "instant semester skip" with a popup. That
is not what this prop did: it already refused while exams were unsat and
already asked a two-button ConfirmPopup before closing the term. So this
phase is not a replacement but an EXTENSION — the same gate, the same
question, plus a second answer:

    ADVANCE SEMESTER   only when every exam has been sat
    DRAIN TIMEPOOL     spend a typed number of days, never past the floor
    CANCEL             nothing happens

ONE NUMBER GATES AND FLOORS BOTH
────────────────────────────────
`engine/exam_days.py` owns "days still needed to complete all remaining
exams this semester" — the value the brief assumes exists and the repo
did not have. `can_advance()` opens option 1 and `drainable()` bounds
option 2, and because `days_needed()` is zero exactly when the exams are
done, the floor disappears at the same instant the gate opens. Neither
answer is derived here.

THE REFUSAL POPUP IS GONE ON PURPOSE
────────────────────────────────────
This state used to open a "NOT YET" MessagePopup and hand control
straight back when the exams were unsat. The brief asks for the blocked
option to be "visibly unavailable rather than silently no-op", which the
greyed button plus the exam count does better: the player sees the
choice exists, sees why it is shut, and is still standing in front of
the other two.

IT OWNS ITS POPUP RATHER THAN USING ctx.popup
─────────────────────────────────────────────
ctx.popup is the shared ConfirmPopup and is wired into
engine/state_router.py's modal list. BedPopup is a module-level
singleton here instead, so this phase adds no member to app_context.py
and no row to the router's overlay list — two shared, already-divergent
files left untouched (G3). The cost is that this state routes the events
and draws the card itself, which is the four lines below.

NOTHING ABOUT THE ROLLOVER LIVES HERE. ADVANCE calls
engine/states/exam.py::close_semester(), unchanged and still the only
thing in the game that closes a term. DRAIN calls
engine/day_drain.py::drain_days(), which puts one PassDaysAction through
GameClock exactly as the pass_days prop already did — so the low-day
warning and the HUD chip still fire on the way down.

THE AUTOSAVE (Task 9) HANGS OFF ADVANCE, here, rather than inside
close_semester(). That function is shared and has two other callers —
engine/final_exam.py rolls a term over when the days run out, and a
frozen run routes to ENDGAME through it — and Task 9's trigger is
specifically the player choosing to advance. See `__autosave()` for why
it is guarded on the semester number rather than on the call.
"""
import pygame

from engine import day_drain, exam_days
from engine.screen_manager import ScreenState
from ui.bed_popup import (RESULT_ADVANCE, RESULT_CANCEL, RESULT_DRAIN,
                          BedPopup)
from ui.popup import SEVERITY_DANGER

# Module-level, the way engine/states/save_game.py and pass_days.py keep
# theirs: nothing outside this file reads it, and app_context.py is a
# shared file worth not touching for one widget.
__popup = None


def __ui(ctx):
    """The card, built once against this screen's size."""
    global __popup
    if __popup is None:
        __popup = BedPopup(ctx.screen_w, ctx.screen_h)
    return __popup


def enter(ctx):
    """
    Ask the question.

    Opened with what the rules allow rather than with the rules: the
    widget is told whether advance is available and how many days may be
    drained, and never consults the game itself (§6.2).
    """
    __ui(ctx).open_bed(
        can_advance=exam_days.can_advance(ctx),
        ceiling=exam_days.drainable(ctx),
        exams_left=exam_days.remaining_exams(ctx))
    ctx.play_sfx("click")


def exit(ctx):
    """Never leave the card up behind a state change."""
    if __popup is not None:
        __popup.close()


def handle_events(ctx, events):
    """
    The card gets every event while it is open — it is a modal.

    Routed here rather than by the router because this popup is not in
    the router's modal list; see the header. `handle_event()` returns
    True for anything it consumed, which is everything while open.
    """
    popup = __ui(ctx)
    for event in events:
        popup.handle_event(event)


def update(ctx, dt):
    """Act on the choice, once."""
    popup = __ui(ctx)
    choice = popup.take_choice()
    if choice is None:
        # A card that closed without recording anything would strand the
        # player on a screen with no keys. Not reachable through
        # BedPopup, which always records before it closes.
        if not popup.is_open():
            __leave(ctx)
        return

    if choice == RESULT_ADVANCE:
        ctx.play_sfx("confirm")
        # The one call. Imported late for the same reason
        # close_semester() reaches for engine.states.monologue late:
        # state modules are loaded by the router, not by each other.
        from engine.states.exam import close_semester
        before = ctx.semester().get_semester_number()
        close_semester(ctx)
        __autosave(ctx, before)
        return

    if choice == RESULT_DRAIN:
        # The popup already refused anything outside 1..ceiling, and
        # drain_days() caps at the pool again on its own — the number
        # cannot get through twice-checked and still be wrong.
        ctx.play_sfx("confirm")
        day_drain.drain_days(ctx, popup.get_days())
        ctx.go(ctx.return_state or ScreenState.EXPLORATION)
        return

    __leave(ctx)


def __autosave(ctx, semester_before):
    """
    Write the autosave once the term has actually rolled over (Task 9).

    AFTER, NOT AROUND. `close_semester()` does the whole transition
    synchronously — expire the term's quest, check the freeze, advance
    the clock, reset the gates — and only then queues the monologue. So
    by the time it returns, `ctx.semester()` IS the new semester and a
    capture taken here is the new term's state, not a half-transitioned
    one. That is the ordering Task 9 asks to confirm rather than assume.

    GUARDED ON THE NUMBER MOVING, not on having called the function.
    `close_semester()` has an early return: a run that is frozen goes to
    ENDGAME without advancing anything. Autosaving there would overwrite
    a perfectly good file with a finished run at the moment the player
    can least afford it. Comparing the semester number is the only test
    that distinguishes the two paths from out here.

    SAME ROUTINE AS `SAVE GAME` (G6). `SaveManager.autosave(state)` is
    literally `save(AUTOSAVE_SLOT_ID, state)`, and the payload comes
    from `save_bridge.capture()` — the same two calls
    engine/states/save_game.py makes when the player picks a slot. No
    second save path exists.

    NO PROMPT, and silence when it works: the player asked to end a
    semester, not to be told about a file. A failure still speaks up,
    because that is the case where something was lost — the same rule
    engine/progression.py's quit-to-menu autosave already follows.
    """
    if ctx.semester().get_semester_number() == semester_before:
        return                      # frozen run: nothing rolled over
    from engine import save_bridge
    if ctx.saves.autosave(save_bridge.capture(ctx)):
        return
    ctx.play_sfx("error")
    ctx.message_popup.open(
        "SAVE FAILED",
        [ctx.saves.get_last_error()[:48] or "Could not write."],
        SEVERITY_DANGER)


def __leave(ctx):
    """Hand control back to the map, term untouched."""
    ctx.play_sfx("cancel")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def render(ctx, screen):
    """
    Draw the map, then the card over it.

    Exploration is redrawn here rather than left over from the previous
    frame because the router only renders the ACTIVE state — without
    this the card would sit on whatever was last flipped to the screen.
    Exploration's render is pure drawing, so calling it is safe, and it
    is what engine/states/activity.py, teleport.py and pass_days.py all
    do. The card is drawn after it, by this state, because it is not one
    of the router's overlays.
    """
    from engine.states import exploration
    if getattr(ctx, "level", None) is not None:
        exploration.render(ctx, screen)
    __ui(ctx).render(screen)

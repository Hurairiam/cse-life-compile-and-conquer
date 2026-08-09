"""
The "pass the rest of the term?" question a pass_days prop opens.

Reached through the normal menu-prop path: a prop whose interaction kind
is "menu" and whose menu id is "pass_days" routes here, so the object
that skips a semester's remaining days is whichever one the author picks
in the level editor rather than a hardcoded one. Registering it cost the
same three edits Phase 5's teleport cost — one appended ScreenState
member, one appended MENU_REGISTRY row, one file in engine/states/ — and
tools/ needed no change at all, because the editor's menu dropdown reads
that dict.

IT ASKS BEFORE IT ACTS
──────────────────────
The days do not come back, so this is destructive in exactly the way
OVERWRITE SLOT n? and END THE SEMESTER? are, and it takes the same
ConfirmPopup named with what it costs. CANCEL changes nothing at all —
the drain is not built, let alone run, until CONFIRM comes back. The
question is asked here rather than on a screen of its own because there
is nothing to draw: the map underneath IS the screen, the way
engine/states/end_semester.py already has it.

IT STOPS AT THE DRAIN (owner ruling, Phase 11)
──────────────────────────────────────────────
CONFIRM spends the days and hands the player straight back to the map at
zero days. It does not open the exam — that would reinstate for this one
prop the automatic bounce Phase 6 removed — and it does not roll the
semester over, which is still only ever done by exam.close_semester(),
reached through the exam screen or an end_semester prop. Nothing in the
time system reacts to a pool hitting zero on its own, and this phase
leaves that true.

It also does not refuse while exams are unsat (same ruling). Draining
before the finals backlogs whatever is never sat, exactly as a term that
runs out of days already does; the confirmation says so and CANCEL is
right there.

NOTHING ABOUT SPENDING DAYS LIVES HERE. CONFIRM calls
engine/day_drain.py, which puts one TimeConsumable through
GameClock.process_time_consumable() — so Phase 6's warning popup and HUD
chip fire on the way down without either being repeated anywhere.
"""
from engine import day_drain
from engine.screen_manager import ScreenState
from ui.popup import RESULT_CONFIRM, SEVERITY_INFO, SEVERITY_WARNING

# Module-level rather than on ctx, the way engine/states/save_game.py and
# engine/states/end_semester.py both keep their own: nothing outside this
# file reads it, and app_context.py is a shared file worth not touching
# for one bool.
__refused = False


def enter(ctx):
    """
    Ask the question, or refuse before anything is drawn.

    A refusal opens one popup and hands control straight back, so the
    player presses E, reads why, and is still standing on the map.
    """
    global __refused
    __refused = not day_drain.can_pass(ctx)
    if __refused:
        ctx.play_sfx("error")
        ctx.message_popup.open(
            "NO DAYS LEFT",
            ["There is nothing left to pass —",
             "this term is already spent."], SEVERITY_INFO)
        ctx.go(ctx.return_state or ScreenState.EXPLORATION)
        return

    days = day_drain.passable(ctx)
    ctx.popup.open(
        "PASS REMAINING DAYS?",
        ["%d day%s left in this term." % (days, "" if days == 1 else "s"),
         "All of them go to the main quest.",
         "They will not come back."],
        SEVERITY_WARNING, confirm_label="PASS DAYS")


def update(ctx, dt):
    """
    Resolve the question. This state has no input of its own — the popup
    is a modal and eats every event before a state sees one.
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
        # The one call. The warning popup and the HUD chip are not fired
        # from here: exploration.update() runs day_warning.check() every
        # frame and the router derives the chip every frame, so both
        # land on the next frame off the count this just changed.
        day_drain.drain(ctx)
        ctx.go(ctx.return_state or ScreenState.EXPLORATION)
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
    engine/states/activity.py, teleport.py and end_semester.py all do.
    """
    from engine.states import exploration
    if getattr(ctx, "level", None) is not None:
        exploration.render(ctx, screen)

"""
The lecture reader a side quest opens: one sheet at a time, in order,
finished in one sitting or not at all.

Reached only from engine/states/side_quests.py — the PC in the player's
room — after the days have already been charged. Nothing on this screen
spends time, and nothing on it can be reached without paying first:
engine/lecture_reader.py::start() is the single door, and it charges
before it opens.

WHY IT LOOKS LIKE THE COURSE LECTURE
────────────────────────────────────
Because it is one. Recon §15 surveyed every long-form text format in
the engine and named engine/states/lecture.py + a content/ dict as the
best fit for these sheets, and Phase 11.5 then split all 36 paragraphs
into `lines` sized for ui/dialog_box.py's three-row card on that basis.
So this module is that one's shape — the same dialogue box, the same
two-stage SPACE (finish the line, then advance), the same typewriter,
the same text-speed setting — with a sheet loop around it instead of a
course loop. No new widget, no new card geometry, and no new UI file:
lecture.py has none either, and inventing one would put a second
long-form reader in a repo that already has six.

THE EXIT WARNING
────────────────
ESC does not leave. It asks, through the shared ConfirmPopup, and the
question states plainly that the days already spent are gone and that
nothing read is kept (Decision R1/R2, Phase 15). Only CONFIRM leaves.

SPACE and left-click are the only advance keys, deliberately. ENTER is
CONFIRM on every ConfirmPopup in this game, so binding it to "next
sheet" as well would let a player mashing through a lecture answer the
leave question by accident — with two days and a whole topic on it.

exit() abandons whatever is still open, so there is no path off this
screen that leaves a sitting half-alive.
"""
import pygame

from engine import lecture_reader
from engine.screen_manager import ScreenState
from ui import skip_button
from ui.popup import RESULT_CONFIRM, SEVERITY_INFO, SEVERITY_WARNING

BG = (231, 214, 189)            # PANEL_TAN, the same fill lecture.py uses
TEXT = (74, 53, 39)             # TEXT_COFFEE
MUTED = (140, 110, 85)          # STAT_BROWN

PROGRESS_Y = 140                # "SHEET 2 OF 3"
REMINDER_Y = 186                # what leaving costs, stated up front
HINT_Y = 486                    # just above the dialog box's top edge

REMINDER = "THIS TOPIC ONLY COUNTS ONCE THE LAST SHEET IS READ"
HINT = "SPACE  NEXT     TAB  SKIP     ESC  LEAVE"

# Module-level rather than on ctx, the way engine/states/teleport.py,
# save_game.py, pass_days.py and side_quests.py all keep theirs.
__leaving = False               # True while OUR exit question is open


def enter(ctx):
    """
    Show the first sheet. Nothing is charged here.

    The days came off in engine/lecture_reader.py::start(), before this
    transition was ever queued, and the caller waited for every popup
    that charge raised to be answered before handing over — so a time
    event can never land on top of an open reader.
    """
    global __leaving
    __leaving = False
    if not lecture_reader.is_open():
        # Nothing paid for it, so there is nothing to read. Only
        # reachable by routing here directly, which no prop can do.
        ctx.go(ctx.return_state or ScreenState.EXPLORATION)
        return
    __load(ctx)


def exit(ctx):
    """
    Leave nothing behind, whichever way the screen was left.

    A no-op after the reader finished or was abandoned, both of which
    have already cleared it. What this covers is any future path off
    this screen that forgets to: there is no per-sheet progress to keep,
    so a sitting must never outlive the screen showing it.
    """
    lecture_reader.end()


def __load(ctx):
    """Put the sheet on screen into the dialogue box."""
    sheet = lecture_reader.current_sheet()
    ctx.dialogue_manager.load_dialogue(list(sheet["lines"]))
    ctx.dialogue_manager.set_speaker(sheet["title"])


# ── input ──────────────────────────────────────────────────────

def handle_events(ctx, events):
    """SPACE or a click reads on; SKIP finishes it; ESC asks to leave."""
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                __ask_to_leave(ctx)
                return
            if event.key == pygame.K_TAB:
                __skip(ctx)
                return
            if event.key == pygame.K_SPACE:
                __advance(ctx)
                return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # The button first: a click inside it is a skip, not a page
            # turn. Tested against skip_button.get_rect() — the same
            # rectangle render() drew — so the two cannot disagree.
            if skip_button.hit(ctx.screen_w, event.pos):
                __skip(ctx)
                return
            __advance(ctx)
            return


def __skip(ctx):
    """
    End the lecture now, with the topic counted (Task 1).

    Completion parity: `lecture_reader.skip_to_end()` drives the SAME
    `advance()` loop reading would, so the quest reaches Completed by
    the one path that can get it there and the Phase 1 skill flag flips
    with it. This function then calls `__finish()` — the identical
    landing SPACE takes on the last sheet — so the notice, the sound and
    the exit are shared rather than reproduced.

    Deliberately no confirmation. Skipping COMPLETES the topic; it is
    not the destructive exit ESC guards, and asking "are you sure?"
    before something purely beneficial trains players to click through
    the question that matters.
    """
    if not lecture_reader.is_open():
        return
    lecture_reader.skip_to_end(ctx)
    __finish(ctx)


def __advance(ctx):
    """
    Finish the line first, then the sheet, then the sitting.

    The two-stage press is lecture.py's and dialogue.py's: the first
    press completes a half-revealed line rather than skipping it, so a
    player reading at SLOW text speed never loses a paragraph to an
    impatient thumb.
    """
    if ctx.dialogue_manager.skip_reveal():
        return
    ctx.play_sfx("page_turn")
    if ctx.dialogue_manager.advance():
        return                              # more of this sheet to read
    if lecture_reader.advance(ctx):
        __load(ctx)                         # the next sheet
        return
    __finish(ctx)                           # that was the last one


def __finish(ctx):
    """
    The last sheet is read. The quest is already Completed and the skill
    already applied — engine/lecture_reader.py::advance() did both, in
    that order, on the line above.

    The notice is built BEFORE end() clears the sitting, because it
    names the topic and the sheet count it is about to forget.
    """
    title, lines = lecture_reader.completion_notice(ctx)
    lecture_reader.end()
    ctx.play_sfx("confirm")
    ctx.message_popup.open(title, lines, SEVERITY_INFO)
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def __ask_to_leave(ctx):
    """
    Any player-initiated exit warns first and needs an explicit yes.

    Opened on ctx.popup, the shared ConfirmPopup, whose CANCEL is what
    ESC maps to — so a second ESC backs out of the question rather than
    confirming it.
    """
    global __leaving
    if not lecture_reader.is_open():
        return
    title, lines = lecture_reader.exit_warning()
    __leaving = True
    ctx.play_sfx("error")
    ctx.popup.open(title, lines, SEVERITY_WARNING,
                   confirm_label="LEAVE", cancel_label="KEEP READING")


def update(ctx, dt):
    """
    Tick the typewriter, and resolve the exit question if one is ours.

    Guarded on `__leaving` rather than on the popup alone: ctx.popup is
    shared, and reading a result this screen did not ask for would throw
    away a lecture off somebody else's question.
    """
    global __leaving
    ctx.dialogue_manager.update(dt)
    if not __leaving:
        return

    result = ctx.popup.take_result()
    if result is None:
        # A popup closed without recording anything would leave the
        # reader waiting on an answer that is never coming. Not
        # reachable through ConfirmPopup, which always sets a result.
        if not ctx.popup.is_open():
            __leaving = False
        return

    __leaving = False
    if result != RESULT_CONFIRM:
        ctx.play_sfx("cancel")
        return

    # Decision R1: the quest stays Unlocked and the days stay spent.
    lecture_reader.abandon()
    ctx.play_sfx("cancel")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


# ── drawing ────────────────────────────────────────────────────

def render(ctx, screen):
    """
    The sheet, its number, and what leaving would cost.

    A flat fill rather than the map behind a veil, unlike the PC's list
    — this is reading, not a card over a room, and lecture.py fills the
    same colour for the same reason.
    """
    screen.fill(BG)
    if not lecture_reader.is_open():
        return
    __line(ctx, screen, ctx.fonts["title"], lecture_reader.progress_label(),
           TEXT, PROGRESS_Y)
    # Stated on every sheet, not just in the exit question: a player who
    # has to be warned on the way out was not told in time.
    __line(ctx, screen, ctx.fonts["small"], REMINDER, MUTED, REMINDER_Y)
    __line(ctx, screen, ctx.fonts["small"], HINT, MUTED, HINT_Y)
    ctx.dialogue_manager.render(screen)
    # Drawn last so nothing lands on top of it, and top-right below the
    # HUD strip the router paints over this screen (Task 1).
    skip_button.render(screen, ctx.screen_w)


def __line(ctx, screen, font, text, colour, y):
    """One centred line of header text."""
    if not text:
        return
    surface = font.render(text, True, colour)
    screen.blit(surface, (ctx.screen_w // 2 - surface.get_width() // 2, y))

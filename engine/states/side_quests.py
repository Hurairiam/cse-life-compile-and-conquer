"""
The side quest list the PC in the player's room opens.

Reached through the normal menu-prop path: a prop whose interaction kind
is "menu" and whose menu id is "side_quests" routes here, so the machine
that shows the list is whichever object the author picks in the level
editor rather than a hardcoded one. Registering it cost the three edits
Phase 5's teleport and Phase 11's pass_days both cost — one appended
ScreenState member, one appended MENU_REGISTRY row, one file in
engine/states/ — and tools/ needed no change at all, because the
editor's menu dropdown reads that dict.

THE PC WAS ALREADY THERE (owner ruling, Phase 14)
─────────────────────────────────────────────────
levels/player_room.json already had one: `prop_0023` and `prop_0024`,
the two lower tiles of the computer desk, both wired to the skill tree.
The brief says extend the PC rather than add a second one, so both were
re-pointed at this list instead of a third interactable being dropped
into a ten-by-ten room. The skill tree did not lose a door — it is on
the pause menu, one ESC away, where it has always been.

WHAT IS SHOWN, AND WHAT IS NOT
──────────────────────────────
Nothing about that is decided here. engine/side_quest_list.py hands over
the Unlocked and Completed quests and nothing else, so a declined or
missed topic never reaches this file, let alone the screen. There is no
filtering step in here to get wrong, and no count of the twelve to leak.

WHAT CONFIRMING DOES  (Phase 15)
────────────────────────────────
Charges the topic's day_cost through engine/lecture_reader.py and opens
the reader on its first sheet. Phase 14 stopped at logging the id; the
log line is still written, and the call that used to be its whole
successor is now three: charge, let the time events land, hand over.

THE TIME CHANGE IS RESOLVED BEFORE THE READER OPENS.
lecture_reader.start() puts the charge through
GameClock.process_time_consumable(), so Phase 6's threshold is crossed
the same way passing days or sitting an exam crosses it. Its warning
popup normally fires from exploration.update(), which does not run
here, so __open_reader() calls day_warning.check() itself on the same
frame — and then WAITS, on this card, until nothing is left on screen
to answer. That is the brief's "resolve the time change fully before
the reader opens, and do not let time events interrupt an open reader",
and it reuses Phase 6's handling rather than repeating it.

The refusals are unchanged and are still total. A quest costing more
days than the term has left cannot be confirmed at all: the question is
never opened, nothing is deducted, and there is no override anywhere in
the path.
"""
import pygame

from engine import day_warning, lecture_reader, side_quest_list
from engine.screen_manager import ScreenState
from ui.popup import RESULT_CONFIRM, SEVERITY_INFO, SEVERITY_WARNING
from ui.side_quest_screen import ROW_GREEN, SideQuestScreen, format_quest_row

# Module-level rather than on ctx, the way engine/states/teleport.py,
# save_game.py and pass_days.py all keep theirs: nothing outside this
# file reads them, and app_context.py is a shared file worth not
# touching for three fields.
__screen = None
__rows = []
__pending = None        # the quest id the open confirmation refers to
__opening = None        # a charged sitting, waiting for the screen to clear


def __ui():
    global __screen
    if __screen is None:
        __screen = SideQuestScreen()
    return __screen


def enter(ctx):
    """
    Re-read the list and highlight the first row worth starting.

    Rebuilt on every open rather than cached, because a quest accepted
    or a term drained between two visits to the same desk changes both
    which rows exist and which of them can be started.
    """
    global __rows, __pending, __opening
    __pending = None
    __opening = None
    __rows = side_quest_list.entries(ctx)
    ui = __ui()
    ui.set_rows(
        [format_quest_row(row["title"], row["day_cost"], row["sheets"],
                          row["completed"]) for row in __rows],
        [ROW_GREEN if row["completed"] else None for row in __rows])
    # Opening with a finished topic under the cursor would make ENTER a
    # refusal, so the first row that can actually be started is picked.
    ui.set_selected(__first_startable(ctx))


def __first_startable(ctx):
    """Index of the first row that can be started, else 0."""
    for index, row in enumerate(__rows):
        if side_quest_list.is_startable(ctx, row["quest_id"]):
            return index
    return 0 if __rows else -1


# ── input ──────────────────────────────────────────────────────

def handle_events(ctx, events):
    """The table answers first; ENTER, the buttons and ESC are ours."""
    screen = pygame.display.get_surface()
    ui = __ui()
    for event in events:
        if screen is not None:
            before = ui.get_selected()
            if ui.handle_event(screen, event):
                # Ticking on every wheel notch turns a scroll into a
                # rattle, so only a real change of row is announced.
                if ui.get_selected() != before:
                    ctx.play_sfx("select")
                continue

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                __leave(ctx)
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                             pygame.K_SPACE, pygame.K_e):
                __select(ctx)
                return
        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and screen is not None):
            if ui.get_start_rect(screen).collidepoint(event.pos):
                __select(ctx)
                return
            if ui.get_close_rect(screen).collidepoint(event.pos):
                __leave(ctx)
                return


def __leave(ctx):
    """Close the card and hand control back to the map."""
    ctx.play_sfx("cancel")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def __select(ctx):
    """
    Act on the highlighted row: ask the question, or say why not.

    A refusal says why rather than doing nothing, matching what
    engine/states/teleport.py and engine/states/activity.py both do with
    an entry that cannot be taken — START is already drawn muted in
    those cases, and a muted button the player presses anyway is a
    question that deserves an answer.
    """
    global __pending
    index = __ui().get_selected()
    if not 0 <= index < len(__rows):
        ctx.play_sfx("error")
        ctx.message_popup.open(
            "NOTHING TO STUDY",
            ["There is nothing saved on this PC."], SEVERITY_INFO)
        return

    quest_id = __rows[index]["quest_id"]
    why = side_quest_list.refusal(ctx, quest_id)
    if why is not None:
        # The block. Nothing is deducted, nothing is opened, and the
        # confirmation below is never reached — there is no override.
        ctx.play_sfx("error")
        ctx.message_popup.open(why[0], why[1], SEVERITY_INFO)
        return

    title, lines = side_quest_list.confirmation(ctx, quest_id)
    __pending = quest_id
    ctx.play_sfx("select")
    ctx.popup.open(title, lines, SEVERITY_WARNING, confirm_label="START")


def update(ctx, dt):
    """
    Resolve the confirmation, if one is open.

    Guarded on `__pending` rather than on the popup alone: ctx.popup is
    shared, and reading a result this screen did not ask for would start
    a lecture off somebody else's question.
    """
    global __pending
    if __opening is not None:
        # The days are already spent and Phase 6 may have had something
        # to say about it. Nothing else happens on this card until that
        # has been read.
        __hand_over(ctx)
        return
    if __pending is None:
        return
    result = ctx.popup.take_result()
    if result is None:
        # A popup that closed without recording anything would leave the
        # card waiting on an answer that is never coming. Not reachable
        # through ConfirmPopup, which always sets a result.
        if not ctx.popup.is_open():
            __pending = None
        return

    quest_id, __pending = __pending, None
    if result != RESULT_CONFIRM:
        ctx.play_sfx("cancel")
        return

    # Re-asked after the question was answered. The term cannot lose a
    # day while a modal is up — the router runs one state and the popup
    # eats every event — but an answer that lands on a quest the rules
    # no longer allow should refuse rather than be honoured, and the
    # check costs one comparison.
    if not side_quest_list.is_startable(ctx, quest_id):
        why = side_quest_list.refusal(ctx, quest_id)
        ctx.play_sfx("error")
        ctx.message_popup.open(why[0], why[1], SEVERITY_INFO)
        return

    ctx.play_sfx("confirm")
    side_quest_list.confirm(quest_id)
    __open_reader(ctx, quest_id)


def __open_reader(ctx, quest_id):
    """
    Charge the days, then let the time change finish landing.

    start() re-checks everything for itself and changes nothing at all
    when it refuses, so a quest that slipped out of reach between the
    question and the answer costs nothing. The check above is not
    redundant with it — this one keeps the refusal wording on the card
    consistent, that one makes the charge safe on its own terms.
    """
    global __opening
    refused = lecture_reader.start(ctx, quest_id)
    if refused is not None:
        ctx.play_sfx("error")
        ctx.message_popup.open(refused[0], refused[1], SEVERITY_INFO)
        return
    __opening = quest_id
    # Phase 6's once-per-semester warning, fired here because
    # exploration.update() — its only other caller — does not run on
    # this screen. The threshold, the wording and the once-per-term
    # bookkeeping all stay in engine/day_warning.py; this is a call, not
    # a second copy.
    day_warning.check(ctx)
    __hand_over(ctx)


def __hand_over(ctx):
    """
    Enter the reader once there is nothing left on screen to answer.

    The wait is the whole point. A warning raised by the charge must be
    read and dismissed on THIS card, over the room — landing it on top
    of an open reader is exactly the interruption the brief rules out.
    """
    global __opening
    if ctx.message_popup.is_open() or ctx.popup.is_open():
        return
    __opening = None
    ctx.go(ScreenState.SIDE_QUEST_LECTURE)


# ── drawing ────────────────────────────────────────────────────

def render(ctx, screen):
    """
    Draw the room, then the card over it.

    The room is redrawn here rather than left over from the previous
    frame because the router only renders the ACTIVE state — without
    this the card would sit on whatever was last flipped to the screen.
    Exploration's render is pure drawing, so calling it is safe, and it
    is what activity.py, teleport.py and pass_days.py all do.
    """
    from engine.states import exploration
    if getattr(ctx, "level", None) is not None:
        exploration.render(ctx, screen)

    ui = __ui()
    index = ui.get_selected()
    startable = (0 <= index < len(__rows)
                 and side_quest_list.is_startable(ctx,
                                                  __rows[index]["quest_id"]))
    ui.render(screen, subtitle=__subtitle(ctx), can_start=startable)


def __subtitle(ctx):
    """
    One line under the title: the days the term has left.

    Deliberately not "n of 12", and deliberately not a count of anything
    — the number of rows on this card is the number of topics the player
    took on, and putting it beside a total would say out loud how many
    they did not.

    Below the end-of-term threshold it says so (Phase 17). START is
    already drawn muted there, and a muted button with no explanation
    beside it reads as a bug; the popup that names the threshold is
    still one keypress away, this is just the standing notice. The rule
    is asked for, never restated — `is_locked_out()` is the only place
    it is decided.
    """
    days = side_quest_list.days_left(ctx)
    if side_quest_list.is_locked_out(ctx):
        # Plain ASCII, the rule tests/test_lecture_reader.py states for
        # every string this feature draws: the pixel font has no glyph
        # for a stray dash or dot and renders a blank box instead.
        return "%d DAY%s LEFT - NO NEW LECTURES" % (
            days, "" if days == 1 else "S")
    return "%d DAY%s LEFT THIS TERM" % (days, "" if days == 1 else "S")

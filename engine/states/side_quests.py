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

WHAT CONFIRMING DOES
────────────────────
Logs the quest id and closes. Not a typo: the lecture reader is Phase
15's and the day charge is Phase 17's, so this phase stops at the point
where the id is known. The state machine is not touched either — the
quest was already Unlocked when it appeared on the list, and nothing
here moves it.

The refusals are the part that is finished. A quest costing more days
than the term has left cannot be confirmed at all: the question is never
opened, nothing is deducted, and there is no override anywhere in the
path.
"""
import pygame

from engine import side_quest_list
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
    global __rows, __pending
    __pending = None
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
    # The whole of it, this phase. Phase 15 opens the reader from here.
    side_quest_list.confirm(quest_id)
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


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
    """
    days = side_quest_list.days_left(ctx)
    return "%d DAY%s LEFT THIS TERM" % (days, "" if days == 1 else "S")

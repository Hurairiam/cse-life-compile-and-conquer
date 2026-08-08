"""
The "Where to go?" destination menu a teleport prop opens.

Reached through the normal menu-prop path: a prop whose interaction
kind is "menu" and whose menu id is "teleport" routes here, so the
teleport is attached to whichever prop the author picks in the level
editor rather than being hardcoded to one object. Adding it cost one
appended ScreenState member and one appended MENU_REGISTRY row — the
editor's dropdown reads that dict, so it needed no edit at all.

WHERE THE DESTINATIONS COME FROM
────────────────────────────────
content/map_directory.py, which derives them from the maps rather than
from a list in here. Anything the player could walk to from their room
is offered; the three areas nothing walks into are not, because
teleport would be their only door in and their only door out. A new
level wired to an existing one appears on its own.

WHERE THE PLAYER LANDS
──────────────────────
engine/return_points.py, read-only — the cell they left that area from,
or its SET SPAWN on a first visit. Arriving by teleport is then the
same as arriving on foot, which is the point.

Teleporting AWAY records nothing. Phase 4 files a return point when the
player steps through a doorway, and this is not one: there is no
threshold to step back from. So an area still remembers the last time
it was walked out of, and an area only ever teleported out of opens at
its SET SPAWN. Changing that would mean writing into Phase 4's table
from outside it, which is that phase's work, not this one's.

NO DAY COST and no trigger cap. engine/menu_prop.py runs before the
per-semester counter because a menu prop is a door, not a payout, and
nothing here goes near GameClock.
"""
import pygame

from content.map_directory import display_name, walk_reachable
from engine import return_points
from engine.level_loader import LevelLoadError, load_level
from engine.screen_manager import ScreenState
from ui.popup import SEVERITY_INFO, SEVERITY_WARNING
from ui.teleport_screen import ROW_GREEN, TeleportScreen, format_destination

# Module-level rather than on ctx, the way engine/states/save_game.py
# keeps its own row highlight: nothing else needs to read these, and
# app_context.py is a shared file worth not touching for two fields.
__screen = None
__destinations = []


def __ui():
    global __screen
    if __screen is None:
        __screen = TeleportScreen()
    return __screen


def enter(ctx):
    """
    Re-derive the destinations and highlight somewhere worth going.

    Rebuilt on every open rather than once at startup, so a map added
    or rewired between two visits to the same prop is already listed.
    """
    global __destinations
    __destinations = walk_reachable()
    here = getattr(ctx, "level_id", "")
    ui = __ui()
    ui.set_rows(
        [format_destination(name, level_id == here)
         for level_id, name in __destinations],
        [ROW_GREEN if level_id == here else None
         for level_id, _ in __destinations])
    # Opening with the player's own area under the cursor would make
    # ENTER a refusal, so the first row that goes somewhere is picked.
    ui.set_selected(__first_elsewhere(here))


def __first_elsewhere(here):
    """Index of the first destination that is not where we already are."""
    for index, (level_id, _) in enumerate(__destinations):
        if level_id != here:
            return index
    return 0 if __destinations else -1


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
                __confirm(ctx)
                return
        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and screen is not None):
            if ui.get_go_rect(screen).collidepoint(event.pos):
                __confirm(ctx)
                return
            if ui.get_back_rect(screen).collidepoint(event.pos):
                __leave(ctx)
                return


def __leave(ctx):
    """Close the card and hand control back to the map."""
    ctx.play_sfx("cancel")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


def __confirm(ctx):
    """
    Act on the highlighted row.

    A refusal says why rather than doing nothing, matching what
    engine/states/activity.py does with a greyed entry — GO is already
    drawn muted in both of these cases, and a muted button the player
    presses anyway is a question.
    """
    index = __ui().get_selected()
    if not 0 <= index < len(__destinations):
        ctx.play_sfx("error")
        ctx.message_popup.open("NOWHERE TO GO",
                               ["No area is connected to this one."],
                               SEVERITY_INFO)
        return
    level_id, name = __destinations[index]
    if level_id == getattr(ctx, "level_id", ""):
        ctx.play_sfx("error")
        ctx.message_popup.open("ALREADY HERE",
                               ["You are standing in %s." % name],
                               SEVERITY_INFO)
        return
    __travel(ctx, level_id)


def __travel(ctx, level_id):
    """
    Put the player in another area and return them to the map.

    Deliberately not a call into exploration.__travel(): that one is
    driven by a portal prop it reads a target and a spawn override off,
    and there is no prop here. exploration.py is also the file the recon
    names the busiest shared one in the repository, so the dozen lines
    it would have taken to generalise it live here instead, in a file
    that cannot conflict with anybody.

    The music and the ambient are not set here either. Handing control
    back to EXPLORATION fires its enter(), which calls
    soundtrack.apply_for_level() and play_ambient() off the level that
    is loaded by then — doing it twice would only restart the loop.
    """
    try:
        level = load_level(level_id)
    except LevelLoadError as error:
        ctx.play_sfx("error")
        ctx.message_popup.open("LEVEL NOT FOUND",
                               ["Could not open '%s'." % level_id,
                                str(error)[:48]], SEVERITY_WARNING)
        return
    ctx.level = level
    ctx.level_id = level.get_level_id()
    # A first visit lands on the area's own SET SPAWN; anywhere the
    # player has been before opens where they left it.
    spawn = return_points.arrival(ctx, level, level.get_spawn())
    if ctx.walker is None:
        # Nothing to place. Only exploration can reach this state and it
        # builds the walker before any prop can be pressed, so this is
        # unreachable today — but handing the cell to ensure_level() and
        # letting it build one beats stranding the player if it ever is.
        ctx.level = None
        ctx.pending_spawn = spawn
    else:
        ctx.walker.place(spawn)
        ctx.last_cell = ctx.walker.get_cell()
    ctx.play_sfx("page_turn")
    ctx.go(ctx.return_state or ScreenState.EXPLORATION)


# ── drawing ────────────────────────────────────────────────────

def render(ctx, screen):
    """
    Draw the map, then the card over it.

    The map is redrawn here rather than left over from the previous
    frame because the router only renders the ACTIVE state — without
    this the card would sit on whatever was last flipped to the screen.
    Exploration's render is pure drawing, so calling it is safe.
    """
    from engine.states import exploration
    if getattr(ctx, "level", None) is not None:
        exploration.render(ctx, screen)

    ui = __ui()
    here = getattr(ctx, "level_id", "")
    index = ui.get_selected()
    ui.render(screen, subtitle=__subtitle(ctx, here),
              can_go=(0 <= index < len(__destinations)
                      and __destinations[index][0] != here))


def __subtitle(ctx, here):
    """One line naming where the player is and how far the list goes."""
    level = getattr(ctx, "level", None)
    name = display_name(
        here, level.get_level_name() if level is not None else "")
    if not name:
        return "%d PLACES" % len(__destinations)
    return "FROM %s  ·  %d PLACES" % (name, len(__destinations))

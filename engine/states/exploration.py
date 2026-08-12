"""
The playable campus. Owns the level, the walker, the camera and every
decision the ui/ classes refuse to make.

Precedence for the E key is:
    gate (STAGE 6) -> NPC -> portal -> interactable prop
and the [E] chip follows it exactly bar one deliberate omission: a
step-on portal draws no chip, because it fires the moment the player
walks onto it and never needs the key. The chip therefore still never
promises something E will not do -- it simply stays quiet about a
threshold that announces itself by working.

MOVING BETWEEN AREAS NEVER NEEDS A KEY (owner ruling, Phase 6).
__check_cell_transition() crosses a portal AND a travel prop on entry,
so every link between two maps is walked through rather than pressed
through. E remains a second route to the same place on both.
"""
import pygame

from engine import (
    day_warning, gate_service, menu_prop, note_prop, npc_availability,
    return_points, soundtrack)
from engine.level_loader import LevelLoadError, load_level
from engine.player_mover import PlayerMover
from engine.screen_manager import ScreenState
from ui.interaction_prompt import (
    LABEL_ENTER, LABEL_EXAMINE, LABEL_LOCKED, LABEL_TALK)
from ui.popup import SEVERITY_INFO, SEVERITY_WARNING

BG = (231, 214, 189)          # PANEL_TAN — the void outside the level edge
FOOTSTEP_PERIOD = 0.34


def ensure_level(ctx) -> bool:
    """Load ctx.level_id if no level is up. False = load failed."""
    if ctx.level is not None:
        return True
    try:
        ctx.level = load_level(ctx.level_id or "campus_main",
                               semester=npc_availability.semester_of(ctx))
    except LevelLoadError as error:
        ctx.level = None
        ctx.level_error = str(error)[:64]
        return False
    ctx.level_id = ctx.level.get_level_id()
    spawn = ctx.pending_spawn or ctx.level.get_spawn()
    if not ctx.level.is_walkable(*spawn):
        spawn = ctx.level.get_spawn()
    ctx.pending_spawn = None
    if ctx.walker is None:
        ctx.walker = PlayerMover(spawn)
    else:
        ctx.walker.place(spawn)
    ctx.last_cell = ctx.walker.get_cell()
    ctx.level_error = ""
    return True


def enter(ctx):
    if not ensure_level(ctx):
        ctx.message_popup.open("LEVEL NOT FOUND",
                               ["Could not open '%s'." % ctx.level_id,
                                ctx.level_error], SEVERITY_WARNING)
        return
    soundtrack.apply_for_level(ctx)
    ctx.play_ambient(ctx.level.get_ambient() or "day")


def exit(ctx):
    if ctx.audio is not None:
        ctx.audio.stop_ambient()


# ── input ──────────────────────────────────────────────────────

def handle_events(ctx, events):
    for event in events:
        if event.type != pygame.KEYDOWN:
            continue
        if event.key == pygame.K_ESCAPE:
            from engine import progression
            progression.open_pause(ctx)
            return
        if event.key == pygame.K_e:
            __interact(ctx)
        elif event.key == pygame.K_x:
            ctx.go(ScreenState.EXAM)
        

def __read_axis(keys):
    dx = (1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0) \
        - (1 if keys[pygame.K_LEFT] or keys[pygame.K_a] else 0)
    dy = (1 if keys[pygame.K_DOWN] or keys[pygame.K_s] else 0) \
        - (1 if keys[pygame.K_UP] or keys[pygame.K_w] else 0)
    return dx, dy


def __blocked(ctx):
    """True while a modal owns the screen — the player must not walk."""
    return (ctx.popup.is_open() or ctx.message_popup.is_open()
            or (ctx.gate_notice is not None and ctx.gate_notice.is_open())
            or (ctx.pause_menu is not None and ctx.pause_menu.is_open()))


# ── frame ──────────────────────────────────────────────────────

def update(ctx, dt):
    if not ensure_level(ctx):
        return
    ctx.pulse = (ctx.pulse + dt) % 3600.0

    # The 15-day firewall used to BOUNCE the player into ScreenState.EXAM
    # here, the frame is_eligible_for_side_activities() went False. That
    # is gone by owner ruling (Phase 6): exploring costs no days, so
    # there is nothing to protect the player from, and a warning they
    # were yanked out of the world to read would have nowhere to live.
    # What the threshold costs them now is NEW SIDE QUESTS (Phase 17) —
    # engine/day_warning.py is where both that phase and this popup ask.
    day_warning.check(ctx)

    dx, dy = (0, 0) if __blocked(
        ctx) else __read_axis(pygame.key.get_pressed())
    ctx.walker.update(dt, dx, dy, ctx.level)

    if ctx.walker.is_moving():
        ctx.anim_time += dt
        if ctx.anim_time >= FOOTSTEP_PERIOD:
            ctx.anim_time = 0.0
            ctx.play_sfx("footstep")
    else:
        ctx.anim_time = 0.0

    from engine import progression
    progression.resolve_pause(ctx)
    gate_service.resolve_pending(ctx)
    __check_cell_transition(ctx)
    ctx.gate_states = gate_service.badge_states(ctx)
    ctx.camera = ctx.map_screen.compute_camera(
        ctx.level, ctx.walker.get_position(), pygame.display.get_surface())

    # The opening tutorial's third beat is walked into rather than handed
    # to: beat 2 gives the controls back in the player's room and beat 3
    # starts when the player reaches the lecture hall. All of the
    # deciding is engine/intro_sequence.py's — a new module cannot
    # conflict — and this file carries the call site, the same way it
    # already does for the gate service and the day warning. It answers
    # False on every frame of every ordinary playthrough.
    #
    # LAST, so the camera above is already framing the level the player
    # just walked into: the transition is pending until the end of the
    # frame, and this one still renders through exploration.render().
    from engine import intro_sequence
    intro_sequence.check_level_trigger(ctx)


def __check_cell_transition(ctx):
    """
    React the frame the player steps into a NEW cell.

    A gate that is not open bounces the player back to the cell they
    came from, so a locked door genuinely blocks the way instead of
    only talking about it. Fired on ENTRY only, so a held-back player
    does not re-open the notice every frame while standing still.
    """
    cell = ctx.walker.get_cell()
    if cell == ctx.last_cell:
        return
    previous = ctx.last_cell

    portal = ctx.level.get_portal_at(*cell)
    if portal is not None:
        ctx.last_cell = cell
        # `previous` is the cell the player held a frame ago, and it is
        # what this area is remembered by — see engine/return_points.py.
        __travel(ctx, portal, previous)
        return

    gate = gate_at(ctx, *cell)
    if gate is not None and not gate_service.is_cleared(ctx, cell):
        if gate_service.present(ctx, cell, gate):
            ctx.walker.place(previous)
            ctx.last_cell = previous
            return

    # A travel prop crosses on entry too, so NOTHING has to be pressed
    # to move between areas (owner ruling, Phase 6). E still works on
    # one — it is a second route to the same place, the way it already
    # is for a portal — but a doorway the player has walked into should
    # never sit there waiting for a key.
    #
    # Below the gate rather than above it, unlike the portal step: a
    # travel prop is a door somebody may have locked, and a lock that
    # opens because you walked at it is not a lock.
    door = ctx.level.get_interactable_at(*cell)
    if door is not None and door.travels_on_interact():
        ctx.last_cell = cell
        __travel(ctx, door, previous)
        return

    ctx.last_cell = cell


# ── interaction ────────────────────────────────────────────────

def gate_at(ctx, x, y):
    """
    The gate guarding a cell, or None. get_gate_at() already applies
    prop-over-zone precedence and already returns None for an open
    default gate, so no is_default() check is needed here.
    """
    if ctx.level is None:
        return None
    return ctx.level.get_gate_at(x, y)


def verb_for(ctx, cell):
    """
    (label, is_locked) — __interact's precedence with the portal step
    left silent.

    A step-on portal is not advertised: __check_cell_transition() fires
    it on entry, so the chip would only ever be read on the way past a
    doorway that opens by itself. __interact still travels when E is
    pressed on one, which is a spare route to the same place rather
    than the only one.

    The portal step stays in the chain and returns a BLANK label rather
    than being deleted. Every authored portal prop is flagged
    interactable, so dropping the step would not silence the chip — it
    would fall through and label a doorway [E] EXAMINE, promising a
    poke that __interact would answer by teleporting the player.
    """
    gate = gate_at(ctx, *cell)
    if gate is not None and not gate_service.is_cleared(ctx, cell):
        outcome, _ = gate_service.classify(ctx, gate)
        return (LABEL_LOCKED, outcome == gate_service.BLOCKED)
    npc = ctx.level.get_npc_at(*cell)
    if npc is not None and npc.get_interactable():
        return (LABEL_TALK, False)
    if ctx.level.get_portal_at(*cell) is not None:
        return ("", False)
    prop = ctx.level.get_interactable_at(*cell)
    if prop is not None:
        # A travel prop is a door you open, so it reads ENTER rather
        # than EXAMINE like a thing you poke at. It KEEPS its chip even
        # though __check_cell_transition() now crosses one on entry as
        # well: unlike a portal, a travel prop is a visible object the
        # player can stand beside and face, so the label answers "what
        # is this?" rather than advertising a key they must press.
        if prop.travels_on_interact():
            return (LABEL_ENTER, False)
        return (LABEL_EXAMINE, False)
    return ("", False)


def __interact(ctx):
    if __blocked(ctx):
        return
    cell = ctx.walker.get_facing_cell()
    gate = gate_at(ctx, *cell)
    if gate is not None and not gate_service.is_cleared(ctx, cell):
        gate_service.present(ctx, cell, gate)
        return
    npc = ctx.level.get_npc_at(*cell)
    if npc is not None and npc.get_interactable():
        __talk(ctx, npc)
        return
    portal = ctx.level.get_portal_at(*cell)
    if portal is not None:
        __travel(ctx, portal)
        return
    prop = ctx.level.get_interactable_at(*cell)
    if prop is not None:
        __trigger_prop(ctx, prop)


def __talk(ctx, npc_data):
    # The semester gate, the chain pick, the portrait and the branching
    # all live in engine/dialogue_flow.py — a new module cannot conflict,
    # and this file is edited by everyone.
    from engine import dialogue_flow
    dialogue_flow.start_talk(ctx, npc_data)


def __trigger_prop(ctx, prop):
    # Menu, note and travel props are doors and signs, not payouts, so
    # all three are checked before the per-semester trigger cap — a
    # doorway usable three times a term would be nonsense, and so would
    # a notice that stops being readable in March. Any restriction on
    # them lives on the prop's GATE, which __interact already evaluated
    # before getting here, so reaching this line means the player is
    # allowed through.
    if menu_prop.trigger(ctx, prop):
        return
    if note_prop.trigger(ctx, prop):
        return
    if prop.travels_on_interact():
        __travel(ctx, prop)
        return
    key = "%s:%s" % (ctx.level_id, prop.get_uid())
    used = ctx.prop_trigger_counts.get(key, 0)
    allowed = prop.get_triggers_per_semester()
    if used >= allowed:
        ctx.play_sfx("error")
        ctx.message_popup.open(
            "NOTHING LEFT",
            ["You have used this %d time(s) this term." % allowed,
             "It refreshes next semester."], SEVERITY_INFO)
        return
    ctx.prop_trigger_counts[key] = used + 1
    ctx.triggered_prop_uids.add(key)

    kind = prop.get_interaction_kind()
    amount = prop.get_amount()
    player = ctx.player()
    if kind == "money":
        player.deposit_funds(float(amount))
        body = ["You found {:,.0f} BDT.".format(amount),
                "Wallet: {:,.0f} BDT".format(player.get_wallet_balance()),
                "Uses left: %d" % (allowed - used - 1)]
    elif kind == "skill":
        skill_id = prop.get_skill_id() or "general"
        player.get_skill_tree().increment_skill(skill_id, int(amount))
        level = player.get_skill_tree().get_skill_level(skill_id)
        body = ["%s +%d" % (skill_id.replace("_", " "), int(amount)),
                "Now at level %d." % level,
                "Uses left: %d" % (allowed - used - 1)]
    else:
        body = ["There is nothing here to take."]
    ctx.play_sfx("confirm")
    ctx.message_popup.open("FOUND SOMETHING", body, SEVERITY_INFO)


def __travel(ctx, portal, origin=None):
    """
    Move the player through `portal`.

    `origin` is the cell they came from, and only a step-on portal has
    to supply it: everything else fires on E, so the walker is already
    standing beside the doorway rather than on top of it.
    """
    target = portal.get_target_level_id()
    if not target:
        ctx.message_popup.open("NOWHERE TO GO",
                               ["This doorway has no destination set."],
                               SEVERITY_WARNING)
        return
    try:
        level = load_level(target,
                           semester=npc_availability.semester_of(ctx))
    except LevelLoadError as error:
        ctx.message_popup.open("LEVEL NOT FOUND",
                               ["Could not open '%s'." % target,
                                str(error)[:48]], SEVERITY_WARNING)
        return
    # Filed under the level being LEFT, so it has to happen before
    # ctx.level_id moves, and after the two failure returns above so a
    # doorway that goes nowhere does not rewrite the way back.
    return_points.record(ctx, portal, origin or ctx.walker.get_cell())
    ctx.level = level
    ctx.level_id = level.get_level_id()
    spawn = portal.get_target_spawn() or level.get_spawn()
    if not level.is_walkable(*spawn):
        spawn = level.get_spawn()
    # An area the player has been in before opens where they left it;
    # a first visit still opens at the spawn worked out just above.
    spawn = return_points.arrival(ctx, level, spawn)
    ctx.walker.place(spawn)
    ctx.last_cell = ctx.walker.get_cell()
    ctx.play_sfx("page_turn")
    # Portal travel keeps us in EXPLORATION, so the router's per-screen
    # music hook never fires — the new level's track is set here.
    soundtrack.apply_for_level(ctx)
    ctx.play_ambient(level.get_ambient() or "day")


# ── drawing ────────────────────────────────────────────────────

def render(ctx, screen):
    screen.fill(BG)
    if ctx.level is None:
        return
    ctx.map_screen.render(screen, ctx.level, ctx.camera,
                          ctx.walker.get_position(),
                          ctx.walker.get_facing(),
                          ctx.walker.get_frame(),
                          gate_states=ctx.gate_states,
                          dt=0.0)
    if __blocked(ctx):
        return
    cell = ctx.walker.get_facing_cell()
    label, locked = verb_for(ctx, cell)
    if not label:
        return
    ctx.prompt.render(screen, label,
                      ctx.map_screen.get_screen_rect_for_cell(
                          *cell, ctx.camera),
                      ctx.pulse, is_locked=locked,
                      clamp_to=ctx.map_screen.get_viewport_rect(screen))

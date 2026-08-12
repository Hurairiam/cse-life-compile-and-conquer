"""
tests/test_bed_popup.py
Task 7 — the bed's three choices, the gate, and the floor.

The floor is the part worth testing hardest: it is the rule that stops a
player draining away days they still need to sit an exam, which is a
soft-locked run rather than a visible bug.

Headless. Nothing is written to saves/.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame                                            # noqa: E402
import pytest                                            # noqa: E402

from engine import day_drain, exam_days, save_bridge     # noqa: E402
from engine.app_context import AppContext                # noqa: E402
from engine.save_manager import AUTOSAVE_SLOT_ID, SaveManager  # noqa: E402
from engine.screen_manager import ScreenState            # noqa: E402
from engine.states import end_semester                   # noqa: E402
from ui.bed_popup import (MODE_MENU, MODE_NUMBER,        # noqa: E402
                          RESULT_ADVANCE, RESULT_CANCEL, RESULT_DRAIN,
                          BedPopup)

pygame.init()
pygame.display.set_mode((1280, 720))

STANDARD = exam_days.STANDARD_DAY_COST      # 14


def register(ctx, count=3):
    """Put `count` real courses in front of the player this term."""
    from academic.course_catalog import get_course_by_code
    codes = [c.get_course_code() for c in ctx.full_catalog][:count]
    for code in codes:
        course = get_course_by_code(ctx.full_catalog, code)
        if course is not None:
            ctx.semester().register_course(course)
    return codes


@pytest.fixture
def ctx():
    """
    A started run whose saves go to a throwaway directory.

    The temp SaveManager matters from Task 9 onwards: advancing a
    semester now writes the autosave, and saves/autosave.json is a real
    file in this repo.
    """
    folder = tempfile.mkdtemp(prefix="cse_life_bed_")
    context = AppContext()
    context.saves = SaveManager(folder)
    save_bridge.new_game(context)
    register(context, 3)
    context.exam = {"course_index": 0, "tier_index": 0,
                    "answers": {}, "message": None}
    try:
        yield context
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def key(code):
    return pygame.event.Event(pygame.KEYDOWN, {"key": code, "unicode": ""})


def typed(char):
    return pygame.event.Event(pygame.KEYDOWN,
                              {"key": ord(char), "unicode": char})


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                              {"button": 1, "pos": pos})


def landed_on(context):
    context.screen_mgr.apply_pending_transition()
    return context.screen_mgr.get_current_state()


def option_pos(context, index):
    """
    Where to click for option `index`.

    Read off a throwaway BedPopup rather than the state's own: the
    geometry is derived purely from the screen size in __init__, so a
    second card of the same size lays out identically. That keeps the
    state's popup module-private, which is how every other state in
    engine/states/ keeps its widget.
    """
    return BedPopup(context.screen_w,
                    context.screen_h).get_option_rects()[index].center


# ── the number the gate and the floor share ────────────────────

def test_the_gate_and_the_floor_read_the_same_value(ctx):
    """
    The whole point of engine/exam_days.py: one number, two uses.

    While an exam is owed, advance is shut AND the floor reserves days.
    When the last one is sat, both change at once.
    """
    assert exam_days.remaining_exams(ctx) == 3
    assert exam_days.days_needed(ctx) == 3 * STANDARD
    assert not exam_days.can_advance(ctx)
    assert exam_days.drainable(ctx) == 80 - 3 * STANDARD

    ctx.exam["course_index"] = 3
    assert exam_days.days_needed(ctx) == 0, "the reserve outlived the exams"
    assert exam_days.can_advance(ctx), "the gate stayed shut"
    assert exam_days.drainable(ctx) == 80


def test_the_floor_never_goes_negative(ctx):
    """A term already below its reserve offers nothing, not a negative."""
    ctx.semester().deduct_time(75)          # 5 left, 42 owed
    assert exam_days.days_needed(ctx) > day_drain.passable(ctx)
    assert exam_days.drainable(ctx) == 0
    assert not exam_days.can_drain(ctx)


# ── the widget ─────────────────────────────────────────────────

def popup(can_advance=False, ceiling=38, exams_left=3):
    card = BedPopup(1280, 720)
    card.open_bed(can_advance=can_advance, ceiling=ceiling,
                  exams_left=exams_left)
    return card


def test_advance_is_unavailable_while_exams_are_owed():
    card = popup(can_advance=False)
    assert not card.is_option_enabled(0)
    card.handle_event(click(card.get_option_rects()[0].center))
    assert card.get_choice() is None, "a greyed option was chosen"
    assert card.is_open(), "clicking a greyed option closed the card"


def test_advance_works_once_the_exams_are_done():
    card = popup(can_advance=True)
    assert card.is_option_enabled(0)
    card.handle_event(click(card.get_option_rects()[0].center))
    assert card.take_choice() == RESULT_ADVANCE
    assert not card.is_open()


def test_cancel_closes_and_decides_nothing_else():
    card = popup()
    card.handle_event(click(card.get_option_rects()[2].center))
    assert card.take_choice() == RESULT_CANCEL
    assert not card.is_open()


def test_escape_cancels():
    card = popup()
    card.handle_event(key(pygame.K_ESCAPE))
    assert card.take_choice() == RESULT_CANCEL


def test_drain_opens_the_number_field():
    card = popup()
    assert card.get_mode() == MODE_MENU
    card.handle_event(click(card.get_option_rects()[1].center))
    assert card.get_mode() == MODE_NUMBER
    assert card.get_choice() is None, "drain decided before a number"
    assert card.is_open()


def test_drain_is_unavailable_when_there_is_no_room():
    card = popup(ceiling=0)
    assert not card.is_option_enabled(1)
    card.handle_event(click(card.get_option_rects()[1].center))
    assert card.get_mode() == MODE_MENU, "opened a field with no legal value"


# ── the number field ───────────────────────────────────────────

def numbering(ceiling=38):
    card = popup(ceiling=ceiling)
    card.handle_event(click(card.get_option_rects()[1].center))
    return card


def test_only_digits_reach_the_field():
    """Negatives, decimals and letters are unrepresentable by design."""
    card = numbering()
    for char in "-+.,abcZ/":
        card.handle_event(typed(char))
    assert card.get_typed() == "", "a non-digit reached the field: %r" % (
        card.get_typed(),)
    card.handle_event(typed("2"))
    card.handle_event(typed("5"))
    assert card.get_typed() == "25"


def test_backspace_edits():
    card = numbering()
    for char in "123":
        card.handle_event(typed(char))
    card.handle_event(key(pygame.K_BACKSPACE))
    assert card.get_typed() == "12"


def test_a_legal_number_is_accepted():
    card = numbering(ceiling=38)
    for char in "12":
        card.handle_event(typed(char))
    card.handle_event(key(pygame.K_RETURN))
    assert card.take_choice() == RESULT_DRAIN
    assert card.get_days() == 12


def test_zero_is_refused():
    card = numbering()
    card.handle_event(typed("0"))
    card.handle_event(key(pygame.K_RETURN))
    assert card.get_choice() is None, "zero days was accepted"
    assert card.is_open(), "the card closed on a refused number"


def test_an_empty_field_is_refused():
    card = numbering()
    card.handle_event(key(pygame.K_RETURN))
    assert card.get_choice() is None
    assert card.is_open()


def test_over_the_ceiling_is_refused_not_clamped():
    """
    Refused, deliberately: silently turning a typed 60 into 38 spends
    days the player did not ask for.
    """
    card = numbering(ceiling=38)
    for char in "60":
        card.handle_event(typed(char))
    card.handle_event(key(pygame.K_RETURN))
    assert card.get_choice() is None, "a number past the floor got through"
    assert card.get_days() == 0
    assert card.get_typed() == "60", "the field was quietly rewritten"


def test_the_ceiling_itself_is_allowed():
    card = numbering(ceiling=38)
    for char in "38":
        card.handle_event(typed(char))
    card.handle_event(key(pygame.K_RETURN))
    assert card.take_choice() == RESULT_DRAIN and card.get_days() == 38


def test_back_returns_to_the_menu_keeping_the_card_up():
    card = numbering()
    card.handle_event(typed("5"))
    card.handle_event(key(pygame.K_ESCAPE))
    assert card.get_mode() == MODE_MENU
    assert card.is_open(), "ESC in the field closed the whole card"
    assert card.get_choice() is None


# ── the state, end to end ──────────────────────────────────────

def test_the_bed_asks_even_when_every_exam_is_done(ctx):
    """
    Never an instant skip. With the exams behind them the player could
    advance, but entering the state must not do it for them.
    """
    ctx.exam["course_index"] = 3
    assert exam_days.can_advance(ctx)
    semester_before = ctx.semester().get_semester_number()

    end_semester.enter(ctx)
    end_semester.update(ctx, 0.016)
    assert ctx.semester().get_semester_number() == semester_before, \
        "the bed rolled the term over without asking"

    # ...and the card is genuinely up: ESC cancels it rather than
    # falling through to the map untouched.
    end_semester.handle_events(ctx, [key(pygame.K_ESCAPE)])
    end_semester.update(ctx, 0.016)
    assert ctx.semester().get_semester_number() == semester_before
    assert landed_on(ctx) is ScreenState.EXPLORATION


def test_advance_through_the_state_closes_the_term(ctx):
    ctx.exam["course_index"] = 3
    end_semester.enter(ctx)
    end_semester.handle_events(ctx, [click(option_pos(ctx, 0))])
    end_semester.update(ctx, 0.016)
    assert ctx.semester().get_semester_number() == 2, \
        "ADVANCE did not close the term"


def test_advance_is_refused_while_exams_are_owed(ctx):
    """The gate, through the state rather than the widget."""
    assert not exam_days.can_advance(ctx)
    semester_before = ctx.semester().get_semester_number()
    end_semester.enter(ctx)
    end_semester.handle_events(ctx, [click(option_pos(ctx, 0))])
    end_semester.update(ctx, 0.016)
    assert ctx.semester().get_semester_number() == semester_before, \
        "a blocked ADVANCE still closed the term"


def test_draining_through_the_state_spends_exactly_that_many(ctx):
    end_semester.enter(ctx)
    before = ctx.semester().get_time_pool_days()
    ceiling = exam_days.drainable(ctx)
    assert ceiling > 10

    end_semester.handle_events(ctx, [click(option_pos(ctx, 1))])
    for char in "10":
        end_semester.handle_events(ctx, [typed(char)])
    end_semester.handle_events(ctx, [key(pygame.K_RETURN)])
    end_semester.update(ctx, 0.016)

    assert ctx.semester().get_time_pool_days() == before - 10
    assert landed_on(ctx) is ScreenState.EXPLORATION


def test_the_floor_is_enforced_through_the_state(ctx):
    """A number past the floor changes nothing at all."""
    ctx.semester().deduct_time(30)              # 50 left, 42 reserved
    ctx.player().deduct_time_pool_days(30)
    assert exam_days.drainable(ctx) == 8

    end_semester.enter(ctx)
    before = ctx.semester().get_time_pool_days()
    end_semester.handle_events(ctx, [click(option_pos(ctx, 1))])
    for char in "40":
        end_semester.handle_events(ctx, [typed(char)])
    end_semester.handle_events(ctx, [key(pygame.K_RETURN)])
    end_semester.update(ctx, 0.016)

    assert ctx.semester().get_time_pool_days() == before, \
        "days went below the exam floor"


def test_cancel_through_the_state_changes_nothing(ctx):
    end_semester.enter(ctx)
    before = ctx.semester().get_time_pool_days()
    end_semester.handle_events(ctx, [key(pygame.K_ESCAPE)])
    end_semester.update(ctx, 0.016)
    assert ctx.semester().get_time_pool_days() == before
    assert landed_on(ctx) is ScreenState.EXPLORATION


# ── Task 9: the autosave that hangs off ADVANCE ────────────────

def advance(ctx):
    """Sit every exam, then take ADVANCE from the bed."""
    ctx.exam["course_index"] = 3
    end_semester.enter(ctx)
    end_semester.handle_events(ctx, [click(option_pos(ctx, 0))])
    end_semester.update(ctx, 0.016)


def autosave_slot(ctx):
    for slot in ctx.saves.list_slots():
        if slot.get_slot_id() == AUTOSAVE_SLOT_ID:
            return slot
    return None


def test_advancing_writes_the_autosave_with_no_prompt(ctx):
    assert autosave_slot(ctx).is_empty(), "the run started with an autosave"
    advance(ctx)
    assert not autosave_slot(ctx).is_empty(), "ADVANCE wrote no autosave"
    assert not ctx.message_popup.is_open(), "the autosave asked something"


def test_the_autosave_holds_the_post_transition_semester(ctx):
    """
    The ordering Task 9 asks to confirm rather than assume: the file
    must be the NEW term, not a half-transitioned one.
    """
    assert ctx.semester().get_semester_number() == 1
    advance(ctx)
    assert ctx.semester().get_semester_number() == 2

    payload = ctx.saves.load(AUTOSAVE_SLOT_ID)
    assert payload is not None, "the autosave did not read back"
    assert payload["player"]["current_semester"] == 2, \
        "the autosave caught the term mid-transition"


def test_the_autosave_uses_the_same_routine_as_save_game(ctx):
    """G6: restoring it must rebuild the run like any other slot."""
    advance(ctx)
    payload = ctx.saves.load(AUTOSAVE_SLOT_ID)
    fresh = AppContext()
    assert save_bridge.restore(fresh, payload), \
        "the autosave is not a normal save file"
    assert fresh.semester().get_semester_number() == 2


def test_draining_does_not_autosave(ctx):
    """Task 9's trigger is ADVANCE, not any use of the bed."""
    end_semester.enter(ctx)
    end_semester.handle_events(ctx, [click(option_pos(ctx, 1))])
    for char in "10":
        end_semester.handle_events(ctx, [typed(char)])
    end_semester.handle_events(ctx, [key(pygame.K_RETURN)])
    end_semester.update(ctx, 0.016)
    assert autosave_slot(ctx).is_empty(), "draining wrote an autosave"


def test_cancel_does_not_autosave(ctx):
    end_semester.enter(ctx)
    end_semester.handle_events(ctx, [key(pygame.K_ESCAPE)])
    end_semester.update(ctx, 0.016)
    assert autosave_slot(ctx).is_empty(), "cancel wrote an autosave"


def test_a_frozen_run_does_not_overwrite_the_autosave(ctx):
    """
    The guard that matters. close_semester() returns early to ENDGAME
    without advancing anything when the run is over; autosaving there
    would replace a good file with a finished run.
    """
    ctx.saves.autosave(save_bridge.capture(ctx))
    keep = ctx.saves.load(AUTOSAVE_SLOT_ID)
    assert keep["player"]["current_semester"] == 1

    ctx.session.freeze_session()
    assert ctx.session.get_is_frozen()

    advance(ctx)
    assert ctx.semester().get_semester_number() == 1, \
        "a frozen run advanced the semester after all"
    after = ctx.saves.load(AUTOSAVE_SLOT_ID)
    assert after["player"]["current_semester"] == 1, \
        "a frozen run overwrote the autosave"

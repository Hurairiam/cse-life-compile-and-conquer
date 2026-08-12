"""
tests/test_lecture_skip.py
Task 1 — skipping a lecture lands exactly where reading it lands.

The acceptance criterion is PARITY, so the important tests here do the
same thing twice — once by paging through every sheet, once by pressing
SKIP — and compare the resulting state. Anything a skip bypassed would
show up as a difference.

Headless. Reuses tests/test_lecture_reader.py's harness rather than
building a second one: it already wires a real GameSession, GameClock,
Semester, Player and QuestStateMachine, which is what makes these
assertions about the pipeline and not about a mock of it.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame                                          # noqa: E402

from content.side_quest_definitions import get_skill_id  # noqa: E402
from engine import lecture_reader, skill_completion    # noqa: E402
from engine.quest_state import STATE_COMPLETED         # noqa: E402
from engine.screen_manager import ScreenState          # noqa: E402
from engine.states import side_quest_lecture           # noqa: E402
from ui import skip_button                             # noqa: E402

from tests.test_lecture_reader import (landed_on,        # noqa: E402
                                       opened, page_to_the_end, quest_of,
                                       unlocked)

pygame.init()
pygame.display.set_mode((1, 1))

SEMESTER = 2
SCREEN_W = 1280


def reading(semester: int = SEMESTER):
    """
    An open sitting on the reader screen, with a screen width.

    test_lecture_reader.py's harness predates this button and carries no
    `screen_w`, which the real AppContext supplies. Set here rather than
    added to the shared harness so that file stays owned by its own
    phase.
    """
    ctx = opened(semester)
    ctx.screen_w = SCREEN_W
    return ctx


def click_skip(ctx):
    """A left click in the middle of the SKIP button."""
    rect = skip_button.get_rect(ctx.screen_w)
    side_quest_lecture.handle_events(ctx, [pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": rect.center})])


def press_tab(ctx):
    side_quest_lecture.handle_events(ctx, [pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_TAB})])


def snapshot(ctx, quest_id):
    """Everything a skip could plausibly have got wrong."""
    return {
        "quest_state": ctx.quest_states.get_state(quest_id),
        "completed": skill_completion.is_completed(
            ctx, get_skill_id(quest_id)),
        "days": ctx.semester().get_time_pool_days(),
        "level": ctx.player().get_skill_tree().get_skill_level(
            get_skill_id(quest_id)),
        "reader_open": lecture_reader.is_open(),
        "landed": landed_on(ctx),
        "popup_title": ctx.message_popup.get_title(),
    }


# ── the reader-level primitive ─────────────────────────────────

def test_skip_to_end_completes_the_quest():
    ctx = unlocked(SEMESTER)
    quest_id = quest_of(SEMESTER)
    lecture_reader.start(ctx, quest_id)
    assert lecture_reader.is_open()

    assert lecture_reader.skip_to_end(ctx) is True
    assert ctx.quest_states.get_state(quest_id) == STATE_COMPLETED
    assert skill_completion.is_completed(ctx, get_skill_id(quest_id))
    lecture_reader.end()


def test_skip_to_end_from_the_first_sheet_still_completes():
    """Not just a no-op that happened to be on the last sheet."""
    ctx = unlocked(SEMESTER)
    quest_id = quest_of(SEMESTER)
    lecture_reader.start(ctx, quest_id)
    assert lecture_reader.progress_label().startswith("SHEET 1")

    lecture_reader.skip_to_end(ctx)
    assert ctx.quest_states.get_state(quest_id) == STATE_COMPLETED
    lecture_reader.end()


def test_skip_to_end_on_nothing_is_false():
    ctx = unlocked(SEMESTER)
    lecture_reader.end()
    assert lecture_reader.skip_to_end(ctx) is False


def test_skip_does_not_refund_the_days():
    """The topic was paid for on open; skipping is not a refund."""
    ctx = unlocked(SEMESTER)
    quest_id = quest_of(SEMESTER)
    before = ctx.semester().get_time_pool_days()
    lecture_reader.start(ctx, quest_id)
    charged = ctx.semester().get_time_pool_days()
    assert charged < before

    lecture_reader.skip_to_end(ctx)
    assert ctx.semester().get_time_pool_days() == charged
    lecture_reader.end()


# ── parity: the acceptance criterion ───────────────────────────

def test_skipping_lands_on_the_same_state_as_reading():
    """
    THE test. Page through every sheet, snapshot; skip, snapshot;
    the two must be identical.
    """
    read_ctx = reading()
    quest_id = quest_of(SEMESTER)
    # SPACE all the way through. A sheet is several presses, not one:
    # Phase 11.5 split each paragraph into dialog-box-sized lines.
    presses = page_to_the_end(read_ctx)
    read_state = snapshot(read_ctx, quest_id)
    lecture_reader.end()

    skip_ctx = reading()
    click_skip(skip_ctx)
    skip_state = snapshot(skip_ctx, quest_id)
    lecture_reader.end()

    assert presses > 1, "the read-through was not actually a read-through"
    assert read_state["quest_state"] == STATE_COMPLETED, \
        "the read-through never completed"
    assert skip_state == read_state, (
        "skipping diverged from reading:\n  read %r\n  skip %r"
        % (read_state, skip_state))


def test_tab_and_the_button_do_the_same_thing():
    quest_id = quest_of(SEMESTER)

    clicked = reading()
    click_skip(clicked)
    by_click = snapshot(clicked, quest_id)
    lecture_reader.end()

    tabbed = reading()
    press_tab(tabbed)
    by_tab = snapshot(tabbed, quest_id)
    lecture_reader.end()

    assert by_click == by_tab


def test_skip_shows_the_completion_notice_and_leaves():
    ctx = reading()
    click_skip(ctx)
    assert ctx.message_popup.get_title() == "TOPIC COMPLETE"
    assert landed_on(ctx) is ScreenState.EXPLORATION
    lecture_reader.end()


def test_a_click_outside_the_button_still_turns_the_page():
    """The button must not swallow the screen's ordinary click."""
    ctx = reading()
    quest_id = quest_of(SEMESTER)
    side_quest_lecture.handle_events(ctx, [pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (40, 600)})])
    assert lecture_reader.is_open(), "an ordinary click ended the lecture"
    assert ctx.quest_states.get_state(quest_id) != STATE_COMPLETED
    lecture_reader.end()


# ── the button's own geometry ──────────────────────────────────

def test_the_button_clears_the_hud():
    """Task 1: top right, below the HUD, not overlapping it."""
    from ui.hud import STRIP_HEIGHT
    rect = skip_button.get_rect(1280)
    assert rect.top >= STRIP_HEIGHT, "the button sits under the HUD strip"
    assert rect.right <= 1280, "the button runs off the screen"
    assert rect.right > 1280 // 2, "the button is not on the right"
    assert rect.top < 1280 // 2, "the button is not near the top"


def test_the_button_follows_the_screen_width():
    narrow = skip_button.get_rect(1024)
    wide = skip_button.get_rect(1600)
    assert wide.right > narrow.right
    assert wide.top == narrow.top


def test_hit_is_tested_against_the_drawn_rect():
    rect = skip_button.get_rect(1280)
    assert skip_button.hit(1280, rect.center)
    assert not skip_button.hit(1280, (rect.left - 5, rect.centery))
    assert not skip_button.hit(1280, (rect.centerx, rect.bottom + 5))
    assert not skip_button.hit(1280, None)

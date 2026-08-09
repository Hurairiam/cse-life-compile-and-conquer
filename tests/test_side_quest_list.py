"""
tests/test_side_quest_list.py
CSE Life: Compile & Conquer
Phase 14 — coverage for the player's room PC and its side quest list

    python -m tests.test_side_quest_list

Headless and self-contained: SDL_VIDEODRIVER=dummy, no window anybody
can see, and nothing at all is written to disk — this phase adds no save
key, so there is not even a temporary directory to clean up.

WHAT IS ACTUALLY DRIVEN. The visibility and day rules are checked
against engine/side_quest_list.py with a stub context, because those are
pure functions and a real AppContext would only make them slower. The
last section then drives the REAL engine/states/side_quests.py with a
REAL AppContext, the real popups and real pygame KEYDOWN events, because
"blocked with a clear reason and no state change" is a claim about the
screen, not about a helper.

    the visibility rule                 test_visible_*, test_hidden_*
    a declined run is indistinguishable test_a_declined_run_*
    what a row shows                    test_row_*
    the day block                       test_day_*
    confirming                          test_confirm_*
    the PC itself                       test_pc_*
    through the real screen             test_screen_*
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame                                          # noqa: E402

from content.level_registry import (                   # noqa: E402
    get_menu_display_name, get_skill_display_name)
from content.level_schema import read_level, level_path  # noqa: E402
from content.side_quest_definitions import (           # noqa: E402
    QUEST_IDS,
    get_day_cost,
    get_lecture_sheets,
    get_skill_id,
)
from engine import side_quest_list                     # noqa: E402
from engine.menu_prop import resolve_state             # noqa: E402
from engine.quest_state import (                       # noqa: E402
    STATE_COMPLETED,
    STATE_DECLINED,
    STATE_MISSED,
    STATE_UNLOCKED,
    STATE_UNOFFERED,
    QuestStateMachine,
)
from engine.screen_manager import ScreenState          # noqa: E402
from ui.popup import (                                 # noqa: E402
    MAX_BODY_LINES, RESULT_CANCEL, RESULT_CONFIRM)
from ui.side_quest_screen import (                     # noqa: E402
    COMPLETE_TEXT, EMPTY_TEXT, format_quest_row)

MENU_ID = "side_quests"
PC_UIDS = ("prop_0023", "prop_0024")
SEMESTERS = tuple(range(1, 13))
DAY_COST = 2                    # what all twelve cost today


# ── a context, without a window ────────────────────────────────

class _Semester:
    """The one method engine/side_quest_list.py::days_left() reads."""

    def __init__(self, days: int) -> None:
        self.__days = int(days)

    def get_time_pool_days(self) -> int:
        return self.__days


class _Ctx:
    """A stub context: a quest machine and a day counter, nothing else.

    Deliberately not an AppContext for the pure-logic cases — those need
    no window, no fonts and no audio device, and a stub makes it obvious
    that the rules below read exactly two things."""

    def __init__(self, machine: QuestStateMachine, days: int = 80) -> None:
        self.quest_states = machine
        self.__semester = _Semester(days)

    def semester(self):
        return self.__semester


def machine_with(plan: dict) -> QuestStateMachine:
    """
    A machine driven into a hand-made mix through the PUBLIC API only.

    `plan` maps a semester to one of the five state names. Nothing here
    reaches into the private dict, so a test can never set up a spread
    the game itself could not reach — an "unlocked" quest really was
    accepted, a "missed" one really did have its term expire.
    """
    machine = QuestStateMachine()
    for semester, wanted in sorted(plan.items()):
        quest_id = machine.get_quest_for_semester(semester)
        if wanted == STATE_UNLOCKED:
            machine.accept(quest_id)
        elif wanted == STATE_COMPLETED:
            machine.accept(quest_id)
            machine.mark_completed(quest_id)
        elif wanted == STATE_DECLINED:
            machine.decline(quest_id)
        elif wanted == STATE_MISSED:
            machine.expire_unoffered_for_semester(semester)
        elif wanted != STATE_UNOFFERED:
            raise AssertionError("no such state: %r" % (wanted,))
    return machine


# The mix used by most of the cases below: every one of the five states
# is represented, and they are interleaved rather than blocked, so an
# ordering bug cannot hide behind a tidy run.
MIXED_PLAN = {
    1: STATE_COMPLETED,
    2: STATE_UNLOCKED,
    3: STATE_DECLINED,
    4: STATE_COMPLETED,
    5: STATE_MISSED,
    6: STATE_UNLOCKED,
    7: STATE_DECLINED,
    8: STATE_UNLOCKED,
    9: STATE_MISSED,
    # 10, 11, 12 left Unoffered — the term has not come round yet.
}


def mixed(days: int = 80) -> _Ctx:
    """A context in the mixed run above."""
    return _Ctx(machine_with(MIXED_PLAN), days)


def quest_of(semester: int) -> str:
    """The quest id a semester offers."""
    return QuestStateMachine().get_quest_for_semester(semester)


def card_rows(ctx) -> list:
    """The cells the table would actually be handed, for one context."""
    return [format_quest_row(row["title"], row["day_cost"], row["sheets"],
                             row["completed"])
            for row in side_quest_list.entries(ctx)]


# ── the visibility rule ────────────────────────────────────────

def test_visible_rows_are_exactly_unlocked_and_completed():
    """The whole acceptance criterion, on a hand-made mix: the list
    shows exactly the right rows and nothing else."""
    ctx = mixed()
    shown = [row["quest_id"] for row in side_quest_list.entries(ctx)]
    expected = [quest_of(s) for s in (1, 2, 4, 6, 8)]
    assert shown == expected, shown
    assert len(shown) == 5


def test_visible_rows_carry_the_completed_flag_only_for_completed():
    """Completed rows are marked; unlocked rows are not."""
    by_id = {row["quest_id"]: row for row in side_quest_list.entries(mixed())}
    for semester in (1, 4):
        assert by_id[quest_of(semester)]["completed"] is True
    for semester in (2, 6, 8):
        assert by_id[quest_of(semester)]["completed"] is False


def test_hidden_unoffered_never_appears():
    """A quest whose term has not come round is not on the card."""
    ctx = mixed()
    shown = [row["quest_id"] for row in side_quest_list.entries(ctx)]
    for semester in (10, 11, 12):
        assert quest_of(semester) not in shown


def test_hidden_declined_never_appears():
    """The player must never see evidence of a quest they refused."""
    ctx = mixed()
    shown = [row["quest_id"] for row in side_quest_list.entries(ctx)]
    for semester in (3, 7):
        assert quest_of(semester) not in shown


def test_hidden_missed_never_appears():
    """Nor of one they slept through."""
    ctx = mixed()
    shown = [row["quest_id"] for row in side_quest_list.entries(ctx)]
    for semester in (5, 9):
        assert quest_of(semester) not in shown


def test_hidden_states_are_never_listed_for_any_quest():
    """Exhaustive: all five states against all twelve quests, one at a
    time, so no single quest can be visible for the wrong reason."""
    visible = (STATE_UNLOCKED, STATE_COMPLETED)
    for semester in SEMESTERS:
        for state in (STATE_UNOFFERED, STATE_DECLINED, STATE_MISSED,
                      STATE_UNLOCKED, STATE_COMPLETED):
            ctx = _Ctx(machine_with({semester: state}))
            shown = [row["quest_id"]
                     for row in side_quest_list.entries(ctx)]
            if state in visible:
                assert shown == [quest_of(semester)], (semester, state, shown)
            else:
                assert shown == [], (semester, state, shown)


def test_visible_a_fresh_run_lists_nothing():
    """Semester 1, nobody talked to: the PC has nothing on it."""
    ctx = _Ctx(QuestStateMachine())
    assert side_quest_list.entries(ctx) == []
    assert side_quest_list.listed_ids(ctx) == []


def test_visible_all_twelve_completed_lists_all_twelve():
    """The other end of the range: twelve rows, all marked, none
    startable, and still no counter anywhere."""
    ctx = _Ctx(machine_with({s: STATE_COMPLETED for s in SEMESTERS}))
    rows = side_quest_list.entries(ctx)
    assert len(rows) == 12
    assert all(row["completed"] for row in rows)
    assert not any(side_quest_list.is_startable(ctx, row["quest_id"])
                   for row in rows)


def test_visible_rows_are_in_semester_order():
    """The order the quests were offered in, which is also QUEST_IDS'."""
    ctx = _Ctx(machine_with({s: STATE_UNLOCKED for s in SEMESTERS}))
    assert side_quest_list.listed_ids(ctx) == list(QUEST_IDS)


def test_a_declined_run_is_indistinguishable_from_a_fresh_one():
    """
    The strongest form of the rule, and the reason it exists.

    A player who refused every single offer must see exactly what a
    player who has never been offered anything sees — same rows, same
    cells, same empty message. Anything that differs is the leak the
    brief is written to prevent.
    """
    refused = _Ctx(machine_with({s: STATE_DECLINED for s in SEMESTERS}))
    slept = _Ctx(machine_with({s: STATE_MISSED for s in SEMESTERS}))
    fresh = _Ctx(QuestStateMachine())
    assert card_rows(refused) == card_rows(fresh) == card_rows(slept) == []


def test_a_declined_quest_is_invisible_beside_an_accepted_one():
    """Two runs that differ only in a refusal produce the same card."""
    took_one = _Ctx(machine_with({1: STATE_UNLOCKED}))
    took_one_refused_one = _Ctx(machine_with({1: STATE_UNLOCKED,
                                              2: STATE_DECLINED}))
    assert card_rows(took_one) == card_rows(took_one_refused_one)


def test_hidden_quests_cannot_be_reached_through_any_accessor():
    """No public function in the module will describe a hidden quest as
    listed, startable, or anything but refused."""
    ctx = mixed()
    for semester in (3, 5, 7, 10):
        quest_id = quest_of(semester)
        assert quest_id not in side_quest_list.listed_ids(ctx)
        assert side_quest_list.is_startable(ctx, quest_id) is False
        assert side_quest_list.refusal(ctx, quest_id) is not None


# ── what one row shows ─────────────────────────────────────────

def test_row_shows_skill_name_day_cost_and_sheet_count():
    """Each Unlocked row shows exactly the three facts the brief asks
    for, read back against the definitions table."""
    ctx = _Ctx(machine_with({s: STATE_UNLOCKED for s in SEMESTERS}))
    for row in side_quest_list.entries(ctx):
        quest_id = row["quest_id"]
        assert row["title"] == get_skill_display_name(get_skill_id(quest_id))
        assert row["title"]                     # never blank
        assert row["day_cost"] == get_day_cost(quest_id) == DAY_COST
        assert row["sheets"] == len(get_lecture_sheets(quest_id)) == 3


def test_row_cells_match_what_the_table_draws():
    """format_quest_row() puts those three facts in the four cells, and
    marks a finished topic in the last one."""
    ctx = mixed()
    rows = side_quest_list.entries(ctx)
    cells = card_rows(ctx)
    for row, cell in zip(rows, cells):
        assert cell[0] == row["title"]
        assert cell[2] == str(row["sheets"])
        if row["completed"]:
            assert cell[1] == "-"               # never charged again
            assert cell[3] == COMPLETE_TEXT
        else:
            assert cell[1] == str(row["day_cost"])
            assert cell[3] == ""


def test_row_a_completed_topic_is_marked_and_not_selectable():
    """Shown, marked complete, and refused with a reason if picked."""
    ctx = _Ctx(machine_with({1: STATE_COMPLETED}))
    quest_id = quest_of(1)
    assert side_quest_list.entries(ctx)[0]["completed"] is True
    assert side_quest_list.is_startable(ctx, quest_id) is False
    title, lines = side_quest_list.refusal(ctx, quest_id)
    assert title == "ALREADY READ"
    assert lines and len(lines) <= MAX_BODY_LINES


def test_row_no_cell_ever_names_a_hidden_quest():
    """Nothing drawn on the card carries a hidden quest's id or its
    skill name — not in a cell, not in the empty-list message."""
    ctx = mixed()
    drawn = " ".join(cell for row in card_rows(ctx) for cell in row)
    drawn += " " + EMPTY_TEXT
    for semester in (3, 5, 7, 10, 11, 12):
        quest_id = quest_of(semester)
        assert quest_id not in drawn
        assert get_skill_display_name(get_skill_id(quest_id)) not in drawn


# ── the day rule ───────────────────────────────────────────────

def test_day_enough_days_allows_confirm():
    """Remaining days above the cost: startable, no refusal."""
    ctx = _Ctx(machine_with({1: STATE_UNLOCKED}), days=80)
    assert side_quest_list.is_startable(ctx, quest_of(1)) is True
    assert side_quest_list.refusal(ctx, quest_of(1)) is None


def test_day_exactly_enough_days_allows_confirm():
    """The boundary the brief spells out: remaining >= cost allows."""
    ctx = _Ctx(machine_with({1: STATE_UNLOCKED}), days=DAY_COST)
    assert side_quest_list.is_startable(ctx, quest_of(1)) is True


def test_day_one_short_blocks():
    """remaining < cost blocks, at the closest possible margin."""
    ctx = _Ctx(machine_with({1: STATE_UNLOCKED}), days=DAY_COST - 1)
    assert side_quest_list.is_startable(ctx, quest_of(1)) is False
    assert side_quest_list.refusal(ctx, quest_of(1))[0] == "NOT ENOUGH DAYS"


def test_day_zero_days_blocks():
    """A term with nothing left in it starts nothing."""
    ctx = _Ctx(machine_with({1: STATE_UNLOCKED}), days=0)
    assert side_quest_list.is_startable(ctx, quest_of(1)) is False


def test_day_the_block_shows_why_with_both_numbers():
    """'Show why' means the two figures, not just a refusal."""
    ctx = _Ctx(machine_with({1: STATE_UNLOCKED}), days=1)
    title, lines = side_quest_list.refusal(ctx, quest_of(1))
    assert title == "NOT ENOUGH DAYS"
    body = " ".join(lines)
    assert "2 days" in body                     # what it costs
    assert "1 day" in body and "1 days" not in body   # what is left
    assert len(lines) <= MAX_BODY_LINES


def test_day_the_block_is_still_a_visible_row():
    """Unaffordable is not hidden — the quest is Unlocked, so it is on
    the card. Only starting it is refused."""
    ctx = _Ctx(machine_with({1: STATE_UNLOCKED}), days=0)
    assert [row["quest_id"] for row in side_quest_list.entries(ctx)] \
        == [quest_of(1)]
    assert side_quest_list.entries(ctx)[0]["affordable"] is False


def test_day_the_block_changes_nothing():
    """No deduction, no state move, nothing recorded — asserted over the
    whole machine and the day counter, not just the one quest."""
    ctx = mixed(days=1)
    before = ctx.quest_states.get_all_states()
    before_days = side_quest_list.days_left(ctx)
    side_quest_list.reset()
    for row in side_quest_list.entries(ctx):
        assert side_quest_list.is_startable(ctx, row["quest_id"]) is False
        side_quest_list.refusal(ctx, row["quest_id"])
    assert ctx.quest_states.get_all_states() == before
    assert side_quest_list.days_left(ctx) == before_days
    assert side_quest_list.get_last_confirmed() is None


def test_day_there_is_no_override():
    """Every listed quest, at every day count below the cost, refuses.
    There is no argument, flag or second call that says yes."""
    for days in range(0, DAY_COST):
        ctx = _Ctx(machine_with({s: STATE_UNLOCKED for s in SEMESTERS}),
                   days=days)
        for row in side_quest_list.entries(ctx):
            assert side_quest_list.is_startable(ctx, row["quest_id"]) is False


def test_day_days_left_reads_the_semester_counter():
    """The number quoted is the one the HUD shows — the semester's pool,
    not the player's separate copy (recon §7)."""
    assert side_quest_list.days_left(_Ctx(QuestStateMachine(), 37)) == 37
    assert side_quest_list.days_left(object()) == 0


def test_day_the_fifteen_day_firewall_is_not_consulted():
    """Phase 17 owns that threshold. A term at 16 days and a term at 3
    days differ only by the day_cost rule, so there is exactly one place
    for Phase 17 to land."""
    for days in (16, 3):
        ctx = _Ctx(machine_with({1: STATE_UNLOCKED}), days=days)
        assert side_quest_list.is_startable(ctx, quest_of(1)) is True


# ── the confirmation step ──────────────────────────────────────

def test_confirmation_states_the_cost_and_the_one_sitting_warning():
    """Both things the brief requires of the confirmation, plus the
    topic it refers to."""
    ctx = _Ctx(machine_with({1: STATE_UNLOCKED}))
    title, lines = side_quest_list.confirmation(ctx, quest_of(1))
    body = " ".join(lines)
    assert "START" in title
    assert "2 days" in body
    assert "one sitting" in body
    assert get_skill_display_name(get_skill_id(quest_of(1))) in body


def test_confirmation_fits_the_popup():
    """ui/popup.py drops anything past three body lines, silently."""
    ctx = _Ctx(machine_with({s: STATE_UNLOCKED for s in SEMESTERS}))
    for row in side_quest_list.entries(ctx):
        _, lines = side_quest_list.confirmation(ctx, row["quest_id"])
        assert 0 < len(lines) <= MAX_BODY_LINES


def test_confirm_logs_the_quest_id():
    """The whole of what confirming does this phase."""
    side_quest_list.reset()
    assert side_quest_list.confirm("SQ_OOP") == "SQ_OOP"
    assert side_quest_list.get_last_confirmed() == "SQ_OOP"
    side_quest_list.reset()
    assert side_quest_list.get_last_confirmed() is None


def test_confirm_changes_no_state():
    """No lecture, no day deducted, no transition — Phases 15 and 17."""
    ctx = mixed()
    before = ctx.quest_states.get_all_states()
    before_days = side_quest_list.days_left(ctx)
    side_quest_list.confirm(quest_of(2))
    assert ctx.quest_states.get_all_states() == before
    assert side_quest_list.days_left(ctx) == before_days
    side_quest_list.reset()


def test_confirm_a_context_with_no_quest_machine_never_raises():
    """The editor, the harnesses and a half-built AppContext all land
    here: an empty list, not an exception."""
    for broken in (object(), _Ctx.__new__(_Ctx)):
        assert side_quest_list.listed_ids(broken) == []
        assert side_quest_list.entries(broken) == []
        assert side_quest_list.is_startable(broken, "SQ_OOP") is False


# ── the PC itself ──────────────────────────────────────────────

def test_pc_menu_id_routes_to_the_screen():
    """One appended MENU_REGISTRY row, one appended ScreenState member,
    and engine/menu_prop.py resolves the pair with no editor change."""
    assert resolve_state(MENU_ID) is ScreenState.SIDE_QUESTS
    assert get_menu_display_name(MENU_ID) == "Side Quests"


def test_pc_in_the_players_room_opens_the_list():
    """Both tiles of the desk that was already there, re-pointed."""
    level = read_level(level_path("player_room"))
    found = {}
    for prop in level.get_props():
        if prop.get_interaction_kind() == "menu":
            found[prop.get_uid()] = prop.get_menu_id()
    for uid in PC_UIDS:
        assert found.get(uid) == MENU_ID, found


def test_pc_no_second_computer_was_added():
    """The brief says extend the PC, not add another. Every interactable
    computer prop in the room is one of the two that were already
    there."""
    level = read_level(level_path("player_room"))
    computers = [prop.get_uid() for prop in level.get_props()
                 if prop.get_interactable()
                 and "computer" in prop.get_type_id()]
    assert sorted(computers) == sorted(PC_UIDS), computers


def test_pc_the_room_still_validates():
    """A level the game refuses to load is a level nobody can use."""
    from engine.level_loader import load_level
    level = load_level("player_room")
    assert level.get_level_id() == "player_room"


# ── through the real screen ────────────────────────────────────

__ctx = None


def context(semester: int = 2, days: int = 80, plan=None):
    """
    A real AppContext, restored into a hand-made run.

    One AppContext is built for the whole file and re-restored per case:
    building it opens an audio device and loads every font, and doing
    that a dozen times is slow for no extra coverage. restore() rebuilds
    the session, the clock and ctx.quest_states from a save payload,
    which is exactly the reset each case wants.
    """
    global __ctx
    from engine import save_bridge
    from engine.app_context import AppContext
    from engine.save_manager import build_state

    if __ctx is None:
        pygame.init()
        pygame.display.set_mode((1280, 720))
        __ctx = AppContext()
    states = machine_with(MIXED_PLAN if plan is None else plan).to_dict()
    save_bridge.restore(__ctx, build_state(current_semester=semester,
                                           time_pool_days=days,
                                           quest_states=states))
    __ctx.return_state = ScreenState.EXPLORATION
    __ctx.popup.close()
    __ctx.popup.take_result()
    __ctx.message_popup.close()
    __ctx.message_popup.take_result()
    # Park the router on this screen, so went_back() below is a real
    # question rather than an assertion about whatever the last case
    # left behind.
    __ctx.screen_mgr.transition_to(ScreenState.SIDE_QUESTS)
    return __ctx


def press(ctx, key) -> None:
    """One KEYDOWN through the real side quest state."""
    from engine.states import side_quests
    side_quests.handle_events(
        ctx, [pygame.event.Event(pygame.KEYDOWN, key=key)])


def answer(ctx, result) -> None:
    """Answer the open ConfirmPopup the way the router's modal would,
    then give the state its update() frame."""
    from engine.states import side_quests
    ctx.popup.set_result(result)
    side_quests.update(ctx, 0.016)


def went_back(ctx) -> bool:
    """True when the state asked to hand control back to the map."""
    ctx.screen_mgr.apply_pending_transition()
    return ctx.screen_mgr.get_current_state() is ScreenState.EXPLORATION


def test_screen_lists_exactly_the_right_rows():
    """The acceptance criterion, through the real state module and the
    real RowTable rather than through the helper."""
    from engine.states import side_quests
    ctx = context()
    side_quests.enter(ctx)
    side_quests.render(ctx, pygame.display.get_surface())

    # What the table itself was handed, read back off the widget.
    card = getattr(side_quests, "__ui")()
    assert card.get_row_count() == 5
    titles = [cells[0] for cells in card_rows(ctx)]
    assert titles == [get_skill_display_name(get_skill_id(quest_of(s)))
                      for s in (1, 2, 4, 6, 8)]
    assert [row["quest_id"] for row in side_quest_list.entries(ctx)] == \
        [quest_of(s) for s in (1, 2, 4, 6, 8)]


def test_screen_opens_on_a_startable_row():
    """A finished topic under the cursor would make ENTER a refusal, so
    the first row that can be started is the one selected."""
    from engine.states import side_quests
    ctx = context()
    side_quests.enter(ctx)
    side_quests.render(ctx, pygame.display.get_surface())
    # Semester 1 is Completed and sits first, so the cursor must have
    # moved past it to semester 2.
    press(ctx, pygame.K_RETURN)
    assert ctx.popup.is_open(), "the confirmation should have opened"
    assert "OOP" in " ".join(ctx.popup.get_lines()).upper()
    answer(ctx, RESULT_CANCEL)


def test_screen_blocks_a_quest_that_costs_more_than_the_term_has_left():
    """One day left, a two-day lecture: refused with a reason, no
    confirmation opened, and nothing anywhere has moved."""
    from engine.states import side_quests
    # One row, Unlocked, so the cursor cannot land on anything else and
    # the refusal under test is unambiguously the day one.
    ctx = context(days=1, plan={2: STATE_UNLOCKED})
    before = ctx.quest_states.get_all_states()
    before_days = ctx.semester().get_time_pool_days()
    side_quest_list.reset()

    side_quests.enter(ctx)
    press(ctx, pygame.K_RETURN)

    assert not ctx.popup.is_open(), "no confirmation may open on a block"
    assert ctx.message_popup.is_open(), "the block must say why"
    assert ctx.message_popup.get_title() == "NOT ENOUGH DAYS"
    body = " ".join(ctx.message_popup.get_lines())
    assert "2 days" in body and "1 day" in body
    assert ctx.quest_states.get_all_states() == before
    assert ctx.semester().get_time_pool_days() == before_days
    assert side_quest_list.get_last_confirmed() is None
    assert not went_back(ctx), "a refusal leaves the player on the card"


def test_screen_blocks_a_topic_already_read():
    """Completed rows are shown but cannot be started."""
    from engine.states import side_quests
    ctx = context(plan={1: STATE_COMPLETED})
    side_quests.enter(ctx)
    press(ctx, pygame.K_RETURN)
    assert not ctx.popup.is_open()
    assert ctx.message_popup.get_title() == "ALREADY READ"


def test_screen_confirming_logs_the_quest_and_closes():
    """CONFIRM logs the id, changes nothing else, and hands the player
    back to the map — the whole of this phase's last line."""
    from engine.states import side_quests
    ctx = context()
    before = ctx.quest_states.get_all_states()
    before_days = ctx.semester().get_time_pool_days()
    side_quest_list.reset()

    side_quests.enter(ctx)
    press(ctx, pygame.K_RETURN)
    assert ctx.popup.is_open()
    assert "ONE SITTING" in " ".join(ctx.popup.get_lines()).upper()
    answer(ctx, RESULT_CONFIRM)

    assert side_quest_list.get_last_confirmed() == quest_of(2)
    assert ctx.quest_states.get_all_states() == before, "no state moved"
    assert ctx.semester().get_time_pool_days() == before_days, "no day spent"
    assert went_back(ctx)
    side_quest_list.reset()


def test_screen_cancelling_the_confirmation_records_nothing():
    """CANCEL leaves the player on the list with nothing logged."""
    from engine.states import side_quests
    ctx = context()
    side_quest_list.reset()
    side_quests.enter(ctx)
    press(ctx, pygame.K_RETURN)
    answer(ctx, RESULT_CANCEL)
    assert side_quest_list.get_last_confirmed() is None
    assert not went_back(ctx)


def test_screen_escape_closes_the_card():
    """ESC is a way out of the list, unlike the confirmation."""
    from engine.states import side_quests
    ctx = context()
    side_quests.enter(ctx)
    press(ctx, pygame.K_ESCAPE)
    assert went_back(ctx)


def test_screen_an_empty_list_opens_and_draws():
    """A fresh run opens the PC to an empty card rather than a crash or
    a message that hints anything was ever there."""
    from engine.states import side_quests
    ctx = context(semester=1, plan={})
    side_quests.enter(ctx)
    side_quests.render(ctx, pygame.display.get_surface())
    press(ctx, pygame.K_RETURN)
    assert not ctx.popup.is_open()
    assert ctx.message_popup.get_title() == "NOTHING TO STUDY"
    assert "QUEST" not in EMPTY_TEXT.upper()


def test_screen_the_subtitle_counts_days_not_quests():
    """No 'n of 12' anywhere on the card."""
    from engine.states import side_quests
    ctx = context(days=37)
    side_quests.enter(ctx)
    subtitle = getattr(side_quests, "__subtitle")(ctx)
    assert "37" in subtitle
    assert "12" not in subtitle
    assert "OF" not in subtitle.replace("LEFT", "")


def test_screen_a_stale_confirmation_is_refused_rather_than_honoured():
    """
    The answer is re-checked before it is acted on.

    Nothing in the engine can drain the term while a modal is up — the
    router runs one state and the popup eats every event — but an answer
    that lands on a quest the rules no longer allow must refuse rather
    than be honoured. Forced here by hand.
    """
    from engine.states import side_quests
    ctx = context()
    side_quest_list.reset()
    side_quests.enter(ctx)
    press(ctx, pygame.K_RETURN)
    assert ctx.popup.is_open()
    ctx.semester().deduct_time(ctx.semester().get_time_pool_days())
    answer(ctx, RESULT_CONFIRM)
    assert side_quest_list.get_last_confirmed() is None
    assert ctx.message_popup.get_title() == "NOT ENOUGH DAYS"
    assert not went_back(ctx)


def test_screen_does_not_read_a_popup_it_did_not_open():
    """ctx.popup is shared. An update() with nothing pending must not
    pick up somebody else's CONFIRM."""
    from engine.states import side_quests
    ctx = context()
    side_quest_list.reset()
    side_quests.enter(ctx)
    ctx.popup.open("SOMEBODY ELSE'S QUESTION", ["not ours"])
    ctx.popup.set_result(RESULT_CONFIRM)
    side_quests.update(ctx, 0.016)
    assert side_quest_list.get_last_confirmed() is None
    assert ctx.popup.take_result() == RESULT_CONFIRM, \
        "the other screen's result must still be there for it to read"


# -------------------------------------------------------------
# RUNNER -- collect every test_* in this module, in the order it is
# written, run it, and report. Exits non-zero if anything failed, so
# this works unchanged as a CI step.
# -------------------------------------------------------------

def main() -> int:
    """Run every test in this module. Returns the process exit code."""
    cases = [(name, function) for name, function in globals().items()
             if name.startswith("test_") and callable(function)]
    cases.sort(key=lambda pair: pair[1].__code__.co_firstlineno)

    failures = []
    for name, function in cases:
        try:
            function()
        except Exception as error:                # noqa: BLE001 - report all
            failures.append((name, error))
            print("FAIL  %s\n        %s: %s"
                  % (name, type(error).__name__, error))
        else:
            print("PASS  %s" % name)

    print("\n%d/%d passed" % (len(cases) - len(failures), len(cases)))
    if failures:
        print("failed: %s" % ", ".join(name for name, _ in failures))
        return 1

    print("\n-- what the PC shows for the mixed run --")
    ctx = mixed()
    print("%-18s %-6s %-7s %-9s %s"
          % ("TOPIC", "DAYS", "SHEETS", "STATUS", "QUEST ID"))
    for row, cell in zip(side_quest_list.entries(ctx), card_rows(ctx)):
        print("%-18s %-6s %-7s %-9s %s"
              % (cell[0], cell[1], cell[2], cell[3] or "-", row["quest_id"]))
    hidden = [quest_of(s) for s in SEMESTERS
              if quest_of(s) not in side_quest_list.listed_ids(ctx)]
    print("\n%d rows shown; %d quests are invisible to this card and "
          "nothing on it says so" % (len(card_rows(ctx)), len(hidden)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

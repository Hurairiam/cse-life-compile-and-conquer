"""
tests/test_gate_evaluator.py
CSE Life: Compile & Conquer — phase F8

Guards engine/gate_evaluator.py — the rules half of Feature 6.

A gate decides whether a door opens, so the cases that matter are the
edges: a threshold met exactly, a wallet one taka short, a paid entry
that must never charge half a toll, and an NPC whose semester has not
arrived versus one whose 20-day window has closed. Every method is
read-only or, for GateEntryAction, all-or-nothing — nothing here ever
half-mutates a player.

The suite proves the evaluator gives the SAME verdict for the sandbox's
fake player and a real core.character.Player (they satisfy the same
seven-method protocol), and that a paid entry charges correctly through
the real GameClock pipeline — never by touching the day pool directly.
"""

from __future__ import annotations

import pytest

from academic.academic_history import AcademicHistory
from content.level_registry import get_npc_min_semester
from content.level_schema import GateData, NpcData
from core.character.player import Player
from core.interfaces import TimeConsumable
from core.skill_tree import SkillTree
from engine.game_clock import GameClock
from engine.game_session import GameSession
from engine.gate_evaluator import (GateEntryAction, GateEvaluator,
                                   GateRequirement, GateResult, NPC_SEMESTER_LOCKED,
                                   NPC_VISIBLE, NPC_WINDOW_CLOSED, REQ_CREDITS,
                                   REQ_SEMESTER, REQ_WALLET)


# ─────────────────────────────────────────────────────────────
# A TEST DOUBLE FOR THE READ-ONLY PLAYER PROTOCOL
# ─────────────────────────────────────────────────────────────


class FakeView:
    """
    Implements exactly the seven read methods GateEvaluator needs.

    Mirrors the sandbox's FakePlayerState: a real Player satisfies the
    identical protocol, and test_protocol_parity proves both give the
    same verdict.
    """

    def __init__(self, semester=1, credits_=0, wallet=0.0, days=80,
                 graduated=False, skills=None, completed=None):
        self._sem = semester
        self._cr = credits_
        self._wallet = wallet
        self._days = days
        self._grad = graduated
        self._tree = SkillTree()
        for skill_id, level in (skills or {}).items():
            self._tree.increment_skill(skill_id, level)
        self._history = AcademicHistory()
        self._completed = list(completed or [])

    def get_current_semester(self):
        return self._sem

    def get_accumulated_credits(self):
        return self._cr

    def get_wallet_balance(self):
        return self._wallet

    def get_time_pool_days(self):
        return self._days

    def get_has_graduated(self):
        return self._grad

    def get_skill_tree(self):
        return self._tree

    def get_academic_history(self):
        # A tiny inline stand-in so completed codes are configurable.
        completed = self._completed

        class _Hist:
            def get_completed_course_codes(self):
                return list(completed)

        return _Hist()


@pytest.fixture
def evaluator():
    """One evaluator, reused — it owns no state."""
    return GateEvaluator()


# ─────────────────────────────────────────────────────────────
# THE DEFAULT (OPEN) GATE
# ─────────────────────────────────────────────────────────────


def test_default_gate_is_open(evaluator):
    """A fresh gate demands nothing, so it opens for anyone."""
    result = evaluator.evaluate(GateData(), FakeView())
    assert result.is_open() is True
    assert result.get_requirements() == []
    assert result.get_unmet() == []
    assert result.get_summary_lines() == []


def test_default_gate_has_no_cost(evaluator):
    """The open gate charges nothing and needs no entry action."""
    result = evaluator.evaluate(GateData(), FakeView())
    assert result.get_costs() == (0, 0.0)
    assert result.has_cost() is False
    assert GateEntryAction.for_gate(GateData()) is None


# ─────────────────────────────────────────────────────────────
# EACH REQUIREMENT TYPE, ALONE
# ─────────────────────────────────────────────────────────────


def test_semester_requirement(evaluator):
    """A semester gate reads the player's current semester."""
    gate = GateData()
    gate.set_min_semester(5)
    assert evaluator.evaluate(gate, FakeView(semester=3)).is_open() is False
    assert evaluator.evaluate(gate, FakeView(semester=6)).is_open() is True


def test_credits_requirement(evaluator):
    gate = GateData()
    gate.set_min_credits(60)
    assert evaluator.evaluate(gate, FakeView(credits_=42)).is_open() is False
    assert evaluator.evaluate(gate, FakeView(credits_=60)).is_open() is True


def test_days_requirement(evaluator):
    gate = GateData()
    gate.set_min_days_remaining(30)
    assert evaluator.evaluate(gate, FakeView(days=20)).is_open() is False
    assert evaluator.evaluate(gate, FakeView(days=46)).is_open() is True


def test_wallet_requirement(evaluator):
    gate = GateData()
    gate.set_min_wallet(12000.0)
    assert evaluator.evaluate(gate, FakeView(wallet=4500.0)).is_open() is False
    assert evaluator.evaluate(gate, FakeView(wallet=12000.0)).is_open() is True


def test_skill_requirement(evaluator):
    gate = GateData()
    gate.set_required_skill_id("programming")
    gate.set_required_skill_level(4)
    low = FakeView(skills={"programming": 2})
    high = FakeView(skills={"programming": 4})
    assert evaluator.evaluate(gate, low).is_open() is False
    assert evaluator.evaluate(gate, high).is_open() is True


def test_course_requirement(evaluator):
    gate = GateData()
    gate.set_required_course_codes("CSE110, CSE111")
    missing = FakeView(completed=["CSE110"])
    both = FakeView(completed=["CSE110", "CSE111"])
    assert evaluator.evaluate(gate, missing).is_open() is False
    assert evaluator.evaluate(gate, both).is_open() is True


def test_course_requirement_is_case_insensitive(evaluator):
    """Codes are compared upper-cased, so a lower-case transcript passes."""
    gate = GateData()
    gate.set_required_course_codes("CSE110")
    assert evaluator.evaluate(
        gate, FakeView(completed=["cse110"])).is_open() is True


def test_graduated_requirement(evaluator):
    gate = GateData()
    gate.set_requires_graduated(True)
    assert evaluator.evaluate(
        gate, FakeView(graduated=False)).is_open() is False
    assert evaluator.evaluate(
        gate, FakeView(graduated=True)).is_open() is True


# ─────────────────────────────────────────────────────────────
# BOUNDARY EQUALITY — MEETING A THRESHOLD ON THE NOSE PASSES
# ─────────────────────────────────────────────────────────────


def test_boundary_equality_passes(evaluator):
    """min_x == current is enough for every numeric requirement (>=)."""
    gate = GateData()
    gate.set_min_semester(5)
    gate.set_min_credits(60)
    gate.set_min_days_remaining(30)
    gate.set_min_wallet(12000.0)
    gate.set_required_skill_id("algorithms")
    gate.set_required_skill_level(3)
    view = FakeView(semester=5, credits_=60, days=30, wallet=12000.0,
                    skills={"algorithms": 3})
    result = evaluator.evaluate(gate, view)
    assert result.is_open() is True
    assert result.get_unmet() == []


# ─────────────────────────────────────────────────────────────
# COMBINED REQUIREMENTS + UNMET REPORTING
# ─────────────────────────────────────────────────────────────


def test_combined_requirements_report_only_failures(evaluator):
    """
    A door with several conditions stays shut on ANY miss, and get_unmet()
    names exactly which — the semester and credits here, not the wallet.
    """
    gate = GateData()
    gate.set_min_semester(5)
    gate.set_min_credits(60)
    gate.set_min_wallet(1000.0)
    view = FakeView(semester=3, credits_=42, wallet=5000.0)
    result = evaluator.evaluate(gate, view)
    assert result.is_open() is False
    unmet_codes = {req.get_code() for req in result.get_unmet()}
    assert unmet_codes == {REQ_SEMESTER, REQ_CREDITS}
    assert len(result.get_requirements()) == 3


def test_rows_shape_for_ui(evaluator):
    """get_rows() hands ui/gate_notice.py (label, actual, is_met) tuples."""
    gate = GateData()
    gate.set_min_semester(5)
    rows = evaluator.evaluate(gate, FakeView(semester=3)).get_rows()
    assert rows == [("SEMESTER 5", "NOW 3", False)]


# ─────────────────────────────────────────────────────────────
# §7 SUMMARY-LINE FORMATTING
# ─────────────────────────────────────────────────────────────


def test_summary_line_formatting(evaluator):
    """REQUIRED / CURRENT pairs read as the style guide §7 shows them."""
    gate = GateData()
    gate.set_min_semester(5)
    gate.set_min_credits(60)
    gate.set_min_wallet(12000.0)
    view = FakeView(semester=3, credits_=42, wallet=4500.0)
    lines = evaluator.evaluate(gate, view).get_summary_lines()
    assert "SEMESTER 5 / NOW 3" in lines
    assert "CREDITS 60 / NOW 42" in lines
    assert "12,000 BDT / NOW 4,500 BDT" in lines


def test_requirement_getters():
    """GateRequirement exposes every field it was built with."""
    req = GateRequirement(REQ_WALLET, "12,000 BDT", "12,000 BDT",
                          "NOW 4,500 BDT", False)
    assert req.get_code() == REQ_WALLET
    assert req.get_label() == "12,000 BDT"
    assert req.get_actual() == "NOW 4,500 BDT"
    assert req.is_met() is False
    assert req.get_summary_line() == "12,000 BDT / NOW 4,500 BDT"
    assert req.as_row() == ("12,000 BDT", "NOW 4,500 BDT", False)


# ─────────────────────────────────────────────────────────────
# COST AFFORDABILITY
# ─────────────────────────────────────────────────────────────


def test_can_afford_costs(evaluator):
    """A cost is affordable only when BOTH wallet and days cover it."""
    gate = GateData()
    gate.set_cost_days(10)
    gate.set_cost_money(1000.0)
    assert evaluator.can_afford_costs(
        gate, FakeView(days=46, wallet=4500.0)) is True
    assert evaluator.can_afford_costs(       # wallet short
        gate, FakeView(days=46, wallet=500.0)) is False
    assert evaluator.can_afford_costs(       # days short
        gate, FakeView(days=5, wallet=4500.0)) is False


def test_can_afford_boundary(evaluator):
    """Exactly enough wallet and days affords the toll."""
    gate = GateData()
    gate.set_cost_days(10)
    gate.set_cost_money(1000.0)
    assert evaluator.can_afford_costs(
        gate, FakeView(days=10, wallet=1000.0)) is True


# ─────────────────────────────────────────────────────────────
# GateEntryAction — A TimeConsumable
# ─────────────────────────────────────────────────────────────


def test_entry_action_is_a_time_consumable():
    """It is a TimeConsumable, so GameClock accepts it polymorphically."""
    action = GateEntryAction(10, 1000.0)
    assert isinstance(action, TimeConsumable)
    assert action.get_time_cost() == 10
    assert action.get_money_cost() == 1000.0


def test_for_gate_factory():
    """for_gate() builds an action for a paid door, None for a free one."""
    free = GateData()
    assert GateEntryAction.for_gate(free) is None
    paid = GateData()
    paid.set_cost_days(10)
    action = GateEntryAction.for_gate(paid)
    assert isinstance(action, GateEntryAction)
    assert action.get_time_cost() == 10


def test_entry_action_charges_money_then_days():
    """A successful entry debits both the wallet and the day pool."""
    player = Player()
    player.deposit_funds(5000.0)
    days_before = player.get_time_pool_days()
    GateEntryAction(10, 1000.0).execute_action(player)
    assert player.get_wallet_balance() == 4000.0
    assert player.get_time_pool_days() == days_before - 10


def test_entry_action_aborts_when_wallet_short_no_side_effects():
    """
    The all-or-nothing rule: if the wallet cannot cover the money, the
    action takes nothing AND deducts no days — no half-paid toll.
    """
    player = Player()
    player.deposit_funds(500.0)          # short of the 1,000 toll
    days_before = player.get_time_pool_days()
    GateEntryAction(10, 1000.0).execute_action(player)
    assert player.get_wallet_balance() == 500.0      # untouched
    assert player.get_time_pool_days() == days_before  # untouched


def test_days_only_entry_action():
    """A time-only toll deducts days and leaves the wallet alone."""
    player = Player()
    player.deposit_funds(100.0)
    GateEntryAction(5, 0.0).execute_action(player)
    assert player.get_wallet_balance() == 100.0
    assert player.get_time_pool_days() == 75


# ─────────────────────────────────────────────────────────────
# THE SINGLE ACTION PIPELINE — GameClock end to end
# ─────────────────────────────────────────────────────────────


def test_entry_action_through_game_clock():
    """
    A paid entry charged through GameClock.process_time_consumable()
    deducts the player's days and money AND advances the global career
    clock by the same days — the one pipeline (IMPLEMENTATION_PLAN §2.2).
    """
    session = GameSession()
    player = session.get_active_player()
    player.deposit_funds(5000.0)
    days_before = player.get_time_pool_days()
    clock = GameClock(session)

    gate = GateData()
    gate.set_cost_days(10)
    gate.set_cost_money(1000.0)
    action = GateEntryAction.for_gate(gate)
    clock.process_time_consumable(action)

    assert player.get_time_pool_days() == days_before - 10
    assert player.get_wallet_balance() == 4000.0
    assert session.get_global_career_clock_days() == 10


# ─────────────────────────────────────────────────────────────
# NPC VISIBILITY — THE THREE-WAY
# ─────────────────────────────────────────────────────────────


def test_npc_visibility_semester_locked(evaluator):
    """Before an NPC's semester arrives, it is semester_locked."""
    npc = NpcData("npc_1", "hoque", 5, 5)      # roster min semester 5
    result = evaluator.evaluate_npc_visibility(
        npc, FakeView(semester=3), ratio_ok=True)
    assert result == NPC_SEMESTER_LOCKED


def test_npc_visibility_window_closed(evaluator):
    """Right semester but the 20-day window has closed -> window_closed."""
    npc = NpcData("npc_1", "hoque", 5, 5)
    result = evaluator.evaluate_npc_visibility(
        npc, FakeView(semester=6), ratio_ok=False)
    assert result == NPC_WINDOW_CLOSED


def test_npc_visibility_visible(evaluator):
    """Right semester and inside the window -> visible."""
    npc = NpcData("npc_1", "hoque", 5, 5)
    result = evaluator.evaluate_npc_visibility(
        npc, FakeView(semester=6), ratio_ok=True)
    assert result == NPC_VISIBLE


def test_npc_visibility_semester_beats_window(evaluator):
    """
    Semester is checked first: an NPC whose term has not come reads as
    semester_locked even when the availability window would also be shut,
    so the map can tell "not yet" from "too late".
    """
    npc = NpcData("npc_1", "roya", 5, 5)       # roster min semester 4
    result = evaluator.evaluate_npc_visibility(
        npc, FakeView(semester=2), ratio_ok=False)
    assert result == NPC_SEMESTER_LOCKED


def test_npc_effective_min_semester_matches_roster():
    """The visibility test leans on the roster figure F5 seeded (§F8)."""
    assert NpcData("n", "hoque", 0, 0).get_effective_min_semester() == \
        get_npc_min_semester("hoque")


# ─────────────────────────────────────────────────────────────
# PROTOCOL PARITY — A REAL PLAYER AND THE FAKE AGREE
# ─────────────────────────────────────────────────────────────


def test_real_player_satisfies_protocol(evaluator):
    """
    A real core.character.Player is a valid player_view with no adapter:
    the evaluator reads it exactly as it reads the fake, so integration
    is a direct hand-off (Build Plan §F8).
    """
    player = Player()
    player.set_skill_tree(SkillTree())
    player.set_academic_history(AcademicHistory())
    player.add_credits(60)
    player.deposit_funds(4500.0)

    gate = GateData()
    gate.set_min_semester(1)          # a real Player starts at semester 1
    gate.set_min_credits(60)
    gate.set_min_wallet(4500.0)

    result = evaluator.evaluate(gate, player)
    assert result.is_open() is True


def test_real_player_and_fake_give_same_verdict(evaluator):
    """The same gate against equivalent real and fake state agrees."""
    gate = GateData()
    gate.set_min_semester(1)
    gate.set_min_credits(30)

    real = Player()
    real.set_skill_tree(SkillTree())
    real.set_academic_history(AcademicHistory())
    real.add_credits(20)              # short of 30

    fake = FakeView(semester=1, credits_=20)

    real_result = evaluator.evaluate(gate, real)
    fake_result = evaluator.evaluate(gate, fake)
    assert real_result.is_open() == fake_result.is_open() is False
    assert real_result.get_summary_lines() == fake_result.get_summary_lines()


def test_missing_skill_tree_reads_as_zero(evaluator):
    """
    A fresh Player carries a None skill tree; a skill gate must not crash,
    it just reads level 0 and stays shut (Build Plan §0.8 — never raise).
    """
    player = Player()                 # skill tree is None until GameSession
    gate = GateData()
    gate.set_required_skill_id("networking")
    gate.set_required_skill_level(2)
    result = evaluator.evaluate(gate, player)
    assert result.is_open() is False


def test_result_holds_costs(evaluator):
    """A GateResult carries the (days, money) cost straight off the gate."""
    gate = GateData()
    gate.set_cost_days(7)
    gate.set_cost_money(750.0)
    result = evaluator.evaluate(gate, FakeView())
    assert isinstance(result, GateResult)
    assert result.get_costs() == (7, 750.0)
    assert result.has_cost() is True

"""
engine/gate_evaluator.py
CSE Life: Compile & Conquer — phase F8  (Feature 6, runtime half)
─────────────────────────────────────────────────────────────
OOP Pillars: Abstraction + Polymorphism

A GateData (content/level_schema.py) only STORES what a locked
door demands and what passing it costs. This module is the other
half: it weighs one gate against a player and says whether the
door opens, exactly which conditions failed, and — when the door
is a paid one — turns "walk through" into a proper time-costing
action.

Three public pieces:

    GateEvaluator   read-only: evaluate a gate, answer NPC
                    visibility, check whether a cost is affordable.
    GateResult      the verdict: is_open(), the per-condition rows,
                    ALL-CAPS summary lines, and the (days, money) cost.
    GateEntryAction a TimeConsumable so a paid entry is charged
                    through GameClock.process_time_consumable() —
                    the ONE action pipeline (IMPLEMENTATION_PLAN §2.2),
                    never by deducting days by hand.

Pure Python, no pygame — this is rules, not rendering, and must be
unit-testable headlessly (Build Plan §0.7). It reads the player
through a small read-only protocol (the seven getters below); a
real core.character.Player satisfies it today with no adapter, and
the sandbox's fake state satisfies the same seven.

DIVERGENCE NOTE (Build Plan §1.4): a gate's required_skill_id lives
in content/level_registry.py::SKILL_IDS (the 9-entry authoring
list), NOT the 12 canonical endgame ids. The two lists are left
unreconciled by owner ruling; this evaluator reads whichever id the
gate carries straight off the player's skill tree and never tries
to map between them.
─────────────────────────────────────────────────────────────
Created by Nangiba Tasnim (Dev 3), branch nangiba-temp-01.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

from core.interfaces import TimeConsumable

if TYPE_CHECKING:                       # imports only for type hints, never at
    from typing import Protocol         # runtime — keeps this module dependency

    from content.level_schema import GateData, NpcData
    from core.character.player import Player

    class PlayerView(Protocol):
        """
        The read-only slice of a player a gate is judged against.

        core.character.Player already exposes all seven, verified in
        PHASELOG_F8 §4, so integration is a direct hand-off with no
        adapter and no edit to player.py. The sandbox's FakePlayerState
        implements the identical seven.
        """

        def get_current_semester(self) -> int: ...
        def get_accumulated_credits(self) -> int: ...
        def get_wallet_balance(self) -> float: ...
        def get_time_pool_days(self) -> int: ...
        def get_has_graduated(self) -> bool: ...
        def get_skill_tree(self) -> object: ...
        def get_academic_history(self) -> object: ...


# ─────────────────────────────────────────────────────────────
# REQUIREMENT CODES + NPC VISIBILITY STATES
# ─────────────────────────────────────────────────────────────
# Machine codes for each kind of condition, so a caller can branch on
# a requirement without string-matching the human label.
REQ_SEMESTER: str = "semester"
REQ_CREDITS: str = "credits"
REQ_DAYS: str = "days"
REQ_WALLET: str = "wallet"
REQ_SKILL: str = "skill"
REQ_COURSE: str = "course"
REQ_GRADUATED: str = "graduated"

# The three answers evaluate_npc_visibility() gives, so the map can tell
# "not this semester yet" apart from "the 20-day window has closed".
NPC_VISIBLE: str = "visible"
NPC_SEMESTER_LOCKED: str = "semester_locked"
NPC_WINDOW_CLOSED: str = "window_closed"


def _money(value: float) -> str:
    """Format BDT the §7 way: thousands commas, no decimals — `12,000 BDT`."""
    return f"{value:,.0f} BDT"


# ─────────────────────────────────────────────────────────────
# ONE CONDITION
# ─────────────────────────────────────────────────────────────


class GateRequirement:
    """
    A single condition and how the player measures up to it.

    An immutable snapshot: it is built once by GateEvaluator.evaluate()
    and only ever read. `label` is the REQUIREMENT column ("SEMESTER 5"),
    `actual` is the YOU HAVE column ("NOW 3"), and the two joined with
    " / " give the §7 summary line the popup and the log both use.
    """

    def __init__(self, code: str, label: str, required: str,
                 actual: str, is_met: bool) -> None:
        """Store one already-decided condition. Nothing here recomputes."""
        self.__code: str = str(code)
        self.__label: str = str(label)
        self.__required: str = str(required)
        self.__actual: str = str(actual)
        self.__is_met: bool = bool(is_met)

    def get_code(self) -> str:
        """The machine code — one of the REQ_* constants."""
        return self.__code

    def get_label(self) -> str:
        """The REQUIREMENT-column text, e.g. `SEMESTER 5` or `12,000 BDT`."""
        return self.__label

    def get_required(self) -> str:
        """The bare required value, e.g. `5`, `60`, `PASSED`, `YES`."""
        return self.__required

    def get_actual(self) -> str:
        """The YOU HAVE-column text, e.g. `NOW 3` or `NOW 4,500 BDT`."""
        return self.__actual

    def is_met(self) -> bool:
        """True when the player already satisfies this condition."""
        return self.__is_met

    def get_summary_line(self) -> str:
        """The §7 `REQUIRED / CURRENT` pair, e.g. `SEMESTER 5 / NOW 3`."""
        return f"{self.__label} / {self.__actual}"

    def as_row(self) -> Tuple[str, str, bool]:
        """(label, actual, is_met) — the plain tuple ui/gate_notice.py draws."""
        return (self.__label, self.__actual, self.__is_met)


# ─────────────────────────────────────────────────────────────
# THE VERDICT
# ─────────────────────────────────────────────────────────────


class GateResult:
    """
    The outcome of weighing one gate against one player.

    Holds every condition (met and unmet) plus the entry cost, so a
    caller can render the full requirement table, ask only for the
    failures, or read the (days, money) charge for a confirmation.
    """

    def __init__(self, requirements: List[GateRequirement],
                 cost_days: int, cost_money: float) -> None:
        """Store the decided conditions and the gate's entry cost."""
        self.__requirements: List[GateRequirement] = list(requirements)
        self.__cost_days: int = int(cost_days)
        self.__cost_money: float = float(cost_money)

    def is_open(self) -> bool:
        """
        True when every condition is met — an empty list opens.

        A default (requirement-free) gate therefore reads as open, which
        is what lets a cost-only toll skip straight to its confirmation.
        """
        return all(req.is_met() for req in self.__requirements)

    def get_requirements(self) -> List[GateRequirement]:
        """A copy of every condition, in the order they are drawn."""
        return list(self.__requirements)

    def get_unmet(self) -> List[GateRequirement]:
        """Only the conditions the player fails — the reason it stays shut."""
        return [req for req in self.__requirements if not req.is_met()]

    def get_summary_lines(self) -> List[str]:
        """Every condition as an ALL-CAPS `REQUIRED / CURRENT` line (§7)."""
        return [req.get_summary_line() for req in self.__requirements]

    def get_rows(self) -> List[Tuple[str, str, bool]]:
        """(label, actual, is_met) per condition — for ui/gate_notice.py."""
        return [req.as_row() for req in self.__requirements]

    def get_costs(self) -> Tuple[int, float]:
        """The (days, money) charged on a successful entry."""
        return (self.__cost_days, self.__cost_money)

    def has_cost(self) -> bool:
        """True when passing this gate charges days or money."""
        return self.__cost_days > 0 or self.__cost_money > 0.0


# ─────────────────────────────────────────────────────────────
# THE EVALUATOR
# ─────────────────────────────────────────────────────────────


class GateEvaluator:
    """
    Weighs a gate against a player. Owns no state — a single instance
    is reused, or a fresh one made per call; both are equivalent.

    Every method is read-only. Nothing here charges the player or moves
    them; that is GateEntryAction's job, run through GameClock. This
    class only ever ANSWERS questions.
    """

    def evaluate(self, gate: "GateData",
                 player_view: "PlayerView") -> GateResult:
        """
        Build the full verdict for `gate` against `player_view`.

        Only conditions the gate actually sets become rows: an unset
        requirement is silence, not a met row, so the table shows exactly
        what the door asks for and nothing else. Every comparison is
        `>=`, so meeting a threshold on the nose passes (a semester-5 door
        admits a semester-5 player).
        """
        requirements: List[GateRequirement] = []

        min_semester = gate.get_min_semester()
        if min_semester > 0:
            now = self.__read_int(player_view.get_current_semester)
            requirements.append(GateRequirement(
                REQ_SEMESTER, f"SEMESTER {min_semester}", str(min_semester),
                f"NOW {now}", now >= min_semester))

        min_credits = gate.get_min_credits()
        if min_credits > 0:
            now = self.__read_int(player_view.get_accumulated_credits)
            requirements.append(GateRequirement(
                REQ_CREDITS, f"CREDITS {min_credits}", str(min_credits),
                f"NOW {now}", now >= min_credits))

        min_days = gate.get_min_days_remaining()
        if min_days > 0:
            now = self.__read_int(player_view.get_time_pool_days)
            requirements.append(GateRequirement(
                REQ_DAYS, f"DAYS {min_days}", str(min_days),
                f"NOW {now}", now >= min_days))

        min_wallet = gate.get_min_wallet()
        if min_wallet > 0:
            now = self.__read_float(player_view.get_wallet_balance)
            requirements.append(GateRequirement(
                REQ_WALLET, _money(min_wallet), _money(min_wallet),
                f"NOW {_money(now)}", now >= min_wallet))

        skill_id = gate.get_required_skill_id()
        skill_level = gate.get_required_skill_level()
        if skill_id and skill_level > 0:
            now = self.__read_skill_level(player_view, skill_id)
            pretty = skill_id.replace("_", " ").upper()
            requirements.append(GateRequirement(
                REQ_SKILL, f"{pretty} LV {skill_level}", str(skill_level),
                f"NOW LV {now}", now >= skill_level))

        completed = self.__read_completed_codes(player_view)
        for code in gate.get_required_course_codes():
            passed = code.upper() in completed
            requirements.append(GateRequirement(
                REQ_COURSE, f"PASS {code}", "PASSED",
                "PASSED" if passed else "NOT YET", passed))

        if gate.get_requires_graduated():
            graduated = bool(self.__read_bool(player_view.get_has_graduated))
            requirements.append(GateRequirement(
                REQ_GRADUATED, "GRADUATE", "YES",
                "YES" if graduated else "NO", graduated))

        return GateResult(requirements, gate.get_cost_days(),
                          gate.get_cost_money())

    def can_afford_costs(self, gate: "GateData",
                         player_view: "PlayerView") -> bool:
        """
        True when the player can pay the gate's entry cost right now.

        Checked BEFORE a paid entry is offered, so the confirmation only
        appears when GateEntryAction.execute_action() will actually go
        through — a wallet-short player is never shown a button that
        would silently do nothing.
        """
        wallet = self.__read_float(player_view.get_wallet_balance)
        days = self.__read_int(player_view.get_time_pool_days)
        return wallet >= gate.get_cost_money() and days >= gate.get_cost_days()

    def evaluate_npc_visibility(self, npc_data: "NpcData",
                                player_view: "PlayerView",
                                ratio_ok: bool) -> str:
        """
        Say whether an NPC is showable, and if not, WHY — as one of
        NPC_VISIBLE / NPC_SEMESTER_LOCKED / NPC_WINDOW_CLOSED.

        The semester test comes first: an NPC whose term has not arrived
        is simply not here yet, which is a different thing from one whose
        first-20-day availability window has closed for this semester.

        `ratio_ok` is the 0.75-1.00 window answer, computed by the caller
        with core.character.npc.NPC.is_within_availability_window() and
        passed in — this method deliberately does NOT reimplement that
        game rule (Build Plan §F8, §1.4). The NPC's effective min semester
        already folds in the roster figure F5 seeded from npc_roster.py.
        """
        effective_min = npc_data.get_effective_min_semester()
        now = self.__read_int(player_view.get_current_semester)
        if now < effective_min:
            return NPC_SEMESTER_LOCKED
        if not ratio_ok:
            return NPC_WINDOW_CLOSED
        return NPC_VISIBLE

    # ── private readers — a broken player_view never crashes a gate ──

    @staticmethod
    def __read_int(getter) -> int:
        """Call a getter and coerce to int, defaulting to 0 on any error."""
        try:
            return int(getter())
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def __read_float(getter) -> float:
        """Call a getter and coerce to float, defaulting to 0.0."""
        try:
            return float(getter())
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def __read_bool(getter) -> bool:
        """Call a getter and coerce to bool, defaulting to False."""
        try:
            return bool(getter())
        except (TypeError, ValueError):
            return False

    @staticmethod
    def __read_skill_level(player_view: "PlayerView", skill_id: str) -> int:
        """
        The player's level in one skill, 0 when the tree is missing.

        A fresh Player carries a None skill tree until GameSession wires
        one (player.py), so this tolerates None rather than assuming the
        tree is always present.
        """
        try:
            tree = player_view.get_skill_tree()
            if tree is None:
                return 0
            return int(tree.get_skill_level(skill_id))
        except (AttributeError, TypeError, ValueError):
            return 0

    @staticmethod
    def __read_completed_codes(player_view: "PlayerView") -> List[str]:
        """
        Upper-cased completed course codes, or [] when history is missing.

        Upper-casing here means a gate's already-upper codes compare
        cleanly whatever case the transcript happens to store.
        """
        try:
            history = player_view.get_academic_history()
            if history is None:
                return []
            return [str(code).upper()
                    for code in history.get_completed_course_codes()]
        except (AttributeError, TypeError, ValueError):
            return []


# ─────────────────────────────────────────────────────────────
# PAID ENTRY — A TimeConsumable
# ─────────────────────────────────────────────────────────────


class GateEntryAction(TimeConsumable):
    """
    Charging a player for walking through a paid gate.

    Implements TimeConsumable so a paid entry is spent through the ONE
    action pipeline (GameClock.process_time_consumable) exactly like a
    MainQuest or a SideQuest — never by deducting days on the side. That
    single-pipeline rule is IMPLEMENTATION_PLAN §2.2 and the whole reason
    the owner approved wiring GameClock in for F8.

    OOP: Polymorphism — GameClock runs this without knowing it is a gate.
    """

    def __init__(self, cost_days: int, cost_money: float) -> None:
        """Fix the charge at construction from a gate's two cost fields."""
        self.__cost_days: int = int(cost_days)
        self.__cost_money: float = float(cost_money)

    @classmethod
    def for_gate(cls, gate: "GateData") -> Optional["GateEntryAction"]:
        """
        The action for a gate, or None when the gate is free.

        A gate with cost_days == 0 and cost_money == 0 produces NO action
        at all — a zero-cost item must never be pushed through the clock
        (Build Plan §F8), because that would advance the global career
        clock by zero days for a door that charges nothing.
        """
        if gate.get_cost_days() <= 0 and gate.get_cost_money() <= 0.0:
            return None
        return cls(gate.get_cost_days(), gate.get_cost_money())

    def get_time_cost(self) -> int:
        """
        Days this entry costs — read by GameClock BEFORE execute_action()
        to advance the global career clock, so it must match what
        execute_action() deducts.
        """
        return self.__cost_days

    def get_money_cost(self) -> float:
        """BDT this entry costs. Not part of TimeConsumable; here for tests."""
        return self.__cost_money

    def execute_action(self, player: "Player") -> None:
        """
        Charge the player for entry: MONEY FIRST, then days.

        If the wallet is short the whole action aborts with no side
        effects — the money is not taken and the days are not deducted,
        so a failed payment can never leave a player charged half a toll.
        Callers gate this behind GateEvaluator.can_afford_costs(), so in
        normal play the wallet is never short here; the guard is the
        belt-and-braces that keeps state uncorrupted if it ever is
        (Build Plan §0.8 — never raise, never corrupt).
        """
        if self.__cost_money > 0.0:
            if not player.withdraw_funds(self.__cost_money):
                return
        if self.__cost_days > 0:
            player.deduct_time_pool_days(self.__cost_days)


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to exercise the evaluator.
# Abu Huraira removes this block when he plugs in the real game.
#   (no window: this is a pure-logic module, so its stub is a headless
#    print of a locked door and then the same door after the player
#    qualifies — proving is_open() flips and the summary lines read right)
# -------------------------------------------------------------
if __name__ == "__main__":
    from content.level_schema import GateData

    class _FakePlayer:
        """A throwaway player_view for the headless demonstration."""

        def __init__(self, semester: int, credits_: int, wallet: float,
                     days: int) -> None:
            self._sem, self._cr = semester, credits_
            self._wallet, self._days = wallet, days

        def get_current_semester(self) -> int:
            return self._sem

        def get_accumulated_credits(self) -> int:
            return self._cr

        def get_wallet_balance(self) -> float:
            return self._wallet

        def get_time_pool_days(self) -> int:
            return self._days

        def get_has_graduated(self) -> bool:
            return False

        def get_skill_tree(self):
            return None

        def get_academic_history(self):
            return None

    door = GateData()
    door.set_min_semester(5)
    door.set_min_credits(60)
    door.set_cost_days(10)
    door.set_cost_money(1000.0)

    evaluator = GateEvaluator()

    print("=== DEAN'S OFFICE: sem-5, 60-credit door, costs 10d + 1,000 ===")
    for label, view in (
            ("freshman  (sem 3, 42 cr)", _FakePlayer(3, 42, 4500.0, 46)),
            ("qualified (sem 5, 60 cr)", _FakePlayer(5, 60, 4500.0, 46))):
        result = evaluator.evaluate(door, view)
        print(f"\n{label}: {'OPEN' if result.is_open() else 'LOCKED'}")
        for line in result.get_summary_lines():
            print(f"   {line}")
        if result.is_open() and result.has_cost():
            afford = evaluator.can_afford_costs(door, view)
            days, money = result.get_costs()
            print(f"   -> costs {days} days + {_money(money)}  "
                  f"(affordable: {afford})")

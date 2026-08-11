"""
engine/ending_gate.py
CSE Life: Compile & Conquer
Phase 16 — the highly-skilled ending gate

The player is highly skilled IF AND ONLY IF all twelve side quests are
Completed. Eleven is not enough, there are no partial tiers, and there
is no second way in.

WHERE THIS SITS
───────────────
`engine/endgame_manager.py::determine_ending_title()` is the one
function in the repo that picks between the four endings, and it does
it on two axes:

                      | highly skilled          | not
    graduated (140cr) | TOP GRADUATE            | AVERAGE GRADUATE
    not graduated     | DROP OUT Strong Skills  | DROP OUT Weak Skills

The academic axis is untouched. **This module is the skill axis.** It
reads `ctx.quest_states` and answers one question;
`engine/states/endgame.py` — the manager's only caller — hands the
answer in.

WHAT IT REPLACED, AND WHY THE OLD RULE HAD TO GO
────────────────────────────────────────────────
The skill axis used to be the *average level over the twelve tracked
skills*, against thresholds of 30.0 for graduates and 15.0 for
dropouts. Three measured facts made that incompatible with "if and only
if":

  1. **Nothing in the shipped game can push the average past 15.0.**
     `progression.invest()` refuses a node already at its `max_level`
     of 10, and a completed quest puts its node at 15 — so completing a
     quest permanently locks hand-investment out of the skill it feeds.
     Twelve nodes at 15 is the ceiling. TOP GRADUATE was therefore
     **unreachable**: every graduate got AVERAGE GRADUATE, whatever
     they did.
  2. **Twelve completed quests average exactly 15.0** — twelve grants
     of 15 EXP onto twelve *distinct* skills. So the dropout row's
     threshold already coincided with the gate, but only by arithmetic
     accident, sitting exactly on the boundary. Retuning `exp_reward`,
     `max_level` or the threshold by one would have broken it silently.
  3. **A `kind: "skill"` prop grants EXP uncapped** and does not
     consult the quest system at all. None exist in the twelve level
     files today, but one authored in the editor tomorrow would have
     been an alternative route to the outcome — the thing the brief
     forbids.

The average is no longer consulted. `TOP_GRADUATE_SKILL_THRESHOLD`,
`STRONG_SKILLS_DROPOUT_THRESHOLD` and `calculate_average_skill_level()`
are still in the manager, marked retired: nothing reads them, and
deleting a teammate's public API in a file that is otherwise identical
to `origin/main` buys nothing.

A NEW MODULE ON PURPOSE
───────────────────────
Recon hazard #4, and the rule `engine/menu_prop.py`,
`engine/quest_offer.py` and `engine/lecture_reader.py` already set: new
logic lives in a new file, and the shared modules take the smallest
possible call site. No pygame, no screen state and no UI here, so the
verdict and the report are testable headless. They are.

THE DEBUG COMMAND
─────────────────
    py -3 -m engine.ending_gate

prints all twelve quests with their final states and the resulting
highly-skilled verdict, then drives the brief's three acceptance
scenarios — so the gate can be checked without a twelve-semester
playthrough. See the block at the bottom of this file.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from content.side_quest_definitions import QUEST_COUNT, QUEST_IDS, get_definition
from engine.quest_state import STATE_COMPLETED, QuestStateMachine

# The four canonical ending titles are NOT restated here. They live in
# engine/endgame_manager.py, ui/endgame_screen.py::THEMES and
# content/epilogue_text.py, and ui/certificate_screen.py already warns
# that a fourth spelling of them exists in content/dialogues.py. The
# report below asks the manager for a title rather than writing one.


# ── the verdict ────────────────────────────────────────────────

def machine_of(source: Any) -> Optional[QuestStateMachine]:
    """
    The QuestStateMachine behind `source`, or None.

    Callers hold different things: `engine/states/endgame.py` has an
    AppContext, a test has a bare machine, the stub below uses both.
    Same shape — and same reason — as
    `engine/quest_offer.py::machine_of()`.
    """
    if isinstance(source, QuestStateMachine):
        return source
    machine = getattr(source, "quest_states", None)
    if isinstance(machine, QuestStateMachine):
        return machine
    return None


def is_highly_skilled(source: Any) -> bool:
    """
    True only when all twelve side quests are Completed.

    A total wrapper over `QuestStateMachine.is_highly_skilled()`: no
    machine at all — a context built before Phase 12, a test double, a
    half-restored save — is False rather than an exception. False is
    the safe default in both directions: the ending it withholds is the
    good one, and a crash on the last screen of the game would lose the
    whole run.

    The count is `all`, not a threshold, and it stays that way — the
    machine's own docstring says so. Eleven is not enough here because
    eleven is not enough there.
    """
    machine = machine_of(source)
    return machine is not None and machine.is_highly_skilled()


def completed_count(source: Any) -> int:
    """How many of the twelve are Completed. Reporting only — the gate
    is `is_highly_skilled()`, never a comparison against this."""
    machine = machine_of(source)
    if machine is None:
        return 0
    return len(machine.get_completed_quests())


# ── the debug report ───────────────────────────────────────────

def quest_rows(source: Any) -> List[Dict[str, Any]]:
    """
    One row per side quest, in semester order, always twelve of them.

    Every field comes from `content/side_quest_definitions.py` except
    the state, which comes from the machine. A source with no machine
    still returns twelve rows, all Unoffered — "there is no quest data"
    and "no quest has been offered" look the same to a player, and the
    report says which by printing the count.
    """
    machine = machine_of(source)
    states = machine.get_all_states() if machine is not None else {}
    rows: List[Dict[str, Any]] = []
    for quest_id in QUEST_IDS:
        definition = get_definition(quest_id) or {}
        state = states.get(quest_id, "unoffered")
        rows.append({
            "semester": definition.get("semester", 0),
            "npc_id": definition.get("npc_id", "?"),
            "quest_id": quest_id,
            "skill_id": definition.get("skill_id", "?"),
            "state": state,
            "completed": state == STATE_COMPLETED,
        })
    return rows


def report_lines(source: Any, title: str = "") -> List[str]:
    """
    The debug report as a list of lines: all twelve quests with their
    final states, the completed count, the verdict, and the ending
    title the verdict produces on each side of the academic axis.

    Both titles are shown because the gate only decides one of the two
    axes — printing just one would read as if the quests alone chose
    the ending. They are fetched from
    `EndgameEvaluationManager.title_for()` rather than written out, so
    this report cannot drift from the endings the game actually shows.
    """
    from engine.endgame_manager import EndgameEvaluationManager

    verdict = is_highly_skilled(source)
    done = completed_count(source)
    manager = EndgameEvaluationManager()

    lines: List[str] = []
    if title:
        lines.append(title)
        lines.append("-" * len(title))
    lines.append("%-4s %-8s %-24s %-24s %s"
                 % ("SEM", "NPC", "QUEST ID", "SKILL ID", "STATE"))
    for row in quest_rows(source):
        lines.append("%-4d %-8s %-24s %-24s %s"
                     % (row["semester"], row["npc_id"], row["quest_id"],
                        row["skill_id"], row["state"]))
    lines.append("")
    lines.append("completed              : %d/%d" % (done, QUEST_COUNT))
    lines.append("HIGHLY SKILLED         : %s" % ("YES" if verdict else "NO"))
    lines.append("ending if graduated    : %s"
                 % manager.title_for(True, verdict))
    lines.append("ending if not graduated: %s"
                 % manager.title_for(False, verdict))
    return lines


def print_report(source: Any, title: str = "") -> None:
    """`report_lines()`, printed. The debug command's whole body."""
    for line in report_lines(source, title):
        print(line)


# -------------------------------------------------------------
# THE DEBUG COMMAND / STUB TEST — the repo's convention for a module
# with no suite of its own (recon §14), and this phase's acceptance
# criterion:
#
#     py -3 -m engine.ending_gate
#
# Prints all twelve quests with their final states and the resulting
# highly-skilled verdict, then runs the brief's three scenarios. Pure
# python: no window, no assets, no pygame, and nothing is written.
# Exits non-zero if any scenario comes out wrong, so it works unchanged
# as a check. The full coverage is in tests/test_ending_gate.py.
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    from content.side_quest_definitions import SEMESTER_MAX, SEMESTER_MIN

    ALL_SEMESTERS = tuple(range(SEMESTER_MIN, SEMESTER_MAX + 1))

    def build(completed=(), declined=(), missed=(), unlocked=()):
        """A machine driven into a shape through the PUBLIC API only, so
        the stub can never demonstrate a state the game cannot reach."""
        machine = QuestStateMachine()
        for semester in completed:
            quest_id = machine.get_quest_for_semester(semester)
            machine.accept(quest_id)
            machine.mark_completed(quest_id)
        for semester in unlocked:
            machine.accept(machine.get_quest_for_semester(semester))
        for semester in declined:
            machine.decline(machine.get_quest_for_semester(semester))
        for semester in missed:
            machine.expire_unoffered_for_semester(semester)
        return machine

    failures = []

    def check(label, machine, expected):
        """Assert the verdict and report it on one line."""
        actual = is_highly_skilled(machine)
        ok = actual is expected
        if not ok:
            failures.append(label)
        print("  %-4s %-52s highly skilled = %s"
              % ("ok" if ok else "FAIL", label, "YES" if actual else "NO"))

    # ── the acceptance criterion: all twelve, in full ──────────
    print_report(build(completed=ALL_SEMESTERS),
                 "FORCED: ALL TWELVE COMPLETED")

    print("\nFORCED: A MIXED RUN")
    print("-------------------")
    print_report(build(completed=(1, 2, 3), unlocked=(4,),
                       declined=(5,), missed=(6,)))

    # ── the brief's three scenarios ────────────────────────────
    print("\nACCEPTANCE")
    print("----------")
    check("12 Completed", build(completed=ALL_SEMESTERS), True)

    for left_out in ALL_SEMESTERS:
        rest = tuple(s for s in ALL_SEMESTERS if s != left_out)
        check("11 Completed + semester %-2d Missed" % left_out,
              build(completed=rest, missed=(left_out,)), False)
    for left_out in ALL_SEMESTERS:
        rest = tuple(s for s in ALL_SEMESTERS if s != left_out)
        check("11 Completed + semester %-2d Declined" % left_out,
              build(completed=rest, declined=(left_out,)), False)

    # The two non-terminal ways to fall short, for completeness.
    check("11 Completed + 1 Unlocked",
          build(completed=ALL_SEMESTERS[:-1], unlocked=(SEMESTER_MAX,)), False)
    check("11 Completed + 1 Unoffered",
          build(completed=ALL_SEMESTERS[:-1]), False)
    check("a fresh run", QuestStateMachine(), False)
    check("no quest machine at all", object(), False)

    if failures:
        print("\n%d scenario(s) wrong: %s" % (len(failures),
                                              ", ".join(failures)))
        sys.exit(1)
    print("\nall scenarios correct")

"""
engine/endgame_manager.py

CSE Life: Compile & Conquer
Engine Package — Endgame Evaluation
─────────────────────────────────────────────────────────────
Spawned by GameSession.trigger_endgame_evaluation() once the session
is frozen (graduation reached, or the year cap hit). Audits the
player's final profile across three dimensions —

    1. Academic State   — accumulated credits (graduated or not)
    2. Skill Profile     — ⚠ CHANGED BY PHASE 16: all twelve side
                            quests Completed, and nothing else. Was the
                            average level across the 12 tracked skills;
                            see the design note below for why that had
                            to go.
    3. Financial state    — final wallet balance (passed through for
                            display; does not currently affect which
                            ending is chosen — see design note below)

— and routes to one of the 4 endings that ui/endgame_screen.py
already knows how to render: "TOP GRADUATE", "AVERAGE GRADUATE",
"DROP OUT Strong Skills", "DROP OUT Weak Skills".

Design notes
────────────
• Ownership: this class touches Player/SkillTree/AcademicHistory data
  from across multiple packages, so it lives in engine/ (alongside
  GameClock, RegistrationManager) rather than academic/ — same
  reasoning we used for RegistrationManager. Built by Saif (Sprint 3).

• SkillTree has no "list all skills" method (only get_skill_level(id)
  for one id at a time), so average skill level is computed over a
  FIXED, KNOWN list of skill IDs — the same 12 skill_id values used
  in academic/side_quest_catalog.py. If new side quests introduce new
  skill IDs later, add them to TRACKED_SKILL_IDS below.

• Graduation is determined directly from
  player.get_accumulated_credits() >= 140, matching exactly what
  GameClock.check_semester_end_state() already checks — NOT from
  player.get_has_graduated(), because
  Player.check_graduation_eligibility() is still an unimplemented
  stub (`pass`) as of this writing. Once that's implemented, this
  can switch to get_has_graduated() if the team prefers a single
  source of truth — flag this to Huraira.

• ⚠ PHASE 16 — THE SKILL AXIS IS NOW THE SIDE QUEST GATE. The two
  thresholds below decide nothing any more:

    TOP_GRADUATE_SKILL_THRESHOLD    = 30.0  (RETIRED — read by nothing)
    STRONG_SKILLS_DROPOUT_THRESHOLD = 15.0  (RETIRED — read by nothing)

  They lined up with SideQuest's exp_reward of 15 per attempt — level
  30 ≈ every tracked skill attempted twice, level 15 ≈ once. What the
  arithmetic actually produced, measured:

    - progression.invest() refuses a node already at its max_level of
      10, and a completed side quest puts its node at 15, which locks
      hand-investment out of that skill for good. Twelve nodes at 15 is
      the ceiling the shipped game can reach — so 30.0 was
      UNREACHABLE and every graduate got AVERAGE GRADUATE.
    - Twelve completed quests average exactly 15.0 (twelve grants of 15
      onto twelve distinct skills), so the dropout row landed exactly
      ON its threshold — the right answer by accident, one retune away
      from being wrong.
    - A `kind: "skill"` prop grants EXP uncapped and never consults the
      quest system, so an author could have opened a second route to
      the outcome from the level editor.

  determine_ending_title() therefore takes the verdict as an argument
  now: `highly_skilled` is all twelve side quests Completed, computed by
  engine/ending_gate.py from ctx.quest_states and handed in by
  engine/states/endgame.py, the only caller. The constants and
  calculate_average_skill_level() are kept — nothing reads them, and
  deleting public API off this class buys nothing — but they are not
  part of the decision. Do not wire them back in without re-reading the
  three points above.

• final_wallet is included in the evaluate() output for display
  purposes only (the stat box shows it) — it does NOT currently
  affect which of the 4 endings is chosen. If the team wants wallet
  balance to influence the ending too, that's a follow-up change.

• Epilogue text is PLACEHOLDER content from content/epilogue_text.py
  — Ayesha owns the real narrative writing. The dict shape there is
  the intended drop-in replacement point; no code here needs to
  change when her content lands.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List

from content.epilogue_text import EPILOGUE_TEXT

if TYPE_CHECKING:
    from core.character.player import Player
    from core.skill_tree import SkillTree


class EndgameEvaluationManager:
    """
    Audits a Player's final profile and determines which of the 4
    endgame narrative endings applies, bundling everything
    ui/endgame_screen.py's render() needs to display it.
    """

    GRADUATION_CREDIT_THRESHOLD: int = 140

    # RETIRED BY PHASE 16 — kept for the record, read by nothing. The
    # skill axis is now all-twelve-side-quests-Completed. See the
    # module docstring for the three measurements that retired them.
    TOP_GRADUATE_SKILL_THRESHOLD: float = 30.0
    STRONG_SKILLS_DROPOUT_THRESHOLD: float = 15.0

    # Known skill IDs from academic/side_quest_catalog.py. SkillTree
    # can't be enumerated directly, so this fixed list stands in for
    # "all skills the player could have invested in".
    TRACKED_SKILL_IDS: List[str] = [
        "programming_language",
        "dsa",
        "git",
        "linux_cli",
        "databases_sql",
        "networking",
        "web_app_dev",
        "docker",
        "ai_tools",
        "debugging_testing",
        "oop",
        "technical_communication",
    ]

    def __init__(self) -> None:
        # No state to hold — this is a stateless evaluator, spawned
        # fresh each time GameSession.trigger_endgame_evaluation() is
        # called, matching its current zero-argument constructor call.
        pass

    def calculate_average_skill_level(self, skill_tree: "SkillTree") -> float:
        """
        Return the average level across all TRACKED_SKILL_IDS.

        ⚠ RETIRED FROM THE ENDING DECISION BY PHASE 16 — this is now a
        plain statistic with no caller. determine_ending_title() no
        longer consults it; the skill axis is all twelve side quests
        Completed. The method stays because it is public API on a
        shared class and removing it gains nothing.

        Skills never touched by the player default to 0 via
        SkillTree.get_skill_level()'s own fallback, so a player who
        only practiced 2 of the 12 skills still gets averaged over
        all 12 — spreading yourself thin is reflected honestly.
        Returns 0.0 if skill_tree is None (unwired player, shouldn't
        normally happen but guarded defensively).
        """
        if skill_tree is None:
            return 0.0
        total = sum(
            skill_tree.get_skill_level(skill_id)
            for skill_id in self.TRACKED_SKILL_IDS
        )
        return total / len(self.TRACKED_SKILL_IDS)

    def title_for(self, graduated: bool, highly_skilled: bool) -> str:
        """
        The whole ending decision, as its 2x2:

                              | highly skilled          | not
            graduated (140cr) | TOP GRADUATE            | AVERAGE GRADUATE
            not graduated     | DROP OUT Strong Skills  | DROP OUT Weak Skills

        Split out by Phase 16 so the two axes can be read, tested and
        reported without a Player to hand — engine/ending_gate.py's
        debug command prints both columns from here rather than writing
        the titles out a fifth time. The four strings are canonical:
        ui/endgame_screen.py::THEMES and content/epilogue_text.py key
        off them exactly, and ui/certificate_screen.py records a known
        misspelling of two of them in content/dialogues.py.
        """
        if graduated:
            return "TOP GRADUATE" if highly_skilled else "AVERAGE GRADUATE"
        return ("DROP OUT Strong Skills" if highly_skilled
                else "DROP OUT Weak Skills")

    def determine_ending_title(
            self, player: "Player", highly_skilled: bool) -> str:
        """
        Decide which of the 4 ending titles applies, based on:
          - Academic State: accumulated credits >= 140 -> graduated
          - Skill Profile: `highly_skilled` — ⚠ PHASE 16: all twelve
            side quests Completed, computed by
            engine/ending_gate.py::is_highly_skilled(ctx) and passed in
            by the caller. Eleven is not enough, there are no partial
            tiers, and this is the only route to the outcome.

        `highly_skilled` deliberately has NO DEFAULT. This class cannot
        reach ctx.quest_states on its own — the machine hangs off the
        AppContext and a Player has no route to it — so a default would
        have to be either a guess or the retired average-level rule,
        and both are a silently wrong ending on the last screen of the
        game. A caller that forgets gets a TypeError at the one call
        site instead, which is loud and immediate.
        """
        accumulated_credits = player.get_accumulated_credits()
        graduated = accumulated_credits >= self.GRADUATION_CREDIT_THRESHOLD
        return self.title_for(graduated, bool(highly_skilled))

    def get_epilogue_lines(self, ending_title: str) -> List[str]:
        """
        Look up the narrative epilogue lines for a given ending title.
        Falls back to "AVERAGE GRADUATE" text if the title is somehow
        unrecognised, so render() never receives an empty list.
        """
        return list(
            EPILOGUE_TEXT.get(ending_title, EPILOGUE_TEXT["AVERAGE GRADUATE"])
        )

    def evaluate(self, player: "Player",
                 highly_skilled: bool) -> Dict[str, object]:
        """
        Run the full evaluation and return a dict shaped EXACTLY to
        match ui/endgame_screen.py's render() keyword arguments:

            EndgameScreen().render(
                screen, **manager.evaluate(player, highly_skilled))

        `highly_skilled` is Phase 16's side quest gate and has no
        default, for the reason determine_ending_title() gives. The one
        caller is engine/states/endgame.py::enter(), which fills it
        from engine/ending_gate.py::is_highly_skilled(ctx).

        Returns:
            {
                "epilogue_title": str,
                "epilogue_lines": list[str],
                "final_credits": int,
                "final_wallet": float,
            }
        """
        ending_title = self.determine_ending_title(player, highly_skilled)
        return {
            "epilogue_title": ending_title,
            "epilogue_lines": self.get_epilogue_lines(ending_title),
            "final_credits": player.get_accumulated_credits(),
            "final_wallet": player.get_wallet_balance(),
        }
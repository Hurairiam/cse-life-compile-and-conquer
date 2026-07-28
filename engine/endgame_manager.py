"""
engine/endgame_manager.py

CSE Life: Compile & Conquer
Engine Package — Endgame Evaluation
─────────────────────────────────────────────────────────────
Spawned by GameSession.trigger_endgame_evaluation() once the session
is frozen (graduation reached, or the year cap hit). Audits the
player's final profile across three dimensions —

    1. Academic State   — accumulated credits (graduated or not)
    2. Skill Profile     — average level across the 12 tracked
                            side-quest skills
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

• Thresholds (confirmed for this iteration):
    TOP_GRADUATE_SKILL_THRESHOLD    = 30.0  (avg skill level, graduates)
    STRONG_SKILLS_DROPOUT_THRESHOLD = 15.0  (avg skill level, dropouts)
  These line up with SideQuest's exp_reward of 15 per attempt — level
  30 ≈ every tracked skill attempted twice on average, level 15 ≈
  every tracked skill attempted once. Easy to retune later.

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

    def determine_ending_title(self, player: "Player") -> str:
        """
        Decide which of the 4 ending titles applies, based on:
          - Academic State: accumulated credits >= 140 -> graduated
          - Skill Profile: average tracked-skill level vs. threshold
        """
        accumulated_credits = player.get_accumulated_credits()
        average_skill_level = self.calculate_average_skill_level(
            player.get_skill_tree()
        )
        graduated = accumulated_credits >= self.GRADUATION_CREDIT_THRESHOLD

        if graduated:
            if average_skill_level >= self.TOP_GRADUATE_SKILL_THRESHOLD:
                return "TOP GRADUATE"
            return "AVERAGE GRADUATE"
        else:
            if average_skill_level >= self.STRONG_SKILLS_DROPOUT_THRESHOLD:
                return "DROP OUT Strong Skills"
            return "DROP OUT Weak Skills"

    def get_epilogue_lines(self, ending_title: str) -> List[str]:
        """
        Look up the narrative epilogue lines for a given ending title.
        Falls back to "AVERAGE GRADUATE" text if the title is somehow
        unrecognised, so render() never receives an empty list.
        """
        return list(
            EPILOGUE_TEXT.get(ending_title, EPILOGUE_TEXT["AVERAGE GRADUATE"])
        )

    def evaluate(self, player: "Player") -> Dict[str, object]:
        """
        Run the full evaluation and return a dict shaped EXACTLY to
        match ui/endgame_screen.py's render() keyword arguments:

            EndgameScreen().render(screen, **manager.evaluate(player))

        Returns:
            {
                "epilogue_title": str,
                "epilogue_lines": list[str],
                "final_credits": int,
                "final_wallet": float,
            }
        """
        ending_title = self.determine_ending_title(player)
        return {
            "epilogue_title": ending_title,
            "epilogue_lines": self.get_epilogue_lines(ending_title),
            "final_credits": player.get_accumulated_credits(),
            "final_wallet": player.get_wallet_balance(),
        }
"""
skill_tree.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation
SkillTree stores all skill node levels as a private dictionary.
Mutations only via incrementSkill() — no direct field access.
Survives across semester resets (aggregated by Player).
─────────────────────────────────────────────────────────────
"""


class SkillTree:
    """
    Stores the player's skill progression across all domains.
    Each skill node is keyed by a string ID and valued by its
    integer level. Queried by evaluateExamResult() to determine
    exam outcomes.

    OOP: Encapsulation — skill data is private, read-only externally.
    """

    def __init__(self) -> None:
        self.__skill_nodes: dict[str, int] = {}

    def get_skill_level(self, skill_id: str) -> int:
        """Return the current level of a skill node (0 if not started)."""
        return self.__skill_nodes.get(skill_id, 0)

    def increment_skill(self, skill_id: str, amount: int) -> None:
        """
        Increase a skill node's level by the given amount.
        Initialises the node at 0 if it has not been seen before.
        Negative increments are ignored.
        """
        if amount <= 0:
            return
        if skill_id not in self.__skill_nodes:
            self.__skill_nodes[skill_id] = 0
        self.__skill_nodes[skill_id] += amount

    def is_skill_unlocked(self, skill_id: str) -> bool:
        """Return True if the skill has been started (level >= 1)."""
        return self.__skill_nodes.get(skill_id, 0) >= 1

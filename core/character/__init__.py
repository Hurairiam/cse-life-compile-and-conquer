"""
core/character/__init__.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
Re-exports Character, Player, and NPC from their individual
modules so that existing imports remain unchanged:
    from core.character import Character  ← still works
    from core.character import Player     ← still works
    from core.character import NPC        ← still works
─────────────────────────────────────────────────────────────
"""

from core.character.base import Character
from core.character.player import Player
from core.character.npc import NPC

__all__ = ["Character", "Player", "NPC"]

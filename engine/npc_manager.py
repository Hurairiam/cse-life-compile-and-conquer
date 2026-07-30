"""
engine/npc_manager.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Composition + Separation of Concerns
Bridges content/npc_roster.py (pure data, owned by Ayesha) into
real core.character.NPC objects the engine can drive.

Why this lives in engine/, not content/:
content/ is intentionally kept as presentation-agnostic pure data
(dicts of strings) — no class construction, no engine coupling, so
it stays trivially readable/editable by whoever owns narrative
content without needing to understand the class hierarchy. The
factory work of turning that data into real objects belongs in the
orchestration layer, same reasoning as RegistrationManager bridging
academic/course_catalog.py's data into gameplay.
─────────────────────────────────────────────────────────────
Sprint 3 — Iteration 13 — Abu Huraira (dev1-hurairiam-core)
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional

from core.character.npc import NPC
from content.npc_roster import NPC_ROSTER, NPC_IDS
from content.dialogues import NPC_DIALOGUES

if TYPE_CHECKING:
    from core.character.player import Player


class NPCManager:
    """
    Owns the roster of NPC objects for the current playthrough.
    Built once at game start (semester_available_from doesn't change
    mid-game, so NPC identity is stable — only their accessibility
    changes as the player's own semester/time pool changes).

    Design notes:
    - "offer" dialogue is intentionally NOT used yet — NPC.offer_quest()
      exists but nothing populates an NPC's quest pool yet (that's
      SideQuest wiring, deferred to a future iteration). Showing an
      "offer" line with no quest behind it would be misleading, so
      interactions currently use greeting -> farewell, or unavailable
      -> [nothing further], depending on the availability window.
    """

    def __init__(self) -> None:
        self.__npcs: Dict[str, NPC] = {}
        self.__build_roster()

    def __build_roster(self) -> None:
        """
        Construct one NPC instance per entry in NPC_ROSTER and load
        its full dialogue set from NPC_DIALOGUES. Runs once, in the
        NPCManager's own constructor — the roster is fixed for the
        whole playthrough, individual NPCs just become accessible or
        inaccessible over time via NPC.expire_for_semester()/
        is_within_availability_window().
        """
        for npc_id in NPC_IDS:
            data = NPC_ROSTER[npc_id]
            npc = NPC(
                character_id=npc_id,
                display_name=data["display_name"],
                location_id=data["location"],
                semester_bound_expiry=data["semester_available_from"],
            )
            # NPC.load_dialogue() takes ONE flat list — flatten
            # greeting + farewell into a single sequence for now.
            # "offer" and "unavailable" are stored separately and
            # selected at interaction time (see get_dialogue_lines()),
            # not loaded onto the NPC object itself.
            dialogue = NPC_DIALOGUES.get(npc_id, {})
            greeting = dialogue.get("greeting", [])
            farewell = dialogue.get("farewell", [])
            npc.load_dialogue(greeting + farewell)
            self.__npcs[npc_id] = npc

    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """Return one NPC by its roster ID, or None if unknown."""
        return self.__npcs.get(npc_id)

    def get_available_npcs(self, current_semester: int) -> List[NPC]:
        """
        Return every NPC whose semester_available_from has been
        reached, in the roster's declared order. This does NOT check
        the 20-day availability window — an NPC "available this
        semester" still shows in the Exploration list even once
        their per-semester window has closed; interacting with them
        then shows their "unavailable" dialogue instead of a real
        greeting (see get_dialogue_lines()).
        """
        return [
            npc for npc_id, npc in self.__npcs.items()
            if NPC_ROSTER[npc_id]["semester_available_from"] <= current_semester
        ]

    def get_dialogue_lines(self, npc_id: str, player: "Player") -> List[str]:
        """
        Decide which dialogue set to show for this interaction:
        - If the NPC's 20-day availability window has closed
          (NPC.is_within_availability_window() is False), return the
          "unavailable" lines.
        - Otherwise return greeting + farewell (the NPC's currently
          loaded dialogue queue).
        Returns [] if npc_id is unknown.
        """
        npc = self.__npcs.get(npc_id)
        if npc is None:
            return []

        if not npc.is_within_availability_window(player):
            return list(NPC_DIALOGUES.get(npc_id, {}).get("unavailable", []))

        dialogue = NPC_DIALOGUES.get(npc_id, {})
        return list(dialogue.get("greeting", [])) + list(dialogue.get("farewell", []))

    def expire_all_for_semester(self) -> None:
        """
        Mark every NPC inaccessible for the rest of the semester.
        Called by the engine when the exploration phase ends (e.g.
        the firewall forces the player into exams) — mirrors the
        pattern GameClock already uses for semester lifecycle events.
        [Sprint 3 — Iteration 13; not yet called from main.py, wiring
        this trigger point is a follow-up once the exam phase itself
        is wired in Iteration 14+]
        """
        for npc in self.__npcs.values():
            npc.expire_for_semester()

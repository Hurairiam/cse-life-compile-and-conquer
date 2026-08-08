"""
engine/dialogue_flow.py
CSE Life: Compile & Conquer — NPC conversation flow and branching
─────────────────────────────────────────────────────────────
One job: run a conversation. Which chain plays, what the portrait
wears, when a branch opens, what the player's reply jumps to, and
what gets remembered about it.

WHY THIS IS ITS OWN FILE
────────────────────────
The same reasoning engine/menu_prop.py records. All of this could
have lived inside engine/states/exploration.py and
engine/states/dialogue.py, but exploration.py is the single busiest
shared file in the repo — the interaction precedence, the day
firewall and the prop dispatch all live there, and every feature
branch wants a piece of it. A new module cannot produce a merge
conflict, so the logic lives here and the two state modules carry
call sites instead of branches.

THE BRANCH
──────────
A DialogChain may end in a choice instead of simply stopping
(content/level_schema.py::DialogChain). When the last line of such a
chain is dismissed, ui/choice_box.py docks above the dialog card with
up to four replies. Picking one either jumps to the chain its `goto`
names or ends the conversation, and the answer is recorded in
ctx.dialogue_choices so it survives a save/load and can be read back
later.

    ctx.dialogue_npc      the NpcData being talked to, or None
    ctx.dialogue_chain    the DialogChain currently playing, or None
    ctx.choice_options    non-empty while a branch is open (the hook
                          engine/states/dialogue.py already draws)
    ctx.choice_prompt     the ALL-CAPS strip above the replies
    ctx.choice_result     the index the player picked, once
    ctx.dialogue_choices  {"<level>:<uid>:<chain>": index} — answered

An answer key is level + npc uid + chain id, so the same NPC placed
in two maps, or asked the same question in two different beats, are
recorded separately.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Any, Optional

from content.level_registry import (
    get_npc_display_name, get_npc_portrait_path)
from engine.screen_manager import ScreenState

# Popup severity is imported lazily inside the failure path so this
# module stays importable by tooling that has no ui/ or pygame.


# ── which chain plays ──────────────────────────────────────────

def chain_index_for(npc_data: Any, semester: int) -> int:
    """
    The chain this NPC plays in `semester`, clamped to what exists.

    One chain per semester of availability, counted from the semester
    the NPC first appears, so the last authored chain repeats forever
    rather than the conversation running out. Lifted verbatim from
    exploration.__talk — the behaviour is unchanged, it just lives
    somewhere a second caller can reach it.
    """
    chains = npc_data.get_chains()
    if not chains:
        return -1
    start = npc_data.get_effective_min_semester()
    return max(0, min(int(semester) - start, len(chains) - 1))


# ── playing a chain ────────────────────────────────────────────

def play_chain(ctx: Any, npc_data: Any, chain: Any) -> bool:
    """
    Load one chain into the dialogue box. False when it will not play.

    The portrait is resolved from the chain's own emotion, falling back
    to the NPC's default, so a branch arm can change the face the
    speaker wears mid-conversation.
    """
    if chain is None:
        return False
    type_id = npc_data.get_type_id()
    portrait = get_npc_portrait_path(type_id, chain.get_emotion() or "neutral")
    if not ctx.dialogue_manager.load_npc_chain(
            chain, portrait, get_npc_display_name(type_id)):
        return False
    ctx.dialogue_npc = npc_data
    ctx.dialogue_chain = chain
    return True


def start_talk(ctx: Any, npc_data: Any) -> bool:
    """
    Begin a conversation with a placed NPC. False when it is refused.

    Refusal covers both the semester gate (the NPC is not around yet)
    and an NPC with no authored chains at all; each plays the error
    sfx, and the gated case says so rather than doing nothing.
    """
    from ui.popup import SEVERITY_INFO

    semester = ctx.semester().get_semester_number()
    if npc_data.get_effective_min_semester() > semester:
        ctx.play_sfx("error")
        ctx.message_popup.open(
            "NOT YET", ["They are not around this semester."], SEVERITY_INFO)
        return False

    index = chain_index_for(npc_data, semester)
    chain = npc_data.get_chain(index) if index >= 0 else None
    if not play_chain(ctx, npc_data, chain):
        ctx.play_sfx("error")
        return False

    ctx.talked_npc_uids.add("%s:%s" % (ctx.level_id, npc_data.get_uid()))
    reset_choice(ctx)
    arm_offer(ctx, npc_data)
    ctx.dialogue_return = ScreenState.EXPLORATION
    ctx.go(ScreenState.DIALOGUE)
    return True


# ── the branch ─────────────────────────────────────────────────

def answer_key(ctx: Any, npc_data: Any, chain: Any) -> str:
    """The ctx.dialogue_choices key for one question."""
    if npc_data is None or chain is None:
        return ""
    return "%s:%s:%s" % (ctx.level_id, npc_data.get_uid(),
                         chain.get_chain_id())


def get_answer(ctx: Any, npc_data: Any, chain: Any) -> Optional[int]:
    """
    The reply index the player already gave, or None.

    Read by anything that needs to know what was said — a later quest
    system, or an author wanting a chain to acknowledge an earlier
    answer. Nothing consumes it inside this module.
    """
    key = answer_key(ctx, npc_data, chain)
    if not key:
        return None
    value = getattr(ctx, "dialogue_choices", {}).get(key)
    return value if isinstance(value, int) else None


def is_choice_open(ctx: Any) -> bool:
    """True while the player owes an answer."""
    return bool(getattr(ctx, "choice_options", None))


def reset_choice(ctx: Any) -> None:
    """
    Close any open branch and clear the widget's own selection.

    Called when a conversation starts and when one ends, so a reply
    list can never leak from one NPC into the next.
    """
    ctx.choice_options = []
    ctx.choice_prompt = ""
    ctx.choice_result = None
    ctx.quest_offer_open = False
    if ctx.choice_box is not None:
        ctx.choice_box.reset()


def open_choice(ctx: Any) -> bool:
    """
    Dock the reply list if the chain that just finished has one.

    False means the chain simply ended, which is the caller's cue to
    leave the conversation.
    """
    chain = getattr(ctx, "dialogue_chain", None)
    if chain is None or not chain.has_choice():
        return False
    labels = chain.get_choice_labels()
    if not labels:
        return False
    ctx.choice_options = labels
    ctx.choice_prompt = chain.get_choice_prompt()
    ctx.choice_result = None
    if ctx.choice_box is not None:
        ctx.choice_box.reset()
    ctx.play_sfx("select")
    return True


def resolve_choice(ctx: Any, index: int) -> bool:
    """
    Act on the reply the player picked. True = the conversation goes on.

    Records the answer first, so it sticks whether the branch continues
    or ends. Then follows the reply's `goto`: a named chain on the same
    NPC continues the conversation there, and anything else — a blank
    goto, or one naming a chain that is not there — ends it. Validation
    already warns about the second case at save time; landing here just
    means the talk stops, never that anything raises.
    """
    npc_data = getattr(ctx, "dialogue_npc", None)
    chain = getattr(ctx, "dialogue_chain", None)

    key = answer_key(ctx, npc_data, chain)
    if key:
        if not isinstance(getattr(ctx, "dialogue_choices", None), dict):
            ctx.dialogue_choices = {}
        ctx.dialogue_choices[key] = int(index)

    goto = chain.get_choice_goto(index) if chain is not None else ""
    ctx.choice_options = []
    ctx.choice_prompt = ""
    ctx.choice_result = None
    if ctx.choice_box is not None:
        ctx.choice_box.reset()

    target = npc_data.find_chain(goto) if (npc_data is not None and goto) \
        else None
    if target is None:
        return False
    ctx.play_sfx("page_turn")
    return play_chain(ctx, npc_data, target)


def end_talk(ctx: Any) -> None:
    """Drop every per-conversation reference on the way out."""
    reset_choice(ctx)
    ctx.dialogue_npc = None
    ctx.dialogue_chain = None
    # An offer left armed but unanswered is not a decision — walking
    # away and coming back must ask it again, so only resolve_offer()
    # ever writes to decided_quest_semesters.
    ctx.pending_quest_npc = None


# ── the semester side-quest offer ──────────────────────────────
# A SECOND reason the reply list can open, and a different kind of
# reason. The branch above is authored per chain in the level editor
# and can jump anywhere; this is one fixed Accept / Decline from
# content/npc_quest_offers.py, offered by one named NPC per term.
#
# They share ui/choice_box.py and ctx.choice_options, so they must
# never be open at once. engine/states/dialogue.py asks the authored
# branch FIRST — it is part of the chain the player is being told —
# and the offer only once that chain has genuinely run out. Nothing in
# the shipped content puts both on the same conversation: semester 3's
# offer is Rafi's, and Rafi's only authored branch is on his
# semester-1 chain.

OFFER_PROMPT: str = "YOUR DECISION"
OFFER_REPLIES: tuple = ("Accept", "Decline")
OFFER_ACCEPT: int = 0


def pending_offer(ctx: Any) -> Optional[dict]:
    """The offer this conversation still owes the player, or None."""
    semester = getattr(ctx, "pending_quest_npc", None)
    if semester is None:
        return None
    from content.npc_quest_offers import SEMESTER_QUEST_OFFERS
    return SEMESTER_QUEST_OFFERS.get(semester)


def arm_offer(ctx: Any, npc_data: Any) -> bool:
    """
    Note that this NPC owes the player a quest offer this term.

    Armed at the START of every talk and cleared at the end, so the
    state cannot outlive the conversation it belongs to. A semester
    already answered is never re-armed — walking back to Purnno after
    declining does not put the question a second time.
    """
    from content.level_registry import get_npc_roster_id
    from content.npc_quest_offers import SEMESTER_QUEST_OFFERS

    ctx.pending_quest_npc = None
    semester = ctx.semester().get_semester_number()
    offer = SEMESTER_QUEST_OFFERS.get(semester)
    if offer is None:
        return False
    if offer.get("npc") != get_npc_roster_id(npc_data.get_type_id()):
        return False
    if semester in getattr(ctx, "decided_quest_semesters", set()):
        return False
    ctx.pending_quest_npc = semester
    return True


def open_offer(ctx: Any) -> bool:
    """
    Put the offer, once the chain has run out. False = nothing owed.

    Unlike an authored branch this REPLACES what is in the dialogue
    box: the offer carries its own lines, so it is asked after
    advance() has emptied the chain rather than while its last line is
    still up. Loading them reactivates the manager, so the reply list
    still has a card to dock above.
    """
    offer = pending_offer(ctx)
    if offer is None:
        return False
    ctx.dialogue_manager.load_dialogue(list(offer["offer_lines"]))
    ctx.choice_options = list(OFFER_REPLIES)
    ctx.choice_prompt = OFFER_PROMPT
    ctx.choice_result = None
    ctx.quest_offer_open = True
    if ctx.choice_box is not None:
        ctx.choice_box.reset()
    ctx.play_sfx("select")
    return True


def is_offer_open(ctx: Any) -> bool:
    """True while the open reply list is the quest offer, not a branch."""
    return bool(getattr(ctx, "quest_offer_open", False))


def resolve_offer(ctx: Any, index: int) -> bool:
    """
    Act on Accept / Decline. True = the conversation goes on.

    Accepting unlocks the quest id; either way the semester is marked
    decided, so the offer is not put again this term. The reply lines
    then play out on their own and the talk ends when they run out.

    ctx.dialogue_chain is dropped first: the chain is over and its
    lines are gone from the box, so leaving it set would let an
    authored branch on it re-open behind the reply lines.
    """
    offer = pending_offer(ctx)
    semester = getattr(ctx, "pending_quest_npc", None)
    ctx.choice_options = []
    ctx.choice_prompt = ""
    ctx.choice_result = None
    ctx.quest_offer_open = False
    ctx.dialogue_chain = None
    if ctx.choice_box is not None:
        ctx.choice_box.reset()
    if offer is None:
        return False

    if int(index) == OFFER_ACCEPT:
        ctx.unlocked_side_quests.add(offer["quest_id"])
        lines = offer["accept_lines"]
    else:
        lines = offer["decline_lines"]
    ctx.decided_quest_semesters.add(semester)
    ctx.pending_quest_npc = None
    ctx.play_sfx("page_turn")
    ctx.dialogue_manager.load_dialogue(list(lines))
    return True

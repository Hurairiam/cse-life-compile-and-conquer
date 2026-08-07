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

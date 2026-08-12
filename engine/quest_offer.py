"""
engine/quest_offer.py
CSE Life: Compile & Conquer — the semester side quest offer
─────────────────────────────────────────────────────────────
One job: decide whether the NPC in front of the player owes them this
term's side quest, and record the answer they give. Everything about
HOW the question is asked — the dialogue card, the reply list, the
portrait — belongs to engine/dialogue_flow.py and is untouched by this
module. What the answer MEANS belongs here.

WHY THIS IS ITS OWN FILE
────────────────────────
The same reasoning engine/menu_prop.py, engine/day_warning.py,
engine/final_exam.py and engine/npc_availability.py all record: a new
module cannot produce a merge conflict, and the alternative was quest
knowledge spread across engine/dialogue_flow.py and the semester
rollover inside engine/states/exam.py. That file carries a one-line
call instead of a branch.

It also keeps the two halves honest about each other. dialogue_flow
knows how to run a conversation and nothing about the five states;
this module knows the five states and nothing about pygame, screens or
the choice box.

THE STATE MACHINE IS NOT MODIFIED, AND NOT REIMPLEMENTED
───────────────────────────────────────────────────────
engine/quest_state.py is used entirely through its public API —
can_offer / accept / decline / expire_unoffered_for_semester — exactly
as Phase 12 left it. The only thing added on top is the tolerance an
interaction path needs: a conversation must never crash the game over
a quest id, and a rollover must never crash over a context that has no
machine on it (the editor, the harnesses, a half-built AppContext).

    ctx.quest_states     the QuestStateMachine (engine/app_context.py)
    ctx.pending_quest_id the quest this conversation owes an answer
                         for, or None. Owned by dialogue_flow for the
                         length of one talk, and never persisted —
                         see WHAT IS NOT WRITTEN below.

WHAT IS NOT WRITTEN, AND WHEN
─────────────────────────────
Arming an offer writes NOTHING. The machine is touched in exactly one
place, resolve(), which runs only when the player has picked Accept or
Decline. So a conversation that is broken off — ESC, quit to menu,
loading a save — leaves the quest Unoffered and the offer is put again
the next time the player talks to that NPC. That is the whole of the
"interrupted conversation" edge case, and it is a property of where
the write is rather than a check anywhere.

resolve() RE-ASKS BEFORE IT WRITES. The offer is armed at the start of
a talk against the semester in hand at that moment, and answered some
seconds later. Nothing in the engine can roll a semester over in
between — the router runs one state at a time and a rollover happens
on the exam screen or at the end_semester prop, never in DIALOGUE — but
the guard costs one comparison and turns "cannot happen" into "cannot
be made to happen". A quest that is no longer this term's, or no longer
Unoffered, is refused and the conversation simply ends.

DAYS ARE NOT CONSULTED (Decision D1, owner ruling)
──────────────────────────────────────────────────
The offer is put whenever the machine says it can be, including on a
term with no days left. The 15-day threshold and the quest's own
day_cost are Phase 17's, and putting either here would mean two places
deciding whether a side quest may be started.
─────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from content.npc_quest_offers import SEMESTER_QUEST_OFFERS
from content.side_quest_definitions import get_quest_for_semester, get_semester
from engine.quest_state import (STATE_DECLINED, STATE_UNOFFERED,
                                QuestStateError)

# The reply list this offer docks, and which index means yes. Two fixed
# replies rather than an authored branch: a DialogChain's `choice` is
# level data and can jump anywhere, and this is one question with one
# meaning that must read identically for all twelve quests.
PROMPT: str = "YOUR DECISION"
REPLIES: tuple = ("Accept", "Decline")
ACCEPT_INDEX: int = 0

# No semester in hand — the editor, the standalone harnesses, a context
# built before STAGE 1. Nothing is offered and nothing expires, the same
# way engine/npc_availability.SEMESTER_ANY filters nobody.
SEMESTER_NONE: int = 0


# ── reading the context ────────────────────────────────────────

def machine_of(ctx: Any) -> Any:
    """
    The QuestStateMachine on `ctx`, or None.

    None disables every function in this module rather than raising.
    The offer path runs inside an interaction and the expiry path runs
    inside a semester rollover; neither is a place where a context that
    happens to have no quest machine should take the game down.
    """
    machine = getattr(ctx, "quest_states", None)
    if machine is None:
        return None
    if not hasattr(machine, "can_offer"):
        return None
    return machine


def semester_of(ctx: Any) -> int:
    """
    The semester `ctx` is in, or SEMESTER_NONE when it has none.

    Never raises, for the reason engine/npc_availability.semester_of()
    gives: whatever a context does when asked for a semester it has not
    got, the answer must be "nothing is offered", never an exception
    thrown out of a conversation.
    """
    getter = getattr(ctx, "semester", None)
    if getter is None:
        return SEMESTER_NONE
    try:
        return int(getter().get_semester_number())
    except Exception:                             # noqa: BLE001 — see above
        return SEMESTER_NONE


# ── the authored lines ─────────────────────────────────────────

def lines_for(quest_id: Any) -> Optional[Dict[str, Any]]:
    """
    The offer / accept / decline lines for one quest, or None.

    content/npc_quest_offers.py is keyed by SEMESTER and
    content/side_quest_definitions.py by QUEST ID, so this hop crosses
    the two — and checks them against each other on the way. A row
    whose `quest_id` does not match the quest the semester table names
    means somebody edited one file and not the other, and the honest
    outcome is no offer at all rather than the right question with the
    wrong quest attached to it.
    """
    semester = get_semester(quest_id)
    if not semester:
        return None
    offer = SEMESTER_QUEST_OFFERS.get(semester)
    if not isinstance(offer, dict):
        return None
    if str(offer.get("quest_id", "")).strip().upper() \
            != str(quest_id or "").strip().upper():
        return None
    if not offer.get("offer_lines"):
        return None
    return offer


# ── the question ───────────────────────────────────────────────

def offered_quest_id(ctx: Any, npc_data: Any) -> Optional[str]:
    """
    The quest this NPC owes the player right now, or None.

    `npc_data` is the NpcData the interaction is holding, and
    get_type_id() is the short NPC_REGISTRY id — which is precisely
    what QuestStateMachine.can_offer() takes (recon §9, Phase 12
    ruling 3). No id translation happens anywhere on this path.

    None covers every ordinary case: this term has no quest, this is
    not the NPC who offers it, or it has already been accepted,
    declined or missed. Only the semester's own NPC is ever answered
    with a quest id, so every other NPC in the game behaves exactly as
    it did before this phase.
    """
    machine = machine_of(ctx)
    if machine is None:
        return None
    semester = semester_of(ctx)
    if semester <= SEMESTER_NONE:
        return None
    type_id = getattr(npc_data, "get_type_id", None)
    if type_id is None:
        return None
    if not machine.can_offer(type_id(), semester):
        return None
    quest_id = get_quest_for_semester(semester)
    if quest_id is None or lines_for(quest_id) is None:
        return None
    return quest_id


def is_still_offerable(ctx: Any, quest_id: Any) -> bool:
    """
    True when `quest_id` is still this term's quest and still unanswered.

    The guard resolve() runs before it writes. Deliberately re-derived
    from the context rather than trusted from the arming call, so an
    answer can only ever land on the quest the game is actually in the
    middle of.

    TASK 2: Declined passes now, for the same reason can_offer() accepts
    it — the offer is live again, so the answer to it must be writable.
    Unlocked, Completed and Missed still fail, which is what stops an
    accepted quest being re-answered.
    """
    machine = machine_of(ctx)
    if machine is None or not quest_id:
        return False
    if get_quest_for_semester(semester_of(ctx)) != quest_id:
        return False
    try:
        return machine.get_state(quest_id) in (STATE_UNOFFERED,
                                               STATE_DECLINED)
    except QuestStateError:
        return False


# ── the answer ─────────────────────────────────────────────────

def resolve(ctx: Any, quest_id: Any, accepted: bool) -> bool:
    """
    Record Accept or Decline. False when nothing was written.

    The ONLY place this module touches the machine.

    TASK 2 — ONLY ACCEPT IS PERMANENT. This used to read "both outcomes
    are permanent ... the question is never put a second time under any
    circumstance", and that is no longer the rule. Accept still ends the
    offer for good: Unlocked answers False from can_offer(). Decline
    leaves the quest offerable, so walking back to the NPC puts the same
    question again, for as long as the term lasts. The boundary is the
    semester, not the answer — expire_semester() moves a still-Declined
    quest to Missed when the term closes.

    ACCEPTING STARTS NOTHING. The quest becomes Unlocked and that is
    all: no lecture, no day charge, no screen, no skill. Phases 14-17
    own what an unlocked quest is worth; this phase owns the answer.

    QuestStateError is caught even though is_still_offerable() has just
    made it unreachable. A conversation is a place where being wrong
    should cost the offer, not the playthrough.
    """
    if not is_still_offerable(ctx, quest_id):
        return False
    machine = machine_of(ctx)
    try:
        if accepted:
            machine.accept(quest_id)
        else:
            machine.decline(quest_id)
    except QuestStateError:
        return False
    return True


# ── the term ending ────────────────────────────────────────────

def expire_semester(ctx: Any, semester: Any = None) -> Optional[str]:
    """
    A term ended: its quest is Missed if it was never put. Returns the
    quest id that expired, or None.

    Called from engine/states/exam.py::close_semester(), which recon §7
    records as the one place in the game a semester rolls over — and
    called BEFORE its freeze check by owner ruling, so a run that ends
    on ENDGAME still closes its books and Phase 16's ending gate sees
    the true picture.

    `semester` defaults to the one `ctx` is currently in, which inside
    close_semester() is the term that is ending: advance_semester() has
    not run yet at the call site.

    THIS IS ALSO WHERE AN UNREACHABLE NPC LANDS. A quest whose NPC the
    player never walked up to — never visited the map, never pressed E,
    or an author's gate hid them for the term — has simply never been
    offered, so it is Missed here along with the ones that were ignored
    on purpose. There is no fallback offer and no second chance: that
    is what Missed is for.
    """
    machine = machine_of(ctx)
    if machine is None:
        return None
    number = semester_of(ctx) if semester is None else semester
    try:
        number = int(number)
    except (TypeError, ValueError):
        return None
    if number <= SEMESTER_NONE:
        return None
    try:
        return machine.expire_unoffered_for_semester(number)
    except QuestStateError:
        return None


# -------------------------------------------------------------
# STUB TEST — the repo's convention for a module with no suite.
# Pure python: no window, no assets, no pygame.
#     py -m engine.quest_offer
# (as a module, so the project root stays on the import path)
#
# The full offer-path coverage, including the three edge cases, is in
# tests/test_quest_offer.py.
# -------------------------------------------------------------
if __name__ == "__main__":
    from engine.quest_state import QuestStateMachine

    class _Npc:
        def __init__(self, type_id):
            self.type_id = type_id

        def get_type_id(self):
            return self.type_id

    class _Sem:
        def __init__(self, number):
            self.number = number

        def get_semester_number(self):
            return self.number

    class _Ctx:
        def __init__(self, number, machine=None):
            self.__sem = _Sem(number)
            self.quest_states = machine or QuestStateMachine()

        def semester(self):
            return self.__sem

    # -- only the semester's own NPC is offered anything -------------
    ctx = _Ctx(1)
    assert offered_quest_id(ctx, _Npc("purnno")) == "SQ_GIT_GITHUB"
    for other in ("rafi", "rahman", "zayan", "kabir", "roya", "hoque"):
        assert offered_quest_id(ctx, _Npc(other)) is None, other

    # -- accepting is permanent, and never asked twice --------------
    assert resolve(ctx, "SQ_GIT_GITHUB", True)
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == "unlocked"
    assert offered_quest_id(ctx, _Npc("purnno")) is None, "asked twice"
    assert not resolve(ctx, "SQ_GIT_GITHUB", False), "answered twice"
    assert ctx.quest_states.get_state("SQ_GIT_GITHUB") == "unlocked"

    # -- declining is NOT permanent (Task 2) ------------------------
    # It holds until the player walks back, and the offer returns for
    # the rest of the term. Accepting stays permanent, above.
    ctx = _Ctx(2)
    assert resolve(ctx, "SQ_OOP", False)
    assert ctx.quest_states.get_state("SQ_OOP") == "declined"
    assert offered_quest_id(ctx, _Npc("rahman")) == "SQ_OOP", \
        "a declined quest was not re-offered"
    assert resolve(ctx, "SQ_OOP", False), "could not decline a second time"
    assert ctx.quest_states.get_state("SQ_OOP") == "declined"
    assert resolve(ctx, "SQ_OOP", True), "could not accept after declining"
    assert ctx.quest_states.get_state("SQ_OOP") == "unlocked"
    assert offered_quest_id(ctx, _Npc("rahman")) is None, \
        "an accepted quest was offered again"

    # -- ...but the term ending IS permanent ------------------------
    ctx = _Ctx(2)
    assert resolve(ctx, "SQ_OOP", False)
    assert expire_semester(ctx) == "SQ_OOP", "a decline outlived its term"
    assert ctx.quest_states.get_state("SQ_OOP") == "missed"
    assert offered_quest_id(ctx, _Npc("rahman")) is None

    # -- a term nobody was talked to ends Missed --------------------
    ctx = _Ctx(3)
    assert expire_semester(ctx) == "SQ_DSA"
    assert ctx.quest_states.get_state("SQ_DSA") == "missed"
    assert offered_quest_id(ctx, _Npc("rafi")) is None, "offered a missed one"
    assert expire_semester(ctx) is None, "expired twice"

    # -- an answered term is left exactly as the player left it -----
    ctx = _Ctx(4)
    assert resolve(ctx, "SQ_WEB_APP_DEV", True)
    assert expire_semester(ctx) is None, "expiry overwrote an answer"
    assert ctx.quest_states.get_state("SQ_WEB_APP_DEV") == "unlocked"

    # -- the guard: an answer can never land on the wrong term -------
    stale = _Ctx(5)
    assert not resolve(stale, "SQ_GIT_GITHUB", True), "answered a stale offer"
    assert stale.quest_states.get_state("SQ_GIT_GITHUB") == "unoffered"

    # -- nothing to work with is quiet, never an exception -----------
    assert offered_quest_id(object(), _Npc("purnno")) is None
    assert expire_semester(object()) is None
    assert not resolve(object(), "SQ_GIT_GITHUB", True)
    assert semester_of(object()) == SEMESTER_NONE
    assert offered_quest_id(_Ctx(1), object()) is None
    assert lines_for("NOPE") is None and lines_for(None) is None

    # -- every one of the twelve is reachable from its own NPC -------
    for number in range(1, 13):
        fresh = _Ctx(number)
        quest_id = get_quest_for_semester(number)
        offer = lines_for(quest_id)
        assert offer is not None, quest_id
        from content.side_quest_definitions import get_npc_id
        assert offered_quest_id(fresh, _Npc(get_npc_id(quest_id))) == quest_id

    print("quest_offer: all checks passed")

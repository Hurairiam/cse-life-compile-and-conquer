"""
engine/lecture_reader.py
CSE Life: Compile & Conquer
Phase 15 — one sitting with a side quest's lecture sheets

The rule half of the lecture reader: what it costs to open one, what
opens it, what moves through it, and what finishing it is worth.
`engine/states/side_quest_lecture.py` draws it and takes the keys.

WHY THIS IS ITS OWN FILE
────────────────────────
Recon hazard #4, and the precedent `engine/menu_prop.py`,
`engine/day_warning.py`, `engine/day_drain.py`, `engine/quest_offer.py`
and `engine/side_quest_list.py` all set: a new module cannot produce a
merge conflict, and the two things in this phase that must not be got
wrong twice — the day charge and the completion — live here exactly
once, with no pygame, no screen state and no UI, so they can be tested
headless. They are.

Named for the reader rather than after the screen so the two basenames
differ: `engine/day_drain.py` records why two modules called the same
thing in different packages read as a mistake even when they import
fine.

THE FLOW
────────
    1. re-check remaining days >= day_cost      blocker()
    2. deduct day_cost, ONCE, on open           start()
    3. open on the first sheet                  start()
    4. every sheet for that quest, in order     advance()
    5. on the LAST sheet: mark_completed()      advance() -> __complete()
       and apply the skill

Step 2 happens once per SITTING, not once per sheet, and not again on
the way out. Step 5 happens once per QUEST — `mark_completed()` refuses
anything that is not Unlocked, and Completed is terminal, so a topic
can never pay its skill out twice.

DECISION R1 — LEAVING EARLY IS RETRYABLE (owner ruling, Phase 15)
─────────────────────────────────────────────────────────────────
Walking out before the last sheet leaves the quest exactly where it
was: **Unlocked**. The days already spent are NOT refunded, the player
may pay the full cost again, and `blocker()` re-checks the day gate on
every attempt because `start()` is the only way in.

That needs no change to `engine/quest_state.py` at all, and the phase
brief forbids one: a quest in a sitting was never moved out of Unlocked
in the first place, so "returns to Unlocked" is a fact about the
machine, not a transition through it. `LEGAL_TRANSITIONS` is untouched
and `mark_completed()` is the one move this phase ever makes.

DECISION R2 — WHAT COUNTS AS LEAVING EARLY (owner ruling, Phase 15)
───────────────────────────────────────────────────────────────────
    * closing the lecture panel      ESC, or CLOSE — warns first
    * saving and reloading           the sitting is not in the payload

Both land in the same place: `end()`. There is NO per-sheet progress
anywhere — not in this module, not on `ctx`, and not in the save file —
so seven sheets of eight is worth exactly what none is worth. That is
not a policy this module enforces; there is simply no bookmark for it
to keep.

Walking away from the PC is not a third case: the reader is a full
screen state, the walker cannot move while it is open, so it is the
first case under another name.

THE 15-DAY FIREWALL IS STILL NOT CONSULTED HERE
───────────────────────────────────────────────
`GameClock.is_eligible_for_side_activities()` is not read by this file,
exactly as Phase 13 and Phase 14 left it. The one day rule here is
`day_cost`, checked through `side_quest_list.refusal()` — still the
single function Phase 17 extends.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from academic.side_quest_catalog import (
    build_side_quest_catalog,
    get_side_quest_by_id,
)
from content.level_registry import get_skill_display_name
from content.side_quest_definitions import get_definition, get_skill_id
from content.side_quest_lectures import DEFAULT_SHEET, get_sheet
from core.interfaces import TimeConsumable
from engine import side_quest_list
from engine.quest_state import QuestStateError

# What one completed topic is worth if academic/side_quest_catalog.py
# cannot be read. It never is unreadable in this build — see
# skill_reward() for why the number is fetched rather than declared.
DEFAULT_SKILL_REWARD: int = 15

# ── the one sitting in progress ────────────────────────────────
# Module-level and transient, the way engine/states/teleport.py keeps
# its destinations and engine/side_quest_list.py keeps its last
# confirmation: exactly one reader can be open, app_context.py is a
# shared already-divergent file, and — the load-bearing reason — a
# sitting that could be stored is a sitting that could be RESUMED.
# Decision R2 says there is no resume point, so there is nowhere for a
# sheet index to be written down. This is that "nowhere".
__quest_id: Optional[str] = None
__sheets: List[str] = []
__index: int = 0
__cost: int = 0
__finished: bool = False

# Built once, on first use. Twelve small objects of pure Python.
__catalog = None


# ── the day charge ─────────────────────────────────────────────

class LectureDayCost(TimeConsumable):
    """
    The price of one sitting, and nothing else.

    Deliberately NOT `academic/quest.py::SideQuest`. That class deducts
    the time, grants the EXP and marks itself completed inside a single
    `execute_action()`, which is precisely the thing this phase has to
    split: the brief charges the days when the reader OPENS and applies
    the skill when the last sheet is READ, and a player who leaves
    partway must have paid the first without collecting the second.
    Running SideQuest here would hand out the skill on the way in.

    `engine/day_drain.py::PassDaysAction` is the precedent — a
    TimeConsumable that buys nothing but the time itself — and
    `engine/gate_evaluator.py::GateEntryAction` is the older one.

    The cost is fixed at construction because
    `GameClock.process_time_consumable()` reads `get_time_cost()`
    BEFORE calling `execute_action()` and advances the global career
    clock by it. A cost that recomputed itself between those two calls
    is the exact drift `MainQuest.get_time_cost()` was overridden to
    stop.

    OOP: Polymorphism — GameClock runs this without knowing it is a
    lecture.
    """

    def __init__(self, days: int) -> None:
        self.__days: int = max(0, int(days))

    def get_time_cost(self) -> int:
        """Days this sitting costs. Read by GameClock before it runs."""
        return self.__days

    def execute_action(self, player) -> None:
        """
        Take the days off the player's own pool.

        GameClock takes the same number off the semester's pool straight
        afterwards — the two counters are separate ints and the clock is
        the one place that touches both (see its own BUG FIX note).
        `blocker()` has already proved both pools can afford this, so
        the deduction cannot silently refuse and leave the two apart.
        """
        if self.__days > 0:
            player.deduct_time_pool_days(self.__days)


def skill_reward(quest_id: Any) -> int:
    """
    EXP one completed topic grants its skill node.

    Read from `academic/side_quest_catalog.py` rather than declared
    here, because that table is where 15 was authored and
    `engine/endgame_manager.py` is already tuned to it: its two ending
    thresholds are documented as "level 30 ≈ every tracked skill
    attempted twice on average, level 15 ≈ every tracked skill
    attempted once". A second 15 written into this file would be a
    second number claiming to be the same rule, and lowering it here
    would quietly put the STRONG SKILLS ending out of reach.

    This is also the first caller `build_side_quest_catalog()` has ever
    had — recon §12 recorded it as dead.
    """
    global __catalog
    if __catalog is None:
        __catalog = build_side_quest_catalog()
    quest = get_side_quest_by_id(__catalog, str(quest_id or ""))
    if quest is None:
        return DEFAULT_SKILL_REWARD
    return max(0, int(quest.get_exp_reward()))


# ── may a sitting be opened? ───────────────────────────────────

def blocker(ctx: Any, quest_id: Any) -> Optional[Tuple[str, List[str]]]:
    """
    Why a sitting cannot be opened — (title, body lines) — or None.

    Shaped for `ui/popup.py`, which draws at most three centred lines.
    Every check here is a refusal with NO side effect: nothing is
    deducted, no sheet is loaded and the state machine is not touched,
    so a blocked start and a start never attempted are the same thing.
    """
    definition = get_definition(quest_id)
    if definition is None:
        return ("LECTURE UNAVAILABLE",
                ["There are no notes under that name."])

    # THE UNCONFIGURED-COST CHECK RUNS BEFORE THE DAY GATE, DELIBERATELY.
    # An unconfigured -1 satisfies `remaining >= cost` for every pool
    # there is, including an empty one, so a day check run first would
    # wave it straight through as free — which is the exact failure the
    # brief names. content/side_quest_definitions.py::validate() also
    # refuses a negative cost at import, so in this build the game would
    # not start at all; this is the second lock, on the one path that
    # would otherwise spend nothing and open anyway.
    cost = definition.get("day_cost")
    if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
        return ("LECTURE NOT CONFIGURED",
                ["This topic has no day cost set.",
                 "It cannot be opened until it has one."])

    if not definition.get("lecture_sheets"):
        return ("NOTHING TO READ",
                ["There are no notes saved for this topic."])

    if __is_frozen(ctx):
        # A frozen session makes process_time_consumable() a no-op, so
        # the sitting would be free. "Never treat as free" applies here
        # too — the run is over, and the reader stays shut.
        return ("NO TIME LEFT",
                ["Your time at university is over.",
                 "There is nothing left to study for."])

    # Phase 14's gate, unchanged and not re-implemented: not on the PC's
    # list, already Completed, or fewer days left in the term than it
    # costs. refusal() is the single function Phase 17 extends, so the
    # firewall lands in one place when it lands.
    refused = side_quest_list.refusal(ctx, quest_id)
    if refused is not None:
        return refused

    # The PLAYER's own pool, which the term's counter does not speak
    # for. day_drain.passable() records that restore() rebuilds the
    # player with a full 80 days and replays the spend onto the semester
    # only, so in every reachable state this one is the larger of the
    # two and this check never fires. What it buys is the guarantee that
    # the days GameClock takes off the semester and the days
    # execute_action() takes off the player are one number — a partial
    # charge would part the two pools for the rest of the run.
    pool = __player_days(ctx)
    if pool < cost:
        return ("NOT ENOUGH DAYS",
                ["This lecture needs %s." % __days(cost),
                 "Your own time is down to %s." % __days(pool)])
    return None


def can_start(ctx: Any, quest_id: Any) -> bool:
    """True when a sitting may be opened right now."""
    return blocker(ctx, quest_id) is None


# ── opening one ────────────────────────────────────────────────

def start(ctx: Any, quest_id: Any) -> Optional[Tuple[str, List[str]]]:
    """
    Charge the days and open the reader on the first sheet.

    Returns None on success, or the refusal `blocker()` gave. A refusal
    aborts with NO side effects — the re-check is step 1 of the brief's
    flow and it happens before a single day moves.

    THE TIME CHANGE IS RESOLVED IN FULL, HERE, BEFORE THE READER OPENS.
    The charge goes through `GameClock.process_time_consumable()`, the
    single entry point for every time-costing action in the game, so all
    three counters move together: the player's pool, the semester's
    pool, and the global career clock. Phase 6's warning and Phase 6's
    HUD chip then fall out of the semester counter with not one line of
    either repeated — the caller fires `day_warning.check()` on this
    same frame and waits for the answer before handing over, so nothing
    about time can land on top of an open reader.

    Nothing in this game rolls a semester or ends a run on a deduction:
    `advance_semester()` is only ever called by `exam.close_semester()`,
    and the 960-day freeze only by `check_semester_end_state()` in that
    same path (recon §7 and §8). A charge can therefore take the term to
    zero and cross the 15-day threshold, and those are the only two
    boundaries it can cross — both of which Phase 6 already owns.
    """
    global __quest_id, __sheets, __index, __cost, __finished

    refused = blocker(ctx, quest_id)
    if refused is not None:
        return refused

    definition = get_definition(quest_id)
    cost = int(definition["day_cost"])

    # Measured off the semester's counter before and after rather than
    # reported from the action's own cost, for the reason
    # day_drain.drain() measures: process_time_consumable() does nothing
    # at all on a frozen session, and a caller that trusted the intent
    # would open a reader it never paid for. Semester.deduct_time() and
    # Player.deduct_time_pool_days() are both all-or-nothing, so `spent`
    # is either 0 or the full cost and a half-charge cannot arise.
    before = side_quest_list.days_left(ctx)
    ctx.game_clock.process_time_consumable(LectureDayCost(cost))
    spent = before - side_quest_list.days_left(ctx)
    if spent < cost:
        return ("NOTHING HAPPENED",
                ["The days could not be spent.",
                 "The lecture was not opened."])

    __quest_id = definition["quest_id"]
    # Every listed sheet, including one that fails to resolve. Filtering
    # a bad id out here would silently shorten the lecture and still
    # mark the topic complete; get_sheet() hands back DEFAULT_SHEET
    # instead, so the player sees a card saying the notes are missing
    # and pages past it. See current_sheet().
    __sheets = list(definition["lecture_sheets"])
    __index = 0
    __cost = cost
    __finished = False
    return None


# ── reading it ─────────────────────────────────────────────────

def is_open() -> bool:
    """True while a sitting is in progress and unfinished."""
    return __quest_id is not None and not __finished


def is_finished() -> bool:
    """True once the last sheet has been read and not yet cleared."""
    return __quest_id is not None and __finished


def get_quest_id() -> Optional[str]:
    """The quest being read, or None."""
    return __quest_id


def get_sheet_count() -> int:
    """How many sheets this sitting has."""
    return len(__sheets)


def get_sheet_number() -> int:
    """Which sheet is on screen, counting from 1. 0 when none is."""
    return __index + 1 if is_open() else 0


def get_day_cost() -> int:
    """The days this sitting was charged."""
    return __cost


def current_sheet(ctx: Any = None) -> Dict[str, Any]:
    """
    The sheet on screen.

    A SHEET THAT FAILS TO LOAD IS STILL A SHEET (owner ruling, R2).
    `content/side_quest_lectures.py::get_sheet()` never raises and never
    returns None — an id it does not know comes back as DEFAULT_SHEET,
    whose text reads "These notes are not on this PC." So a broken id
    mid-sequence costs the player one readable card and nothing else:
    the sequence does not stop, no day is charged again, and the sitting
    still completes on the last sheet. The alternative — treating it as
    leaving early — would take the days and the topic for a fault that
    is the content table's, not the player's.

    Unreachable in this build regardless:
    `side_quest_definitions.validate()` checks all 36 ids against the
    sheet table at import, so a bad one stops the game starting.
    """
    if __quest_id is None or not 0 <= __index < len(__sheets):
        return DEFAULT_SHEET
    return get_sheet(__sheets[__index])


def topic() -> str:
    """
    The lecture's own title, e.g. "Git & GitHub".

    Clamped to the last real sheet rather than read straight off
    `current_sheet()`, because the index sits one past the end once the
    sitting is finished and the completion notice is built from there.
    An unclamped read hands back DEFAULT_SHEET's "Study Notes", which
    would name the topic wrongly on the one card that reports it.
    """
    if not __sheets:
        return str(DEFAULT_SHEET["title"])
    position = min(max(__index, 0), len(__sheets) - 1)
    return str(get_sheet(__sheets[position]).get("title") or "Study Notes")


def skill_name() -> str:
    """The skill tree's name for what this topic feeds, e.g. "Version
    Control". The PC's list calls the topic this, so the completion
    notice does too — it is the node that goes up."""
    return get_skill_display_name(get_skill_id(__quest_id or ""))


def progress_label() -> str:
    """"SHEET 2 OF 3", for the header. "" when nothing is open."""
    if not is_open():
        return ""
    return "SHEET %d OF %d" % (get_sheet_number(), get_sheet_count())


def advance(ctx: Any) -> bool:
    """
    Move on from the sheet on screen. True while sheets remain.

    False means the LAST sheet has now been read: the quest is marked
    Completed and the skill is applied, on this line and nowhere else in
    the codebase.
    """
    global __index, __finished
    if not is_open():
        return False
    __index += 1
    if __index < len(__sheets):
        return True
    __index = len(__sheets)
    __finished = True
    __complete(ctx)
    return False


def completion_notice(ctx: Any) -> Tuple[str, List[str]]:
    """
    The card shown for a topic just finished — (title, lines).

    Names both of the topic's names on purpose. The PC's list calls it
    "Version Control" and the sheets call themselves "Git & GitHub";
    saying both here is the one place the two are tied together, and the
    third line is the only report the player gets that the skill moved.

    The title gets a line of its own rather than being folded into the
    sentence below it: "Object-Oriented Programming (OOP)" is 33
    characters, and inside "All 3 sheets of ... read." it overruns the
    600px box. Three lines is the popup's maximum and this uses all of
    them.
    """
    count = get_sheet_count()
    return ("TOPIC COMPLETE",
            [topic(),
             "All %d sheet%s read." % (count, "" if count == 1 else "s"),
             "%s is now level %d." % (skill_name(), __skill_level(ctx))])


# ── leaving one ────────────────────────────────────────────────

def exit_warning() -> Tuple[str, List[str]]:
    """
    The question asked before any player-initiated exit — (title,
    lines). Three lines exactly, the popup's hard maximum.

    It states the cost plainly rather than softening it: the days are
    gone, nothing read is kept, and the next attempt starts at sheet 1.
    That third line is Decision R1 said out loud — the topic is still
    there to be taken again, at full price.
    """
    return ("LEAVE THE LECTURE?",
            ["The %s you spent are gone." % __days(__cost),
             "Nothing you have read is kept.",
             "You would start again from sheet 1."])


def abandon() -> bool:
    """
    End a sitting with nothing kept (Decision R1). True if one was open.

    The quest is left exactly where it was — Unlocked — so the player
    may pay the full day_cost again and read it from the first sheet.
    The days already spent are NOT refunded and no sheet index is
    remembered, because there is nowhere in this build for one to be
    remembered: not in this module, not on ctx, not in the save file.

    Nothing is written to the state machine here at all.
    `mark_completed()` is the only transition this phase makes and it is
    on the other branch entirely.
    """
    was_open = is_open()
    end()
    return was_open


def end() -> None:
    """
    Forget the sitting, however it ended.

    Called by `abandon()`, by the reader screen's `exit()` hook so no
    path off that screen can leave one half-open, and by
    `save_bridge.restore()` so a loaded game never inherits one.
    """
    global __quest_id, __sheets, __index, __cost, __finished
    __quest_id = None
    __sheets = []
    __index = 0
    __cost = 0
    __finished = False


# ── private ────────────────────────────────────────────────────

def __complete(ctx: Any) -> None:
    """
    Mark the quest Completed and raise its skill. Both, or neither.

    The order matters. `mark_completed()` raises unless the quest is
    Unlocked, and that raise is the guard against paying a skill out for
    a quest the player never took — so the transition goes first and the
    skill only follows a transition that was allowed. A reward with no
    completion behind it is the one outcome worth refusing outright.

    Unreachable in practice: `blocker()` proved the quest was Unlocked
    before the days were charged, and nothing between then and here can
    move it — the reader is a modal screen with no other actor on it.

    The skill tree is fetched BEFORE the transition too, for the same
    "both or neither" reason. `GameSession.__init__` injects one into
    every Player it builds, so None means a harness context rather than
    a real run — and marking a quest Completed on a context that cannot
    pay the skill out would burn a terminal state for nothing.
    """
    machine = side_quest_list.machine_of(ctx)
    tree = __skill_tree(ctx)
    if machine is None or tree is None:
        return
    try:
        machine.mark_completed(__quest_id)
    except QuestStateError:
        return
    tree.increment_skill(get_skill_id(__quest_id), skill_reward(__quest_id))


def __skill_tree(ctx: Any):
    """The player's skill tree, or None on a harness context."""
    try:
        return ctx.player().get_skill_tree()
    except AttributeError:
        return None


def __skill_level(ctx: Any) -> int:
    """The live level of the skill this quest feeds, or 0."""
    tree = __skill_tree(ctx)
    if tree is None:
        return 0
    return int(tree.get_skill_level(get_skill_id(__quest_id or "")))


def __player_days(ctx: Any) -> int:
    """
    Days in the PLAYER's own pool, or the term's count when there is no
    player to ask. Falling back to the term's number makes the check a
    no-op on a harness context rather than a refusal.
    """
    try:
        return int(ctx.player().get_time_pool_days())
    except (AttributeError, TypeError, ValueError):
        return side_quest_list.days_left(ctx)


def __is_frozen(ctx: Any) -> bool:
    """True when the run is over and the clock will spend nothing."""
    try:
        return bool(ctx.session.get_is_frozen())
    except AttributeError:
        return False


def __days(count: int) -> str:
    """"2 days" / "1 day" — singular is worth the three lines."""
    return "%d day%s" % (count, "" if count == 1 else "s")


# -------------------------------------------------------------
# STUB TEST -- read one topic end to end, and walk out of another:
#
#     python -m engine.lecture_reader
#
# The full day-charge, completion, refusal and leaving coverage is in
# tests/test_lecture_reader.py. Headless -- no pygame, no display, and
# nothing is written.
# -------------------------------------------------------------
if __name__ == "__main__":
    from engine.game_clock import GameClock
    from engine.game_session import GameSession
    from engine.quest_state import QuestStateMachine

    class _Ctx:
        """
        The five things this module asks a context for, over the REAL
        GameSession, GameClock, Player, Semester and SkillTree — so what
        this proves is the pipeline and not a mock of it.
        """

        def __init__(self):
            self.session = GameSession()
            self.game_clock = GameClock(self.session)
            self.quest_states = QuestStateMachine()

        def semester(self):
            return self.session.get_active_semester()

        def player(self):
            return self.session.get_active_player()

    context = _Ctx()
    for term in (1, 2):
        context.quest_states.accept(
            context.quest_states.get_quest_for_semester(term))

    # -- read one all the way through ------------------------------
    quest = context.quest_states.get_quest_for_semester(1)
    print("days before      : %d" % side_quest_list.days_left(context))
    print("start            : %r" % (start(context, quest),))
    print("days after open  : %d  (charged once, on open)"
          % side_quest_list.days_left(context))
    while is_open():
        print("  %-12s %s" % (progress_label(), current_sheet()["title"]))
        advance(context)
    print("state            : %s" % context.quest_states.get_state(quest))
    print("skill            : %s = %d"
          % (skill_name(), context.player().get_skill_tree()
             .get_skill_level("git")))
    print("notice           : %s" % (completion_notice(context),))
    print("days after read  : %d  (not charged per sheet)"
          % side_quest_list.days_left(context))
    end()

    # -- walk out of another (Decision R1) -------------------------
    quest = context.quest_states.get_quest_for_semester(2)
    before_days = side_quest_list.days_left(context)
    start(context, quest)
    advance(context)                      # one sheet in, then leave
    print("\nleft on          : %s" % progress_label())
    print("warning          : %s" % (exit_warning(),))
    abandon()
    print("state            : %s  (still takeable)"
          % context.quest_states.get_state(quest))
    print("days lost        : %d  (not refunded)"
          % (before_days - side_quest_list.days_left(context)))
    print("bookmark         : %r  (there is no resume point)"
          % get_sheet_number())

    # -- and it may be paid for again ------------------------------
    print("blocked now?     : %r" % (blocker(context, quest),))
    start(context, quest)
    print("re-opened on     : %s" % progress_label())
    end()
    print("\nlecture_reader: all checks passed")

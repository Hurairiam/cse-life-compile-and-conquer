"""
engine/npc_availability.py
CSE Life: Compile & Conquer — who is actually on the map this term
─────────────────────────────────────────────────────────────
An NPC who is not available in the current semester is not there.
Not drawn, not talked to, not stood in front of — absent, the way
they are absent from the story until their term comes round.

WHY THIS IS ITS OWN FILE
────────────────────────
The same reason engine/menu_prop.py, engine/day_warning.py and
engine/final_exam.py are. The alternative was three branches in three
shared files — one in ui/map_screen.py to skip the sprite, one in
engine/states/exploration.py to skip the [E] TALK chip and the talk,
and one wherever the collision grid is baked. All three files are
already divergent from main; this one is new and cannot conflict.

THE RULE IS NOT DEFINED HERE
────────────────────────────
It is content/npc_roster.py::NPC_ROSTER[...]["semester_available_from"],
Ayesha's file, one integer per NPC:

    purnno 1 · rafi 1 · rahman 1 · zayan 2 · kabir 3 · roya 4 · hoque 5

A LOWER BOUND ONLY. Nothing in the narrative data ever takes an NPC
away again, so once someone has appeared they stay for the rest of the
degree, and only semesters 1-4 look any different from semester 12.
That reading is corroborated by the authored dialogue itself: every
NPC carries exactly one chain per semester from their debut through
semester 12 (Rafi's 14 are 12 plus his two branch arms).

The number reaches this module through the chain the repo already had:
content/level_registry.py::_bind_roster_fields() stamps it onto every
NPC_REGISTRY entry at import, and NpcData.get_effective_min_semester()
returns the stricter of that and the NPC's own editor gate. Reading it
through that method rather than the roster directly is deliberate —
engine/dialogue_flow.py::start_talk() and chain_index_for() both
already do, so an NPC delayed by an author's gate is hidden on exactly
the semester they would have been refused a conversation on. No NPC in
the repo carries a gate today, so the two agree everywhere.

WHERE IT IS APPLIED — ON THE DOCUMENT, BEFORE THE LEVEL IS BUILT
────────────────────────────────────────────────────────────────
    read_level()  ->  LevelData  ->  validate()  ->  [FILTER]  ->  Level

engine/level_loader.py::Level.__init__ bakes its NPC list, its
{cell: npc} lookup AND its O(1) collision grid out of the document it
is handed — content/level_schema.py::is_cell_walkable() is what makes
an NPC solid. So an NPC removed from the document one step earlier is
absent from all three at once: ui/map_screen.py has nothing to draw,
exploration.verb_for()/__interact() get None from get_npc_at(), and
the cell they stood on is walkable. One filter, three requirements,
and not one line of branching in the consumers.

AFTER validate(), never before. A level is judged exactly as it was
authored — the same blockers, the same warnings, in semester 1 and in
semester 12 — because which term the player is in must never decide
whether a map is well formed.

The document is the loader's own throwaway copy, built fresh from the
JSON on every load. Nothing is written back: engine/level_loader.py is
a one-way door, and the file on disk never learns what semester it was
read in.

NOTHING NEEDS TO REMEMBER ANYTHING
──────────────────────────────────
"A returning NPC reappears at its correct position with no manual
intervention" is free, because the filter runs at load and every route
into a new semester drops the loaded level:

    engine/states/registration.py:72   ctx.level = None  (every rollover)
    engine/save_bridge.py:167          ctx.level = None  (every load)

So the next ensure_level() rebuilds the map from the JSON against the
new semester number, and an NPC whose term has come is back on the
cell the file always said they stood on. No state, no save key, no
SAVE_SCHEMA_VERSION bump, and nothing to reset.
─────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Any, List

# A semester of 0 means "no semester in hand" — filter nothing. It is
# what the level editor, the standalone harnesses and every existing
# load_level() caller pass by omission, so tooling keeps seeing the map
# exactly as it was authored.
SEMESTER_ANY: int = 0

MIN_SEMESTER_DEFAULT: int = 1


# ── the rule ───────────────────────────────────────────────────

def min_semester_of(npc_data: Any) -> int:
    """
    The semester this NPC first appears in.

    get_effective_min_semester() is the roster figure widened by any
    gate the author set — see the header. Anything that cannot answer
    is treated as always present: a placement this module does not
    understand must never be made to vanish.
    """
    getter = getattr(npc_data, "get_effective_min_semester", None)
    if getter is None:
        return MIN_SEMESTER_DEFAULT
    try:
        return int(getter())
    except (TypeError, ValueError):
        return MIN_SEMESTER_DEFAULT


def is_available(npc_data: Any, semester: int) -> bool:
    """
    Is this NPC on the map in `semester`?

    A lower bound and nothing else, because that is all Ayesha's data
    says. SEMESTER_ANY (and any non-positive number) answers True for
    everyone — the editor and the harnesses have no semester and must
    keep seeing the whole cast.
    """
    try:
        number = int(semester)
    except (TypeError, ValueError):
        return True
    if number <= SEMESTER_ANY:
        return True
    return min_semester_of(npc_data) <= number


def semester_of(ctx: Any) -> int:
    """
    The semester `ctx` is in, or SEMESTER_ANY when it has none.

    Never raises. A context without a live GameSession — the editor,
    a harness, a half-built AppContext during STAGE 2 — filters nobody
    rather than crashing the level load.

    The except is deliberately broad, which is rare in this repo. This
    runs inside load_level(): whatever a context does when asked for a
    semester it has not got, the answer must be "no filtering", never
    an exception that takes the map down with it.
    """
    getter = getattr(ctx, "semester", None)
    if getter is None:
        return SEMESTER_ANY
    try:
        return int(getter().get_semester_number())
    except Exception:
        return SEMESTER_ANY


# ── applying it ────────────────────────────────────────────────

def hidden_in(document: Any, semester: int) -> List[str]:
    """
    The uids `apply_to_document` would remove, without removing them.

    Read by the tests and by anything that wants to report on a term
    without disturbing the document.
    """
    return [npc.get_uid() for npc in document.get_npcs()
            if not is_available(npc, semester)]


def apply_to_document(document: Any, semester: int) -> List[str]:
    """
    Drop every NPC who is not around in `semester`. Returns their uids.

    Called by engine/level_loader.py::load_level() between validation
    and Level construction — see the header for why that is the one
    place this belongs.

    A cell holds at most one NPC (Spec §4.3): the editor's add_npc()
    replaces whatever was standing there, and both Level.__npc_at and
    LevelData.get_npc_at() assume it. The identity check below is
    belt-and-braces for a hand-edited file that stacked two anyway —
    a shadowed NPC is already invisible to the document's own lookup,
    and removing by cell would take the wrong one, so it is left
    alone rather than guessed at.
    """
    removed: List[str] = []
    for npc in document.get_npcs():
        if is_available(npc, semester):
            continue
        cell = npc.get_position()
        if document.get_npc_at(*cell) is not npc:
            continue
        if document.remove_npc_at(*cell):
            removed.append(npc.get_uid())
    return removed


# -------------------------------------------------------------
# STUB TEST — the repo's convention for a module with no suite.
# Pure python: no window, no assets, no pygame.
#     py -m engine.npc_availability
# (as a module, so the project root stays on the import path)
# -------------------------------------------------------------
if __name__ == "__main__":

    class _Npc:
        def __init__(self, uid, cell, min_semester):
            self.uid, self.cell, self.min = uid, cell, min_semester

        def get_uid(self):
            return self.uid

        def get_position(self):
            return self.cell

        def get_effective_min_semester(self):
            return self.min

    class _Doc:
        def __init__(self, npcs):
            self.npcs = list(npcs)

        def get_npcs(self):
            return list(self.npcs)

        def get_npc_at(self, x, y):
            return next((n for n in self.npcs if n.cell == (x, y)), None)

        def remove_npc_at(self, x, y):
            npc = self.get_npc_at(x, y)
            if npc is None:
                return False
            self.npcs.remove(npc)
            return True

    class _Sem:
        def __init__(self, number):
            self.number = number

        def get_semester_number(self):
            return self.number

    class _Ctx:
        def __init__(self, number):
            self.__sem = _Sem(number)

        def semester(self):
            return self.__sem

    # The shipped cast, at the cells they actually occupy.
    def cast():
        return _Doc([_Npc("purnno", (10, 12), 1), _Npc("rafi", (8, 6), 1),
                     _Npc("rahman", (8, 5), 1), _Npc("zayan", (11, 11), 2),
                     _Npc("kabir", (12, 6), 3), _Npc("roya", (10, 9), 4),
                     _Npc("hoque", (12, 5), 5)])

    # -- the rule ---------------------------------------------------
    hoque = _Npc("hoque", (12, 5), 5)
    assert not is_available(hoque, 4), "hoque is not around in semester 4"
    assert is_available(hoque, 5), "hoque debuts in semester 5"
    assert is_available(hoque, 12), "nobody leaves once they arrive"
    assert is_available(hoque, SEMESTER_ANY), "no semester filters nobody"
    assert is_available(hoque, 0) and is_available(hoque, -3)
    assert is_available(_Npc("mystery", (0, 0), 1), 1)

    class _Opaque:
        def get_uid(self):
            return "opaque"

        def get_position(self):
            return (0, 0)

    assert is_available(_Opaque(), 1), "an unreadable NPC stays put"
    assert min_semester_of(_Opaque()) == MIN_SEMESTER_DEFAULT

    # -- semester by semester ---------------------------------------
    expected = {1: ["zayan", "kabir", "roya", "hoque"],
                2: ["kabir", "roya", "hoque"],
                3: ["roya", "hoque"],
                4: ["hoque"],
                5: [], 6: [], 9: [], 12: []}
    for number, gone in expected.items():
        assert hidden_in(cast(), number) == gone, f"semester {number}"
        document = cast()
        assert apply_to_document(document, number) == gone
        left = [n.get_uid() for n in document.get_npcs()]
        assert all(uid not in left for uid in gone), f"semester {number} left"
        assert len(left) == 7 - len(gone)

    # -- positions survive, and so does everyone else ----------------
    document = cast()
    apply_to_document(document, 4)
    kept = {n.get_uid(): n.get_position() for n in document.get_npcs()}
    assert kept == {"purnno": (10, 12), "rafi": (8, 6), "rahman": (8, 5),
                    "zayan": (11, 11), "kabir": (12, 6), "roya": (10, 9)}
    assert document.get_npc_at(12, 5) is None, "hoque's cell must be empty"

    # A term later he is back, on the cell the file always gave him,
    # with nobody having reset anything.
    document = cast()
    assert apply_to_document(document, 5) == []
    assert document.get_npc_at(12, 5).get_uid() == "hoque"

    # -- no semester in hand: the editor and the harnesses -----------
    document = cast()
    assert apply_to_document(document, SEMESTER_ANY) == []
    assert len(document.get_npcs()) == 7, "tooling sees the whole cast"

    # -- reading the semester off a context -------------------------
    assert semester_of(_Ctx(7)) == 7
    assert semester_of(object()) == SEMESTER_ANY, "no session, no filtering"

    class _Broken:
        def semester(self):
            raise RuntimeError("no active semester")

    try:
        assert semester_of(_Broken()) == SEMESTER_ANY
    except RuntimeError:
        raise AssertionError("semester_of must never raise") from None

    # -- a stacked cell is left alone, not guessed at ----------------
    stacked = _Doc([_Npc("first", (3, 3), 1), _Npc("second", (3, 3), 9)])
    assert apply_to_document(stacked, 1) == [], "shadowed NPC not removed"
    assert len(stacked.get_npcs()) == 2

    print("npc_availability: all checks passed")

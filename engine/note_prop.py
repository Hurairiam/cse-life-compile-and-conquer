"""
engine/note_prop.py
CSE Life: Compile & Conquer — the note prop

One job: a prop whose interaction kind is "note" shows the text its
author typed in the level editor, and nothing else happens.

A sign outside the lecture hall, a poster on the corridor wall, a page
left on a desk. The player presses E and reads it.

WHY THIS IS ITS OWN FILE
────────────────────────
The same reasoning `engine/menu_prop.py` records, and the file this one
is deliberately modelled on: `engine/states/exploration.py` is the
busiest shared module in the repository — the interaction precedence,
the travel dispatch and the prop payouts all live there and every
feature branch wants a piece of it. A new module cannot produce a merge
conflict, so the behaviour lives here and that file carries a one-line
call beside the one it already carries for menus.

READ EVERY TIME, LIKE A MENU AND UNLIKE A PAYOUT
────────────────────────────────────────────────
`__trigger_prop()` calls this BEFORE the per-semester trigger cap, in
the same band as `menu_prop.trigger()` and the travel check, for the
reason that band exists: a doorway usable three times a term would be
nonsense, and so would a notice that stops being readable in March.
A note grants nothing, so there is nothing to budget and nothing to
stop the player reading it again.

Anything that should restrict WHO may read one goes on the prop's
GATE, which `__interact()` has already evaluated by the time this runs.

WHERE THE TEXT LIVES
────────────────────
`content/level_schema.py::PropData` — `note_title` and `note_lines`
inside the prop's `interaction` block, written into `levels/*.json`
only when something was actually typed, so every level authored before
notes existed round-trips byte for byte. The editor authors them in
`tools/editor_popups.py::PropSettingsPopup`.

The shape is `ui/popup.py`'s and the caps are enforced by the schema on
the way in: one title of at most `NOTE_TITLE_MAX`, at most
`NOTE_LINES_MAX` body lines of `NOTE_LINE_MAX` each. The popup neither
wraps nor truncates, so those caps are what stops a long line running
off both sides of the card.
"""
from __future__ import annotations

from typing import Any, List

from content.level_registry import NOTE_TITLE_DEFAULT


def shows(prop: Any) -> bool:
    """
    True when interacting with `prop` should show a note.

    Delegated to `PropData.shows_note()` rather than re-tested here —
    interactable, kind, and text actually present are one question, and
    asking it in two places is how the editor and the game come to
    disagree about what a prop does. Never raises: anything that is not
    a prop simply is not a note.
    """
    getter = getattr(prop, "shows_note", None)
    if getter is None:
        return False
    try:
        return bool(getter())
    except Exception:                             # noqa: BLE001 — see above
        return False


def title_of(prop: Any) -> str:
    """
    The heading the card wears.

    Falls back to the registry's default rather than to a blank, so a
    note whose title was cleared by hand in the JSON still opens with a
    heading instead of an empty bar.
    """
    try:
        return str(prop.get_note_title() or NOTE_TITLE_DEFAULT)
    except AttributeError:
        return NOTE_TITLE_DEFAULT


def lines_of(prop: Any) -> List[str]:
    """The body lines, already clamped and blank-stripped by the schema."""
    try:
        return list(prop.get_note_lines())
    except AttributeError:
        return []


def trigger(ctx: Any, prop: Any) -> bool:
    """
    Show the note. False means this prop is not a note — carry on.

    The return value is what lets `exploration.__trigger_prop()` stay
    one line: True is "handled, stop here", exactly the contract
    `engine/menu_prop.py::trigger()` already has, so the two calls read
    the same and the dispatch chain keeps its shape.

    NOTHING IS RECORDED. No trigger is spent, no uid is added to
    `ctx.triggered_prop_uids`, no state moves and no day is charged. A
    note is read, not taken — there is nothing about it worth carrying
    in the save file, and a sign that remembered how often it had been
    looked at would be remembering the wrong thing.
    """
    if not shows(prop):
        return False
    from ui.popup import SEVERITY_INFO
    ctx.play_sfx("select")
    ctx.message_popup.open(title_of(prop), lines_of(prop), SEVERITY_INFO)
    return True


# -------------------------------------------------------------
# STUB TEST — the repo's convention for a module with no suite.
# Pure python: no window, no assets, no pygame beyond what the schema
# already needs.
#     py -m engine.note_prop
# (as a module, so the project root stays on the import path)
# -------------------------------------------------------------
if __name__ == "__main__":
    from content.level_schema import PropData

    class _Popup:
        def __init__(self):
            self.opened = []

        def open(self, title, lines, accent):
            self.opened.append((title, list(lines)))

    class _Ctx:
        def __init__(self):
            self.message_popup = _Popup()

        def play_sfx(self, key):
            pass

    def note(**kwargs):
        """A note prop with whatever this case wants set on it."""
        prop = PropData("prop_0001", "signboard", 3, 4)
        prop.set_interactable(kwargs.get("interactable", True))
        prop.set_interaction_kind("note")
        prop.set_note_title(kwargs.get("title", "NOTICE BOARD"))
        prop.set_note_lines(kwargs.get("lines", ["Mid-terms start Sunday.",
                                                 "Do not be late."]))
        return prop

    # -- an ordinary note opens a card with its own words on it -----
    ctx = _Ctx()
    assert trigger(ctx, note())
    assert ctx.message_popup.opened == [
        ("NOTICE BOARD", ["Mid-terms start Sunday.", "Do not be late."])]

    # -- and again, and again: a sign is not a payout ---------------
    for _ in range(5):
        assert trigger(ctx, note())
    assert len(ctx.message_popup.opened) == 6, "a note stopped being readable"

    # -- a note with nothing written on it falls through ------------
    empty = _Ctx()
    assert not trigger(empty, note(lines=[]))
    assert empty.message_popup.opened == []

    # -- so does one nobody may interact with -----------------------
    assert not trigger(_Ctx(), note(interactable=False))

    # -- and so does every other kind of prop -----------------------
    for kind in ("none", "money", "skill", "menu", "travel"):
        other = PropData("prop_0002", "signboard", 1, 1)
        other.set_interactable(True)
        other.set_interaction_kind(kind)
        assert not shows(other), kind
        assert not trigger(_Ctx(), other), kind

    # -- a cleared title still gets a heading -----------------------
    titled = note(title="")
    assert title_of(titled) == NOTE_TITLE_DEFAULT

    # -- blank lines are holes in the card, so they are dropped -----
    gapped = note(lines=["First.", "   ", "Third."])
    assert lines_of(gapped) == ["First.", "Third."]

    # -- and no more than the card can draw -------------------------
    long_one = note(lines=["a", "b", "c", "d", "e"])
    assert len(lines_of(long_one)) == 3

    # -- nothing that is not a prop takes the game down -------------
    assert not shows(object()) and not shows(None)
    assert title_of(object()) == NOTE_TITLE_DEFAULT
    assert lines_of(object()) == []

    # -- it survives a round trip through the level file format -----
    reloaded = PropData.from_dict(note().to_dict())
    assert reloaded.shows_note()
    assert lines_of(reloaded) == lines_of(note())
    assert title_of(reloaded) == "NOTICE BOARD"

    # -- and a prop that is not a note writes no note keys ----------
    plain = PropData("prop_0003", "signboard", 0, 0)
    assert "note_title" not in plain.to_dict()["interaction"]
    assert "note_lines" not in plain.to_dict()["interaction"]

    print("note_prop: all checks passed")

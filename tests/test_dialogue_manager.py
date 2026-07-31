"""
tests/test_dialogue_manager.py
CSE Life: Compile & Conquer — phase F2
─────────────────────────────────────────────────────────────
Guards the one sanctioned edit (Build Plan §0.2).

The point of this suite is not that the new dialogue box looks
nice -- it is that engine/dialogue_manager.py still presents the
SAME six public methods, with the same signatures and the same
behaviour, so main.py keeps working without being touched.

The signature test is the important one: if someone later
"improves" advance() into advance(self, skip=False), this fails.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from content.dialogues import NPC_DIALOGUES
from content.npc_roster import NPC_IDS, NPC_ROSTER
from engine.dialogue_manager import DIALOGUE_SECTIONS, DialogueManager
from ui.dialog_box import TYPEWRITER_CPS, DialogBox

SCREEN_W = 1280
SCREEN_H = 720


@pytest.fixture(scope="module", autouse=True)
def _display():
    """One dummy display for the whole module -- fonts need pygame up."""
    pygame.init()
    surface = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    yield surface
    pygame.quit()


@pytest.fixture
def surface(_display):
    """A clean surface to render onto."""
    _display.fill((0, 0, 0))
    return _display


@pytest.fixture
def manager():
    """A fresh DialogueManager at the game's resolution."""
    return DialogueManager(SCREEN_W, SCREEN_H)


# ─────────────────────────────────────────────────────────────
# THE CONTRACT — all six original signatures, unchanged
# ─────────────────────────────────────────────────────────────

# Resolved signatures, recorded from the pre-edit file. `eval_str=True`
# is needed because the module uses `from __future__ import annotations`,
# which would otherwise report every annotation as a quoted string.
# Note pygame.Surface resolves to its canonical pygame.surface.Surface.
ORIGINAL_SIGNATURES = {
    "__init__": "(self, screen_width: int, screen_height: int) -> None",
    "load_dialogue": "(self, lines: list[str], "
                     "portrait_path: str | None = None) -> None",
    "advance": "(self) -> bool",
    "is_active": "(self) -> bool",
    "get_current_line": "(self) -> str",
    "render": "(self, screen: pygame.surface.Surface) -> None",
}

# The `def` lines exactly as they appear in the pre-edit file. This is
# the literal byte-level guard the build plan asks for (§0.2) -- the
# resolved-signature test above can be satisfied by a rewritten
# annotation, this one cannot.
ORIGINAL_DEF_LINES = (
    "    def __init__(self, screen_width: int, screen_height: int) -> None:",
    "    def load_dialogue(self, lines: list[str],\n"
    "                      portrait_path: str | None = None) -> None:",
    "    def advance(self) -> bool:",
    "    def is_active(self) -> bool:",
    "    def get_current_line(self) -> str:",
    "    def render(self, screen: pygame.Surface) -> None:",
)


@pytest.mark.parametrize("name, expected", sorted(ORIGINAL_SIGNATURES.items()))
def test_original_signatures_are_unchanged(name, expected):
    """Every pre-existing public signature resolves exactly as before."""
    method = getattr(DialogueManager, name)
    assert str(inspect.signature(method, eval_str=True)) == expected


@pytest.mark.parametrize("def_line", ORIGINAL_DEF_LINES)
def test_original_def_lines_are_byte_identical(def_line):
    """The six `def` lines are unchanged, character for character."""
    import engine.dialogue_manager as dm

    source = open(dm.__file__, encoding="utf-8").read().replace("\r\n", "\n")
    assert def_line in source


def test_no_original_method_was_removed():
    """All six originals still exist and are callable."""
    for name in ORIGINAL_SIGNATURES:
        assert callable(getattr(DialogueManager, name, None)), name


def test_additions_are_present():
    """The additive members the build plan asked for all exist."""
    for name in ("update", "set_speaker", "set_typewriter_enabled",
                 "skip_reveal", "get_progress", "load_npc_dialogue"):
        assert callable(getattr(DialogueManager, name, None)), name


# ─────────────────────────────────────────────────────────────
# ORIGINAL BEHAVIOUR
# ─────────────────────────────────────────────────────────────


def test_starts_inactive(manager):
    """Nothing is showing before load_dialogue()."""
    assert manager.is_active() is False
    assert manager.get_current_line() == ""


def test_load_then_walk_the_queue(manager):
    """advance() steps through the lines and reports more remaining."""
    manager.load_dialogue(["one", "two", "three"])
    assert manager.is_active() is True
    assert manager.get_current_line() == "one"
    assert manager.advance() is True
    assert manager.get_current_line() == "two"
    assert manager.advance() is True
    assert manager.get_current_line() == "three"


def test_advance_returns_false_on_the_last_line_and_deactivates(manager):
    """The end of a sequence returns False and clears is_active()."""
    manager.load_dialogue(["only line"])
    assert manager.advance() is False
    assert manager.is_active() is False
    assert manager.get_current_line() == ""


def test_get_current_line_is_empty_when_inactive(manager):
    """An inactive manager never raises on get_current_line()."""
    manager.load_dialogue(["a"])
    manager.advance()
    assert manager.is_active() is False
    assert manager.get_current_line() == ""


def test_empty_list_is_safe(manager):
    """Loading nothing must not crash advance(), render() or the getters."""
    manager.load_dialogue([])
    assert manager.get_current_line() == ""
    assert manager.advance() is False
    assert manager.is_active() is False


def test_empty_list_renders_without_raising(manager, surface):
    """render() on an empty queue draws nothing rather than crashing."""
    manager.load_dialogue([])
    manager.render(surface)


def test_render_is_a_noop_while_inactive(manager, surface):
    """An inactive manager draws nothing at all."""
    before = surface.get_at((SCREEN_W // 2, SCREEN_H - 100))
    manager.render(surface)
    assert surface.get_at((SCREEN_W // 2, SCREEN_H - 100)) == before


def test_missing_portrait_never_raises(manager):
    """A portrait path that does not exist degrades to a placeholder."""
    manager.load_dialogue(["hello"], "assets/portraits/does_not_exist.png")
    assert manager.is_active() is True


# ─────────────────────────────────────────────────────────────
# THE main.py PATH — update() is never called
# ─────────────────────────────────────────────────────────────


def test_render_without_update_draws_the_whole_line(manager, surface):
    """
    main.py never calls update(). The line must therefore be fully
    revealed immediately, or the re-theme would have changed behaviour.
    """
    manager.load_dialogue(["a reasonably long line of dialogue"])
    assert manager.is_reveal_complete() is True
    manager.render(surface)          # must not raise
    assert manager.is_reveal_complete() is True


def test_render_paints_the_tan_card(manager, surface):
    """The box is drawn in the style guide's card tan, not the old navy."""
    from ui.dialog_box import BOTTOM_MARGIN, BOX_H, CARD_TAN, SIDE_MARGIN

    manager.load_dialogue(["hello"])
    manager.render(surface)
    box_top = SCREEN_H - BOTTOM_MARGIN - BOX_H
    inside = surface.get_at((SIDE_MARGIN + 6, box_top + 6))
    assert (inside.r, inside.g, inside.b) == CARD_TAN


# ─────────────────────────────────────────────────────────────
# THE TYPEWRITER — opt-in, driven by update()
# ─────────────────────────────────────────────────────────────


def test_update_reveals_progressively(manager):
    """Ticking update() reveals the line a few characters at a time."""
    line = "x" * 60
    manager.load_dialogue([line])
    manager.update(0.1)                       # 0.1 s -> 3 chars at 30 cps
    assert manager.is_reveal_complete() is False
    manager.update(0.4)                       # 0.5 s total -> 15 chars
    assert manager.is_reveal_complete() is False
    manager.update(10.0)
    assert manager.is_reveal_complete() is True


def test_visible_length_matches_the_dialog_box_clock():
    """The reveal speed lives in exactly one place."""
    assert DialogBox.visible_length(0.0) == 0
    assert DialogBox.visible_length(1.0) == TYPEWRITER_CPS
    assert DialogBox.visible_length(-5.0) == 0


def test_skip_reveal_completes_then_reports_nothing_left(manager):
    """skip_reveal() finishes the line once, then returns False."""
    manager.load_dialogue(["a" * 40])
    manager.update(0.05)
    assert manager.is_reveal_complete() is False
    assert manager.skip_reveal() is True
    assert manager.is_reveal_complete() is True
    assert manager.skip_reveal() is False


def test_skip_reveal_is_false_when_inactive(manager):
    """Nothing to skip on an inactive manager."""
    assert manager.skip_reveal() is False


def test_typewriter_can_be_switched_off(manager):
    """With the typewriter off, a freshly loaded line is complete."""
    manager.load_dialogue(["a" * 40])
    manager.update(0.01)
    assert manager.is_reveal_complete() is False
    manager.set_typewriter_enabled(False)
    assert manager.is_typewriter_enabled() is False
    assert manager.is_reveal_complete() is True


def test_advance_restarts_the_reveal(manager):
    """Each new line starts from the beginning of the typewriter."""
    manager.load_dialogue(["a" * 40, "b" * 40])
    manager.update(10.0)
    assert manager.is_reveal_complete() is True
    manager.advance()
    assert manager.is_reveal_complete() is False


def test_update_ignores_rubbish(manager):
    """A bad dt is ignored rather than corrupting the clock."""
    manager.load_dialogue(["a" * 40])
    manager.update(0.2)
    manager.update(-5.0)
    manager.update("nonsense")
    manager.update(None)
    assert manager.is_reveal_complete() is False


def test_get_progress(manager):
    """Progress is one-based over the loaded queue, (0, 0) when inactive."""
    assert manager.get_progress() == (0, 0)
    manager.load_dialogue(["a", "b", "c"])
    assert manager.get_progress() == (1, 3)
    manager.advance()
    assert manager.get_progress() == (2, 3)
    manager.advance()
    manager.advance()
    assert manager.get_progress() == (0, 0)


def test_set_speaker(manager):
    """The speaker label round-trips."""
    assert manager.get_speaker() == ""
    manager.set_speaker("Prof. Hoque")
    assert manager.get_speaker() == "Prof. Hoque"


# ─────────────────────────────────────────────────────────────
# CONTENT BINDING — real lines, no invented prose
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("npc_id", NPC_IDS)
def test_load_npc_dialogue_binds_every_roster_npc(manager, npc_id):
    """All seven roster NPCs produce real greeting lines."""
    assert manager.load_npc_dialogue(npc_id) is True
    assert manager.is_active() is True
    assert manager.get_current_line() == \
        NPC_DIALOGUES[npc_id]["greeting"][0]
    assert manager.get_speaker() == NPC_ROSTER[npc_id]["display_name"]


@pytest.mark.parametrize("npc_id", NPC_IDS)
@pytest.mark.parametrize("section", DIALOGUE_SECTIONS)
def test_every_section_of_every_npc_binds(manager, npc_id, section):
    """All four sections exist and load for all seven NPCs."""
    assert manager.load_npc_dialogue(npc_id, section) is True
    expected = NPC_DIALOGUES[npc_id][section]
    assert manager.get_progress() == (1, len(expected))
    assert manager.get_current_line() == expected[0]


def test_unknown_npc_is_refused_without_disturbing_state(manager):
    """A bad id returns False and leaves the loaded dialogue alone."""
    manager.load_dialogue(["kept"])
    assert manager.load_npc_dialogue("no_such_npc") is False
    assert manager.get_current_line() == "kept"


def test_unknown_section_is_refused_without_disturbing_state(manager):
    """A bad section returns False and leaves the loaded dialogue alone."""
    manager.load_dialogue(["kept"])
    assert manager.load_npc_dialogue(NPC_IDS[0], "no_such_section") is False
    assert manager.get_current_line() == "kept"


def test_npc_dialogue_renders(manager, surface):
    """A bound NPC conversation draws without raising, portrait or not."""
    for npc_id in NPC_IDS:
        manager.load_npc_dialogue(npc_id)
        while manager.is_active():
            manager.render(surface)
            manager.advance()


def test_no_new_prose_was_written():
    """
    Every line this manager can show comes from content/dialogues.py.

    Guards the owner's ruling that F2/F3 are binding jobs, not writing
    jobs -- if someone adds a hard-coded line to the manager, the line
    will not be found in the content file and this fails.
    """
    import engine.dialogue_manager as dm

    source = open(dm.__file__, encoding="utf-8").read()
    for npc_id in NPC_IDS:
        for section in DIALOGUE_SECTIONS:
            for line in NPC_DIALOGUES[npc_id][section]:
                assert line not in source

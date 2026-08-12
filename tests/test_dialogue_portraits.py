"""
tests/test_dialogue_portraits.py
Task 5 — the portrait follows the line, and the old call still doesn't.

Two halves, and the second matters as much as the first: every existing
caller passes load_dialogue(lines) or load_dialogue(lines, portrait),
and the INTRO beats depend on one portrait being held for a whole beat.
So these tests assert the NEW behaviour and pin the OLD one.

Headless: SDL_VIDEODRIVER=dummy, one 1x1 display so convert_alpha()
has a format to convert to. No assets are written — the portraits used
are the real PNGs in assets/portraits/, which is also what proves
__resolve_portrait_path() picks the emotion it is asked for.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame                                          # noqa: E402

from content.npc_roster import NPC_ROSTER              # noqa: E402
from engine.dialogue_manager import (PROJECT_ROOT,     # noqa: E402
                                     DialogueManager)

pygame.init()
pygame.display.set_mode((1, 1))

NPC = "warm_classmate_purnno"
LINES = ["one", "two", "three"]


def portrait(emotion: str) -> str:
    """A real portrait path for Purnno, as the roster declares them."""
    return "assets/portraits/npc_%s_%s.png" % ("purnno", emotion)


def exists(relative: str) -> bool:
    return os.path.isfile(os.path.join(PROJECT_ROOT, relative))


def manager() -> DialogueManager:
    return DialogueManager(1280, 720)


# ── the art this whole feature rests on ────────────────────────

def test_the_emotion_art_actually_shipped():
    """
    Every variant the roster declares for Purnno is on disk.

    dialogue_manager.py used to carry a comment saying only Hoque and
    Roya had art. That is stale, and this is the check that keeps it
    honest — if the PNGs go, the per-line tests below fail for a
    confusing reason, and this one fails for the real one.
    """
    for emotion in NPC_ROSTER[NPC]["portrait_variants"]:
        assert exists(portrait(emotion)), "missing %s" % portrait(emotion)


# ── the old contract, pinned ───────────────────────────────────

def test_single_portrait_is_held_for_every_line():
    """The pre-Task-5 call: one portrait, unchanged across advance()."""
    box = manager()
    box.load_dialogue(list(LINES), portrait("neutral"))
    first = box.get_current_portrait()
    assert first is not None, "the neutral portrait did not load"
    assert not box.has_line_portraits()
    while box.advance():
        assert box.get_current_portrait() is first, \
            "a single-portrait call changed face mid-sequence"


def test_no_portrait_at_all_still_loads():
    """load_dialogue(lines) alone — what lecture.py and
    side_quest_lecture.py both call — draws the placeholder block."""
    box = manager()
    box.load_dialogue(list(LINES))
    assert box.get_current_portrait() is None
    assert box.is_active() and box.get_current_line() == "one"
    while box.advance():
        assert box.get_current_portrait() is None


def test_advance_still_reports_the_end():
    """The return contract did not move: False on the last line."""
    box = manager()
    box.load_dialogue(["only"], portrait("neutral"))
    assert box.advance() is False
    assert not box.is_active()


# ── per-line portraits ─────────────────────────────────────────

def test_each_line_gets_its_own_portrait():
    """The acceptance criterion, for a whole conversation."""
    box = manager()
    wanted = [portrait(e) for e in ("neutral", "happy", "encouraging")]
    box.load_dialogue(list(LINES), None, wanted)
    assert box.has_line_portraits()

    seen = [box.get_current_portrait()]
    while box.advance():
        seen.append(box.get_current_portrait())

    assert len(seen) == len(LINES)
    assert all(face is not None for face in seen), "a line drew no face"
    assert len({id(face) for face in seen}) == 3, \
        "the three lines did not resolve to three different portraits"


def test_the_same_emotion_twice_is_decoded_once():
    """The cache is keyed by path, so a repeated face is one surface."""
    box = manager()
    repeat = [portrait("happy"), portrait("neutral"), portrait("happy")]
    box.load_dialogue(list(LINES), None, repeat)
    first = box.get_current_portrait()
    box.advance()
    box.advance()
    assert box.get_current_portrait() is first, \
        "the same path decoded twice instead of hitting the cache"


def test_a_portrait_depends_only_on_the_line_index():
    """
    Line 3's face is line 3's face, on every pass through the sequence.

    __portrait_for() walks back from the index rather than remembering
    what was last drawn, so replaying the same conversation cannot drift.
    Asserted on ONE manager: the portrait cache is per-instance, so
    identity across two managers would compare two legitimate decodes of
    the same PNG.
    """
    box = manager()
    wanted = [portrait("neutral"), portrait("happy"), portrait("encouraging")]

    box.load_dialogue(list(LINES), None, wanted)
    box.advance()
    box.advance()
    third = box.get_current_portrait()
    assert third is not None

    box.load_dialogue(list(LINES), None, wanted)
    box.advance()
    box.advance()
    assert box.get_current_portrait() is third, \
        "the same line resolved to a different face on a second pass"


# ── the ragged cases, each resolved explicitly ─────────────────

def test_fewer_portraits_than_lines_holds_the_last_one():
    box = manager()
    box.load_dialogue(list(LINES), None, [portrait("happy")])
    first = box.get_current_portrait()
    assert first is not None
    while box.advance():
        assert box.get_current_portrait() is first, \
            "a short list did not hold the last valid portrait"


def test_a_none_entry_inherits_the_previous_face():
    box = manager()
    box.load_dialogue(list(LINES), None,
                      [portrait("happy"), None, portrait("neutral")])
    happy = box.get_current_portrait()
    box.advance()
    assert box.get_current_portrait() is happy, "None did not inherit"
    box.advance()
    assert box.get_current_portrait() is not happy, "line 3 did not change"


def test_an_empty_string_is_treated_as_no_entry():
    box = manager()
    box.load_dialogue(list(LINES), None, [portrait("happy"), "", "   "])
    happy = box.get_current_portrait()
    while box.advance():
        assert box.get_current_portrait() is happy


def test_a_missing_file_falls_back_to_the_single_portrait():
    """An unknown emotion resolves to a path that is not there."""
    box = manager()
    box.load_dialogue(list(LINES), portrait("neutral"),
                      ["assets/portraits/npc_purnno_does_not_exist.png"] * 3)
    fallback = box.get_current_portrait()
    assert fallback is not None, "did not fall back to the loaded portrait"
    while box.advance():
        assert box.get_current_portrait() is fallback


def test_everything_missing_draws_the_placeholder():
    box = manager()
    box.load_dialogue(list(LINES), None, ["nope.png", None, ""])
    assert box.get_current_portrait() is None
    while box.advance():
        assert box.get_current_portrait() is None


# ── the two routes an emotion can arrive by ────────────────────

def test_load_npc_dialogue_without_emotions_is_unchanged():
    """No emotions argument, no tags in the file: one neutral face."""
    box = manager()
    assert box.load_npc_dialogue(NPC, "greeting")
    assert not box.has_line_portraits(), \
        "plain string lines should not build a per-line list"
    first = box.get_current_portrait()
    while box.advance():
        assert box.get_current_portrait() is first


def test_load_npc_dialogue_takes_an_emotions_list():
    box = manager()
    assert box.load_npc_dialogue(NPC, "greeting",
                                 emotions=["happy", "encouraging"])
    assert box.has_line_portraits()
    faces = [box.get_current_portrait()]
    while box.advance():
        faces.append(box.get_current_portrait())
    assert all(face is not None for face in faces)
    assert len({id(face) for face in faces}) >= 2, \
        "the emotions list did not change the portrait"


def test_tagged_lines_would_work_if_the_content_had_tags(monkeypatch):
    """
    The forward-compatible half of Task 5.

    content/dialogues.py has no emotion tags today (G2 — Ayesha's file).
    This proves the manager is ready for them: a section authored as
    (line, emotion) pairs drives the portrait with no further code
    change. Patched here rather than written into her file.
    """
    from content import dialogues
    tagged = dict(dialogues.NPC_DIALOGUES)
    tagged[NPC] = dict(tagged[NPC])
    tagged[NPC]["greeting"] = [("Hey.", "happy"),
                               ("Long week.", "neutral"),
                               ("You'll get there.", "encouraging")]
    monkeypatch.setattr(dialogues, "NPC_DIALOGUES", tagged)

    box = manager()
    assert box.load_npc_dialogue(NPC, "greeting")
    assert box.has_line_portraits(), "authored tags were not picked up"
    assert box.get_current_line() == "Hey.", \
        "the tag leaked into the line text"

    faces = [box.get_current_portrait()]
    while box.advance():
        faces.append(box.get_current_portrait())
    assert len(faces) == 3
    assert len({id(face) for face in faces}) == 3, \
        "authored tags did not give three different faces"


def test_an_explicit_emotions_list_beats_authored_tags(monkeypatch):
    from content import dialogues
    tagged = dict(dialogues.NPC_DIALOGUES)
    tagged[NPC] = dict(tagged[NPC])
    tagged[NPC]["greeting"] = [("a", "happy"), ("b", "happy")]
    monkeypatch.setattr(dialogues, "NPC_DIALOGUES", tagged)

    both = manager()
    assert both.load_npc_dialogue(NPC, "greeting",
                                  emotions=["neutral", "encouraging"])
    first = both.get_current_portrait()
    both.advance()
    assert both.get_current_portrait() is not first, \
        "the authored tag overrode the explicit argument"


def test_an_unknown_npc_or_section_still_returns_false():
    box = manager()
    assert not box.load_npc_dialogue("nobody", "greeting")
    assert not box.load_npc_dialogue(NPC, "not_a_section")

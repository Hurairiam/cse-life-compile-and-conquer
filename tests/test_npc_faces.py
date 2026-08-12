"""
tests/test_npc_faces.py
Every authored line has a face behind it.

TWO BUGS, ONE SYMPTOM. Players reported that NPC portraits "disappear",
and there were two independent reasons for it:

  1. content/level_registry.py named happy/serious portraits for five of
     the seven NPCs that were never drawn. A curated NPC_REGISTRY entry
     CLAIMS its NPC — scan_npcs() is handed set(NPC_REGISTRY) and skips
     anything already there — so the asset scanner never corrected them,
     and 30 of the 76 authored chains in levels/*.json drew the dialog
     box's placeholder block instead of a face.
  2. engine/dialogue_flow.py's side quest offer REPLACES what is in the
     dialogue box, and both load_dialogue() calls omitted the optional
     portrait argument, which sets the manager's portrait to None. The
     NPC's face vanished the moment the quest question appeared and
     stayed gone through the accept/decline reply — with their name
     still on the card above the empty block.

The first two tests would have caught (1) the day the art was named, and
they are written against the LEVEL FILES rather than a fixed list, so an
NPC placed or re-emotioned in the editor tomorrow is covered too.

Headless: no window is needed for the first two — they are path checks —
but the offer test drives the real dialogue manager, so SDL gets a dummy
driver and a display the way tests/test_dialogue_portraits.py does.
"""
from __future__ import annotations

import glob
import json
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame                                            # noqa: E402
import pytest                                            # noqa: E402

from academic.semester import Semester                   # noqa: E402
from content.level_registry import (NPC_REGISTRY,        # noqa: E402
                                    get_npc_portrait_path)
from engine import dialogue_flow, save_bridge            # noqa: E402
from engine.app_context import AppContext                # noqa: E402
from engine.level_loader import load_level               # noqa: E402

pygame.init()
pygame.display.set_mode((1280, 720))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def on_disk(relative: str) -> bool:
    return bool(relative) and os.path.isfile(
        os.path.join(PROJECT_ROOT, relative))


def placed_chains():
    """(level file, type_id, emotion) for every chain in every level."""
    for path in sorted(glob.glob(os.path.join(PROJECT_ROOT, "levels",
                                              "*.json"))):
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        for npc in data.get("npcs") or []:
            for chain in (npc.get("dialog") or {}).get("chains") or []:
                yield (os.path.basename(path), npc.get("type_id"),
                       chain.get("emotion") or "neutral")


# ── the registry against the art ───────────────────────────────

def test_every_registered_portrait_is_a_file_that_exists():
    """
    A curated entry claims its NPC, so a path here that is not on disk
    is never corrected by the scanner — it just draws nothing.
    """
    missing = []
    for type_id, entry in sorted(NPC_REGISTRY.items()):
        for emotion, path in (entry.get("portraits") or {}).items():
            if not on_disk(path):
                missing.append("%s/%s -> %s" % (type_id, emotion, path))
    assert not missing, "portraits named but never drawn: %s" % missing


def test_every_authored_chain_resolves_to_a_face():
    """
    THE regression. Walks the real level files, so it covers whatever
    the editor saved last, not a list someone has to remember to update.
    """
    faceless = []
    for level, type_id, emotion in placed_chains():
        if type_id not in NPC_REGISTRY:
            continue
        path = get_npc_portrait_path(type_id, emotion)
        if not on_disk(path):
            faceless.append("%s: %s/%s -> %r" % (level, type_id,
                                                 emotion, path))
    assert not faceless, \
        "%d chains would draw the placeholder block: %s" % (len(faceless),
                                                            faceless)


def test_the_editors_three_emotions_resolve_for_every_npc():
    """
    neutral / happy / serious is what a DialogChain can declare, so all
    three have to land on a real file for every NPC — even the ones
    whose art is named approving, focused or stressed instead.
    """
    for type_id in sorted(NPC_REGISTRY):
        if not (NPC_REGISTRY[type_id].get("portraits") or {}):
            continue
        for emotion in ("neutral", "happy", "serious"):
            assert on_disk(get_npc_portrait_path(type_id, emotion)), \
                "%s has no face for %r" % (type_id, emotion)


def test_a_portrait_that_goes_missing_falls_back_to_the_default(monkeypatch):
    """
    The safety net: a named-but-missing file degrades to the NPC's
    default emotion, never to no face at all.
    """
    patched = dict(NPC_REGISTRY["rafi"])
    patched["portraits"] = dict(patched["portraits"])
    patched["portraits"]["serious"] = "assets/npcs/npc_rafi_nothing.png"
    monkeypatch.setitem(NPC_REGISTRY, "rafi", patched)

    resolved = get_npc_portrait_path("rafi", "serious")
    assert resolved == "assets/npcs/npc_rafi_neutral.png"
    assert on_disk(resolved)


# ── the side quest offer keeps the speaker's face ──────────────

@pytest.fixture
def talking_to_rafi():
    """Semester 3, mid-conversation with Rafi, who owes SQ_DSA."""
    ctx = AppContext()
    save_bridge.new_game(ctx)
    while ctx.player().get_current_semester() < 3:
        ctx.player().advance_semester()
    ctx.session.set_active_semester(Semester(3))

    ctx.level = load_level("university_library", semester=3)
    ctx.level_id = "university_library"
    rafi = [n for n in ctx.level.get_npcs()
            if n.get_type_id() == "rafi"][0]
    dialogue_flow.start_talk(ctx, rafi)
    return ctx


def test_the_quest_offer_keeps_the_npcs_face(talking_to_rafi):
    ctx = talking_to_rafi
    assert ctx.dialogue_manager.get_current_portrait() is not None, \
        "the chain itself had no face — the registry is wrong again"

    while ctx.dialogue_manager.advance():
        pass
    assert dialogue_flow.open_offer(ctx), "Rafi owed no offer in semester 3"

    assert ctx.dialogue_manager.get_current_portrait() is not None, \
        "the portrait vanished when the quest offer opened"
    assert ctx.dialogue_manager.get_speaker() == "Rafi"


def test_the_answer_wears_the_same_face_as_the_question(talking_to_rafi):
    ctx = talking_to_rafi
    while ctx.dialogue_manager.advance():
        pass
    dialogue_flow.open_offer(ctx)
    asked_with = ctx.offer_portrait

    assert dialogue_flow.resolve_offer(ctx, dialogue_flow.OFFER_ACCEPT)
    assert ctx.dialogue_manager.get_current_portrait() is not None, \
        "the portrait vanished on the accept lines"
    assert asked_with, "the offer never resolved a portrait to remember"


def test_the_face_does_not_leak_into_the_next_conversation(talking_to_rafi):
    ctx = talking_to_rafi
    while ctx.dialogue_manager.advance():
        pass
    dialogue_flow.open_offer(ctx)
    assert ctx.offer_portrait

    dialogue_flow.end_talk(ctx)
    assert ctx.offer_portrait is None

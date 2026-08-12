"""
content/epilogue_text.py

CSE Life: Compile & Conquer
Content Layer — Endgame Epilogue Text
─────────────────────────────────────────────────────────────
THE PLACEHOLDER HAS BEEN REPLACED. This module was written by Saif to
make EndgameEvaluationManager functional/testable before the narrative
landed, and it said so: "Ayesha (Dev 4, narrative) owns the real,
polished epilogue writing — this module is the intended drop-in
replacement point". Ayesha's four epilogues have been on the branch
since Sprint 3, in content/dialogues.py::EPILOGUE_TEXTS, and NOTHING
IMPORTED THEM — the ending screen was still showing the placeholder.
This module is now the swap it always advertised.

    EPILOGUE_TEXT  ending title -> list of line strings
                   (the shape engine/endgame_manager.py reads; unchanged)

WHY A BRIDGE RATHER THAN A COPY-PASTE
─────────────────────────────────────
The prose stays in Ayesha's file, which is hers to edit, and the two
mismatches between her table and the engine are reconciled here instead
of in it:

  1. THE KEYS. The four ending titles are canonical — they are written
     in engine/endgame_manager.py::title_for(), ui/endgame_screen.py::
     THEMES and ui/certificate_screen.py, and a lookup miss silently
     shows the AVERAGE GRADUATE epilogue under a DROP OUT heading.
     EPILOGUE_TEXTS spells the two drop-out keys "DROP OUT with Strong
     Skills" / "DROP OUT with Weak Skills", with a `with` the rest of
     the game does not have. KEY_ALIASES maps them across. This is worth
     fixing upstream, and when it is, the aliases simply stop matching
     anything and nothing here breaks.

  2. THE FALLBACK. Any title Ayesha's table does not carry keeps Saif's
     placeholder lines, so the screen can never be handed an empty list
     however the two files drift.

Line WRAPPING is deliberately NOT done here. Ayesha writes sentences,
not screen rows, and how many characters fit on the certificate is a
question about a font size that only ui/endgame_screen.py knows the
answer to — it wraps what it is given.
─────────────────────────────────────────────────────────────
"""

from typing import Dict, List

# Saif's originals. Kept as the safety net described above, and as the
# reference for what shape the manager expects.
PLACEHOLDER_TEXT: Dict[str, List[str]] = {
    "TOP GRADUATE": [
        "You walked across the stage with your degree in hand and",
        "a resume that already turned heads. Four years of late",
        "nights paid off — offers are waiting, and so is the rest",
        "of your career.",
    ],
    "AVERAGE GRADUATE": [
        "You made it. Diploma in hand, you leave campus a graduate",
        "of the CSE program — steady, dependable, done. The real",
        "world is next, and you're ready to figure it out as you go.",
    ],
    "DROP OUT Strong Skills": [
        "The degree never came through, but somewhere along the way",
        "you became genuinely good at this. Your skills speak for",
        "themselves — plenty of builders never finished the paper",
        "that says they can build.",
    ],
    "DROP OUT Weak Skills": [
        "University life ended before it really began to click.",
        "No degree, and not much to show for the years spent here.",
        "But the story isn't over — it just didn't go the way",
        "anyone planned.",
    ],
}

# The four canonical ending titles, in the 2x2 order
# engine/endgame_manager.py::title_for() lays them out.
ENDING_TITLES: tuple = (
    "TOP GRADUATE",
    "AVERAGE GRADUATE",
    "DROP OUT Strong Skills",
    "DROP OUT Weak Skills",
)

# canonical title -> the key content/dialogues.py files it under.
# Only the two drop-out endings differ; the aliases are dead the day
# that file is corrected.
KEY_ALIASES: Dict[str, str] = {
    "DROP OUT Strong Skills": "DROP OUT with Strong Skills",
    "DROP OUT Weak Skills": "DROP OUT with Weak Skills",
}


def __authored() -> Dict[str, List[str]]:
    """
    Ayesha's epilogues under the canonical keys, placeholder elsewhere.

    A missing content/dialogues.py, a table that is not a dict, or an
    ending with no lines all fall back rather than raise: this module is
    imported at the top of engine/endgame_manager.py, and the last
    screen of the game is not a place to discover a content error.
    """
    try:
        from content.dialogues import EPILOGUE_TEXTS
    except ImportError:                                  # pragma: no cover
        return {title: list(lines)
                for title, lines in PLACEHOLDER_TEXT.items()}

    resolved: Dict[str, List[str]] = {}
    for title in ENDING_TITLES:
        lines = None
        if isinstance(EPILOGUE_TEXTS, dict):
            lines = EPILOGUE_TEXTS.get(title) \
                or EPILOGUE_TEXTS.get(KEY_ALIASES.get(title, title))
        resolved[title] = [str(line) for line in lines] if lines \
            else list(PLACEHOLDER_TEXT[title])
    return resolved


EPILOGUE_TEXT: Dict[str, List[str]] = __authored()


# -------------------------------------------------------------
# STUB TEST — the content/ convention.
#     py -m content.epilogue_text
# -------------------------------------------------------------
if __name__ == "__main__":
    from content.dialogues import EPILOGUE_TEXTS

    assert set(EPILOGUE_TEXT) == set(ENDING_TITLES), \
        "an ending lost its epilogue"
    for title in ENDING_TITLES:
        assert EPILOGUE_TEXT[title], "%s has no lines" % title

    # The point of the whole module: the shipped text is Ayesha's, not
    # the placeholder, for all four endings including the two her file
    # spells differently.
    for title in ENDING_TITLES:
        authored = EPILOGUE_TEXTS.get(title) \
            or EPILOGUE_TEXTS.get(KEY_ALIASES.get(title, title))
        assert authored, "%s is not in EPILOGUE_TEXTS at all" % title
        assert EPILOGUE_TEXT[title] == [str(line) for line in authored], \
            "%s still shows the placeholder" % title

    print("epilogue_text: all four endings carry the authored text")

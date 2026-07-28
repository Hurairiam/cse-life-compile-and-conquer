"""
content/epilogue_text.py

CSE Life: Compile & Conquer
Content Layer — Endgame Epilogue Text
─────────────────────────────────────────────────────────────
PLACEHOLDER CONTENT — written by Saif to make EndgameEvaluationManager
functional/testable now. Ayesha (Dev 4, narrative) owns the real,
polished epilogue writing — this module is the intended drop-in
replacement point: keep the same dict shape (ending title -> list of
line strings) and EndgameEvaluationManager needs no code changes.

Keys MUST exactly match the 4 ending titles ui/endgame_screen.py's
THEMES dict expects:
    "TOP GRADUATE", "AVERAGE GRADUATE",
    "DROP OUT Strong Skills", "DROP OUT Weak Skills"
─────────────────────────────────────────────────────────────
"""

from typing import Dict, List

EPILOGUE_TEXT: Dict[str, List[str]] = {
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
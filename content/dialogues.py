"""
content/dialogues.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
Created by: Ayesha Saheba Mostafa (dev4-aysha-narrative)
Sprint 3

All in-game text content.
EndgameEvaluationManager calls EPILOGUE_TEXTS.
DialogueManager calls NPC_DIALOGUES.
GameClock calls SEMESTER_INTROS at the start of each semester.
─────────────────────────────────────────────────────────────
"""

# ── SEMESTER INTRO MONOLOGUES ─────────────────────────────────────
SEMESTER_INTROS: dict[int, list[str]] = {
    
    1: [
        "Semester 1. The gates are open. You step in with one bag and zero context.",
        "Your transcript is blank. Your wallet is empty. Your time pool is full.",
        "80 days. Choose your courses. Try not to panic.",
    ],
    2: [
        "Semester 2. The excitement of week one is a distant memory.",
        "Your backlog does not reset. Your habits have not changed.",
        "Stay ahead — or start catching up.",
    ],
    3: [
        "Semester 3. Something called OOP is on your schedule.",
        "Abstract classes. Inheritance. Encapsulation. Polymorphism.",
        "You will understand all four. Or you will carry them into next semester.",
    ],
}

DEFAULT_SEMESTER_INTRO: list[str] = [
    "Another semester begins.",
    "80 days. Choose carefully.",
]

# ── NPC DIALOGUE SCRIPTS ──────────────────────────────────────────
NPC_DIALOGUES: dict[str, dict[str, list[str]]] = {
    # content to be added
}

# ── EPILOGUE TEXTS ────────────────────────────────────────────────
EPILOGUE_TEXTS: dict[str, list[str]] = {
    # content to be added
}
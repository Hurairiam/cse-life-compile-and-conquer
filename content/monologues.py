from __future__ import annotations

MAX_LINE_CHARS: int = 48

FALLBACK_LINES: list[str] = [
    "Another term. The same eighty days.",
    "The catalogue is open and the clock is not.",
    "Spend it well.",
]

MONOLOGUES: dict[int, list[str]] = {
    1: [
        "First semester. Nobody knows your name yet.",
        "Eighty days to change that, or not.",
        "The registration desk is already open.",
    ],
    2: [
        "You survived the first one. Barely counts.",
        "The courses get heavier from here.",
        "So does everything else.",
    ],
    3: [
        "Third semester. The novelty has worn off.",
        "Your seniors look tired for a reason.",
        "Pick your battles early this time.",
    ],
    4: [
        "Halfway to halfway.",
        "The backlog you ignored is still waiting.",
        "So is the credit counter.",
    ],
}


def get_monologue(semester_number: int) -> list[str]:
    return list(MONOLOGUES.get(semester_number, FALLBACK_LINES))

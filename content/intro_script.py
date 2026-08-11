"""
content/intro_script.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
Created by: Ayesha Saheba Mostafa (dev4-aysha-narrative)
Phase 18 — the three opening cutscenes.

Ms. Roya's briefing, room tour and lecture hall tour, played once
at the start of a new game. engine/states/intro.py reads this
module through the four accessors at the bottom and nothing else.

Beat 1 plays BEFORE name entry, so it must not use {name}.
─────────────────────────────────────────────────────────────
"""

BEAT_BRIEFING: str = "briefing"
BEAT_ROOM_TOUR: str = "room_tour"
BEAT_CAMPUS_TOUR: str = "campus_tour"

BEAT_IDS: tuple = (
    BEAT_BRIEFING,
    BEAT_ROOM_TOUR,
    BEAT_CAMPUS_TOUR,
)

SPEAKER: str = "Ms. Roya"


INTRO_BEATS: dict[str, dict] = {
    BEAT_BRIEFING: {
        "emotion": "neutral",
        "lines": [
            "Hello there.",
            "Welcome to Compile & Conquer. I'm Ms. Roya.",
            "You're about to start your journey as a Computer Science and Engineering student. It'll be twelve semesters of coding, problem solving, and the occasional all-nighter.",
            "You'll need 140 credits to graduate, and each semester gives you a budget of 80 days for studying, exams, side work, and everything in between.",
            "It won't always be an easy path, but if you stick with it, you'll have something to be proud of at the end.",
            "And I'll be your advisor for the road ahead.",
            "Before any of that begins, though, what should I call you?",
        ],
    },

    BEAT_ROOM_TOUR: {
        "emotion": "happy",
        "lines": [
            "Welcome to your new home, {name}. You’ll be spending quite a bit of time here, so you should probably get familiar with it.",
            "Most things around you have a purpose. If you want to interact with something, walk up to it, face it, and press E. Easy peasy.",
            "That bed over there is where you end your semester when you’re done with everything you need to do.",
            "Your computer is a little more important than it looks. It gives you access to side quests, where you can spend two days working on a skill and unlock lecture sheets to help you improve.",
            "And that rug by the door can take you to places you've already unlocked, so it'll save you some walking later.",
            "You’ll start every semester right here, so this room will become pretty familiar before long.",
            "For now, that's enough of the basics. Head over to the lecture hall when you're ready. I'll meet you there.",
        ],
    },

    BEAT_CAMPUS_TOUR: {
        "emotion": "serious",
        "lines": [
            "Now, this is where the academic side of university really begins. Don't worry, I'll keep it simple.",
            "Each semester gives you 80 days to work with. Lectures and exams take time, so use those days wisely.",
            "Lectures are where you'll actually learn your courses. When you're ready, use the desk at the front to start one.",
            "Once you've learned what you need, you'll take your exams from that same desk. That's how your courses get credited.",
            "And that's Professor Rahman over there. Don't be afraid to talk to him or the people around you. Getting to know your professors and classmates can make university a lot easier.",
            "You should also make time for extracurricular activities. They may not be part of your degree, but they'll help you grow outside the classroom too.",
            "And don't spend all your time in one place. Explore the campus, see what's around you, and make this place feel a little more like home.",
            "That's the most important part, {name}. Take your studies seriously, but give yourself room to actually experience university too.",
            "I'll leave you to it now. Good luck, {name}. I have a feeling you're going to do just fine.",
        ],
    },
}


def has_beat(beat_id: str) -> bool:
    """True when this beat has authored lines."""
    return bool((INTRO_BEATS.get(beat_id) or {}).get("lines"))


def get_lines(beat_id: str) -> list[str]:
    """The beat's lines in order. Empty list for an unknown beat."""
    return list((INTRO_BEATS.get(beat_id) or {}).get("lines", []))


def get_emotion(beat_id: str) -> str:
    """The portrait Roya wears for this beat. Defaults to neutral."""
    return str((INTRO_BEATS.get(beat_id) or {}).get("emotion", "neutral"))


def get_speaker(beat_id: str) -> str:
    """The name drawn above the dialogue. Always Ms. Roya here."""
    return SPEAKER
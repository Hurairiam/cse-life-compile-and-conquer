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
    4: [
        "Semester 4. The career office is open for the first time.",
        "Money enters the picture. So does pressure.",
        "Manage both. Or let one consume the other.",
    ],
    5: [
        "Semester 5. The courses are harder. The deadlines are closer.",
        "The students who coasted are starting to feel it.",
        "You know which one you are.",
    ],
    6: [
        "Semester 6. Halfway through. No room to pretend anymore.",
        "Your academic history is a record of every decision you made.",
        "It does not forget. Neither does the backlog.",
    ],
    7: [
        "Semester 7. The grind is real now.",
        "Skill sprints, internship shifts, exams — all competing for the same 80 days.",
        "Something will have to give. Choose wisely what it is.",
    ],
    8: [
        "Semester 8. You have seen people fall behind and come back.",
        "You have seen people fall behind and not come back.",
        "The difference was never talent.",
    ],
    9: [
        "Semester 9. Three semesters left.",
        "The students who are ahead know it. The ones who are behind know it too.",
        "The clock does not slow down for either.",
    ],
    10: [
        "Semester 10. Final year.",
        "Every exam matters more than it did before.",
        "140 credits. That is the only number that matters now.",
    ],
    11: [
        "Semester 11. Second to last.",
        "Last real chance to clear the backlog before everything converges.",
        "Whatever you have been putting off — stop putting it off.",
    ],
    12: [
        "Semester 12. This is it.",
        "Everything you built — or failed to build — across four years ends here.",
        "Graduate. Or carry it forward into a very different kind of fight.",
    ],
}

DEFAULT_SEMESTER_INTRO: list[str] = [
    "Another semester begins.",
    "80 days. Choose carefully.",
]

# ── NPC DIALOGUE SCRIPTS ──────────────────────────────────────────
NPC_DIALOGUES: dict[str, dict[str, list[str]]] = {
    "warm_classmate_purnno": {
        "greeting": [
            "Oh, you're in the CSE program too?",
            "I'm Purnno by the way. Just grabbed some food— this place gets crowded really fast.",
            "Join us please!",
        ],
        "offer": [
            "I found something we could work on together.",
            "A few days of focused practice — nothing crazy.",
            "Interested?",
        ],
        "farewell": [
            "No pressure. Food's getting cold so I gotta dash.",
            "You know where to find me.",
        ],
        "unavailable": [
            "Hey — I'd love to chat but exams are coming up.",
            "I'm basically living in the library right now.",
            "Find me at the start of next semester, yeah?",
        ],
    },
    "overachiever_classmate_rafi": {
        "greeting": [
            "Hey. You're in the CSE program? Which courses did you register for?",
            "I'm Rafi. What're your thoughts about Rukhsana ma'am's assignment?",
            "If you need notes let me know, I have everything organized by topic.",
        ],
        "offer": [
            "I'm working on something this week. You can join if you want.",
            "Warning— I don't go slow.",
            "A few days of proper focused work.It's totally worth it.",
        ],
        "farewell": [
            "Alright. The offer stands if you change your mind.",
        ],
        "unavailable": [
            "Exam week. I'm not available for anything else right now.",
            "You should be studying too, honestly instead of loitering.",
        ],
    },
    "struggling_friend_zayan": {
        "greeting": [
            "Oh hey. We met in class before.",
            "I'm Zayan. Been sitting out here avoiding the library.",
            "Don't tell me you actually did the readings.",
        ],
        "offer": [
            "Okay so I found this thing we could work on.",
            "I'm probably not going to do it alone if I'm honest.",
            "You in?",
        ],
        "farewell": [
            "Fair enough. I'll probably just sit here a bit longer.",
        ],
        "unavailable": [
            "Bro I haven't even started studying yet.",
            "Let's meet up sometime again later. Maybe I'll have my life together by then.",
        ],
    },
}

# ── EPILOGUE TEXTS ────────────────────────────────────────────────
EPILOGUE_TEXTS: dict[str, list[str]] = {
    "TOP GRADUATE": [
        "You made it through all 140 credits—and you actually know your stuff!",
        "Recruiters were already reaching out before you even finished updating your resume.",
        "Turns out all that hard work was 100% worth it in the end. Time to celebrate!",
    ],
    "AVERAGE GRADUATE": [
        "140 credits in the bag! You officially did it.",
        "You have the qualification ready, and there's still plenty of room to polish your toolkit.",
        "Now the fun part starts: learning through real projects out in the field.",
    ],
    "DROP OUT with Strong Skills": [
        "So the formal degree didn't happen—look at how much practical skill you picked up anyway!",
        "Even if the credits fell short this time, every project you worked on taught you something valuable.",
        "Success doesn't only happen inside a 12-semester box. You're building your own way forward.",
    ],
    "DROP OUT with Weak Skills": [
        "Things didn't go as planned with the credits, and your skill set is still finding its footing.",
        "Four years of hard work brought you here, and none of that effort was wasted.",
        "Consider this just a bump in the road—you have all the room in the world to rebuild and try again.",
    ],
}
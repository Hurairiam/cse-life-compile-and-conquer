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

CUTSCENES = {
    1: {
        "title": "First Impressions",
        "lines": [
            "Everything is unfamiliar today — the sounds, the faces, the version of yourself you haven't figured out yet.",
            "Somewhere in this crowd are several people whose names you don't know yet.",
            "You won't remember this moment later. But it's the one everything else grows out of."
        ]
    },
    3: {
        "title": "Cracks You Don't Notice Yet",
        "lines": [
            "The newness has worn off, and campus feels almost familiar now — which is its own kind of strange.",
            "Small things are starting to slip, quietly, in places nobody's paying attention to.",
            "You keep going, the way everyone does right before they notice they've stopped noticing things."
        ]
    },
    4: {
        "title": "Seen",
        "lines": [
            "Someone sits you down and actually looks at you.",
            "For the first time, you're not just passing through.",
            "Whatever she's seeing, it's the first time anyone's looked this closely.",
            "This is what she sees."
        ]
    },
    5: {
        "title": "Quiet Hours",
        "lines": [
            "There's a version of tonight happening behind closed doors all over campus — the kind no one talks about after.",
            "A few people you think you know are quietly unraveling, each in their own way.",
            "You're unraveling a little yourself, in a way you haven't said out loud to anyone.",
            "Somewhere, someone keeps a chair empty for you anyway — whether or not you ever show up to sit in it."
        ]
    },
    6: {
        "title": "What Breaks, Bends",
        "lines": [
            "Something breaks today. Somewhere. You can feel it before you can name it.",
            "Not everyone survives a semester the same way they started it.",
            "For you, it starts smaller — walking back into a room you'd been avoiding, just once.",
            "You're not sure what you did to be noticed. Maybe nothing. Maybe that was the point."
        ]
    },
    9: {
        "title": "Passing It On",
        "lines": [
            "Campus looks the same as it did on your first day here, except now you're not the one who's lost.",
            "Somewhere, someone is being handed the exact thing that once got handed to you.",
            "Somewhere else, someone tells a stranger the thing they probably should have told you sooner.",
            "You've become part of a story you didn't realize you were writing."
        ]
    },
    12: {
        "title": "Commencement",
        "lines": [
            "Four years compress into a single afternoon that feels both too long and nowhere near long enough.",
            "For the only time in this whole story, everyone you've known is standing in the same place at once.",
            "Then, one by one, they disappear back into a crowd that's already forgotten they were ever new here too.",
            "The story doesn't really end. It just stops being about you."
        ]
    }
}


def has_cutscene(semester: int) -> bool:
    return semester in CUTSCENES


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
    "late_bloomer_kabir": {
        "greeting": [
            "I'm Kabir. I've been here a while.",
            "Don't make the same mistakes I did. That's all I'll say.",
        ],
        "offer": [
            "There's something I wish someone had shown me earlier.",
            "It's a few days of work. Probably saves you more than that later.",
            "Up to you.",
        ],
        "farewell": [
            "No rush. You still have time.",
        ],
        "unavailable": [
            "I'm deep in exam prep right now.",
            "I've failed enough courses to know not to skip this part.",
            "Find me at the start of next semester.",
        ],
    },
    "professor_rahman": {
        "greeting": [
            "Ah, a student who actually comes to office hours.",
            "Prof. Rahman here"
            ". Sit down — I don't bite.",
            "Tell me what you're struggling with. That's what I'm here for.",
        ],
        "offer": [
            "There is a study group forming this week.",
            "I think it would help you. A few days of focused work.",
            "Think about it.",
        ],
        "farewell": [
            "My door is open. Remember that.",
        ],
        "unavailable": [
            "I'm preparing exam papers right now.",
            "Come see me at the start of next semester.",
            "And please — don't leave it this late next time.",
        ],
    },
    "professor_hoque": {
        "greeting": [
            "You are registered in my course.",
            "I am Prof. Hoque. I do not repeat instructions.",
            "Come prepared. Every single time.",
        ],
        "offer": [
            "There is an activity this week.",
            "It will be difficult. That is the point.",
            "If you are serious about this field — show up.",
        ],
        "farewell": [
            "Your choice. The work still needs to be done.",
        ],
        "unavailable": [
            "The semester is almost over.",
            "Whatever you needed to do — you should have done it earlier.",
        ],
    },
    "career_advisor_roya": {
        "greeting": [
            "Oh, a student! Come in, come in.",
            "I'm Ms. Roya — I run the career office.",
            "You're here earlier than most. That's already a good sign.",
        ],
        "offer": [
            "I have an internship shift available this week.",
            "It pays a stipend — not much, but real experience.",
            "Interested? It won't take long.",
        ],
        "farewell": [
            "No worries at all. My door is always open.",
            "Come back any time — even just to talk through your options.",
        ],
        "unavailable": [
            "I'm a bit swamped right now ,end of semester is always hectic.",
            "Come find me at the beginning of next semester.",
            "We'll have more options then anyway.",
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
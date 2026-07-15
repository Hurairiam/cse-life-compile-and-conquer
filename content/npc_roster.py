"""
content/npc_roster.py
CSE Life: Compile & Conquer
Created by: Ayesha Saheba Mostofa (dev3-narrative)
Sprint 1 — handed to Nangiba Tasnim for sprite/portrait production

This file defines every NPC that appears in the short scope.
The sprite_file and portrait_file values MUST match exactly
what Nangiba names her PNG files in assets/.
"""

NPC_ROSTER: dict = {
    "warm_classmate_purnno": {
        "display_name": "Purnno",
        "location": "cafeteria",
        "role": "Warm and supportive classmate, makes university feel survivable",
        "personality": "Genuine, kind, approachable",
        "semester_available_from": 1,
        "sprite_file": "assets/sprites/npc_purnno.png",
        "portrait_file": "assets/portraits/npc_purnno_{emotion}.png",
        "portrait_variants": ["neutral", "happy", "encouraging"],
    },
    "overachiever_classmate_rafi": {
        "display_name": "Rafi",
        "location": "university_library",
        "role": "Overachiever classmate who offers study tips and skill sprint quests",
        "personality": "Driven, helpful, slightly intimidating",
        "semester_available_from": 1,
        "sprite_file": "assets/sprites/npc_rafi.png",
        "portrait_file": "assets/portraits/npc_rafi_{emotion}.png",
        "portrait_variants": ["neutral", "encouraging", "focused"],
    },
    "struggling_friend_zayan": {
        "display_name": "Zayan",
        "location": "campus_courtyard",
        "role": "Struggling friend who enables bad habits early, faces moral dilemmas later",
        "personality": "Casual, avoidant, secretly stressed",
        "semester_available_from": 2,
        "sprite_file": "assets/sprites/npc_zayan.png",
        "portrait_file": "assets/portraits/npc_zayan_{emotion}.png",
        "portrait_variants": ["neutral", "stressed", "joking"],
    },
    "late_bloomer_kabir": {
        "display_name": "Kabir",
        "location": "university_library",
        "role": "Senior student who serves as cautionary figure then source of inspiration",
        "personality": "Quiet, worn out, eventually calm and wise",
        "semester_available_from": 3,
        "sprite_file": "assets/sprites/npc_kabir.png",
        "portrait_file": "assets/portraits/npc_kabir_{emotion}.png",
        "portrait_variants": ["neutral", "serious", "calm"],
    },
    "professor_rahman": {
        "display_name": "Prof. Rahman",
        "location": "classroom_a",
        "role": "Understanding professor who gives second chances without shame",
        "personality": "Patient, fair, quietly encouraging",
        "semester_available_from": 1,
        "sprite_file": "assets/sprites/npc_rahman.png",
        "portrait_file": "assets/portraits/npc_rahman_{emotion}.png",
        "portrait_variants": ["neutral", "disapproving", "approving"],
    },
    "professor_hoque": {
        "display_name": "Prof. Hoque",
        "location": "lecture_hall",
        "role": "Strict professor whose rare praise means everything",
        "personality": "Demanding, no nonsense, deeply fair",
        "semester_available_from": 5,
        "sprite_file": "assets/sprites/npc_hoque.png",
        "portrait_file": "assets/portraits/npc_hoque_{emotion}.png",
        "portrait_variants": ["neutral", "strict", "approving"],
    },
    "career_advisor_roya": {
        "display_name": "Ms. Roya",
        "location": "campus_lobby",
        "role": "Career advisor who guides player through internship and job applications",
        "personality": "Warm, professional, encouraging",
        "semester_available_from": 4,
        "sprite_file": "assets/sprites/npc_roya.png",
        "portrait_file": "assets/portraits/npc_roya_{emotion}.png",
        "portrait_variants": ["neutral", "happy", "serious"],
    },
}

# This list is used by the game engine to initialise NPC objects
NPC_IDS: list[str] = list(NPC_ROSTER.keys())

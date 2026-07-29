"""
side_quest_catalog.py

CSE Life: Compile & Conquer
Academic Package — Side Quest Catalog
─────────────────────────────────────────────────────────────
Content-loading layer for extracurricular SideQuests — the 12
self-study topics a player can repeatedly invest time in to grow
their SkillTree, outside of the formal course/exam pipeline.

EVALUATION MODEL (confirmed): participation-based, not perfection-
based. There is no quiz, no pass/fail, and no project submission
gate. A SideQuest is "completed" simply by spending the time —
exactly what SideQuest.execute_action() already does: deduct time,
grant EXP to the linked skill, mark completed. No changes were
needed to that method for this catalog.

Design notes
────────────
• Like _CATALOG_DATA in course_catalog.py, _SIDE_QUEST_DATA is a
  plain data table kept separate from the object-construction loop,
  so the full topic list reads like a simple table at a glance.

• Each topic is repeatable — GameClock/UI can hand out a fresh
  SideQuest instance from this catalog (or reuse the same one;
  SideQuest has no "already completed, can't repeat" lock the way
  Course does) whenever the player wants to invest more time in
  a skill. There's no cap on how many times a topic is attempted.

• time_cost and exp_reward are uniform (5 days / 15 EXP) across all
  12 topics by default — this keeps the "participation over
  perfection" philosophy consistent: every topic is treated as
  equally worthy of a player's time, regardless of real-world
  scope. Easy to differentiate later by editing the table below.

• skill_id values (e.g. "git", "docker") are arbitrary string keys
  — SkillTree.increment_skill() creates the entry on first use, so
  no separate skill registry needs to be maintained anywhere else.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import List, Optional, Tuple

from academic.quest import SideQuest


# Table columns: (quest_id, title, description, skill_id, time_cost, exp_reward)
_SIDE_QUEST_DATA: List[Tuple[str, str, str, str, int, int]] = [
    (
        "SQ_PROGRAMMING_LANGUAGE",
        "Learn a Core Programming Language",
        "Pick one main language like Python, Java, or C++ and master "
        "its syntax, features, and quirks.",
        "programming_language",
        5, 15,
    ),
    (
        "SQ_DSA",
        "Learn Data Structures & Algorithms",
        "Understand arrays, trees, and graphs so you can solve complex "
        "problems efficiently and pass coding interviews.",
        "dsa",
        5, 15,
    ),
    (
        "SQ_GIT_GITHUB",
        "Learn Git & GitHub",
        "Master how to track changes in your code, collaborate with "
        "team members, and manage project versions.",
        "git",
        5, 15,
    ),
    (
        "SQ_LINUX_CLI",
        "Learn Linux & Command Line",
        "Get comfortable navigating the operating system via the "
        "terminal instead of relying on a graphical user interface.",
        "linux_cli",
        5, 15,
    ),
    (
        "SQ_DATABASES_SQL",
        "Learn Databases & SQL",
        "Understand how to store, structure, and query data for web "
        "apps, services, and backend systems.",
        "databases_sql",
        5, 15,
    ),
    (
        "SQ_NETWORKING",
        "Learn Computer Networking",
        "Understand how data moves across the web — including basic "
        "concepts like HTTP, DNS, IP addresses, and REST APIs.",
        "networking",
        5, 15,
    ),
    (
        "SQ_WEB_APP_DEV",
        "Learn Web or App Development",
        "Build a complete full-stack project from start to finish so "
        "you know how frontend interfaces communicate with backends.",
        "web_app_dev",
        5, 15,
    ),
    (
        "SQ_DOCKER",
        "Learn Docker Basics",
        "Package your applications into containers so they run "
        "consistently on any machine without setup issues.",
        "docker",
        5, 15,
    ),
    (
        "SQ_AI_TOOLS",
        "Learn Modern AI Tools",
        "Understand how to integrate modern AI APIs into projects and "
        "use developer tools to speed up your coding workflow.",
        "ai_tools",
        5, 15,
    ),
    (
        "SQ_DEBUGGING_TESTING",
        "Learn Debugging & Testing",
        "Develop the skill to systematically hunt down bugs in your "
        "code and write simple unit tests to prevent future breaks.",
        "debugging_testing",
        5, 15,
    ),
    (
        "SQ_OOP",
        "Learn Object-Oriented Programming (OOP)",
        "Organize your code using classes and objects to keep your "
        "programs structured, reusable, and readable.",
        "oop",
        5, 15,
    ),
    (
        "SQ_TECH_COMMUNICATION",
        "Learn Technical Communication",
        "Practice writing clear documentation, doing code reviews, "
        "and explaining complex concepts in plain language.",
        "technical_communication",
        5, 15,
    ),
]


def build_side_quest_catalog() -> List[SideQuest]:
    """
    Construct and return the full side quest catalog as a list of
    SideQuest objects, one per topic, in the order above.

    Unlike build_course_catalog(), these instances are templates —
    since SideQuests are repeatable and carry no persistent pass/fail
    state, the engine/UI layer is free to either reuse these exact
    objects across attempts, or construct fresh copies from this same
    _SIDE_QUEST_DATA table each time one is offered to the player.
    """
    catalog: List[SideQuest] = []
    for quest_id, title, description, skill_id, time_cost, exp_reward in _SIDE_QUEST_DATA:
        quest = SideQuest(
            quest_id=quest_id,
            time_cost=time_cost,
            title=title,
            description=description,
        )
        quest.set_academic_gate_dependency_flag(skill_id)
        quest.set_exp_reward(exp_reward)
        catalog.append(quest)
    return catalog


def get_side_quest_by_id(catalog: List[SideQuest], quest_id: str) -> Optional[SideQuest]:
    """
    Convenience lookup: find a SideQuest in a catalog list by its
    quest_id. Returns None if not found.
    """
    if not quest_id:
        return None
    target = quest_id.strip().upper()
    for quest in catalog:
        if quest.get_quest_id().strip().upper() == target:
            return quest
    return None
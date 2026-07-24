"""
course_catalog.py

CSE Life: Compile & Conquer
Academic Package — Master Course Catalog
─────────────────────────────────────────────────────────────
This is the content-loading layer for the academic domain.
It builds the full, persistent list of Course objects that
the entire game (RegistrationManager, GameClock, etc.) draws
from — sourced directly from the official curriculum sheet.

STATUS: Prerequisites and categories are fully populated below.
Question/Answer content is intentionally left EMPTY — Course
already has add_question() ready to receive it; this file will
be updated with a second pass once question data is supplied.

Design notes
────────────
• _CATALOG_DATA is a plain data table (tuples), kept separate
  from the object-construction loop in build_course_catalog().
  This makes the curriculum easy to read/verify at a glance —
  it looks like the same table you'd see in the course sheet —
  without repeating 65 near-identical constructor calls.

• Elective/Minor slots (Major Elective 1-4, Optional/Minor 1-3,
  GED Elective 3) don't have official course codes yet in the
  curriculum sheet ("CSEXXXX", "N/A", "GEDXXXX") — placeholder
  codes were assigned below so each Course has a unique,
  hashable identity. Rename these once real course codes for
  the chosen electives are finalised.

• "GED Core N" / "GED Tier N" / "Mandatory for CSE" labels are
  treated as CATEGORY tags (descriptive metadata), not functional
  prerequisites — see chat discussion. Only real course codes
  (e.g. "CSE1102") are stored in the `prerequisites` field.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import List, Optional, Tuple

from academic.course import Course


# Table columns: (course_code, course_name, credit_value,
#                 prerequisites, is_lab_component, category)
_CATALOG_DATA: List[Tuple[str, str, int, List[str], bool, Optional[str]]] = [
    ("CSE1102", "Introduction to Programming", 1, [], False, None),
    ("GEF1101", "Academic English I", 3, [], False, "GED Core 1"),
    ("MAT1101", "Differential and Integral Calculus", 3, [], False, None),
    ("PHY1101", "Physics I", 3, [], False, None),
    ("PHY1102", "Physics I Lab", 1, [], True, None),
    ("CSE1201", "Structured Programming", 3, ["CSE1102"], False, None),
    ("CSE1202", "Structured Programming Lab", 1, ["CSE1102"], True, None),
    ("CSE1203", "Discrete Mathematics", 3, [], False, None),
    ("UCC1101", "Bangla Bhasa", 3, [], False, "GED Core 2"),
    ("MAT1201", "Coordinate Geometry and Linear Algebra", 3, [], False, None),
    ("ESK1110", "Study Skills", 0, [], False, "GED Core 6"),
    ("PHY1301", "Physics II", 3, [], False, None),
    ("CSE1301", "Data Structures", 3, ["CSE1201", "CSE1202"], False, None),
    ("CSE1302", "Data Structures Lab", 1, ["CSE1201", "CSE1202"], True, None),
    ("EEE1101", "Electrical Circuit 1", 3, [], False, None),
    ("EEE1102", "Electrical Circuit 1 Lab", 1, [], True, None),
    ("UCC1201", "History of the Emergence of Independent Bangladesh", 3, [], False, "GED Core 3"),
    ("ESK1111", "Healthy Life Skills", 0, [], False, "GED Core 6"),
    ("MAT2101", "Differential Equations and Numerical Analysis", 3, [], False, None),
    ("GEF1201", "English II", 3, [], False, "GED Core 4"),
    ("CSE2101", "Digital Logic Design", 3, [], False, None),
    ("CSE2102", "Digital Logic Design Lab", 1, [], True, None),
    ("CSE2103", "Object Oriented Programming", 3, ["CSE1201", "CSE1202"], False, None),
    ("CSE2104", "Object Oriented Programming Lab", 1, ["CSE1201", "CSE1202"], True, None),
    ("ESK1112", "Social Skills", 0, [], False, "GED Core 6"),
    ("CSE2201", "Algorithms", 3, ["CSE1203", "CSE1201", "CSE1202"], False, None),
    ("CSE2202", "Algorithms Lab", 1, ["CSE1203", "CSE1201", "CSE1202"], True, None),
    ("CSE2203", "Computer Organization and Architecture", 3, ["CSE2101"], False, None),
    ("STA2101", "Statistics and Probability", 3, [], False, None),
    ("EEE1301", "Electronic Device and Circuits 1", 3, [], False, None),
    ("EEE1302", "Electronic Device and Circuits 1 Lab", 1, [], True, None),
    ("CSE2200", "Design Project-I", 1, ["CSE2103", "CSE2104"], False, None),
    ("ESK1113", "Professional Skills", 0, [], False, "GED Core 6"),
    ("CSE2301", "Database Management System", 3, [], False, None),
    ("CSE2302", "Database Management System Lab", 1, [], True, None),
    ("CSE2303", "Automata and Theory of Computation", 3, ["CSE2201"], False, None),
    ("CSE2305", "Operating Systems", 3, ["CSE2203"], False, None),
    ("CSE2306", "Operating Systems Lab", 1, ["CSE2203"], True, None),
    ("GED2159", "Professional Ethics", 3, [], False, "GED Core 5"),
    ("CSE3101", "Microprocessor and Microcontroller", 3, ["CSE2203"], False, None),
    ("CSE3102", "Microprocessor and Microcontroller Lab", 1, ["CSE2203"], True, None),
    ("GED_ELEC3", "GED Elective 3", 3, [], False, "GED Elective - Social Science"),
    ("CSE3103", "System Analysis and Design", 3, ["CSE2103"], False, None),
    ("GED2243", "Environment and Sustainability", 3, [], False, "Mandatory for CSE / GED Tier 3"),
    ("CSE3120", "Web Programming", 1, ["CSE2103", "CSE2104"], False, None),
    ("CSE3201", "Artificial Intelligence & Machine Learning", 3,
        ["CSE2201", "CSE2202", "STA2101", "MAT1201"], False, None),
    ("CSE3202", "Artificial Intelligence & Machine Learning Lab", 1,
        ["CSE2201", "CSE2202", "STA2101", "MAT1201"], True, None),
    ("CSE3203", "Software Engineering", 3, ["CSE3103"], False, None),
    ("CSE3200", "Design Project-II", 1,
        ["CSE2301", "CSE2302", "CSE3103", "CSE2200"], False, None),
    ("CSE3205", "Computer Networks", 3, [], False, None),
    ("CSE3206", "Computer Networks Lab", 1, [], True, None),
    ("GED2248", "Industrial Management", 3, [], False, "Mandatory for CSE / GED Tier 2"),
    ("CSE_ELEC1", "Major Elective 1", 3, [], False, "Major Elective"),
    ("CSE3301", "Cyber Security", 3, ["CSE2305", "CSE2306", "CSE3205", "CSE3206"], False, None),
    ("MINOR1", "Optional/Minor 1", 3, [], False, "Optional/Minor"),
    ("CSE4098A", "Capstone Project 1", 1, [], False, None),
    ("CSE_ELEC2", "Major Elective 2", 3, [], False, "Major Elective"),
    ("CSE_ELEC2_LAB", "Major Elective 2 Lab", 1, [], True, "Major Elective"),
    ("CSE_ELEC3", "Major Elective 3", 3, [], False, "Major Elective"),
    ("MINOR2", "Optional/Minor 2", 3, [], False, "Optional/Minor"),
    ("CSE4098B", "Capstone Project 2", 1, [], False, None),
    ("CSE_ELEC4", "Major Elective 4", 3, [], False, "Major Elective"),
    ("MINOR3", "Optional/Minor 3", 3, [], False, "Optional/Minor"),
    ("CSE4098C", "Capstone Project 3", 2, [], False, None),
    ("CSE4099", "Internship / Thesis", 1, [], False, None),
]


def build_course_catalog() -> List[Course]:
    """
    Construct and return the full master catalog as a list of
    persistent Course objects, in curriculum order.

    Called ONCE at game startup (GameSession initialisation).
    The same Course instances returned here are the ones that
    live on forever — RegistrationManager filters this list,
    AcademicHistory tracks these exact objects' codes, and
    Semester holds references into this same list. No Course
    is ever re-instantiated for a backlog/retake.
    """
    catalog: List[Course] = []
    for code, name, credits, prereqs, is_lab, category in _CATALOG_DATA:
        catalog.append(
            Course(
                course_code=code,
                course_name=name,
                credit_value=credits,
                prerequisites=prereqs,
                is_lab_component=is_lab,
                category=category,
            )
        )
    return catalog


def get_course_by_code(catalog: List[Course], course_code: str) -> Optional[Course]:
    """
    Convenience lookup: find a Course in a catalog list by its code.
    Returns None if not found. Useful for wiring up MainQuest
    instances or content scripts that reference a course by ID.
    """
    if not course_code:
        return None
    target = course_code.strip().upper()
    for course in catalog:
        if course.get_course_code() == target:
            return course
    return None
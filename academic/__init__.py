"""
academic/__init__.py

CSE Life: Compile & Conquer
Academic Package — Public Interface
─────────────────────────────────────────────────────────────
This file marks academic/ as a Python package and re-exports
its public classes, so other packages (engine/, core/, main.py)
can import directly from "academic" instead of reaching into
each internal module:

    from academic import Course, AcademicHistory, Semester
    from academic import Quest, MainQuest, SideQuest

instead of the longer form:

    from academic.course import Course
    from academic.academic_history import AcademicHistory
    ...

Both import styles still work — this file just adds the shorter
option and gives the package a single, clear "table of contents".
─────────────────────────────────────────────────────────────
"""

from academic.course import Course
from academic.academic_history import AcademicHistory
from academic.semester import Semester
from academic.quest import Quest, MainQuest, SideQuest

__all__ = [
    "Course",
    "AcademicHistory",
    "Semester",
    "Quest",
    "MainQuest",
    "SideQuest",
]
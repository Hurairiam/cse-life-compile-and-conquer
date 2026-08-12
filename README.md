# CSE Life: Compile & Conquer

A 2D life-simulation RPG built with **Python** and **Pygame**, where the player navigates a Computer Science & Engineering undergraduate's journey through course registration, exams, time and resource management, and campus exploration.

Object-Oriented Programming is a core design constraint, with major game systems implemented through class hierarchies demonstrating abstraction, encapsulation, inheritance, and polymorphism.

## Gameplay

Players take on the role of a CSE student progressing semester by semester:

- Register for courses under credit-limit and prerequisite constraints
- Manage a limited time pool and wallet balance across academic and exploration activities
- Sit timed multiple-choice exams with pass/fail outcomes affecting credits and backlog status
- Explore a tile-based campus, interact with NPCs through dialogue, and encounter gated areas with entry requirements
- Save and resume progress across sessions
- Reach different endings based on accumulated credits, skills, and academic standing

## Scope

The project is defined across two scopes:

- **Short Scope (MVP)** — the currently implemented core loop: registration, exploration, exams, NPC dialogue, gates, save/load, and endgame evaluation. This is the playable scope.
- **Full Scope** — a larger design extending into a post-graduate career simulation, including corporate and freelance tracks, certifications, and an expanded financial system. It exists as UML documentation only and is not currently implemented.

The Full Scope defines the direction for future development beyond the MVP.

## Architecture

The codebase separates game/domain logic from presentation:

- `core/`, `academic/`, and the domain layer of `engine/` contain the game's rules and state, including `Player`, `Course`, `Quest`, `AcademicHistory`, `GameSession`, `GameClock`, and `RegistrationManager`. This layer has no dependency on Pygame.
- `ui/` and `engine/states/` contain rendering and screen logic. Each game screen is a self-contained module reached through a routed screen-state system, keeping presentation separate from the rules it displays.
- `content/` contains static data such as dialogue, course catalogs, and level definitions.
- `levels/` contains level data produced with the in-repository level editor in `tools/level_editor.py`.

This separation allows the underlying simulation to be reasoned about and tested independently of how it is rendered.

## Current Status

The **Short Scope (MVP)** is under active development through a fixed-scope Agile workflow, using sprint-based iterations, per-contributor Git branches, and pull-request-based integration.

The **Full Scope** is documented but not currently scheduled for implementation until the MVP is complete.

## Getting Started

### Requirements

- Python 3.10+
- Pygame

### Installation

```bash
git clone https://github.com/Hurairiam/cse-life-compile-and-conquer.git
cd cse-life-compile-and-conquer
pip install -r requirements-dev.txt
```

### Run the Game

```bash
python main.py
```

### Run the Test Suite

```bash
pytest tests/
```

## Project Structure

```text
core/           Foundational abstractions (Character, TimeConsumable, SkillTree)
academic/       Academic domain model (Course, Quest, AcademicHistory, Semester)
engine/         Game orchestration — session, clock, registration, exams, gates, save/load
engine/states/  One module per screen; routed by the active screen state
ui/             Pygame rendering — every screen the player sees
content/        Static data — dialogue, course catalog, level schema, skill tree layout
levels/         Level data authored with the in-repository level editor
tools/          Standalone level editor used to author levels/*.json
tests/          Automated test suite (pytest)
diagrams/       UML diagrams for both project scopes
```

## Documentation

UML documentation for both scopes is available in [`diagrams/`](diagrams/):

- [Short Scope](diagrams/short_scope/) — diagrams matching the current MVP
- [Full Scope](diagrams/full_scope/) — diagrams for the extended, not-yet-implemented design

Additional design notes are available in [`docs/`](docs/).

## Team

| Member | Role |
|---|---|
| Abu Huraira | Engine architecture, game systems, integration |
| Saif Hasan Khan | Academic domain logic |
| Nangiba Tasnim | UI, Pygame implementation, level design tooling |
| Ayesha Saheba Mostofa | Narrative content, dialogue |

## License

No license has been specified for this project. All rights reserved by the authors unless otherwise stated.
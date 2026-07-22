# CSE Life: Compile & Conquer

Welcome to **CSE Life: Compile & Conquer**, an analytical, text-based simulation engine and resource-management role-playing game. Built on a strict Object-Oriented Programming (OOP) framework, this system models the strategic, academic, professional, and financial lifecycle of a Computer Science and Engineering (CSE) undergraduate student.

The system utilizes an **evolutionary prototyping strategy**, establishing a verified architectural baseline before scaling into a decoupled, multi-phase lifecycle ecosystem.

---

## 🗺️ System Architecture & Architecture Blueprint

The simulation environment is organized into discrete architectural phases to model immediate academic requirements as well as post-graduate career horizons.

### 1. Phase 1: Short-Scope (Core Undergraduate Simulation)
*Focuses on strict undergraduate constraints, abstract class verification contracts, custom runtime exceptions, and the fundamental semester progression loop.*

* 📄 [Short Scope — Use Case Diagram](diagrams/short_scope/Short_Use_Case.pdf)
* 📄 [Short Scope — Activity Diagram](diagrams/short_scope/Short_Activity_Diagram.pdf)
* 📄 [Short Scope — UML Class Diagram](diagrams/short_scope/Short_UML.pdf)
* 📄 [Short Scope — System Sequence Diagram (SSD)](diagrams/short_scope/Short_System_Sequence_Diagram.pdf)

### 2. Phase 2: Full-Scope (Extended Professional Horizon)
*Models the post-graduate horizon, featuring dynamic professional tracks (Corporate Enterprise Career vs. Volatile Freelance Track), certifications, advanced financial dependencies, and an expanded chronological endgame evaluation engine.*

* 📄 [Full Scope — Use Case Diagram](diagrams/full_scope/Full_Use_Case.pdf)
* 📄 [Full Scope — Activity Diagram](diagrams/full_scope/Full_Activity_Diagram.pdf)
* 📄 [Full Scope — UML Class Diagram](diagrams/full_scope/Full_UML.pdf)
* 📄 [Full Scope — System Sequence Diagram (SSD)](diagrams/full_scope/Full_System_Sequence_Diagram.pdf)

---

## 🎮 Core Game Mechanics & Engine Constraints

The simulation operates under strict resource-allocation matrices managed by the central simulation loop:

### 💼 1. Semester Registration & Course Prerequisites
Before entering active gameplay loops at the start of a semester, the engine executes initialization check sequences:
* **Registration Cost Routing:** Players choose between **Option A (Work-Study)**, which costs `10 Days` from the upcoming semester time pool, or **Option B (Flat Tuition Fee)**, which deducts `12,000 BDT` from the player's wallet balance.
* **Prerequisite Enforcement:** Available courses are filtered dynamically through the player's `AcademicHistory` tracking ledger to enforce prerequisite trees.
* **Credit Constraints:** The engine caps course selection at a strict maximum limit of **15 Credits** per semester.

### 🛡️ 2. The 15-Day Borderline Firewall
During the active gameplay phase, a structural constraint firewall safeguards state progression:
* When the remaining semester time pool falls to **15 Days or fewer**, all extracurricular activity and side quest pipelines are locked out.
* The system isolates the state machine, forcing the execution of `MainQuest` threads (Theory & Lab Exam sequences) to prevent terminal game state traps.

### 📝 3. Exam Optimization & Backlog Lifecycle
* **Q&A Optimization Loop:** Players can attempt an interactive 3-question Q&A sequence before major milestones. Success optimizes the action time cost down to **10 Days**; failure defaults it to an unoptimized cost of **14 Days**.
* **Persistent Course Lifecycle:** Courses are tracked as persistent single-instance entities. Failed course objects are flagged as incomplete and moved directly into the `AcademicHistory` backlog array, seamlessly re-injecting them into the next available semester catalog without artificial duplication.

### 🏁 4. Analytical Endgame Evaluation
Upon reaching the final chronological timeline cap (**960 days** for Short-Scope / **1680 days** for Full-Scope), the system freezes inputs and routes control to the `EndgameEvaluationManager`. The profile is audited across three criteria:
1. **Academic State:** Validates graduation criteria (completion of exactly **140 Credits**).
2. **Financial Liquidity:** Audits the accumulated `walletBalance` tier.
3. **Skill Profile:** Evaluates `SkillTree` progression depths to route the player profile into a highly tailored, text-driven narrative epilogue.

---

## 🛠️ Codebase Layout & OOP Mapping

The codebase enforces strict encapsulation boundaries, cleanly distributing object responsibilities across isolated packages:

### 📦 `core/` Package (Universal Foundation)
* **`interfaces.py` (`TimeConsumable`):** A pure abstract contract driving the **Polymorphism** engine. Any action modifying the timeline implements `execute_action()`, allowing uniform time tracking.
* **`character.py` (`Character`, `Player`, `NPC`):** Enforces **Abstraction** (the base class cannot be instantiated directly), **Encapsulation** (private identity and location attributes), and **Inheritance** (`Player` and `NPC` extend the abstract base).
* **`skill_tree.py` (`SkillTree`):** Encapsulates cross-semester technical and soft skill proficiency matrices inside private structures, exposed only via validated mutation methods.

### 📦 `academic/` Package (Educational Logic Domain)
* **`semester.py` (`Semester`):** Manages the 80-day time pool and registered course arrays for individual terms. Instantiated fresh each semester cycle while the player profile persists.
* **`quest.py` (`Quest`, `MainQuest`, `SideQuest`):** Provides an abstract tracking hierarchy for events, branching into core academic requirements (`MainQuest`) and skill-building activities (`SideQuest`).
* **`course.py` (`Course`):** Houses course metadata and provides verification logic for tracking dependencies against the player's profile.
* **`academic_history.py` (`AcademicHistory`):** The private, permanent ledger tracking accumulated credits, completed course listings, and backlogged subjects.

### 📦 `engine/` Package (Simulation Orchestration Core)
* **`game_session.py` (`GameSession`):** The top-level composition owner of the runtime environment. Encapsulates the global career clock, the persistent player profile, and the active semester instance.
* **Simulation Managers:** Orchestrates time progression, handles transactional flows during course registration, and computes final grading weights.

### 🚀 Root Entry Point
* **`main.py`:** The system bootloader. Initializes the tracking loop, validates abstract design contracts, and provisions user interface states.
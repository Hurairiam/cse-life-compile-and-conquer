# CSE Life: Compile & Conquer

Welcome to **CSE Life: Compile & Conquer**, an analytical, text-based role-playing and resource-management simulation engine. This project is built using a strict Object-Oriented Programming (OOP) framework to simulate the strategic, academic, professional, and financial lifecycle of a Computer Science and Engineering (CSE) undergraduate student.

The project follows an **evolutionary prototyping strategy**, establishing a stable, verified structural baseline (**Short-Scope MVP**) before scaling into a decoupled multi-phase lifecycle ecosystem (**Full-Scope Target**).

---

## 🗺️ System Architecture & Blueprint Ledger

### 1. Phase 1: Short-Scope (Current Implementation Baseline)
*Focuses on the strict undergraduate simulation constraints, abstract class verification contracts, runtime exceptions, and the fundamental semester progression loop.*

* 📄 [Short Scope — Use Case Diagram](diagrams/short_scope/Short_Use_Case.pdf)
* 📄 [Short Scope — Activity Diagram](diagrams/short_scope/Short_Activity_Diagram.pdf)
* 📄 [Short Scope — UML Class Diagram](diagrams/short_scope/Short_UML.pdf)
* 📄 [Short Scope — System Sequence Diagram (SSD)](diagrams/short_scope/Short_System_Sequence_Diagram.pdf)

### 2. Phase 2: Full-Scope (Target Horizon Blueprint)
*Models the extended post-graduate horizon, featuring dynamic professional tracks (Corporate Enterprise Career vs. Volatile Freelance Track), certifications, advanced financial dependencies, and a 1680-day hard-capped Endgame Evaluation engine.*

* 📄 [Full Scope — Use Case Diagram](diagrams/full_scope/Full_Use_Case.pdf)
* 📄 [Full Scope — Activity Diagram](diagrams/full_scope/Full_Activity_Diagram.pdf)
* 📄 [Full Scope — UML Class Diagram](diagrams/full_scope/Full_UML.pdf)
* 📄 [Full Scope — System Sequence Diagram (SSD)](diagrams/full_scope/Full_System_Sequence_Diagram.pdf)

---

## 🎮 Core Game Mechanics & System Rules

Based on our updated architectural blueprints, the simulation operates under strict resource-allocation matrices:

### 💼 1. Semester Registration & OR Penalty Matrix
Before selecting courses at the start of a semester, the system enforces an Operations Research (OR) style tuition selection:
* **Option A (Work-Study):** Costs `10 Days` from the player's upcoming semester time pool.
* **Option B (Flat Tuition Fee):** Costs `12,000 BDT` from the player's wallet balance.
* **Academic Constraints:** Courses are filtered through the player's `AcademicHistory` to enforce self-referential prerequisite trees. The engine enforces a strict cap of **Max 15 Credits** per semester during selection.

### 🛡️ 2. The 15-Day Borderline Firewall
During the active gameplay phase, a strict structural firewall is applied by the engine:
* When the remaining semester time pool falls to **15 Days or fewer**, all extracurricular activity pipelines are locked down.
* The player is forced to exclusively execute `MainQuest` threads (Theory & Lab Exam sequences) to prevent game state traps.

### 📝 3. Exam Optimization & Backlog Lifecycle
* **Q&A Optimization Loop:** Players can attempt an interactive 3-question Q&A sequence before exams. Success optimizes the exam action time cost down to **10 Days**; failure leaves it at an unoptimized **14 Days**.
* **Persistent Course Tracking:** Courses are persistent single-instance objects. If an exam is failed, the course object is flagged as incomplete and pushed directly into the `AcademicHistory` backlog array to be cleanly re-injected into the next semester's catalog with no artificial duplication penalties.

### 🏁 4. Analytical Endgame Evaluation
Upon reaching the ultimate chronological timeline cap (960 days for Short-Scope / 1680 days for Full-Scope), the system freezes and passes control to the `EndgameEvaluationManager` to grade the profile across three distinct criteria:
1. **Academic State:** Checks for graduation criteria (exactly **140 Credits** completed).
2. **Financial Liquidity:** Audits the `walletBalance` tier.
3. **Skill Profile:** Evaluates `SkillTree` progression levels to route the player into one of multiple customized, text-driven narrative epilogues (ranging from *Corporate Elite* to *Prolonged Debt Junior Freelancer*).

---

## 🛠️ Sprint 1 Project Layout & OOP Mapping

The codebase cleanly distributes object roles across distinct domain packages to demonstrate decoupling and strict encapsulation boundaries:

### 📦 `core/` Package (Universal Simulation Core)
* **`interfaces.py` (`TimeConsumable`):** A pure abstract contract driving our **Polymorphism** engine. Any action that consumes chronological days must implement `execute_action()`, letting the global clock handle processes uniformly.
* **`character.py` (`Character`, `Player`, `NPC`):** Enforces **Abstraction** (base cannot be instantiated directly), **Encapsulation** (private identity and location attributes), and **Inheritance** (`Player` and `NPC` specialize the abstract base).
* **`skill_tree.py` (`SkillTree`):** Completely encapsulates cross-semester skill matrices inside private structures, exposed only via validated methods.

### 📦 `academic/` Package (Educational Logic Domain)
* **`quest.py` (`Quest`, `MainQuest`, `SideQuest`):** Provides an abstract tracking hierarchy for time-bound events, branching into core academic requirements (`MainQuest`) and skill-building activities (`SideQuest`).
* **`course.py` (`Course`):** Houses course metadata and driving mechanisms for prerequisite validations against the player profile.
* **`academic_history.py` (`AcademicHistory`):** The private permanent ledger tracking accumulated credit values, completed course listings, and backlogged subjects.

### 🚀 Root Entry Point
* **`main.py`:** The validation test suite proving that runtime constraints (`TypeError` handling for abstract classes) and behavioral pipelines are fully functional.
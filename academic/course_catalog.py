"""
course_catalog.py

CSE Life: Compile & Conquer
Academic Package — Master Course Catalog
─────────────────────────────────────────────────────────────
This is the content-loading layer for the academic domain.
It builds the full, persistent list of Course objects that
the entire game (RegistrationManager, GameClock, etc.) draws
from — sourced directly from the official curriculum sheet —
and now also loads the full 3-tier MCQ exam ladder (easy/
medium/hard) for every single course, sourced from the
official question bank document.

STATUS: COMPLETE. Prerequisites, categories, AND questions
are all populated. build_course_catalog() returns fully
exam-ready Course objects — is_question_set_complete() will
be True for all 65 courses.

Design notes
────────────
• _CATALOG_DATA is a plain data table (tuples), kept separate
  from the object-construction loop in build_course_catalog().
  This makes the curriculum easy to read/verify at a glance —
  it looks like the same table you'd see in the course sheet —
  without repeating 65 near-identical constructor calls.

• _QUESTION_DATA is a second plain data table, keyed by course
  code, holding the (question_text, options, correct_letter)
  triple for each of the 3 difficulty tiers. It was generated
  from the official MCQ document and lightly cleaned (LaTeX
  math notation like $O(n)$, \frac{}{}, \begin{bmatrix} was
  converted to plain, readable text since this is a text-based
  game with no math-rendering engine).

• Elective/Minor slots (Major Elective 1-4, Optional/Minor 1-3,
  GED Elective 3) don't have official course codes yet in the
  curriculum sheet ("CSEXXXX", "N/A", "GEDXXXX") — placeholder
  codes were assigned below so each Course has a unique,
  hashable identity. Rename these once real course codes for
  the chosen electives are finalised.

• "Major Elective 2 + Lab" (CSE_ELEC2 / CSE_ELEC2_LAB) only had
  ONE shared set of 3 questions in the source document (labeled
  "Theory Q1/Q2" + "LAB Q3"), unlike every other theory+lab pair
  which had two fully separate question sets. The same 3
  questions are therefore applied to BOTH Course objects here.
  Flag this to the team if separate lab-specific questions are
  wanted later — it's a one-line change in _QUESTION_DATA.

• "GED Core N" / "GED Tier N" / "Mandatory for CSE" labels are
  treated as CATEGORY tags (descriptive metadata), not functional
  prerequisites — see chat discussion. Only real course codes
  (e.g. "CSE1102") are stored in the `prerequisites` field.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

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


# Auto-generated MCQ data: course_code -> {tier: (question_text, [options...], correct_letter)}
_QUESTION_DATA: Dict[str, Dict[str, Tuple[str, List[str], str]]] = {
    "CSE1102": {
        "easy": ("Which device component directly executes machine code instructions?", ["Hard Disk Drive", "Central Processing Unit (CPU)", "RAM", "Monitor"], "B"),
        "medium": ("In programming, what is the value of 15 % 4?", ["3", "3.75", "1", "0"], "A"),
        "hard": ("What is the key characteristic of an algorithm with O(1) time complexity?", ["Execution time grows linearly with input size.", "Execution time remains constant regardless of input size.", "Execution time grows quadratically.", "It requires recursive calls."], "B"),
    },
    "GEF1101": {
        "easy": ("Which part of speech is used to modify a verb, an adjective, or another adverb?", ["Noun", "Preposition", "Adverb", "Conjunction"], "C"),
        "medium": ("Identify the passive voice structure of the sentence: \"The researcher conducted an experiment.\"", ["An experiment was conducted by the researcher.", "The researcher has conducted an experiment.", "An experiment conducted the researcher.", "An experiment is being conducted by the researcher."], "A"),
        "hard": ("What constitutes a thesis statement in an academic essay?", ["A summary of the author's biography", "A single statement that presents the central argument or claim of the essay", "A list of all reference citations", "A rhetorical question at the end of the conclusion"], "B"),
    },
    "MAT1101": {
        "easy": ("What is the derivative of f(x) = x^3 with respect to x?", ["3x", "3x^2", "x^2", "x^4/4"], "B"),
        "medium": ("What is the definite integral of 2x dx from 0 to 2?", ["2", "4", "6", "8"], "B"),
        "hard": ("According to L'Hôpital's Rule, what is the limit as x approaches 0 of (sin x)/x?", ["0", "1", "infinity", "Undefined"], "B"),
    },
    "PHY1101": {
        "easy": ("What is the SI unit of force?", ["Joule", "Watt", "Newton", "Pascal"], "C"),
        "medium": ("What is the work done when a force of 10 N moves an object by 5 meters in the direction of the force?", ["2 J", "15 J", "50 J", "100 J"], "C"),
        "hard": ("If the momentum of an isolated system is conserved during a collision, which type of collision guarantees kinetic energy is also conserved?", ["Inelastic collision", "Completely inelastic collision", "Elastic collision", "Explosive collision"], "C"),
    },
    "PHY1102": {
        "easy": ("Which instrument is used to measure small linear dimensions or thickness with high accuracy?", ["Stopwatch", "Screw Gauge / Micrometer", "Thermometer", "Voltmeter"], "B"),
        "medium": ("What is the main source of systematic error in a pendulum timing experiment?", ["Human reaction time variations", "Friction at the pivot point and air resistance", "Random temperature fluctuations", "Parallax error during counting"], "B"),
        "hard": ("When plotting a V vs I graph for an ideal resistor, what does the slope of the linear plot represent?", ["Power", "Resistance", "Capacitance", "Inductance"], "B"),
    },
    "CSE1201": {
        "easy": ("Which data type in C is best suited to store a single character?", ["int", "float", "char", "double"], "C"),
        "medium": ("What is the output of sizeof(int) on standard 32-bit/64-bit architecture?", ["1 byte", "2 bytes", "4 bytes", "8 bytes"], "C"),
        "hard": ("What does the keyword static do when applied to a local variable inside a function?", ["Makes the variable accessible globally across all files.", "Preserves its value between successive function calls.", "Stores the variable directly in CPU registers.", "Converts the variable into a constant."], "B"),
    },
    "CSE1202": {
        "easy": ("Which function is used in standard C to read formatted input from the keyboard?", ["printf()", "scanf()", "puts()", "write()"], "B"),
        "medium": ("What will happen if you attempt to open a non-existent file in read mode (\"r\") using fopen()?", ["The file is automatically created.", "fopen() returns NULL.", "The program throws a syntax error.", "The computer reboots."], "B"),
        "hard": ("In C pointer laboratory, if int arr[5] = {10, 20, 30, 40, 50};, what is the value of *(arr + 3)?", ["10", "30", "40", "Address of arr[3]"], "C"),
    },
    "CSE1203": {
        "easy": ("What is the truth value of P AND Q if P is True and Q is False?", ["True", "False", "Undefined", "Tautology"], "B"),
        "medium": ("How many edges are in a complete graph K_5 with 5 vertices?", ["5", "10", "20", "25"], "B"),
        "hard": ("Which of the following describes a relation that is Reflexive, Symmetric, and Transitive?", ["Partial Order Relation", "Equivalence Relation", "Total Order Relation", "Bijective Function"], "B"),
    },
    "UCC1101": {
        "easy": ("বাংলা ভাষার মূল উৎস কোনটি?", ["বৈদিক ভাষা", "সংস্কৃত ভাষা", "প্রাকৃত ভাষা / ইন্দো-ইউরোপীয় মূল ভাষা", "পালি ভাষা"], "C"),
        "medium": ("বাংলা ব্যাকরণের প্রধান অঙ্গ কয়টি?", ["৩ টি", "৪ টি", "৫ টি", "৬ টি"], "B"),
        "hard": ("'সন্ধি' বাংলা ব্যাকরণের কোন অংশে আলোচিত হয়?", ["রূপতত্ত্ব", "ধ্বনিতত্ত্ব", "বাক্যতত্ত্ব", "অর্থতত্ত্ব"], "B"),
    },
    "MAT1201": {
        "easy": ("What is the determinant of a 2 x 2 matrix [[a, b], [c, d]]?", ["ac - bd", "ad - bc", "ad + bc", "a + d"], "B"),
        "medium": ("What is the distance between points (1,2) and (4,6) in a Cartesian coordinate system?", ["3", "4", "5", "25"], "C"),
        "hard": ("When is a square matrix A invertible?", ["When its determinant is equal to zero (det(A) = 0).", "When its determinant is non-zero (det(A) != 0).", "Only when it is an identity matrix.", "When all its entries are positive."], "B"),
    },
    "ESK1110": {
        "easy": ("Which note-taking technique divides a page into two columns (cues and notes) with a summary section at the bottom?", ["Mind Mapping", "Cornell Method", "Outlining Method", "Sentence Method"], "B"),
        "medium": ("What does the \"S\" stand for in the SMART goal-setting framework?", ["Simple", "Specific", "Sustainable", "Systemic"], "B"),
        "hard": ("What is the active reading strategy SQ3R composed of?", ["Summarize, Question, Read, Recite, Review", "Survey, Question, Read, Recite, Review", "Scan, Query, Read, Write, Repeat", "Study, Question, Read, Reflect, Revise"], "B"),
    },
    "PHY1301": {
        "easy": ("According to Coulomb's Law, what happens to the electrostatic force between two charges if the distance between them is doubled?", ["It doubles.", "It quadruples.", "It drops to one-half.", "It drops to one-fourth."], "D"),
        "medium": ("What does Gauss's Law for Magnetism (∇·B = 0) state regarding magnetic poles?", ["Isolated magnetic monopoles do not exist.", "Magnetic field lines always start and end at infinity.", "Electric charge creates magnetic dipoles.", "Magnetic flux is always non-zero in a closed surface."], "A"),
        "hard": ("Which phenomenon demonstrates the particle nature of light?", ["Interference", "Diffraction", "Photoelectric Effect", "Polarization"], "C"),
    },
    "CSE1301": {
        "easy": ("Which data structure follows the Last-In-First-Out (LIFO) principle?", ["Queue", "Stack", "Array", "Binary Tree"], "B"),
        "medium": ("What is the worst-case time complexity of standard Binary Search on a sorted array of n elements?", ["O(1)", "O( log n )", "O(n)", "O( n^2 )"], "B"),
        "hard": ("What is the maximum number of children a node can have in a standard Binary Tree?", ["1", "2", "n", "Unlimited"], "B"),
    },
    "CSE1302": {
        "easy": ("In a C stack implementation using an array, what variable condition indicates an empty stack?", ["top == 0", "top == -1", "top == MAX_SIZE", "top == NULL"], "B"),
        "medium": ("In a Queue laboratory exercise, what operation removes an element from the front of the queue?", ["Push", "Pop", "Enqueue", "Dequeue"], "D"),
        "hard": ("When implementing a circular linked list, what does the next pointer of the last node point to?", ["NULL", "The previous node", "The head node", "Itself"], "C"),
    },
    "EEE1101": {
        "easy": ("What does Ohm's Law state?", ["V = I/R", "V = I * R", "P = V * R", "I = V * R"], "B"),
        "medium": ("According to Kirchhoff's Current Law (KCL), what is the algebraic sum of currents entering a node in an electric circuit?", ["Equal to total voltage", "Zero", "Infinite", "Equal to resistance"], "B"),
        "hard": ("In a parallel circuit containing two resistors R_1 = 6 Ω and R_2 = 3 Ω, what is the equivalent resistance?", ["9 Ω", "4.5 Ω", "2 Ω", "18 Ω"], "C"),
    },
    "EEE1102": {
        "easy": ("How should an Ammeter be connected in a circuit to measure current through a component?", ["In parallel with the component", "In series with the component", "Directly across the DC source", "It does not matter"], "B"),
        "medium": ("What happens if a Voltmeter with low internal resistance is connected in parallel to a high-resistance component?", ["It measures the voltage accurately.", "It creates a severe loading effect and alters circuit behavior.", "It acts as an open circuit.", "The circuit resistance increases."], "B"),
        "hard": ("In a lab setup verifying Thevenin's Theorem, how is R_th measured between load terminals?", ["By replacing all independent voltage sources with open circuits and current sources with short circuits.", "By turning off independent sources (short voltage sources, open current sources) and measuring resistance across open load terminals.", "By connecting maximum load resistance across the terminals.", "By measuring the current under direct short-circuit conditions."], "B"),
    },
    "UCC1201": {
        "easy": ("In which year was the Historic Language Movement (Bhasha Andolon) peak observed on 21st February?", ["1947", "1952", "1966", "1971"], "B"),
        "medium": ("Who delivered the historic speech on 7th March 1971 at Suhrawardy Udyan (then Race Course Maidan)?", ["Tajuddin Ahmad", "Bangabandhu Sheikh Mujibur Rahman", "Maulana Bhashani", "Syed Nazrul Islam"], "B"),
        "hard": ("When was the provisional government of the People's Republic of Bangladesh (Mujibnagar Government) formed?", ["26th March 1971", "10th April 1971", "16th December 1971", "21st February 1952"], "B"),
    },
    "ESK1111": {
        "easy": ("What is the recommended average daily amount of sleep for an adult to maintain physical health?", ["3--4 hours", "7--9 hours", "10--12 hours", "14+ hours"], "B"),
        "medium": ("Which factor is considered a core element of emotional intelligence?", ["High IQ score", "Self-awareness and empathy", "Memorization ability", "Technical expertise"], "B"),
        "hard": ("Which body index is calculated as weight in kilograms divided by height in meters squared (kg/m^2)?", ["BMR", "BMI", "Heart Rate Reserve", "Caloric Burn Index"], "B"),
    },
    "MAT2101": {
        "easy": ("What is the degree of the differential equation \\frac{d^2y}{dx^2} + 3( dy/dx )^3 + y = 0?", ["1", "2", "3", "5"], "A"),
        "medium": ("Which numerical method is an iterative root-finding technique that uses linear interpolation between bounds with opposite signs?", ["Newton-Raphson Method", "Bisection Method / Regula Falsi", "Euler's Method", "Simpson's Rule"], "B"),
        "hard": ("What is the order of convergence of the Newton-Raphson method for a simple root?", ["1 (Linear)", "2 (Quadratic)", "3 (Cubic)", "1.618"], "B"),
    },
    "GEF1201": {
        "easy": ("Which sentence contains a correctly punctuated compound sentence?", ["I wanted to go for a walk, but it started to rain.", "I wanted to go for a walk but it started to rain.", "I wanted to go for a walk; but it started to rain.", "I wanted to go for a walk but, it started to rain."], "A"),
        "medium": ("What is the term for a word that connects clauses or sentences, such as *furthermore*, *however*, or *therefore*?", ["Preposition", "Conjunctive Adverb", "Interjection", "Relative pronoun"], "B"),
        "hard": ("In critical literature analysis, what does \"tone\" refer to?", ["The physical loudness of an audio reading", "The author's attitude toward the subject matter or audience", "The chronological order of plot points", "The primary conflict between protagonist and antagonist"], "B"),
    },
    "CSE2101": {
        "easy": ("Which logic gate produces an output of 1 only when both of its inputs are 1?", ["OR", "AND", "XOR", "NOR"], "B"),
        "medium": ("What is the simplified form of A + A * B using Boolean algebra theorems?", ["B", "A", "A * B", "1"], "B"),
        "hard": ("How many select lines are required for a 16-to-1 Multiplexer (MUX)?", ["2", "3", "4", "8"], "C"),
    },
    "CSE2102": {
        "easy": ("Which IC number corresponds to a standard quad 2-input NAND gate in TTL logic?", ["7400", "7404", "7408", "7432"], "A"),
        "medium": ("In a lab experiment, what is the output of a 7404 IC inverter when given a high input (5V / Logic 1)?", ["5V / Logic 1", "0V / Logic 0", "High Impedance", "2.5V"], "B"),
        "hard": ("When constructing a J-K flip-flop circuit in lab, what condition occurs when both J = 1 and K = 1 upon receiving a clock pulse?", ["Set condition (Q = 1)", "Reset condition (Q = 0)", "Toggle condition (Q_next = NOT Q)", "Invalid/Forbidden state"], "C"),
    },
    "CSE2103": {
        "easy": ("Which OOP pillar allows a child class to acquire properties and behaviors of a parent class?", ["Encapsulation", "Inheritance", "Polymorphism", "Abstraction"], "B"),
        "medium": ("What is Method Overloading?", ["Defining a method in a subclass with the same name and parameters as in the superclass.", "Defining multiple methods in the same class with the same name but different parameters.", "Dynamic dispatch of functions at runtime.", "Hiding variable visibility within private scope."], "B"),
        "hard": ("What distinguishes an Abstract Class from a standard class in OOP?", ["An abstract class cannot contain constructors.", "An abstract class cannot be instantiated directly using new.", "Abstract classes cannot have member variables.", "Abstract classes automatically run faster than normal classes."], "B"),
    },
    "CSE2104": {
        "easy": ("Which keyword is used in C++ to instantiate a new dynamic object on the heap?", ["malloc", "create", "new", "alloc"], "C"),
        "medium": ("In Java/C++, what access modifier ensures a class member is accessible only within its own class?", ["public", "protected", "private", "default"], "C"),
        "hard": ("In C++ OOP lab, what is the purpose of a Virtual Destructor in a base class?", ["To prevent instantiation of the base class.", "To ensure correct destructor invocation order when deleting a derived object via a base pointer.", "To speed up garbage collection.", "To force compilation errors on derived classes."], "B"),
    },
    "ESK1112": {
        "easy": ("What is active listening?", ["Listening while multitasking on a phone", "Fully focusing, understanding, responding, and remembering what is being said", "Waiting for your turn to interrupt the speaker", "Agreeing with everything the speaker says"], "B"),
        "medium": ("Which communication style is respectful, direct, and honors both personal rights and the rights of others?", ["Passive", "Aggressive", "Assertive", "Passive-Aggressive"], "C"),
        "hard": ("In group dynamics, what is \"Groupthink\"?", ["A brainstorming method that increases creative output", "A psychological phenomenon where the desire for harmony leads to irrational decision-making", "Systematic delegation of software engineering tasks", "Open peer review of project proposals"], "B"),
    },
    "CSE2201": {
        "easy": ("Which algorithm design paradigm does Merge Sort use?", ["Greedy approach", "Divide and Conquer", "Dynamic Programming", "Backtracking"], "B"),
        "medium": ("What is the average-case time complexity of Quick Sort?", ["O(n)", "O( nlog n )", "O( n^2 )", "O( 2^n )"], "B"),
        "hard": ("Dijkstra's algorithm is guaranteed to find the shortest path in a graph provided that:", ["The graph is acyclic.", "All edge weights are non-negative.", "The graph is complete.", "It uses a LIFO stack."], "B"),
    },
    "CSE2202": {
        "easy": ("In algorithm labs, which data structure is used to implement Breadth-First Search (BFS)?", ["Stack", "Queue", "Heap", "Array List"], "B"),
        "medium": ("Which technique is used in lab to optimize recursive Dynamic Programming algorithms by storing previously computed results?", ["Linear Search", "Memoization", "Backtracking", "Bitwise masking"], "B"),
        "hard": ("When finding the Minimum Spanning Tree (MST) using Kruskal's algorithm in C++, which data structure efficiently checks for cycles?", ["Segment Tree", "Disjoint Set Union (DSU) / Union-Find", "Binary Search Tree", "Priority Queue alone"], "B"),
    },
    "CSE2203": {
        "easy": ("Which component of the CPU carries out mathematical and logical computations?", ["Control Unit (CU)", "Arithmetic Logic Unit (ALU)", "Program Counter (PC)", "Cache Memory"], "B"),
        "medium": ("What is the primary function of the Program Counter (PC) register?", ["Holds the current instruction being decoded.", "Holds the memory address of the next instruction to be fetched.", "Stores temporary arithmetic calculation results.", "Counts the total clock ticks since boot."], "B"),
        "hard": ("Which hazard occurs in a pipelined processor when an instruction depends on the result of a previous instruction still in the pipeline?", ["Structural Hazard", "Data Hazard", "Control Hazard", "Branch Hazard"], "B"),
    },
    "STA2101": {
        "easy": ("What is the mean of the numbers 2, 4, 6, 8, 10?", ["5", "6", "7", "30"], "B"),
        "medium": ("If two independent events A and B have probabilities P(A) = 0.5 and P(B) = 0.4, what is P(A ∩ B)?", ["0.9", "0.2", "0.1", "0.8"], "B"),
        "hard": ("What is the total area under the probability density curve of a Normal Distribution?", ["0.5", "1.0", "π", "σ"], "B"),
    },
    "EEE1301": {
        "easy": ("What type of semiconductor material is formed by doping pure silicon with trivalent impurities (like boron)?", ["N-type", "P-type", "Intrinsic", "Insulator"], "B"),
        "medium": ("What is the barrier potential for a standard silicon P-N junction diode at room temperature?", ["0.2V", "0.7V", "1.2V", "5.0V"], "B"),
        "hard": ("In a Bipolar Junction Transistor (BJT) operating in the Active Region, how are the junctions biased?", ["Base-Emitter reverse biased, Base-Collector forward biased", "Base-Emitter forward biased, Base-Collector reverse biased", "Both junctions forward biased", "Both junctions reverse biased"], "B"),
    },
    "EEE1302": {
        "easy": ("Which laboratory component allows current to flow in only one direction?", ["Resistor", "Capacitor", "Diode", "Inductor"], "C"),
        "medium": ("In a full-wave bridge rectifier lab experiment, how many diodes are used in the bridge configuration?", ["1", "2", "4", "6"], "C"),
        "hard": ("Which component is placed in parallel across the output of a rectifier circuit to smooth out voltage ripples?", ["Zener Diode", "Filtering Capacitor", "Variable Resistor", "Series Inductor"], "B"),
    },
    "CSE2200": {
        "easy": ("What is the main objective of Design Project-I?", ["Pass a theoretical paper exam.", "Apply foundational software engineering concepts to build a working project prototype.", "Write purely academic essays.", "Memorize hardware manuals."], "B"),
        "medium": ("Which version control system is most commonly used in software design projects to track code changes?", ["Docker", "Git", "Jenkins", "Kubernetes"], "B"),
        "hard": ("In project software architecture, what does the Model-View-Controller (MVC) pattern separate?", ["Frontend style, backend database, and physical server setup", "Data logic (Model), User Interface (View), and Request Processing (Controller)", "Class structures, functions, and unit testing scripts", "Compilation, linking, and execution steps"], "B"),
    },
    "ESK1113": {
        "easy": ("Which document summarizes a job candidate's education, work experience, and technical skills?", ["Cover Letter", "Resume / CV", "Offer Letter", "Transcript"], "B"),
        "medium": ("What does \"STAR\" stand for in behavioral job interview responses?", ["Situation, Task, Action, Result", "Strategy, Team, Assessment, Review", "Skill, Talent, Ability, Role", "System, Test, Analysis, Report"], "A"),
        "hard": ("What constitutes professional etiquette when communicating via email in a corporate environment?", ["Writing in all capital letters for emphasis", "Using clear, concise subject lines, professional greetings, and structured feedback", "Ignoring reply threads", "Using informal slang and missing signatures"], "B"),
    },
    "CSE2301": {
        "easy": ("Which language is standard for querying and managing relational databases?", ["HTML", "SQL", "Python", "C++"], "B"),
        "medium": ("In a relational database, what is a Primary Key?", ["A field that accepts duplicate values.", "A column or set of columns that uniquely identifies each row in a table.", "A key that points to another table's index.", "A non-unique attribute."], "B"),
        "hard": ("What do the ACID properties stand for in relational transactions?", ["Atomicity, Consistency, Isolation, Durability", "Accuracy, Control, Integration, Data", "Association, Concurrency, Indexing, Dependency", "Allocation, Compilation, Integrity, Distribution"], "A"),
    },
    "CSE2302": {
        "easy": ("Which SQL command is used to retrieve data from a database table?", ["FETCH", "GET", "SELECT", "EXTRACT"], "C"),
        "medium": ("Which SQL clause is used to filter records resulting from a GROUP BY clause?", ["WHERE", "HAVING", "ORDER BY", "LIKE"], "B"),
        "hard": ("What type of JOIN returns all rows from the left table, and matching records from the right table?", ["INNER JOIN", "RIGHT JOIN", "LEFT JOIN", "FULL OUTER JOIN"], "C"),
    },
    "CSE2303": {
        "easy": ("Which formal machine recognizes Regular Languages?", ["Turing Machine", "Pushdown Automata", "Finite Automata (DFA / NFA)", "Linear Bounded Automata"], "C"),
        "medium": ("Which data structure is added to a finite automaton to build a Pushdown Automaton (PDA)?", ["Queue", "Stack", "Linked List", "Hash Table"], "B"),
        "hard": ("According to the Church-Turing thesis, which model represents the ultimate formal capability of algorithmic computation?", ["Deterministic Finite Automaton", "Context-Free Grammar", "Turing Machine", "Non-deterministic Pushdown Automaton"], "C"),
    },
    "CSE2305": {
        "easy": ("What is a process in operating systems terminology?", ["A program stored on disk", "A program currently in execution", "A CPU hardware register", "An I/O device controller"], "B"),
        "medium": ("Which CPU scheduling algorithm gives the lowest average waiting time for a given set of processes?", ["First-Come, First-Served (FCFS)", "Round Robin (RR)", "Shortest Job First (SJF)", "Priority Scheduling"], "C"),
        "hard": ("Which four conditions must hold simultaneously for a Deadlock to occur?", ["Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait", "Synchronization, Paging, Segmentation, Mutual Exclusion", "Context Switch, Starvation, Aging, Thrashing", "Race Condition, Critical Section, Semaphore, Mutex"], "A"),
    },
    "CSE2306": {
        "easy": ("In Linux/Unix operating systems, which shell command creates a new process by cloning the calling process?", ["exec()", "fork()", "clone()", "spawn()"], "B"),
        "medium": ("Which POSIX system call is used to wait for a child process to terminate in C OS lab experiments?", ["exit()", "wait()", "sleep()", "kill()"], "B"),
        "hard": ("What system tool or synchronization construct is used in OS labs to solve the Producer-Consumer problem and avoid race conditions?", ["Pipe", "Semaphore / Mutex", "Shared File", "Global Variable"], "B"),
    },
    "GED2159": {
        "easy": ("What is \"Whistleblowing\" in professional ethics?", ["Promoting product releases on social media", "Reporting illegal, unethical, or unsafe practices within an organization to authorities", "Selling company trade secrets to competitors", "Conducting public relations campaigns"], "B"),
        "medium": ("What does Intellectual Property (IP) protection via Patents grant?", ["Perpetual rights to software source code", "Exclusive rights to an invention for a limited period", "Public domain rights immediately upon publication", "Freedom from taxation"], "B"),
        "hard": ("Under the ACM / IEEE Code of Ethics, what is a computing professional's primary obligation?", ["Maximize shareholder profits at all costs", "Protect public health, safety, and well-being", "Write code using only open-source software", "Minimize development time"], "B"),
    },
    "CSE3101": {
        "easy": ("How many address lines does the classic Intel 8086 microprocessor have?", ["8", "16", "20", "32"], "C"),
        "medium": ("What physical memory space can be directly addressed by a 20-bit address bus (2^20 bytes)?", ["64 KB", "1 MB", "4 MB", "16 MB"], "B"),
        "hard": ("In microprocessor instruction cycles, what is the difference between RISC and CISC architectures?", ["RISC uses complex variable-length instructions; CISC uses simple single-cycle instructions.", "RISC focuses on simple, highly optimized, fixed-length instructions; CISC provides complex multi-cycle instructions.", "RISC lacks registers; CISC relies entirely on registers.", "CISC does not support interrupts."], "B"),
    },
    "CSE3102": {
        "easy": ("Which assembly instruction moves the value 05H into register AL in 8086 assembly?", ["ADD AL, 05H", "MOV AL, 05H", "PUSH AL, 05H", "OUT AL, 05H"], "B"),
        "medium": ("Which pin/port protocol is commonly used on Arduino / microcontroller boards for serial communication?", ["UART (TX/RX)", "VGA", "HDMI", "SATA"], "A"),
        "hard": ("In microcontroller laboratory experiments, what is the purpose of an Interruption Service Routine (ISR)?", ["To shut down the board on power loss.", "A specialized function automatically executed when a hardware/software interrupt occurs.", "A continuous while(1) loop in main code.", "An error handler during code compilation."], "B"),
    },
    "GED_ELEC3": {
        "easy": ("What is the primary methodology applied in Social Sciences to gather empirical population data?", ["Mathematical proofs", "Surveys and field observations", "Software unit testing", "Physics lab simulations"], "B"),
        "medium": ("In economics, what happens when demand for a product increases while supply remains constant?", ["Price tends to decrease.", "Price tends to increase.", "Price drops to zero.", "Supply drops instantly."], "B"),
        "hard": ("What does the term \"Globalization\" describe in social science frameworks?", ["Isolation of national markets", "Growing interdependence of world economies, cultures, and populations", "Shift toward localized agricultural economies", "Standardization of programming languages globally"], "B"),
    },
    "CSE3103": {
        "easy": ("What does SDLC stand for in system design?", ["System Data Logic Control", "Software Development Life Cycle", "Structured Design Language Compiler", "System Diagnostic Life Center"], "B"),
        "medium": ("Which diagram represents the flow of data through an information system?", ["Entity Relationship Diagram (ERD)", "Data Flow Diagram (DFD)", "Use Case Diagram", "Class Diagram"], "B"),
        "hard": ("What is the main difference between Functional and Non-Functional requirements?", ["Functional describes system features/behaviors; Non-functional describes quality attributes (performance, security).", "Functional requirements are optional; Non-functional are mandatory.", "Functional requirements are written by coders; Non-functional by managers.", "There is no distinction in modern systems design."], "A"),
    },
    "GED2243": {
        "easy": ("Which gas is the primary contributor to human-induced global warming?", ["Oxygen", "Carbon Dioxide (CO_2)", "Nitrogen", "Argon"], "B"),
        "medium": ("What is the primary goal of Sustainable Development?", ["Depleting natural resources as quickly as possible for rapid growth", "Meeting present needs without compromising the ability of future generations to meet theirs", "Halting all technological advancement", "Relying exclusively on fossil fuels"], "B"),
        "hard": ("What is E-waste and why is it problematic in environmental science?", ["Excessive carbon emissions from internet browsing", "Discarded electronic equipment containing toxic heavy metals like lead and mercury", "Energy wasted by idle data centers", "Plastic waste floating in oceans"], "B"),
    },
    "CSE3120": {
        "easy": ("Which language provides the fundamental structure and content of web pages?", ["CSS", "HTML", "JavaScript", "PHP"], "B"),
        "medium": ("Which JavaScript method is used to manipulate a DOM element's text content by ID?", ["document.getElementById(\"id\").innerHTML", "window.changeText(\"id\")", "Console.log(\"id\")", "document.fetch(\"id\")"], "A"),
        "hard": ("What is the purpose of the Fetch API or Axios in modern client-side Web Development?", ["To style HTML elements dynamically", "To send asynchronous HTTP requests (AJAX) to a server without reloading the web page", "To compile JavaScript into C++ code", "To design web database schemas"], "B"),
    },
    "CSE3201": {
        "easy": ("Which search algorithm uses a heuristic function h(n) to guide path selection toward a target?", ["Breadth-First Search (BFS)", "Depth-First Search (DFS)", "A^* Search Algorithm", "Uniform Cost Search"], "C"),
        "medium": ("What type of machine learning uses labeled training datasets (inputs paired with correct outputs)?", ["Unsupervised Learning", "Supervised Learning", "Reinforcement Learning", "Self-Organizing Maps"], "B"),
        "hard": ("What condition occurs when a machine learning model learns noise and training data details too well, leading to poor generalization on unseen data?", ["Underfitting", "Overfitting", "Optimization", "Regularization"], "B"),
    },
    "CSE3202": {
        "easy": ("Which Python library is widely used for array processing and numerical operations in AI/ML labs?", ["Matplotlib", "NumPy", "Flask", "BeautifulSoup"], "B"),
        "medium": ("In Scikit-Learn laboratory exercises, which method is used to train a model on training data?", ["model.compile()", "model.fit(X_train, y_train)", "model.run()", "model.predict()"], "B"),
        "hard": ("When evaluating a binary classification model on an imbalanced dataset in lab, why is Precision/Recall or F1-Score preferred over plain Accuracy?", ["Plain accuracy can be misleadingly high by predicting only the majority class.", "Accuracy requires more memory to compute.", "Precision guarantees no false positives exist.", "F1-Score eliminates the need for test data."], "A"),
    },
    "CSE3203": {
        "easy": ("Which software development model follows a strict, sequential linear progression of phases?", ["Agile Model", "Waterfall Model", "Scrum Model", "Extreme Programming"], "B"),
        "medium": ("What type of testing evaluates individual components or functions in isolation?", ["System Testing", "Acceptance Testing", "Unit Testing", "Integration Testing"], "C"),
        "hard": ("In Agile software development methodology, what is a \"Sprint\"?", ["A single day of rapid coding", "A set, short time-box (typically 2--4 weeks) during which specific product increments are completed", "The final deployment phase before project completion", "An emergency bug-fix process"], "B"),
    },
    "CSE3200": {
        "easy": ("What distinguishes Design Project-II from Design Project-I?", ["It requires solving theoretical math equations only.", "It builds upon prior fundamentals to produce a complete, complex, tested software/hardware engineering system.", "It is a written essay course.", "No presentation or demonstration is required."], "B"),
        "medium": ("What is a Minimum Viable Product (MVP)?", ["A complete product with all envisioned features fully designed.", "A product version with just enough core features to be usable by early customers and validated.", "A wireframe mockup on paper.", "The final code refactored for enterprise deployment."], "B"),
        "hard": ("Which testing phase ensures that newly added features in Design Project-II do not break existing working functionality?", ["Smoke Testing", "Regression Testing", "Alpha Testing", "Stress Testing"], "B"),
    },
    "CSE3205": {
        "easy": ("How many layers are in the OSI (Open Systems Interconnection) reference model?", ["4", "5", "7", "9"], "C"),
        "medium": ("Which protocol operates at the Transport Layer of the OSI model to provide reliable, connection-oriented data transfer?", ["UDP", "IP", "TCP", "HTTP"], "C"),
        "hard": ("What is the purpose of the Address Resolution Protocol (ARP)?", ["Map domain names to IP addresses", "Map IP addresses to physical MAC addresses", "Assign dynamic IP addresses automatically", "Route packets across different autonomous networks"], "B"),
    },
    "CSE3206": {
        "easy": ("Which command-line utility is used to test reachability to a host over an IP network?", ["ipconfig", "ping", "netstat", "nslookup"], "B"),
        "medium": ("Which network simulation software tool is commonly used in labs to build visual network topologies and configure routers/switches?", ["Wireshark", "Cisco Packet Tracer", "Visual Studio", "Eclipse"], "B"),
        "hard": ("In packet analyzer tools like Wireshark, what signature indicates a 3-Way TCP Handshake establishing a connection?", ["FIN -> FIN-ACK -> ACK", "SYN -> SYN-ACK -> ACK", "GET -> POST -> 200 OK", "PING -> PONG -> REPLY"], "B"),
    },
    "GED2248": {
        "easy": ("What does SWOT analysis evaluate in strategic management?", ["Software, Web, Operations, Technology", "Strengths, Weaknesses, Opportunities, Threats", "Sales, Work, Organization, Training", "Standards, Workforce, Optimization, Tools"], "B"),
        "medium": ("In inventory management, what does EOQ stand for?", ["Essential Operations Quality", "Economic Order Quantity", "Efficient Output Quotient", "Environmental Order Quota"], "B"),
        "hard": ("In Critical Path Method (CPM) project management, what is defined as the \"Critical Path\"?", ["The shortest sequence of activities in a project network.", "The longest sequence of dependent activities that determines the minimum total project completion time.", "The path with the highest financial budget.", "The path containing non-dependent tasks only."], "B"),
    },
    "CSE_ELEC1": {
        "easy": ("In Cloud Computing electives, what model delivers software applications over the internet on a subscription basis?", ["IaaS (Infrastructure as a Service)", "PaaS (Platform as a Service)", "SaaS (Software as a Service)", "FaaS (Function as a Service)"], "C"),
        "medium": ("In Mobile Application Development, what platform-independent language is used by Flutter for cross-platform app construction?", ["Kotlin", "Swift", "Dart", "Java"], "C"),
        "hard": ("In Computer Graphics, what fundamental transformation scales an object relative to the origin in 2D space?", ["Matrix Addition", "Matrix Multiplication using diagonal scaling factors [[sx, 0], [0, sy]]", "Translation Vector displacement", "Dot product projection"], "B"),
    },
    "CSE3301": {
        "easy": ("What is the term for a malicious attempt to trick individuals into revealing sensitive information like passwords or credit card numbers?", ["Spoofing", "Phishing", "DDoS", "Buffer Overflow"], "B"),
        "medium": ("What type of cryptography uses a public key for encryption and a private key for decryption?", ["Symmetric Encryption", "Asymmetric Encryption / Public-Key Cryptography", "Hashing", "Steganography"], "B"),
        "hard": ("Which attack exploits improper input validation to execute arbitrary SQL commands on a database server?", ["Cross-Site Scripting (XSS)", "SQL Injection (SQLi)", "Man-in-the-Middle (MitM)", "Cross-Site Request Forgery (CSRF)"], "B"),
    },
    "MINOR1": {
        "easy": ("In basic business information systems, what does ERP stand for?", ["Enterprise Resource Planning", "Electronic Record Processing", "External Relationship Performance", "Executive Reporting Portal"], "A"),
        "medium": ("In digital marketing and analytics minor courses, what does CTR measure?", ["Cost To Run", "Click-Through Rate", "Customer Tracking Ratio", "Conversion Total Range"], "B"),
        "hard": ("In organizational behavior studies, what is the core premise of Maslow's Hierarchy of Needs?", ["Lower-level physiological/safety needs must be satisfied before higher-level growth needs motivate behavior.", "Salary is the sole motivator for workplace performance.", "Self-actualization is achieved prior to social needs.", "Human motivation is completely random."], "A"),
    },
    "CSE4098A": {
        "easy": ("What primary activity takes place during the initial Capstone Project 1 phase?", ["Project deployment and customer handover", "Problem domain identification, literature review, and requirement specifications definition", "Writing user manuals", "Final product commercialization"], "B"),
        "medium": ("What document outlines the scope, objectives, feasibility, and architecture of a capstone research/development project?", ["Code Repository README", "Project Proposal / SRS Document", "Expense Report", "Test Suite Log"], "B"),
        "hard": ("Why is a Feasibility Study conducted before proceeding with full capstone implementation?", ["To prove that software will never encounter bugs.", "To evaluate technical, operational, and economic viability of the project before investing significant resources.", "To generate marketing leads.", "To bypass ethics review."], "B"),
    },
    "CSE_ELEC2": {
        "easy": ("In Data Data Science / Big Data electives, what defines the \"3 Vs\" of Big Data?", ["Value, Validity, Verification", "Volume, Velocity, Variety", "Vector, Variable, Virtual", "Visual, Virtual, Versatile"], "B"),
        "medium": ("In Image Processing electives, what filter operation is commonly used to smooth an image and reduce noise?", ["Sobel Edge Detection", "Gaussian Blur", "High-pass filter", "Thresholding"], "B"),
        "hard": ("In elective lab exercises involving Convolutional Neural Networks (CNNs), what is the function of a Pooling Layer (e.g., Max Pooling)?", ["Increase spatial dimensions of feature maps", "Downsample spatial dimensions to reduce parameters and computation while retaining key features", "Calculate loss function gradients", "Flatten output into a string"], "B"),
    },
    "CSE_ELEC2_LAB": {
        "easy": ("In Data Data Science / Big Data electives, what defines the \"3 Vs\" of Big Data?", ["Value, Validity, Verification", "Volume, Velocity, Variety", "Vector, Variable, Virtual", "Visual, Virtual, Versatile"], "B"),
        "medium": ("In Image Processing electives, what filter operation is commonly used to smooth an image and reduce noise?", ["Sobel Edge Detection", "Gaussian Blur", "High-pass filter", "Thresholding"], "B"),
        "hard": ("In elective lab exercises involving Convolutional Neural Networks (CNNs), what is the function of a Pooling Layer (e.g., Max Pooling)?", ["Increase spatial dimensions of feature maps", "Downsample spatial dimensions to reduce parameters and computation while retaining key features", "Calculate loss function gradients", "Flatten output into a string"], "B"),
    },
    "CSE_ELEC3": {
        "easy": ("In Human-Computer Interaction (HCI) electives, what does UI/UX stand for?", ["User Interface / User Experience", "Universal Integration / Universal Execution", "Unified Input / User Extension", "Unit Interaction / Utility Index"], "A"),
        "medium": ("In Distributed Systems electives, what does CAP theorem state?", ["A system can simultaneously guarantee Consistency, Availability, and Partition Tolerance.", "A distributed data store can simultaneously provide at most two out of three guarantees: Consistency, Availability, Partition Tolerance.", "Computation speed doubles every two years.", "Network latency is zero in peer-to-peer networks."], "B"),
        "hard": ("In Compiler Design electives, which phase translates the token stream into an Abstract Syntax Tree (AST)?", ["Lexical Analysis (Scanner)", "Syntax Analysis (Parser)", "Code Optimization", "Target Code Generation"], "B"),
    },
    "MINOR2": {
        "easy": ("In accounting/finance minor courses, what is the fundamental accounting equation?", ["Assets = Liabilities + Owner's Equity", "Revenue = Expenses + Net Income", "Assets = Liabilities - Equity", "Profit = Cash Flow - Debt"], "A"),
        "medium": ("In microeconomics, what elasticity measure checks how quantity demanded responds to price changes?", ["Price Elasticity of Demand", "Income Yield Ratio", "Cross-Marginal Rate", "Inflation Rate"], "A"),
        "hard": ("In business analytics minor modules, what does a Time-Series Forecasting model analyze?", ["Cross-sectional data at a single point in time", "Chronologically ordered data points collected over successive time intervals", "Unordered qualitative survey results", "Random independent samples"], "B"),
    },
    "CSE4098B": {
        "easy": ("What is the focus of Capstone Project 2 stage?", ["Selecting a team project topic", "Core implementation, prototype development, and intermediate progress defense", "Final graduation ceremony preparation", "Basic language syntax training"], "B"),
        "medium": ("What type of diagram is used in Capstone Project 2 to map system database tables and their relationships?", ["Class Diagram", "Entity-Relationship Diagram (ERD)", "State Machine Diagram", "Deployment Diagram"], "B"),
        "hard": ("During mid-capstone evaluation, what does Integration Testing demonstrate?", ["Individual modules work independently in isolation.", "Independently developed system modules interact correctly when combined as an integrated solution.", "Source code formatting complies with coding standards.", "The presentation slides look professional."], "B"),
    },
    "CSE_ELEC4": {
        "easy": ("In Natural Language Processing (NLP) electives, what is \"Tokenization\"?", ["Encrypting text for security", "Breaking text string down into smaller units like words or subwords (tokens)", "Translating text into audio", "Removing HTML tags"], "B"),
        "medium": ("In Internet of Things (IoT) electives, which lightweight messaging protocol is designed for constrained devices and low-bandwidth networks?", ["HTTP/2", "MQTT", "FTP", "SMTP"], "B"),
        "hard": ("In Cryptography / Blockchain electives, what is a Consensus Algorithm (such as Proof of Work or Proof of Stake)?", ["A method to compress data blocks on disk", "A mechanism by which nodes in a distributed network reach agreement on the single data state", "An encryption cipher for passwords", "A peer-to-peer file transfer system"], "B"),
    },
    "MINOR3": {
        "easy": ("In project risk management minor courses, what is Risk Mitigation?", ["Ignoring identified risks", "Developing strategies to reduce the likelihood or impact of potential project risks", "Transferring all work to contractors", "Cancelling the project immediately"], "B"),
        "medium": ("In consumer behavior studies, what is cognitive dissonance?", ["High brand loyalty after purchase", "Psychological discomfort felt when holding contradictory beliefs or post-purchase regret", "Instant decision-making at checkout", "Effective visual advertising response"], "B"),
        "hard": ("In modern operations management, what is the core philosophy of \"Lean Thinking\"?", ["Maximizing inventory buffer sizes", "Eliminating waste and non-value-adding activities to maximize customer value", "Increasing workforce size", "Automating without process optimization"], "B"),
    },
    "CSE4098C": {
        "easy": ("What is the primary deliverable for Capstone Project 3?", ["An initial preliminary topic slide deck", "Fully functional verified software/hardware system, complete final report (thesis/book), and comprehensive defense presentation", "A simple code snippet", "Literature review summary"], "B"),
        "medium": ("What type of testing evaluates whether the complete system meets all original business and user requirements before defense?", ["Acceptance / System Testing", "Unit Testing", "Syntax Validation", "Compiler Verification"], "A"),
        "hard": ("When publishing or archiving capstone results, what does reproducible research/project execution require?", ["Pre-compiled binary executables only", "Well-documented code, environment specifications, clear setup instructions, and evaluation datasets", "Proprietary closed source code", "High resolution video demonstrations only"], "B"),
    },
    "CSE4099": {
        "easy": ("What is the main goal of an industry Internship track in CSE?", ["Attending daily lectures on campus", "Gaining real-world industry experience, applying engineering knowledge, and understanding corporate workflows", "Writing competitive programming problems", "Retracing textbook solutions"], "B"),
        "medium": ("In a Thesis track, what section provides a critical evaluation of existing academic publications relevant to the research topic?", ["Methodology", "Literature Review", "Conclusion", "Acknowledgments"], "B"),
        "hard": ("What defines academic integrity when writing a thesis report or internship technical documentation?", ["Paraphrasing technical books without citation", "Proper citation of all external sources, originality of work, and honest reporting of experimental data", "Copying source code directly from open repositories", "Submitting work completed by peers"], "B"),
    },
}

def build_course_catalog() -> List[Course]:
    """
    Construct and return the full master catalog as a list of
    persistent Course objects, in curriculum order — fully loaded
    with prerequisites, categories, AND the 3-tier MCQ exam ladder.

    Called ONCE at game startup (GameSession initialisation).
    The same Course instances returned here are the ones that
    live on forever — RegistrationManager filters this list,
    AcademicHistory tracks these exact objects' codes, and
    Semester holds references into this same list. No Course
    is ever re-instantiated for a backlog/retake.
    """
    catalog: List[Course] = []
    for code, name, credits, prereqs, is_lab, category in _CATALOG_DATA:
        course = Course(
            course_code=code,
            course_name=name,
            credit_value=credits,
            prerequisites=prereqs,
            is_lab_component=is_lab,
            category=category,
        )
        _load_questions_for_course(course)
        catalog.append(course)
    return catalog


def _load_questions_for_course(course: Course) -> None:
    """
    Look up this course's code in _QUESTION_DATA and register all
    3 MCQ tiers on it via Course.add_question(). Silently does
    nothing if the course code has no entry (shouldn't happen —
    every catalog course has a matching question set).
    """
    tiers = _QUESTION_DATA.get(course.get_course_code())
    if not tiers:
        return
    for tier, (question_text, options, correct_option) in tiers.items():
        course.add_question(tier, question_text, options, correct_option)


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
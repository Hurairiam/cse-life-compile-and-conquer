"""
content/side_quest_lectures.py
CSE Life: Compile & Conquer
Phase 11.5 — side quest lecture sheets

The twelve self-study topics, as sheets the game can already draw.
Converted from `side_quest_lectures.html`, which the engine cannot
render at all. One paragraph became one sheet (Decision D2b), so each
topic has three, in the reading order of the source document.

Pure data, per the `content/` convention: no pygame, no engine imports,
no `academic/` imports. The shape follows content/lectures.py — a
module-level dict keyed by a stable id, with get_*() accessors that
never raise and never return None.

    SIDE_QUEST_SHEETS   sheet id -> {skill_id, title, text, lines}
    SHEET_IDS           skill id -> its sheet ids, in reading order

`text` is the paragraph exactly as it was written: nothing reworded,
summarised, reordered or cut.

`lines` is that same string split for the card, one line per SPACE, the
way content/lectures.py already feeds engine/states/lecture.py.
ui/dialog_box.py wraps a line to MAX_LINES = 3 rows and **drops
whatever is left** (`return lines[:MAX_LINES]`), which is about 220
characters at 1280px — a 308–557 character paragraph handed over whole
would lose roughly half of itself on screen, silently. Splitting is not
editing: the cuts land on spaces at clause boundaries, and validate()
asserts `" ".join(lines) == text` on all 36 sheets, so a single
character of drift raises instead of shipping.

Sheet ids are `<skill id>_S<n>`, numbered from 1 — stable, readable,
and unique by construction. Phase 12 validates its `lecture_sheets`
column against SHEET_IDS.
"""
from __future__ import annotations

# The twelve topics, in the source document's order. Spelled out rather
# than imported because content/ may not import academic/ — these are
# the same ids academic/side_quest_catalog.py stores as `quest_id`, and
# the same section ids the source HTML used. validate() fails if the
# table below stops covering exactly these.
SKILL_IDS: tuple = (
    "SQ_PROGRAMMING_LANGUAGE",
    "SQ_DSA",
    "SQ_GIT_GITHUB",
    "SQ_LINUX_CLI",
    "SQ_DATABASES_SQL",
    "SQ_NETWORKING",
    "SQ_WEB_APP_DEV",
    "SQ_DOCKER",
    "SQ_AI_TOOLS",
    "SQ_DEBUGGING_TESTING",
    "SQ_OOP",
    "SQ_TECH_COMMUNICATION",
)


SIDE_QUEST_SHEETS: dict[str, dict] = {
    # Core Programming Language ─────────────────────────────
    "SQ_PROGRAMMING_LANGUAGE_S1": {
        "skill_id": "SQ_PROGRAMMING_LANGUAGE",
        "title": "Core Programming Language",
        "text": "A programming language is how you translate an idea into instructions a computer can actually run. Every language — Python, Java, C++, whichever you pick — gives you the same basic toolkit underneath different syntax: variables to hold data, control flow (if statements, loops) to make decisions and repeat actions, and functions to organize logic into reusable pieces. Learning \"a language\" really means learning to think in these terms first, and the specific keywords second.",
        "lines": [
            "A programming language is how you translate an idea into instructions a computer can actually run.",
            "Every language — Python, Java, C++, whichever you pick — gives you the same basic toolkit underneath different syntax:",
            "variables to hold data, control flow (if statements, loops) to make decisions and repeat actions,",
            "and functions to organize logic into reusable pieces.",
            "Learning \"a language\" really means learning to think in these terms first, and the specific keywords second.",
        ],
    },
    "SQ_PROGRAMMING_LANGUAGE_S2": {
        "skill_id": "SQ_PROGRAMMING_LANGUAGE",
        "title": "Core Programming Language",
        "text": "Different languages make different trade-offs. Python favors readability and speed of writing code, which is why it's common for beginners, scripting, and data-heavy work. Java and C++ push you closer to how the computer actually manages memory and types, which builds habits that transfer well to performance-sensitive or large-scale systems. Neither approach is \"better\" in isolation — the right choice depends on what you're building and what kind of problems you expect to run into.",
        "lines": [
            "Different languages make different trade-offs. Python favors readability and speed of writing code,",
            "which is why it's common for beginners, scripting, and data-heavy work. Java and C++ push you closer to how the computer actually",
            "manages memory and types, which builds habits that transfer well to performance-sensitive or large-scale systems.",
            "Neither approach is \"better\" in isolation — the right choice depends on",
            "what you're building and what kind of problems you expect to run into.",
        ],
    },
    "SQ_PROGRAMMING_LANGUAGE_S3": {
        "skill_id": "SQ_PROGRAMMING_LANGUAGE",
        "title": "Core Programming Language",
        "text": "What matters most early on isn't memorizing syntax, it's building a mental model of how code actually executes: line by line, top to bottom, with decisions branching the path along the way, and functions pausing execution to run elsewhere before returning. Once that clicks, picking up a second or third language later becomes far easier — the vocabulary changes, but the underlying logic mostly doesn't.",
        "lines": [
            "What matters most early on isn't memorizing syntax, it's building a mental model of how code actually executes:",
            "line by line, top to bottom, with decisions branching the path along the way,",
            "and functions pausing execution to run elsewhere before returning. Once that clicks,",
            "picking up a second or third language later becomes far easier — the vocabulary changes, but the underlying logic mostly doesn't.",
        ],
    },
    # Data Structures & Algorithms ──────────────────────────
    "SQ_DSA_S1": {
        "skill_id": "SQ_DSA",
        "title": "Data Structures & Algorithms",
        "text": "Data structures are ways of organizing information so it's fast and easy to work with. An array keeps items in order and lets you jump to any position instantly. A tree organizes information hierarchically, like a file system or an org chart. A graph represents connections between things — cities linked by roads, people linked by friendships — where the relationships matter as much as the items themselves.",
        "lines": [
            "Data structures are ways of organizing information so it's fast and easy to work with.",
            "An array keeps items in order and lets you jump to any position instantly.",
            "A tree organizes information hierarchically, like a file system or an org chart.",
            "A graph represents connections between things — cities linked by roads,",
            "people linked by friendships — where the relationships matter as much as the items themselves.",
        ],
    },
    "SQ_DSA_S2": {
        "skill_id": "SQ_DSA",
        "title": "Data Structures & Algorithms",
        "text": "Algorithms are the step-by-step processes that operate on that data: searching for a value, sorting a list, or finding the shortest path between two points in a graph. The same task can often be solved multiple ways, and part of learning this topic is developing a sense for which approach fits which structure — searching a sorted array, for instance, can be done far faster than searching an unsorted one, simply because of how the data is arranged.",
        "lines": [
            "Algorithms are the step-by-step processes that operate on that data: searching for a value, sorting a list,",
            "or finding the shortest path between two points in a graph. The same task can often be solved multiple ways,",
            "and part of learning this topic is developing a sense for which approach fits which structure — searching a sorted array,",
            "for instance, can be done far faster than searching an unsorted one, simply because of how the data is arranged.",
        ],
    },
    "SQ_DSA_S3": {
        "skill_id": "SQ_DSA",
        "title": "Data Structures & Algorithms",
        "text": "The reason this pairing gets so much attention is efficiency: the same problem can be solved in a way that takes seconds or a way that takes hours, depending purely on which structure and algorithm you choose, especially as the amount of data grows. It's also the backbone of most technical coding interviews, since it tests how you reason about a problem — breaking it down, spotting the right structure, estimating how well a solution will scale — rather than just whether you can write working syntax.",
        "lines": [
            "The reason this pairing gets so much attention is efficiency: the same problem can be solved in a way that takes seconds or a",
            "way that takes hours, depending purely on which structure and algorithm you choose, especially as the amount of data grows.",
            "It's also the backbone of most technical coding interviews, since it tests how you reason about a problem — breaking it down,",
            "spotting the right structure, estimating how well a solution will scale — rather than just whether you can write working syntax.",
        ],
    },
    # Git & GitHub ──────────────────────────────────────────
    "SQ_GIT_GITHUB_S1": {
        "skill_id": "SQ_GIT_GITHUB",
        "title": "Git & GitHub",
        "text": "Git is a version control system — it keeps a history of every change made to a codebase, so you can move backward, compare versions, or work on something experimental without risking the working version. Think of it as a very detailed save system for code, where every \"commit\" is a checkpoint with a message describing what changed and why, building up a full timeline of a project's development.",
        "lines": [
            "Git is a version control system — it keeps a history of every change made to a codebase, so you can move backward, compare versions,",
            "or work on something experimental without risking the working version. Think of it as a very detailed save system for code,",
            "where every \"commit\" is a checkpoint with a message describing what changed and why,",
            "building up a full timeline of a project's development.",
        ],
    },
    "SQ_GIT_GITHUB_S2": {
        "skill_id": "SQ_GIT_GITHUB",
        "title": "Git & GitHub",
        "text": "The real power shows up with branching: you can create a separate line of work off the main codebase to try something new, fix a bug, or build a feature, without touching the stable version at all. Once that work is ready, it gets merged back in. This is what makes it possible to experiment freely and to have multiple people working on completely different parts of the same project at the same time without constantly overwriting each other.",
        "lines": [
            "The real power shows up with branching: you can create a separate line of work off the main codebase to try something new,",
            "fix a bug, or build a feature, without touching the stable version at all. Once that work is ready, it gets merged back in.",
            "This is what makes it possible to experiment freely and to have multiple people working on completely",
            "different parts of the same project at the same time without constantly overwriting each other.",
        ],
    },
    "SQ_GIT_GITHUB_S3": {
        "skill_id": "SQ_GIT_GITHUB",
        "title": "Git & GitHub",
        "text": "GitHub takes that local history and puts it online, which is what turns version control into real collaboration. It adds pull requests (a formal way to propose merging one branch into another, usually with review from teammates first), issue tracking, and a shared remote copy of the project everyone can pull from and push to. Even solo developers use it constantly, just for the safety net of a full, backed-up change history — but it becomes essential the moment more than one person touches the same code.",
        "lines": [
            "GitHub takes that local history and puts it online, which is what turns version control into real collaboration.",
            "It adds pull requests (a formal way to propose merging one branch into another, usually with review from teammates first),",
            "issue tracking, and a shared remote copy of the project everyone can pull from and push to.",
            "Even solo developers use it constantly, just for the safety net of a full,",
            "backed-up change history — but it becomes essential the moment more than one person touches the same code.",
        ],
    },
    # Linux & Command Line ──────────────────────────────────
    "SQ_LINUX_CLI_S1": {
        "skill_id": "SQ_LINUX_CLI",
        "title": "Linux & Command Line",
        "text": "The command line is a text-based way of controlling a computer — instead of clicking through folders and menus, you type instructions directly and the system executes them. It feels slower and less intuitive at first, but it's often faster and more precise once it's familiar, especially for repetitive tasks, since a sequence of commands can be saved and rerun instantly instead of manually repeating clicks.",
        "lines": [
            "The command line is a text-based way of controlling a computer — instead of clicking through folders and menus,",
            "you type instructions directly and the system executes them. It feels slower and less intuitive at first,",
            "but it's often faster and more precise once it's familiar, especially for repetitive tasks,",
            "since a sequence of commands can be saved and rerun instantly instead of manually repeating clicks.",
        ],
    },
    "SQ_LINUX_CLI_S2": {
        "skill_id": "SQ_LINUX_CLI",
        "title": "Linux & Command Line",
        "text": "Core skills here include navigating the file system (moving between directories, listing files, understanding paths), managing files and permissions, and chaining commands together so the output of one becomes the input of the next. That last habit — piping simple tools together to build something more powerful — is one of the most distinctive ways of working on the command line, and it scales up to genuinely complex automation once it clicks.",
        "lines": [
            "Core skills here include navigating the file system (moving between directories, listing files, understanding paths),",
            "managing files and permissions, and chaining commands together so the output of one becomes the input of the next.",
            "That last habit — piping simple tools together to build something more powerful —",
            "is one of the most distinctive ways of working on the command line, and it scales up to genuinely complex automation once it clicks.",
        ],
    },
    "SQ_LINUX_CLI_S3": {
        "skill_id": "SQ_LINUX_CLI",
        "title": "Linux & Command Line",
        "text": "Linux is the operating system most commonly paired with this way of working, especially in professional and server environments — most of the internet runs on Linux servers, and most developer tooling assumes at least basic comfort with a terminal. Learning your way around it is less about mastering one specific skill and more about becoming comfortable with the environment nearly every other technical tool, from Git to Docker to deployment pipelines, eventually expects you to already know.",
        "lines": [
            "Linux is the operating system most commonly paired with this way of working, especially in professional and server environments —",
            "most of the internet runs on Linux servers, and most developer tooling assumes at least basic comfort with a terminal.",
            "Learning your way around it is less about mastering one specific skill and more about becoming comfortable with the environment",
            "nearly every other technical tool, from Git to Docker to deployment pipelines, eventually expects you to already know.",
        ],
    },
    # Databases & SQL ───────────────────────────────────────
    "SQ_DATABASES_SQL_S1": {
        "skill_id": "SQ_DATABASES_SQL",
        "title": "Databases & SQL",
        "text": "Almost every real application needs somewhere to permanently store information — user accounts, orders, messages, anything that has to survive after the program stops running or the server restarts. A database is that storage system, organized so information can be added, updated, and retrieved reliably, even as it grows to millions of records and gets accessed by many users at once.",
        "lines": [
            "Almost every real application needs somewhere to permanently store information — user accounts, orders, messages,",
            "anything that has to survive after the program stops running or the server restarts.",
            "A database is that storage system, organized so information can be added, updated,",
            "and retrieved reliably, even as it grows to millions of records and gets accessed by many users at once.",
        ],
    },
    "SQ_DATABASES_SQL_S2": {
        "skill_id": "SQ_DATABASES_SQL",
        "title": "Databases & SQL",
        "text": "The relational model is the most common approach: data is organized into tables, where each row is one record and each column is one attribute of that record — a \"users\" table might have columns for name, email, and signup date, for example. Tables can also be linked to each other through relationships, so an \"orders\" table can reference which user placed each order without duplicating all their information every time.",
        "lines": [
            "The relational model is the most common approach: data is organized into tables,",
            "where each row is one record and each column is one attribute of that record — a \"users\" table might have columns for name,",
            "email, and signup date, for example. Tables can also be linked to each other through relationships,",
            "so an \"orders\" table can reference which user placed each order without duplicating all their information every time.",
        ],
    },
    "SQ_DATABASES_SQL_S3": {
        "skill_id": "SQ_DATABASES_SQL",
        "title": "Databases & SQL",
        "text": "SQL is the language used to talk to most of these databases — it lets you ask precise questions like \"find every order placed this month\" or \"update this user's email,\" using structured, readable syntax built around a small set of core operations: creating, reading, updating, and deleting data. Understanding how data should be organized into tables and relationships in the first place is just as important as knowing the language itself, since a poorly structured database causes problems no query can fully fix later.",
        "lines": [
            "SQL is the language used to talk to most of these databases — it lets you ask precise questions like \"find every order placed this",
            "month\" or \"update this user's email,\" using structured, readable syntax built around a small set of core operations:",
            "creating, reading, updating, and deleting data. Understanding how data should be organized",
            "into tables and relationships in the first place is just as important as knowing the language itself,",
            "since a poorly structured database causes problems no query can fully fix later.",
        ],
    },
    # Computer Networking ───────────────────────────────────
    "SQ_NETWORKING_S1": {
        "skill_id": "SQ_NETWORKING",
        "title": "Computer Networking",
        "text": "Networking is the study of how computers talk to each other — how a request from your browser finds its way to a server on the other side of the world and gets a response back in a fraction of a second. Every device on a network has an IP address, a kind of numeric location that other devices use to find it, and DNS is the system that translates readable names, like a website's URL, into that underlying address.",
        "lines": [
            "Networking is the study of how computers talk to each other — how a request from your browser finds its",
            "way to a server on the other side of the world and gets a response back in a fraction of a second.",
            "Every device on a network has an IP address, a kind of numeric location that other devices use to find it,",
            "and DNS is the system that translates readable names, like a website's URL, into that underlying address.",
        ],
    },
    "SQ_NETWORKING_S2": {
        "skill_id": "SQ_NETWORKING",
        "title": "Computer Networking",
        "text": "HTTP is the protocol that governs most communication for the web specifically — it defines the format of a request (what's being asked for) and a response (what's being sent back), along with details like status codes that indicate whether something succeeded, failed, or needs redirecting. This same request-and-response pattern underlies nearly everything that happens when you load a page or use an app that talks to a server.",
        "lines": [
            "HTTP is the protocol that governs most communication for the web specifically —",
            "it defines the format of a request (what's being asked for) and a response (what's being sent back),",
            "along with details like status codes that indicate whether something succeeded, failed, or needs redirecting.",
            "This same request-and-response pattern underlies nearly everything that",
            "happens when you load a page or use an app that talks to a server.",
        ],
    },
    "SQ_NETWORKING_S3": {
        "skill_id": "SQ_NETWORKING",
        "title": "Computer Networking",
        "text": "REST APIs are a common pattern built on top of HTTP, giving applications a predictable, structured way to request and exchange data — for example, asking a server for a list of items, or sending it new data to save. None of this needs to be mastered deeply to build things, but a working sense of how requests travel and where they can fail makes debugging \"why isn't this working\" dramatically easier, since a huge share of real-world bugs live somewhere in this layer.",
        "lines": [
            "REST APIs are a common pattern built on top of HTTP, giving applications a predictable,",
            "structured way to request and exchange data — for example, asking a server for a list of items, or sending it new data to save.",
            "None of this needs to be mastered deeply to build things, but a working sense of how requests travel and where they can fail",
            "makes debugging \"why isn't this working\" dramatically easier, since a huge share of real-world bugs live somewhere in this layer.",
        ],
    },
    # Web & App Development ─────────────────────────────────
    "SQ_WEB_APP_DEV_S1": {
        "skill_id": "SQ_WEB_APP_DEV",
        "title": "Web & App Development",
        "text": "Most applications are split into two halves that work together: the frontend, which is what a user actually sees and interacts with — buttons, forms, layouts — and the backend, which handles logic, storage, and everything happening behind the scenes, usually running on a server the user never directly sees.",
        "lines": [
            "Most applications are split into two halves that work together: the frontend,",
            "which is what a user actually sees and interacts with — buttons, forms, layouts — and the backend, which handles logic,",
            "storage, and everything happening behind the scenes, usually running on a server the user never directly sees.",
        ],
    },
    "SQ_WEB_APP_DEV_S2": {
        "skill_id": "SQ_WEB_APP_DEV",
        "title": "Web & App Development",
        "text": "Building something full-stack means understanding how those two halves communicate. When a user clicks a button, the frontend sends a request to the backend; the backend processes it, maybe checking or updating a database, and sends a response back; the frontend then updates what the user sees based on that response. This round trip, repeated constantly in different forms, is the foundation almost every app is built on, whether it's a simple to-do list or a large-scale platform.",
        "lines": [
            "Building something full-stack means understanding how those two halves communicate.",
            "When a user clicks a button, the frontend sends a request to the backend; the backend processes it,",
            "maybe checking or updating a database, and sends a response back; the frontend then updates what the user sees based on that response.",
            "This round trip, repeated constantly in different forms, is the foundation almost every app is built on,",
            "whether it's a simple to-do list or a large-scale platform.",
        ],
    },
    "SQ_WEB_APP_DEV_S3": {
        "skill_id": "SQ_WEB_APP_DEV",
        "title": "Web & App Development",
        "text": "Working through one complete project end to end is one of the fastest ways to understand this, because it forces every piece to connect: a button has to trigger a request, the server has to handle it correctly, the data has to be stored or retrieved properly, and the result has to make it back to the screen in a form the user can actually use. It's less about mastering any single framework or tool and more about understanding — and being able to trace — that full round trip when something breaks.",
        "lines": [
            "Working through one complete project end to end is one of the fastest ways to understand this,",
            "because it forces every piece to connect: a button has to trigger a request, the server has to handle it correctly,",
            "the data has to be stored or retrieved properly, and the result has to make it back to the screen in a form the user can actually use.",
            "It's less about mastering any single framework or tool and more about understanding —",
            "and being able to trace — that full round trip when something breaks.",
        ],
    },
    # Docker Basics ─────────────────────────────────────────
    "SQ_DOCKER_S1": {
        "skill_id": "SQ_DOCKER",
        "title": "Docker Basics",
        "text": "One of the most common headaches in software is \"it works on my machine\" — an app runs fine for one developer but breaks somewhere else because of differences in operating system, installed versions, or configuration that nobody fully tracked. Docker exists to solve exactly this problem, by packaging an application together with everything it needs to run — code, dependencies, settings — into a self-contained unit called a container.",
        "lines": [
            "One of the most common headaches in software is \"it works on my machine\" —",
            "an app runs fine for one developer but breaks somewhere else because of differences in operating system, installed versions,",
            "or configuration that nobody fully tracked. Docker exists to solve exactly this problem,",
            "by packaging an application together with everything it needs to run — code,",
            "dependencies, settings — into a self-contained unit called a container.",
        ],
    },
    "SQ_DOCKER_S2": {
        "skill_id": "SQ_DOCKER",
        "title": "Docker Basics",
        "text": "Because that container includes its own environment, it behaves the same way regardless of what computer or server it's running on, whether that's a teammate's laptop, a testing server, or a production environment used by real users. Containers are also lightweight compared to full virtual machines, since they share the underlying operating system instead of duplicating it, which makes them fast to start and cheap to run many of at once.",
        "lines": [
            "Because that container includes its own environment, it behaves the same way regardless of what computer or server it's running on,",
            "whether that's a teammate's laptop, a testing server, or a production environment used by real users.",
            "Containers are also lightweight compared to full virtual machines, since they share the underlying operating",
            "system instead of duplicating it, which makes them fast to start and cheap to run many of at once.",
        ],
    },
    "SQ_DOCKER_S3": {
        "skill_id": "SQ_DOCKER",
        "title": "Docker Basics",
        "text": "This makes Docker especially useful for deployment and teamwork, since it removes a huge category of \"works here, not there\" bugs before they ever reach a user, and it's become close to a standard expectation in most professional development workflows — many teams assume some baseline familiarity with it the same way they assume familiarity with Git.",
        "lines": [
            "This makes Docker especially useful for deployment and teamwork, since it removes a huge category of \"works here,",
            "not there\" bugs before they ever reach a user, and it's become close to a standard expectation in most professional",
            "development workflows — many teams assume some baseline familiarity with it the same way they assume familiarity with Git.",
        ],
    },
    # Modern AI Tools ───────────────────────────────────────
    "SQ_AI_TOOLS_S1": {
        "skill_id": "SQ_AI_TOOLS",
        "title": "Modern AI Tools",
        "text": "AI tools have shifted from a specialized niche to something woven into everyday development — from AI-assisted code completion that suggests entire functions as you type, to APIs that let an application call a language model directly for tasks like summarizing text, answering questions, or generating content on the fly, without building that intelligence from scratch.",
        "lines": [
            "AI tools have shifted from a specialized niche to something woven into everyday development —",
            "from AI-assisted code completion that suggests entire functions as you type,",
            "to APIs that let an application call a language model directly for tasks like summarizing text,",
            "answering questions, or generating content on the fly, without building that intelligence from scratch.",
        ],
    },
    "SQ_AI_TOOLS_S2": {
        "skill_id": "SQ_AI_TOOLS",
        "title": "Modern AI Tools",
        "text": "Getting comfortable here means two overlapping skills. The first is using AI-powered developer tools to work faster — treating them as a capable assistant that speeds up boilerplate and exploration, while still reviewing and understanding what they produce rather than accepting it blindly. The second is knowing how to integrate an AI API into your own projects, which usually comes down to sending a request with the right input, often a piece of text or a structured prompt, and handling the response the same way you'd handle any other external service.",
        "lines": [
            "Getting comfortable here means two overlapping skills. The first is using AI-powered developer tools to work faster —",
            "treating them as a capable assistant that speeds up boilerplate and exploration,",
            "while still reviewing and understanding what they produce rather than accepting it blindly.",
            "The second is knowing how to integrate an AI API into your own projects, which usually comes down to sending a request with the right",
            "input, often a piece of text or a structured prompt, and handling the response the same way you'd handle any other external service.",
        ],
    },
    "SQ_AI_TOOLS_S3": {
        "skill_id": "SQ_AI_TOOLS",
        "title": "Modern AI Tools",
        "text": "It's a fast-moving space — specific tools and models change constantly — so the goal isn't to memorize any one product but to understand the general pattern well enough to pick up whatever's current: what these tools are good at, where they tend to be unreliable, and how to plug one into a workflow without depending on it blindly.",
        "lines": [
            "It's a fast-moving space — specific tools and models change constantly —",
            "so the goal isn't to memorize any one product but to understand the general pattern well enough to pick up whatever's current:",
            "what these tools are good at, where they tend to be unreliable, and how to plug one into a workflow without depending on it blindly.",
        ],
    },
    # Debugging & Testing ───────────────────────────────────
    "SQ_DEBUGGING_TESTING_S1": {
        "skill_id": "SQ_DEBUGGING_TESTING",
        "title": "Debugging & Testing",
        "text": "Bugs are inevitable — the real skill isn't avoiding them entirely, it's finding them efficiently. Debugging is the systematic process of narrowing down where something went wrong, usually by reading error messages carefully rather than skimming past them, checking assumptions about what the code should be doing at each step, and isolating the smallest piece of code that reproduces the problem so it's easier to reason about.",
        "lines": [
            "Bugs are inevitable — the real skill isn't avoiding them entirely, it's finding them efficiently.",
            "Debugging is the systematic process of narrowing down where something went wrong,",
            "usually by reading error messages carefully rather than skimming past them, checking assumptions about what the code should",
            "be doing at each step, and isolating the smallest piece of code that reproduces the problem so it's easier to reason about.",
        ],
    },
    "SQ_DEBUGGING_TESTING_S2": {
        "skill_id": "SQ_DEBUGGING_TESTING",
        "title": "Debugging & Testing",
        "text": "Good debugging habits include using tools like breakpoints and step-through debuggers to watch code execute in slow motion, printing intermediate values to check whether they match expectations, and resisting the urge to guess-and-check randomly — a methodical approach almost always finds the issue faster than trial and error, even when it feels slower at first.",
        "lines": [
            "Good debugging habits include using tools like breakpoints and step-through debuggers to watch code execute in slow motion,",
            "printing intermediate values to check whether they match expectations, and resisting the urge to guess-and-check randomly —",
            "a methodical approach almost always finds the issue faster than trial and error, even when it feels slower at first.",
        ],
    },
    "SQ_DEBUGGING_TESTING_S3": {
        "skill_id": "SQ_DEBUGGING_TESTING",
        "title": "Debugging & Testing",
        "text": "Testing flips that process around: instead of reacting to bugs after they happen, you write small checks — unit tests — that automatically verify a piece of code behaves the way it's supposed to, given specific inputs. These catch problems early, often before code is even shipped, and just as importantly, they prevent old bugs from quietly resurfacing later when other parts of the code change. Together, debugging and testing are what separate code that mostly works from code you can actually trust.",
        "lines": [
            "Testing flips that process around: instead of reacting to bugs after they happen,",
            "you write small checks — unit tests — that automatically verify a piece of code behaves the way it's supposed to,",
            "given specific inputs. These catch problems early, often before code is even shipped, and just as importantly,",
            "they prevent old bugs from quietly resurfacing later when other parts of the code change.",
            "Together, debugging and testing are what separate code that mostly works from code you can actually trust.",
        ],
    },
    # Object-Oriented Programming (OOP) ─────────────────────
    "SQ_OOP_S1": {
        "skill_id": "SQ_OOP",
        "title": "Object-Oriented Programming (OOP)",
        "text": "Object-oriented programming is a way of structuring code around \"objects\" — bundles of data and the behavior that acts on that data, modeled using a class as their blueprint. A \"Car\" class, for example, might bundle data like speed and fuel level together with behavior like accelerate() or refuel(), and each individual car in the program is a separate object built from that same blueprint.",
        "lines": [
            "Object-oriented programming is a way of structuring code around \"objects\" — bundles of data and the behavior that acts on that data,",
            "modeled using a class as their blueprint. A \"Car\" class, for example, might bundle data like speed and fuel level together with",
            "behavior like accelerate() or refuel(), and each individual car in the program is a separate object built from that same blueprint.",
        ],
    },
    "SQ_OOP_S2": {
        "skill_id": "SQ_OOP",
        "title": "Object-Oriented Programming (OOP)",
        "text": "A few core ideas build on top of this. Encapsulation means keeping an object's internal details protected, exposing only what other parts of the program actually need to interact with. Inheritance lets one class build on another, reusing and extending existing behavior instead of rewriting it — a \"SportsCar\" class could inherit everything from \"Car\" and just add or override a few details. Polymorphism allows different objects to respond to the same instruction in their own way, which keeps code flexible as a program grows.",
        "lines": [
            "A few core ideas build on top of this. Encapsulation means keeping an object's internal details protected,",
            "exposing only what other parts of the program actually need to interact with.",
            "Inheritance lets one class build on another, reusing and extending existing behavior instead of rewriting it —",
            "a \"SportsCar\" class could inherit everything from \"Car\" and just add or override a few details.",
            "Polymorphism allows different objects to respond to the same instruction in their own way,",
            "which keeps code flexible as a program grows.",
        ],
    },
    "SQ_OOP_S3": {
        "skill_id": "SQ_OOP",
        "title": "Object-Oriented Programming (OOP)",
        "text": "This matters most as projects grow larger: organizing code this way makes it easier to reuse, extend, and reason about, since each object is responsible for its own piece of the logic instead of everything living in one long, tangled script. The core habit worth internalizing first, before any of the more advanced terminology, is simply thinking in terms of \"what is this thing, and what can it do.\"",
        "lines": [
            "This matters most as projects grow larger: organizing code this way makes it easier to reuse, extend, and reason about,",
            "since each object is responsible for its own piece of the logic instead of everything living in one long, tangled script.",
            "The core habit worth internalizing first, before any of the more advanced terminology,",
            "is simply thinking in terms of \"what is this thing, and what can it do.\"",
        ],
    },
    # Technical Communication ───────────────────────────────
    "SQ_TECH_COMMUNICATION_S1": {
        "skill_id": "SQ_TECH_COMMUNICATION",
        "title": "Technical Communication",
        "text": "Writing code that works is only half the job — being able to explain it is the other half. Technical communication covers things like writing clear documentation, leaving useful comments that explain the \"why\" rather than just restating the \"what,\" and describing a problem or solution in a way someone else, or future you months later, can actually follow without having to reverse-engineer every decision.",
        "lines": [
            "Writing code that works is only half the job — being able to explain it is the other half.",
            "Technical communication covers things like writing clear documentation,",
            "leaving useful comments that explain the \"why\" rather than just restating the \"what,\" and describing a problem or solution",
            "in a way someone else, or future you months later, can actually follow without having to reverse-engineer every decision.",
        ],
    },
    "SQ_TECH_COMMUNICATION_S2": {
        "skill_id": "SQ_TECH_COMMUNICATION",
        "title": "Technical Communication",
        "text": "Code reviews are a big part of this in practice: giving and receiving feedback on someone else's code requires being specific and constructive rather than vague — pointing to exact lines, explaining the reasoning behind a suggestion, and separating \"this is wrong\" from \"this is a style preference.\" Being on the receiving end of that feedback well, without getting defensive, is just as much a communication skill as giving it.",
        "lines": [
            "Code reviews are a big part of this in practice: giving and receiving feedback on someone else's code requires",
            "being specific and constructive rather than vague — pointing to exact lines, explaining the reasoning behind a suggestion,",
            "and separating \"this is wrong\" from \"this is a style preference.\"",
            "Being on the receiving end of that feedback well, without getting defensive, is just as much a communication skill as giving it.",
        ],
    },
    "SQ_TECH_COMMUNICATION_S3": {
        "skill_id": "SQ_TECH_COMMUNICATION",
        "title": "Technical Communication",
        "text": "This skill tends to get overlooked next to \"harder\" technical topics, but in team settings it's often what determines whether good work actually gets understood, adopted, and built on by others. Code that's technically excellent but impossible for anyone else to follow tends to get rewritten, avoided, or quietly become a liability — clear communication is what makes good work actually last.",
        "lines": [
            "This skill tends to get overlooked next to \"harder\" technical topics, but in team settings it's often what determines whether good",
            "work actually gets understood, adopted, and built on by others. Code that's technically excellent but impossible for anyone else to",
            "follow tends to get rewritten, avoided, or quietly become a liability — clear communication is what makes good work actually last.",
        ],
    },
}


# The ordered handoff Phase 12's `lecture_sheets` column expects. Written
# out rather than derived from the table above so the two can be checked
# against each other — validate() fails on an id listed here with no
# sheet behind it, and on a sheet no skill lists.
SHEET_IDS: dict[str, list[str]] = {
    "SQ_PROGRAMMING_LANGUAGE": [
        "SQ_PROGRAMMING_LANGUAGE_S1",
        "SQ_PROGRAMMING_LANGUAGE_S2",
        "SQ_PROGRAMMING_LANGUAGE_S3",
    ],
    "SQ_DSA": [
        "SQ_DSA_S1",
        "SQ_DSA_S2",
        "SQ_DSA_S3",
    ],
    "SQ_GIT_GITHUB": [
        "SQ_GIT_GITHUB_S1",
        "SQ_GIT_GITHUB_S2",
        "SQ_GIT_GITHUB_S3",
    ],
    "SQ_LINUX_CLI": [
        "SQ_LINUX_CLI_S1",
        "SQ_LINUX_CLI_S2",
        "SQ_LINUX_CLI_S3",
    ],
    "SQ_DATABASES_SQL": [
        "SQ_DATABASES_SQL_S1",
        "SQ_DATABASES_SQL_S2",
        "SQ_DATABASES_SQL_S3",
    ],
    "SQ_NETWORKING": [
        "SQ_NETWORKING_S1",
        "SQ_NETWORKING_S2",
        "SQ_NETWORKING_S3",
    ],
    "SQ_WEB_APP_DEV": [
        "SQ_WEB_APP_DEV_S1",
        "SQ_WEB_APP_DEV_S2",
        "SQ_WEB_APP_DEV_S3",
    ],
    "SQ_DOCKER": [
        "SQ_DOCKER_S1",
        "SQ_DOCKER_S2",
        "SQ_DOCKER_S3",
    ],
    "SQ_AI_TOOLS": [
        "SQ_AI_TOOLS_S1",
        "SQ_AI_TOOLS_S2",
        "SQ_AI_TOOLS_S3",
    ],
    "SQ_DEBUGGING_TESTING": [
        "SQ_DEBUGGING_TESTING_S1",
        "SQ_DEBUGGING_TESTING_S2",
        "SQ_DEBUGGING_TESTING_S3",
    ],
    "SQ_OOP": [
        "SQ_OOP_S1",
        "SQ_OOP_S2",
        "SQ_OOP_S3",
    ],
    "SQ_TECH_COMMUNICATION": [
        "SQ_TECH_COMMUNICATION_S1",
        "SQ_TECH_COMMUNICATION_S2",
        "SQ_TECH_COMMUNICATION_S3",
    ],
}


# What get_sheet() hands back for an id it does not know. Mirrors
# DEFAULT_LECTURE in content/lectures.py: the reader gets a readable
# card instead of a KeyError, and validate() is what makes sure no real
# sheet id ever lands here.
DEFAULT_SHEET: dict = {
    "skill_id": "",
    "title": "Study Notes",
    "text": "These notes are not on this PC.",
    "lines": ["These notes are not on this PC."],
}


class SideQuestLectureError(Exception):
    """Raised when the tables above do not agree with each other."""


def get_sheet(sheet_id: str) -> dict:
    """Return the sheet for an id, or DEFAULT_SHEET.
    Never raises, never returns None."""
    return SIDE_QUEST_SHEETS.get(
        (sheet_id or "").strip().upper(), DEFAULT_SHEET)


def get_sheet_ids(skill_id: str) -> list[str]:
    """The sheet ids for a skill, in reading order, or [] if unknown.
    A copy, so a caller paging through it cannot edit the table."""
    return list(SHEET_IDS.get((skill_id or "").strip().upper(), ()))


def validate() -> None:
    """
    Raise SideQuestLectureError unless every skill is present, has at
    least one sheet, and every sheet id resolves to real text.

    Called at import, deliberately: this table is only ever wrong
    because someone edited it, and a lecture that silently loses a
    paragraph is far worse than a game that refuses to start. Phase 12
    validates its own `lecture_sheets` column against the same tables.
    """
    problems: list[str] = []

    for skill_id in SKILL_IDS:
        if skill_id not in SHEET_IDS:
            problems.append("%s: skill missing from SHEET_IDS" % skill_id)
        elif not SHEET_IDS[skill_id]:
            problems.append("%s: skill has zero sheets" % skill_id)
    for skill_id in SHEET_IDS:
        if skill_id not in SKILL_IDS:
            problems.append("%s: not one of the twelve topics" % skill_id)

    listed: dict = {}
    for skill_id, sheet_ids in SHEET_IDS.items():
        for sheet_id in sheet_ids:
            if sheet_id in listed:
                problems.append("%s: listed by both %s and %s"
                                % (sheet_id, listed[sheet_id], skill_id))
                continue
            listed[sheet_id] = skill_id
            sheet = SIDE_QUEST_SHEETS.get(sheet_id)
            if sheet is None:
                problems.append("%s: no sheet with this id" % sheet_id)
                continue
            if not str(sheet.get("text", "")).strip():
                problems.append("%s: sheet has no text" % sheet_id)
            if not sheet.get("lines"):
                problems.append("%s: sheet has no lines" % sheet_id)
            if not str(sheet.get("title", "")).strip():
                problems.append("%s: sheet has no title" % sheet_id)
            if sheet.get("skill_id") != skill_id:
                problems.append("%s: sheet says skill_id %r, listed under %s"
                                % (sheet_id, sheet.get("skill_id"), skill_id))
            if " ".join(sheet.get("lines") or ()) != sheet.get("text"):
                problems.append("%s: lines do not rejoin to text" % sheet_id)

    for sheet_id in SIDE_QUEST_SHEETS:
        if sheet_id not in listed:
            problems.append("%s: sheet no skill lists" % sheet_id)

    if problems:
        raise SideQuestLectureError(
            "side quest lecture content is invalid:\n  "
            + "\n  ".join(problems))


validate()


# -------------------------------------------------------------
# STUB TEST -- print every sheet id with its size, and re-run the
# checks that import already ran:
#
#     python -m content.side_quest_lectures
#
# Run as a module from the project root. Headless -- no pygame, no
# display, and nothing is written.
# -------------------------------------------------------------
if __name__ == "__main__":
    validate()
    print("%d topics, %d sheets" % (len(SHEET_IDS), len(SIDE_QUEST_SHEETS)))
    for skill_id in SKILL_IDS:
        sheet_ids = get_sheet_ids(skill_id)
        print("\n%s  (%d sheets)  %s"
              % (skill_id, len(sheet_ids), get_sheet(sheet_ids[0])["title"]))
        for sheet_id in sheet_ids:
            sheet = get_sheet(sheet_id)
            print("  %-30s %4d chars  %d lines"
                  % (sheet_id, len(sheet["text"]), len(sheet["lines"])))
    longest = max(SIDE_QUEST_SHEETS.values(),
                  key=lambda sheet: max(len(line) for line in sheet["lines"]))
    print("\nlongest line: %d chars"
          % max(len(line) for line in longest["lines"]))
    print("unknown id -> %r" % get_sheet("NOPE")["title"])

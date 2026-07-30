"""
main.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
Entry point — Sprint 3 screen routing + HUD integration.
Nangiba's HUD renders on top of every gameplay screen.
─────────────────────────────────────────────────────────────
Sprint 3 — Abu Huraira (dev1-hurairiam-core)

── Merged: dev1 engine wiring + dev3 presentation pass ──────
This file is the reconciliation of two parallel lines of work on
the same main loop. Nothing from either side was dropped.

From dev1/main (engine layer):
  * NPCManager-backed Exploration list + real DialogueManager
    dialogue (DIALOGUE state)
  * full MCQ exam pipeline — 3 tiers per course, real MainQuest
    routed through game_clock.process_time_consumable()
  * EndgameEvaluationManager wired into EndgameScreen

From dev3/Nangiba (presentation layer):
  * SCALED windowed / SCALED|FULLSCREEN window + F11 toggle
  * MainMenuScreen driving handle_main_menu()
  * MONOLOGUE state — per-semester opening monologue
  * RESULTS state — end-of-semester recap after exams
  * ESC opens a ConfirmPopup (exit / return-to-menu) instead of
    an instant quit
  * HUD also shows the backlog count

Where the two collided, both behaviours were kept: the exam
screen still runs dev1's real MainQuest pipeline, but on
finishing a semester it now routes through dev3's RESULTS recap
(which then decides ENDGAME vs. the next semester's MONOLOGUE)
instead of jumping straight back to Registration.
─────────────────────────────────────────────────────────────
"""

import sys
import pygame

from engine.game_session import GameSession
from engine.game_clock import GameClock
from engine.registration_manager import RegistrationManager
from engine.screen_manager import ScreenManager, ScreenState
from engine.npc_manager import NPCManager
from engine.dialogue_manager import DialogueManager
from ui.hud import HUD
from ui.registration_screen import (
    RegistrationScreen, FIRST_ROW_Y, FOOTER_Y, ROW_PITCH
)
from academic.course_catalog import build_course_catalog
from academic.quest import MainQuest
from content.npc_roster import NPC_ROSTER

# ── Screens + content from the dev3 presentation pass ─────────────
from ui.main_menu_screen import MainMenuScreen, START_GAME, EXIT
from ui.monologue_screen import MonologueScreen, MonologueController
from ui.results_screen import ResultsScreen
from ui.endgame_screen import EndgameScreen
from ui.confirm_popup import ConfirmPopup
from content.monologues import get_monologue

# ── Constants ─────────────────────────────────────────────────────
SCREEN_WIDTH:  int = 1280
SCREEN_HEIGHT: int = 720
FPS:           int = 60
WINDOW_TITLE:  str = "CSE Life: Compile & Conquer"

# Display flags — SCALED keeps the pixel art crisp; F11 toggles
# between these two at runtime.
SIZE:             tuple = (SCREEN_WIDTH, SCREEN_HEIGHT)
WINDOWED_FLAGS:   int = pygame.SCALED
FULLSCREEN_FLAGS: int = pygame.SCALED | pygame.FULLSCREEN
VERSION_STRING:   str = "v0.3 — short scope"

# Derived from RegistrationScreen's own layout constants, not
# hand-copied — the table area sits between FIRST_ROW_Y and
# FOOTER_Y, each row occupying ROW_PITCH px. No scrolling support
# yet (Iteration 12 scope), so the visible catalog is simply
# truncated to whatever physically fits without overlapping the
# credit-total footer box. [Sprint 3 — Iteration 12, known limitation]
MAX_VISIBLE_COURSE_ROWS: int = (FOOTER_Y - FIRST_ROW_Y) // ROW_PITCH

# Which states show the HUD strip. Full-card screens (main menu,
# monologue, results recap, endgame) draw their own framed panel
# edge-to-edge, so the HUD would clash with them — it only shows
# during the interactive gameplay states.
#
# DIALOGUE is included: dev1's Iteration 13 loop rendered the HUD
# over dialogue (it excluded only MAIN_MENU/ENDGAME), and the
# dialogue box draws along the bottom, so the 44px top strip does
# not overlap it.
HUD_STATES = {
    ScreenState.REGISTRATION,
    ScreenState.EXPLORATION,
    ScreenState.DIALOGUE,
    ScreenState.EXAM,
}

# ── Colours ───────────────────────────────────────────────────────
BG_COLOUR:     tuple = (22, 22, 35)
HUD_COLOUR:    tuple = (30, 30, 48)
TEXT_COLOUR:   tuple = (200, 210, 255)
ACCENT_COLOUR: tuple = (80, 130, 200)
DIM_COLOUR:    tuple = (70, 75, 95)


# ── Helper: snapshot this semester's exam outcomes ────────────────

def build_results_snapshot(semester) -> list:
    """
    Turn the semester's registered courses into the plain tuple list
    ResultsScreen.render() expects: (code, name, credits, status).

    Called the instant we leave the exam phase — after
    check_semester_end_state() has backlogged anything incomplete, but
    before advance_semester() clears the course list — so the recap
    reflects what just happened.

    A course is PASSED if its lifecycle flag says completed, BACKLOG if
    it was carried over, or PENDING in the (now rare) case the exam
    pipeline never touched it. With dev1's real MainQuest pipeline
    wired in, PASSED/BACKLOG are the normal outcomes; PENDING is kept
    as an honest fallback rather than silently mislabelling a course.
    """
    snapshot = []
    for course in semester.get_registered_courses():
        if course.is_completed():
            status = "PASSED"
        elif course.is_backlogged():
            status = "BACKLOG"
        else:
            status = "PENDING"
        snapshot.append((
            course.get_course_code(),
            course.get_course_name(),
            course.get_credit_value(),
            status,
        ))
    return snapshot


# ── Screen Handler Functions ───────────────────────────────────────

def handle_main_menu(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    main_menu_screen: MainMenuScreen,
    ui: dict,
    events: list
) -> None:
    """
    Renders the animated main menu (START GAME / EXIT) and handles
    keyboard + mouse focus. START GAME routes into the semester-1
    monologue; EXIT raises the exit-confirm popup (handled centrally
    in the main loop). HUD is NOT shown here — no gameplay data yet.
    """
    focus = ui["menu_focus"]
    button_rects = main_menu_screen.get_button_rects()

    def activate(index: int) -> None:
        if index == START_GAME:
            screen_mgr.queue_transition(ScreenState.MONOLOGUE)
        elif index == EXIT:
            ui["popup"] = "exit"

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                focus = (focus - 1) % len(button_rects)
            elif event.key == pygame.K_DOWN:
                focus = (focus + 1) % len(button_rects)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                activate(focus)
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(button_rects):
                if rect.collidepoint(event.pos):
                    focus = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(button_rects):
                if rect.collidepoint(event.pos):
                    activate(i)
                    break

    ui["menu_focus"] = focus
    main_menu_screen.render(screen, focus, VERSION_STRING)


def handle_monologue(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    session: GameSession,
    monologue_screen: MonologueScreen,
    monologue: MonologueController,
    dt: float,
    events: list
) -> None:
    """
    Plays the opening monologue for the current semester using the
    typewriter effect in MonologueController. A key/click finishes the
    current line, then advances; once every line is revealed, the next
    key/click marks the semester's intro as played and routes into
    registration.
    """
    semester = session.get_active_semester()
    sem_no = semester.get_semester_number()

    # Start (once) for whichever semester we're on. is_started_for()
    # keeps re-entry from restarting the text mid-read.
    if not monologue.is_started_for(sem_no):
        monologue.start(sem_no, get_monologue(sem_no))

    for event in events:
        advanced = (
            (event.type == pygame.KEYDOWN
             and event.key not in (pygame.K_F11, pygame.K_ESCAPE))
            or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
        )
        if advanced:
            if monologue.is_done():
                semester.play_intro_monologue()
                screen_mgr.queue_transition(ScreenState.REGISTRATION)
            else:
                monologue.advance()

    monologue.update(dt)
    monologue_screen.render(
        screen, sem_no, semester.get_time_pool_days(),
        monologue.visible_lines(), monologue.is_done())


def handle_registration(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    session: GameSession,
    registration_manager: RegistrationManager,
    registration_screen: RegistrationScreen,
    full_catalog: list,
    events: list
) -> None:
    """
    Renders the real registration screen (Nangiba's RegistrationScreen)
    driven live by RegistrationManager — no more placeholder text.

    Flow:
    - The visible catalog is RegistrationManager.build_semester_catalog()
      (prereqs-satisfied + backlog-injected), truncated to
      MAX_VISIBLE_COURSE_ROWS since there's no scrolling yet.
    - Clicking a course row toggles select/deselect via
      RegistrationManager — the 15-credit cap is enforced there, not
      here, so an over-limit click is just silently rejected (the
      credit bar/footer visually explains why).
    - CONFIRM calls confirm_registration(semester); on success,
      transitions to Exploration. An empty selection is a no-op click
      (confirm_registration() returns False and nothing happens).
    - CANCEL clears the current selection without transitioning.
    - "confirmed" (green/locked rows) is intentionally always passed
      as [] this iteration — there's no partial-confirm/re-open flow
      yet, registration confirms and immediately advances the screen.

    [Sprint 3 — Iteration 12]
    """
    player = session.get_active_player()
    semester = session.get_active_semester()
    history = player.get_academic_history()

    visible_courses = registration_manager.build_semester_catalog(
        full_catalog, history
    )[:MAX_VISIBLE_COURSE_ROWS]

    row_rects = registration_screen.get_course_row_rects(len(visible_courses))
    confirm_rect = registration_screen.get_confirm_rect()
    cancel_rect = registration_screen.get_cancel_rect()

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            if confirm_rect.collidepoint(pos):
                if registration_manager.confirm_registration(semester):
                    screen_mgr.queue_transition(ScreenState.EXPLORATION)

            elif cancel_rect.collidepoint(pos):
                registration_manager.clear_selection()

            else:
                for i, rect in enumerate(row_rects):
                    if rect.collidepoint(pos):
                        course = visible_courses[i]
                        if course in registration_manager.get_selected_courses():
                            registration_manager.deselect_course(course)
                        else:
                            registration_manager.select_course(course)
                        break

    registration_screen.render(
        screen,
        visible_courses=visible_courses,
        selected=registration_manager.get_selected_courses(),
        confirmed=[],
        current_credits=registration_manager.get_current_selected_credits(),
        credit_limit=registration_manager.get_max_credit_limit(),
        player_name=player.get_display_name(),
        student_id=player.get_character_id(),
        semester=semester.get_semester_number()
    )


def handle_exploration(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    session: GameSession,
    game_clock: GameClock,
    npc_manager: NPCManager,
    dialogue_manager: DialogueManager,
    fonts: dict,
    events: list
) -> None:
    """
    Plain-text placeholder for the Exploration screen — NOT a designed
    UI. The real styled map screen (art, layout, click regions) is
    still Nangiba's to build; the other screens in this build
    (menu/monologue/registration/results/endgame) are already hers.

    What IS wired here (the engine-layer part of the job): the NPC
    list is real data from NPCManager, not a fake placeholder string,
    and selecting one actually loads real dialogue through
    DialogueManager. Selection is number-key driven (1-7) rather than
    mouse+Rect click detection, since building clickable row regions
    with visual feedback is exactly the kind of UI polish that belongs
    in ui/, not here.

    [Sprint 3 — Iteration 13]
    """
    screen.fill((20, 24, 38))

    player = session.get_active_player()
    semester = session.get_active_semester()

    if not game_clock.is_eligible_for_side_activities():
        screen_mgr.queue_transition(ScreenState.EXAM)
        return

    header = fonts["title"].render(
        "Exploration Phase", True, TEXT_COLOUR)
    screen.blit(header, (40, 60))

    available_npcs = npc_manager.get_available_npcs(
        semester.get_semester_number()
    )

    placeholder = fonts["small"].render(
        "[ Nangiba's map/NPC art renders here — list below is real "
        "data, plain text until then ]", True, DIM_COLOUR)
    screen.blit(placeholder, (40, 100))

    y = 140
    for i, npc in enumerate(available_npcs):
        available = npc.is_within_availability_window(player)
        colour = TEXT_COLOUR if available else DIM_COLOUR
        suffix = "" if available else "  (unavailable right now)"
        line = fonts["body"].render(
            f"[{i + 1}] {npc.get_display_name()}{suffix}", True, colour)
        screen.blit(line, (60, y))
        y += 28

    # Hint updated: ESC now opens a menu popup, not an instant quit.
    hint = fonts["small"].render(
        "Press 1-7 to talk to someone  |  E: exam phase  |  ESC: menu",
        True, DIM_COLOUR)
    screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                       SCREEN_HEIGHT - 40))

    number_keys = [
        pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
        pygame.K_5, pygame.K_6, pygame.K_7,
    ]

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                screen_mgr.queue_transition(ScreenState.EXAM)
            elif event.key in number_keys:
                index = number_keys.index(event.key)
                if index < len(available_npcs):
                    npc = available_npcs[index]
                    npc_id = npc.get_character_id()
                    lines = npc_manager.get_dialogue_lines(npc_id, player)
                    if not lines:
                        continue

                    variants = NPC_ROSTER[npc_id]["portrait_variants"]
                    portrait_path = None
                    if "neutral" in variants:
                        portrait_path = NPC_ROSTER[npc_id][
                            "portrait_file"
                        ].format(emotion="neutral")

                    dialogue_manager.load_dialogue(lines, portrait_path)
                    screen_mgr.queue_transition(ScreenState.DIALOGUE)


def handle_dialogue(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    dialogue_manager: DialogueManager,
    events: list
) -> None:
    """
    DialogueManager (Ayesha's file, engine/ layer — it only imports
    Pygame to draw a text box, not to design a screen) renders on a
    plain dark background here — same reasoning as above, this isn't
    trying to be Exploration's real background art.

    [Sprint 3 — Iteration 13]
    """
    screen.fill((20, 24, 38))

    for event in events:
        advance = (
            (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE)
            or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
        )
        if advance and not dialogue_manager.advance():
            screen_mgr.queue_transition(ScreenState.EXPLORATION)

    dialogue_manager.render(screen)


EXAM_TIERS: list = ["easy", "medium", "hard"]
EXAM_OPTION_KEYS: dict = {
    pygame.K_a: "A", pygame.K_b: "B", pygame.K_c: "C", pygame.K_d: "D",
}


def handle_exam(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    session: GameSession,
    game_clock: GameClock,
    exam_state: dict,
    ui: dict,
    fonts: dict,
    events: list
) -> None:
    """
    Plain-text exam flow — same non-designed style as Exploration's
    placeholder (this isn't a styled Exam screen, just the engine-layer
    wiring underneath it).

    Walks every course in the active Semester's registered list, one
    at a time: shows its 3 MCQ tiers (easy/medium/hard) one at a
    time, letter keys A-D answer each. Once all 3 tiers are
    answered, builds a real MainQuest for that course and runs it
    through game_clock.process_time_consumable() — the SAME pipeline
    every other TimeConsumable action goes through (polymorphism,
    not a special case for exams). Shows a brief PASS/FAIL message,
    SPACE continues to the next course.

    MERGE NOTE: once every registered course has been attempted,
    check_semester_end_state() still runs here exactly as before — but
    the screen now hands off to the RESULTS recap instead of jumping
    straight to Endgame/Registration. The snapshot is built right
    after check_semester_end_state() and before any advance_semester()
    call (which now lives in handle_results), so the recap sees the
    real, final PASSED/BACKLOG state of this term's courses.

    exam_state is a small mutable dict ({"course_index": 0,
    "tier_index": 0, "answers": {}, "result_message": None}) created
    once in main() — needed because, unlike Exploration/Dialogue,
    this screen has real multi-step state (which course, which
    question, answers collected so far) that must persist frame to
    frame within a single semester's exam session. Reset to its
    initial values right before transitioning out, so the next
    semester's exam session starts clean.

    [Sprint 3 — Iteration 14]
    """
    screen.fill((25, 18, 35))

    semester = session.get_active_semester()
    registered_courses = semester.get_registered_courses()

    header = fonts["title"].render("Exam Phase", True, TEXT_COLOUR)
    screen.blit(header, (40, 60))

    # All courses attempted -> close out the semester for real.
    if exam_state["course_index"] >= len(registered_courses):
        info = fonts["body"].render(
            "All exams attempted for this semester.", True, ACCENT_COLOUR)
        screen.blit(info, (40, 100))
        hint = fonts["small"].render(
            "Press SPACE to see results  |  ESC for menu", True, DIM_COLOUR)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                           SCREEN_HEIGHT - 40))

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                game_clock.check_semester_end_state()

                # Snapshot BEFORE advance_semester() (now called in
                # handle_results) clears this term's course list.
                ui["results"] = build_results_snapshot(semester)

                reset_exam_state(exam_state)
                screen_mgr.queue_transition(ScreenState.RESULTS)
        return

    course = registered_courses[exam_state["course_index"]]

    course_info = fonts["body"].render(
        f"{course.get_course_code()} — {course.get_course_name()} "
        f"({exam_state['course_index'] + 1}/{len(registered_courses)})",
        True, ACCENT_COLOUR)
    screen.blit(course_info, (40, 100))

    # A result is showing -- wait for SPACE before moving on.
    if exam_state["result_message"] is not None:
        result = fonts["title"].render(
            exam_state["result_message"], True, TEXT_COLOUR)
        screen.blit(result, (40, 160))
        hint = fonts["small"].render(
            "Press SPACE to continue", True, DIM_COLOUR)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                           SCREEN_HEIGHT - 40))

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                exam_state["course_index"] += 1
                exam_state["tier_index"] = 0
                exam_state["answers"] = {}
                exam_state["result_message"] = None
        return

    # Still answering this course's 3 tiers.
    if not course.is_question_set_complete():
        # Defensive fallback -- shouldn't happen with the real
        # catalog (every course loads all 3 tiers), but course.
        # check_answers() already handles an incomplete set safely
        # (returns False), so this just skips straight to running
        # the quest with whatever answers (none) were collected.
        placeholder = fonts["small"].render(
            "[ No question data loaded for this course — skipping ]",
            True, DIM_COLOUR)
        screen.blit(placeholder, (40, 160))
        exam_state["tier_index"] = len(EXAM_TIERS)
    else:
        tier = EXAM_TIERS[exam_state["tier_index"]]
        question = course.get_question(tier)

        tier_label = fonts["small"].render(
            f"[{tier.upper()}] question "
            f"{exam_state['tier_index'] + 1}/{len(EXAM_TIERS)}",
            True, DIM_COLOUR)
        screen.blit(tier_label, (40, 150))

        q_text = fonts["body"].render(
            question["question_text"], True, TEXT_COLOUR)
        screen.blit(q_text, (40, 180))

        y = 220
        for letter, option_text in question["options"].items():
            option_line = fonts["body"].render(
                f"{letter}) {option_text}", True, TEXT_COLOUR)
            screen.blit(option_line, (60, y))
            y += 30

        hint = fonts["small"].render(
            "Press A / B / C / D to answer  |  ESC for menu",
            True, DIM_COLOUR)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                           SCREEN_HEIGHT - 40))

        for event in events:
            if event.type == pygame.KEYDOWN and event.key in EXAM_OPTION_KEYS:
                exam_state["answers"][tier] = EXAM_OPTION_KEYS[event.key]
                exam_state["tier_index"] += 1

    # All 3 tiers answered (or skipped) -- run the real MainQuest.
    if exam_state["tier_index"] >= len(EXAM_TIERS):
        main_quest = MainQuest(
            quest_id=f"MQ_{course.get_course_code()}",
            linked_course=course,
        )
        main_quest.attempt_qa_optimization(exam_state["answers"])
        game_clock.process_time_consumable(main_quest)

        if not main_quest.get_is_completed():
            # execute_action() no-opped: not enough days left in the
            # player's own time pool to cover this exam's cost. No
            # credit/backlog bookkeeping happened here — but
            # check_semester_end_state() (called once every course
            # has been attempted) already backlogs any course whose
            # is_completed() is still False, so this still resolves
            # correctly without any special-casing needed there.
            exam_state["result_message"] = (
                "Not enough time left this semester — course carries "
                "over to next semester."
            )
        else:
            passed = main_quest.evaluate_exam_result()
            exam_state["result_message"] = (
                f"PASSED — {course.get_credit_value()} credits awarded!"
                if passed else
                "FAILED — course backlogged for next semester."
            )


def handle_results(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    session: GameSession,
    game_clock: GameClock,
    results_screen: ResultsScreen,
    ui: dict,
    events: list
) -> None:
    """
    Shows the recap of the semester that just ended: which courses passed
    or went to backlog, credits earned this term, running total, and the
    backlog count. A key/click then either routes to the endgame (if the
    session froze — graduation or year cap) or advances to the next
    semester's monologue.

    MERGE NOTE: check_semester_end_state() already ran in handle_exam
    (it is what decides frozen/backlogged), so this screen only reads
    the outcome and owns the advance_semester() call.
    """
    semester = session.get_active_semester()
    player = session.get_active_player()
    results = ui["results"]

    credits_earned = sum(credits for (_code, _name, credits, status)
                         in results if status == "PASSED")
    history = player.get_academic_history()
    backlog_count = len(history.get_backlog_courses()) if history else 0

    for event in events:
        advanced = (
            (event.type == pygame.KEYDOWN
             and event.key not in (pygame.K_F11, pygame.K_ESCAPE))
            or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
        )
        if advanced:
            if session.get_is_frozen():
                screen_mgr.queue_transition(ScreenState.ENDGAME)
            else:
                game_clock.advance_semester()
                screen_mgr.queue_transition(ScreenState.MONOLOGUE)

    results_screen.render(
        screen,
        semester_number=semester.get_semester_number(),
        results=results,
        credits_earned=credits_earned,
        total_credits=player.get_accumulated_credits(),
        backlog_count=backlog_count,
        hint_visible=True)


def handle_endgame(
    screen: pygame.Surface,
    session: GameSession,
    endgame_screen: EndgameScreen,
    ui: dict,
    events: list
) -> None:
    """
    Wires Saif's EndgameEvaluationManager into Nangiba's already-built
    EndgameScreen — both classes already existed fully working, this
    just connects them. evaluate() returns a dict shaped exactly to
    EndgameScreen.render()'s keyword arguments, so the two plug
    together directly.

    The evaluation is computed ONCE and cached in ui["endgame"] rather
    than every frame: evaluate() is deterministic for a given player,
    and the session is already frozen by the time this screen is
    reached, so nothing about the player changes here that would need
    re-evaluating. The cache is cleared when the player returns to the
    main menu (see handle_popup_events).

    KNOWN, NOT MINE TO FIX: EndgameEvaluationManager currently pulls
    epilogue text from content/epilogue_text.py (Saif's placeholder
    prose), not content/dialogues.py's EPILOGUE_TEXTS (Ayesha's real
    narrative) — that reconciliation is a content-ownership decision
    between the two of them, not something to silently change here.
    Both dicts use matching, correct key names, so this works
    correctly either way — it's just placeholder prose for now.

    events is accepted for signature consistency with every other
    screen handler and to leave room for a future "play again" input.
    ESC (handled in the main loop) raises the exit popup.

    [Sprint 3 — Iteration 15]
    """
    if ui["endgame"] is None:
        player = session.get_active_player()
        manager = session.trigger_endgame_evaluation()
        ui["endgame"] = manager.evaluate(player)

    endgame_screen.render(screen, **ui["endgame"])


# ── Shared state helpers ──────────────────────────────────────────

def reset_exam_state(exam_state: dict) -> None:
    """
    Return the exam screen's multi-step state to its initial values so
    the next semester's exam session starts clean. Called both when a
    semester's exams finish normally and when the player bails back to
    the main menu mid-exam.
    """
    exam_state["course_index"] = 0
    exam_state["tier_index"] = 0
    exam_state["answers"] = {}
    exam_state["result_message"] = None


# ── Central popup handling (ESC → confirm) ────────────────────────

def handle_popup_events(
    screen_mgr: ScreenManager,
    confirm_popup: ConfirmPopup,
    monologue: MonologueController,
    exam_state: dict,
    ui: dict,
    events: list,
    running: bool
) -> bool:
    """
    While a popup is open it swallows all gameplay input. Clicking the
    confirm button acts on the popup's mode ("exit" quits the game,
    "menu" returns to the main menu); the cancel button or ESC closes it
    (STAY). Returns the possibly-updated `running` flag.
    """
    mode = ui["popup"]
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            ui["popup"] = None                       # ESC = STAY / close
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if confirm_popup.get_confirm_rect().collidepoint(event.pos):
                if mode == "exit":
                    running = False
                elif mode == "menu":
                    # Soft return to the title screen. NOTE: this does not
                    # reset the session — a full "new game" reset is a
                    # follow-up for whoever owns GameSession. For now the
                    # menu re-appears and START resumes the current run.
                    ui["popup"] = None
                    ui["endgame"] = None
                    ui["results"] = []
                    ui["menu_focus"] = START_GAME
                    monologue.reset()
                    # Bailing out mid-exam would otherwise leave the exam
                    # screen pointing at a stale course index on re-entry.
                    reset_exam_state(exam_state)
                    screen_mgr.queue_transition(ScreenState.MAIN_MENU)
            elif confirm_popup.get_cancel_rect().collidepoint(event.pos):
                ui["popup"] = None                   # STAY
    return running


def draw_popup(screen: pygame.Surface, confirm_popup: ConfirmPopup,
               ui: dict) -> None:
    """Draw the open popup on top of the frozen screen underneath it."""
    mode = ui["popup"]
    if mode == "exit":
        confirm_popup.render(
            screen, "EXIT GAME?",
            ["Any unsaved progress will be lost."],
            "EXIT", "STAY")
    elif mode == "menu":
        confirm_popup.render(
            screen, "RETURN TO MAIN MENU?",
            ["Progress cannot be saved yet."],
            "RETURN", "STAY")


# ── Main ──────────────────────────────────────────────────────────

def main() -> None:
    """
    Initialises Pygame, creates game systems, runs main loop.
    HUD renders on top of the interactive gameplay screens
    (registration, exploration, dialogue, exam).
    """
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    # SCALED window + fullscreen toggle state.
    is_fullscreen = False
    screen = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    clock = pygame.time.Clock()

    # Game systems
    session = GameSession()
    game_clock = GameClock(session)
    registration_manager = RegistrationManager()
    screen_mgr = ScreenManager()

    # Static content — built once, same Course instances reused every
    # frame and across semesters (required for the backlog mechanic:
    # a failed course is the SAME object re-offered later, not a copy).
    full_catalog = build_course_catalog()

    # Fonts (used by the placeholder exploration/exam screens)
    fonts = {
        "title": pygame.font.SysFont("Arial", 28, bold=True),
        "body":  pygame.font.SysFont("Arial", 16),
        "small": pygame.font.SysFont("Arial", 13),
    }

    # UI components
    hud = HUD()
    registration_screen = RegistrationScreen(SCREEN_WIDTH, SCREEN_HEIGHT)
    main_menu_screen = MainMenuScreen(SCREEN_WIDTH, SCREEN_HEIGHT)
    monologue_screen = MonologueScreen()
    monologue = MonologueController()
    results_screen = ResultsScreen()
    endgame_screen = EndgameScreen()
    confirm_popup = ConfirmPopup(SCREEN_WIDTH, SCREEN_HEIGHT)
    dialogue_manager = DialogueManager(SCREEN_WIDTH, SCREEN_HEIGHT)

    # NPC roster — built once, same NPC instances reused every frame
    # (their accessibility state, e.g. expire_for_semester(), needs
    # to persist across frames the same way Course instances do).
    npc_manager = NPCManager()

    # Multi-step state for the Exam screen (which course, which
    # question tier, answers collected so far) — needs to persist
    # frame to frame within one semester's exam session, reset right
    # before transitioning out. See handle_exam()'s docstring.
    exam_state = {
        "course_index": 0,
        "tier_index": 0,
        "answers": {},
        "result_message": None,
    }

    # Transient UI state that doesn't belong to any single screen:
    #   popup      : None | "exit" | "menu"  — which confirm box is open
    #   menu_focus : which main-menu button is highlighted
    #   results    : snapshot of the last semester's outcomes (for RESULTS)
    #   endgame    : cached EndgameEvaluationManager.evaluate() result
    ui = {
        "popup": None,
        "menu_focus": START_GAME,
        "results": [],
        "endgame": None,
    }

    running = True

    while running:

        screen_mgr.apply_pending_transition()

        dt = clock.tick(FPS) / 1000.0
        events = pygame.event.get()
        state = screen_mgr.get_current_state()

        # ── Global input: quit + fullscreen (always active) ───────
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                flags = FULLSCREEN_FLAGS if is_fullscreen else WINDOWED_FLAGS
                screen = pygame.display.set_mode(SIZE, flags)

        # ── Popup gate: an open popup swallows input; otherwise ESC
        # opens the right popup (exit on menu/endgame, return-to-menu
        # during gameplay). When the popup is (or just became) open, the
        # screen underneath renders but receives no input this frame.
        if ui["popup"] is not None:
            running = handle_popup_events(
                screen_mgr, confirm_popup, monologue, exam_state, ui,
                events, running)
            dispatch_events: list = []
            frame_dt = 0.0
        else:
            opened_popup = False
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    ui["popup"] = ("exit"
                                   if state in (ScreenState.MAIN_MENU,
                                                ScreenState.ENDGAME)
                                   else "menu")
                    opened_popup = True
            dispatch_events = [] if opened_popup else events
            frame_dt = 0.0 if opened_popup else dt

        # ── Dispatch to the active screen ─────────────────────────
        if state == ScreenState.MAIN_MENU:
            handle_main_menu(
                screen, screen_mgr, main_menu_screen, ui, dispatch_events)

        elif state == ScreenState.MONOLOGUE:
            handle_monologue(
                screen, screen_mgr, session, monologue_screen, monologue,
                frame_dt, dispatch_events)

        elif state == ScreenState.REGISTRATION:
            handle_registration(
                screen, screen_mgr, session, registration_manager,
                registration_screen, full_catalog, dispatch_events)

        elif state == ScreenState.EXPLORATION:
            handle_exploration(
                screen, screen_mgr, session, game_clock, npc_manager,
                dialogue_manager, fonts, dispatch_events)

        elif state == ScreenState.DIALOGUE:
            handle_dialogue(
                screen, screen_mgr, dialogue_manager, dispatch_events)

        elif state == ScreenState.EXAM:
            handle_exam(
                screen, screen_mgr, session, game_clock, exam_state, ui,
                fonts, dispatch_events)

        elif state == ScreenState.RESULTS:
            handle_results(
                screen, screen_mgr, session, game_clock, results_screen,
                ui, dispatch_events)

        elif state == ScreenState.ENDGAME:
            handle_endgame(
                screen, session, endgame_screen, ui, dispatch_events)

        # ── HUD on the interactive gameplay screens ───────────────
        # Full-card screens (main menu, monologue, results, endgame)
        # draw their own framed panel edge-to-edge, so the HUD is
        # excluded there — and once the session is frozen there's no
        # time pool left worth showing anyway.
        #
        # Now also passes the backlog count. The registration card was
        # nudged down in ui/registration_screen.py so this 44px strip
        # no longer covers its top border — the cosmetic overlap
        # flagged in Iteration 12 is resolved.
        if state in HUD_STATES:
            player = session.get_active_player()
            semester = session.get_active_semester()
            history = player.get_academic_history()
            backlog_count = len(history.get_backlog_courses()) if history else 0
            hud.render(
                screen,
                time_pool=semester.get_time_pool_days(),
                wallet=player.get_wallet_balance(),
                semester=semester.get_semester_number(),
                credits=player.get_accumulated_credits(),
                backlog=backlog_count
            )

        # ── Popup draws last, on top of everything ────────────────
        if ui["popup"] is not None:
            draw_popup(screen, confirm_popup, ui)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

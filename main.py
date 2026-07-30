"""
main.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
Entry point — Sprint 3 screen routing + HUD integration.
Nangiba's HUD renders on top of every gameplay screen.
─────────────────────────────────────────────────────────────
Sprint 3 — Abu Huraira (dev1-hurairiam-core)

── dev3 / Nangiba integration pass ──────────────────────────
This version wires Nangiba's finished screens into the routing that
Abu Huraira built. Every change is tagged with a "[dev3]" banner so
it's easy to see what was added vs. Abu's original. Summary of the
additions:
  * SCALED windowed / SCALED|FULLSCREEN window + F11 toggle
  * MainMenuScreen driving handle_main_menu()
  * new MONOLOGUE state — per-semester opening monologue
  * new RESULTS state — end-of-semester recap after exams
  * EndgameScreen + EndgameEvaluationManager driving handle_endgame()
  * ESC opens a ConfirmPopup (exit / return-to-menu) instead of an
    instant quit
  * HUD now also shows the backlog count
None of Abu's engine logic changed — only the routing/presentation
layer around it.
─────────────────────────────────────────────────────────────
"""

import sys
import pygame

from engine.game_session import GameSession
from engine.game_clock import GameClock
from engine.registration_manager import RegistrationManager
from engine.screen_manager import ScreenManager, ScreenState
from ui.hud import HUD
from ui.registration_screen import (
    RegistrationScreen, FIRST_ROW_Y, FOOTER_Y, ROW_PITCH
)
from academic.course_catalog import build_course_catalog

# ── [dev3] Screens + content wired in this pass ───────────────────
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

# ── [dev3] Display flags — SCALED keeps the pixel art crisp; F11
# toggles between these two at runtime (the same pattern every one of
# my screen stub-tests used, now living in the real entry point).
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

# ── [dev3] Which states show the HUD strip. Full-card screens
# (main menu, monologue, results recap, endgame) draw their own framed
# panel edge-to-edge, so the HUD would clash with them — it only shows
# during the three interactive gameplay states.
HUD_STATES = {
    ScreenState.REGISTRATION,
    ScreenState.EXPLORATION,
    ScreenState.EXAM,
}

# ── Colours ───────────────────────────────────────────────────────
BG_COLOUR:     tuple = (22, 22, 35)
HUD_COLOUR:    tuple = (30, 30, 48)
TEXT_COLOUR:   tuple = (200, 210, 255)
ACCENT_COLOUR: tuple = (80, 130, 200)
DIM_COLOUR:    tuple = (70, 75, 95)


# ── [dev3] Helper: snapshot this semester's exam outcomes ─────────
def build_results_snapshot(semester) -> list:
    """
    Turn the semester's registered courses into the plain tuple list
    ResultsScreen.render() expects: (code, name, credits, status).

    Called the instant we leave the exam phase — before advance_semester()
    clears the course list — so the recap reflects what just happened.
    A course is PASSED if its lifecycle flag says completed, BACKLOG if it
    was carried over, or PENDING if the exam pipeline hasn't marked it yet
    (the exam phase is still a placeholder until Saif's MainQuest pipeline
    is plugged in — this stays honest until then).
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

# ── [dev3] Rewritten to drive Nangiba's MainMenuScreen ────────────
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


# ── [dev3] New handler: per-semester opening monologue ────────────
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
    fonts: dict,
    events: list
) -> None:
    """
    Renders exploration phase. Checks 15-day firewall every frame.
    E key manually enters exam phase for testing.
    """
    screen.fill((20, 24, 38))

    if not game_clock.is_eligible_for_side_activities():
        screen_mgr.queue_transition(ScreenState.EXAM)
        return

    header = fonts["title"].render(
        "Exploration Phase", True, TEXT_COLOUR)
    screen.blit(header, (40, 60))

    placeholder = fonts["body"].render(
        "[ Map and NPC interactions render here ]",
        True, DIM_COLOUR)
    screen.blit(placeholder,
                (SCREEN_WIDTH // 2 - placeholder.get_width() // 2,
                 SCREEN_HEIGHT // 2))

    # [dev3] hint updated: ESC now opens a menu popup, not an instant quit.
    hint = fonts["small"].render(
        "Press E to enter exam phase  |  ESC for menu",
        True, DIM_COLOUR)
    screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                       SCREEN_HEIGHT - 40))

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                screen_mgr.queue_transition(ScreenState.EXAM)


def handle_exam(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    session: GameSession,
    game_clock: GameClock,
    ui: dict,
    fonts: dict,
    events: list
) -> None:
    """
    Renders exam phase placeholder.
    SPACE finishes the semester: it runs the end-of-semester state check
    (which carries incomplete courses to backlog and freezes the session
    if graduation / the year cap is reached), snapshots the outcomes for
    the recap screen, then routes to the new RESULTS state.
    """
    screen.fill((25, 18, 35))

    semester = session.get_active_semester()

    header = fonts["title"].render("Exam Phase", True, TEXT_COLOUR)
    screen.blit(header, (40, 60))

    placeholder = fonts["body"].render(
        "[ MainQuest Q&A and exam pipeline renders here ]",
        True, DIM_COLOUR)
    screen.blit(placeholder,
                (SCREEN_WIDTH // 2 - placeholder.get_width() // 2,
                 SCREEN_HEIGHT // 2))

    # [dev3] hint updated for the new results step + menu popup.
    hint = fonts["small"].render(
        "Press SPACE to finish semester  |  ESC for menu",
        True, DIM_COLOUR)
    screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                       SCREEN_HEIGHT - 40))

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                # [dev3] End the semester, then show the recap. Advancing
                # the semester now happens AFTER the results screen, so the
                # recap can read this term's courses before they're cleared.
                game_clock.check_semester_end_state()
                ui["results"] = build_results_snapshot(semester)
                screen_mgr.queue_transition(ScreenState.RESULTS)


# ── [dev3] New handler: end-of-semester results recap ─────────────
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


# ── [dev3] Rewritten to drive Nangiba's EndgameScreen ─────────────
def handle_endgame(
    screen: pygame.Surface,
    session: GameSession,
    endgame_screen: EndgameScreen,
    ui: dict,
    events: list
) -> None:
    """
    Runs Saif's EndgameEvaluationManager once (the first frame we land
    here) to decide the ending + epilogue, caches the result, and hands
    it to Nangiba's EndgameScreen to render. evaluate() returns a dict
    shaped exactly to EndgameScreen.render()'s keyword arguments, so the
    two plug together directly. ESC (handled in the main loop) exits.
    """
    if ui["endgame"] is None:
        manager = session.trigger_endgame_evaluation()
        ui["endgame"] = manager.evaluate(session.get_active_player())

    endgame_screen.render(screen, **ui["endgame"])


# ── [dev3] Central popup handling (ESC → confirm) ─────────────────
def handle_popup_events(
    screen_mgr: ScreenManager,
    confirm_popup: ConfirmPopup,
    monologue: MonologueController,
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
                    ui["menu_focus"] = START_GAME
                    monologue.reset()
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
    HUD renders on top of the interactive gameplay screens.
    """
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    # [dev3] SCALED window + fullscreen toggle state.
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
    # [dev3] Nangiba's screens, instantiated once.
    main_menu_screen = MainMenuScreen(SCREEN_WIDTH, SCREEN_HEIGHT)
    monologue_screen = MonologueScreen()
    monologue = MonologueController()
    results_screen = ResultsScreen()
    endgame_screen = EndgameScreen()
    confirm_popup = ConfirmPopup(SCREEN_WIDTH, SCREEN_HEIGHT)

    # [dev3] Transient UI state that doesn't belong to any single screen:
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

        # ── [dev3] Popup gate: an open popup swallows input; otherwise
        # ESC opens the right popup (exit on menu/endgame, return-to-menu
        # during gameplay). When the popup is (or just became) open, the
        # screen underneath renders but receives no input this frame.
        if ui["popup"] is not None:
            running = handle_popup_events(
                screen_mgr, confirm_popup, monologue, ui, events, running)
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
                screen, screen_mgr, session, game_clock, fonts,
                dispatch_events)

        elif state == ScreenState.EXAM:
            handle_exam(
                screen, screen_mgr, session, game_clock, ui, fonts,
                dispatch_events)

        elif state == ScreenState.RESULTS:
            handle_results(
                screen, screen_mgr, session, game_clock, results_screen,
                ui, dispatch_events)

        elif state == ScreenState.ENDGAME:
            handle_endgame(
                screen, session, endgame_screen, ui, dispatch_events)

        # ── HUD on the interactive gameplay screens ───────────────
        # [dev3] Now also passes the backlog count. The registration card
        # was nudged down in ui/registration_screen.py so this 44px strip
        # no longer covers its top border.
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

        # ── [dev3] Popup draws last, on top of everything ─────────
        if ui["popup"] is not None:
            draw_popup(screen, confirm_popup, ui)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

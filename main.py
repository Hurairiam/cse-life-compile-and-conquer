"""
main.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
Entry point — Sprint 3 screen routing + HUD integration.
Nangiba's HUD renders on top of every gameplay screen.
─────────────────────────────────────────────────────────────
Sprint 3 — Abu Huraira (dev1-hurairiam-core)
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

# ── Constants ─────────────────────────────────────────────────────
SCREEN_WIDTH:  int = 1280
SCREEN_HEIGHT: int = 720
FPS:           int = 60
WINDOW_TITLE:  str = "CSE Life: Compile & Conquer"

# Derived from RegistrationScreen's own layout constants, not
# hand-copied — the table area sits between FIRST_ROW_Y and
# FOOTER_Y, each row occupying ROW_PITCH px. No scrolling support
# yet (Iteration 12 scope), so the visible catalog is simply
# truncated to whatever physically fits without overlapping the
# credit-total footer box. [Sprint 3 — Iteration 12, known limitation]
MAX_VISIBLE_COURSE_ROWS: int = (FOOTER_Y - FIRST_ROW_Y) // ROW_PITCH

# ── Colours ───────────────────────────────────────────────────────
BG_COLOUR:     tuple = (22, 22, 35)
HUD_COLOUR:    tuple = (30, 30, 48)
TEXT_COLOUR:   tuple = (200, 210, 255)
ACCENT_COLOUR: tuple = (80, 130, 200)
DIM_COLOUR:    tuple = (70, 75, 95)


# ── Screen Handler Functions ───────────────────────────────────────

def handle_main_menu(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    fonts: dict,
    events: list
) -> None:
    """
    Renders the main menu. SPACE starts the game.
    HUD is NOT shown on the main menu — no gameplay data yet.
    """
    screen.fill(BG_COLOUR)

    cx = SCREEN_WIDTH // 2

    title = fonts["title"].render(
        "CSE Life: Compile & Conquer", True, TEXT_COLOUR)
    sub = fonts["body"].render(
        "An OOP Lifecycle Simulation RPG", True, ACCENT_COLOUR)
    prompt = fonts["small"].render(
        "Press SPACE to begin", True, DIM_COLOUR)

    screen.blit(title,  (cx - title.get_width() // 2, 280))
    screen.blit(sub,    (cx - sub.get_width() // 2, 330))
    screen.blit(prompt, (cx - prompt.get_width() // 2, 420))

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                screen_mgr.queue_transition(ScreenState.REGISTRATION)


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

    hint = fonts["small"].render(
        "Press E to enter exam phase  |  ESC to quit",
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
    fonts: dict,
    events: list
) -> None:
    """
    Renders exam phase placeholder.
    SPACE simulates completing semester and advancing.
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

    hint = fonts["small"].render(
        "Press SPACE to advance semester  |  ESC to quit",
        True, DIM_COLOUR)
    screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                       SCREEN_HEIGHT - 40))

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                game_clock.check_semester_end_state()
                if session.get_is_frozen():
                    screen_mgr.queue_transition(ScreenState.ENDGAME)
                else:
                    game_clock.advance_semester()
                    screen_mgr.queue_transition(ScreenState.REGISTRATION)


def handle_endgame(
    screen: pygame.Surface,
    fonts: dict,
    events: list
) -> None:
    """
    Renders endgame placeholder.
    Saif's EndgameEvaluationManager and Nangiba's
    EndgameScreen integrate here in Sprint 3.
    """
    screen.fill((8, 8, 18))

    cx = SCREEN_WIDTH // 2

    title = fonts["title"].render(
        "Game Over", True, (255, 215, 70))
    screen.blit(title, (cx - title.get_width() // 2, 200))

    placeholder = fonts["body"].render(
        "[ Endgame evaluation and epilogue renders here ]",
        True, DIM_COLOUR)
    screen.blit(placeholder,
                (cx - placeholder.get_width() // 2, 300))

    hint = fonts["small"].render(
        "Press ESC to quit", True, DIM_COLOUR)
    screen.blit(hint, (cx - hint.get_width() // 2,
                       SCREEN_HEIGHT - 40))


# ── Main ──────────────────────────────────────────────────────────

def main() -> None:
    """
    Initialises Pygame, creates game systems, runs main loop.
    HUD renders on top of every screen except main menu.
    """
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
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

    # Fonts
    fonts = {
        "title": pygame.font.SysFont("Arial", 28, bold=True),
        "body":  pygame.font.SysFont("Arial", 16),
        "small": pygame.font.SysFont("Arial", 13),
    }

    # UI components
    hud = HUD()
    registration_screen = RegistrationScreen(SCREEN_WIDTH, SCREEN_HEIGHT)

    running = True

    while running:

        screen_mgr.apply_pending_transition()

        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        state = screen_mgr.get_current_state()

        if state == ScreenState.MAIN_MENU:
            handle_main_menu(screen, screen_mgr, fonts, events)

        elif state == ScreenState.REGISTRATION:
            handle_registration(
                screen, screen_mgr, session, registration_manager,
                registration_screen, full_catalog, events)

        elif state == ScreenState.EXPLORATION:
            handle_exploration(
                screen, screen_mgr, session, game_clock, fonts, events)

        elif state == ScreenState.EXAM:
            handle_exam(
                screen, screen_mgr, session, game_clock, fonts, events)

        elif state == ScreenState.ENDGAME:
            handle_endgame(screen, fonts, events)

        # HUD renders on top of every screen except main menu.
        # KNOWN COSMETIC ISSUE (Iteration 12): on Registration,
        # RegistrationScreen's card starts at y=24, slightly under
        # the 44px HUD strip — top border/corner marks get covered.
        # Not functional, just a layout overlap — flagging for
        # whoever does UI polish next.
        if state != ScreenState.MAIN_MENU:
            player = session.get_active_player()
            semester = session.get_active_semester()
            hud.render(
                screen,
                time_pool=semester.get_time_pool_days(),
                wallet=player.get_wallet_balance(),
                semester=semester.get_semester_number(),
                credits=player.get_accumulated_credits()
            )

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
"""
main.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
Entry point — Sprint 3 screen routing implementation.
Adds ScreenManager to route between game screens.
Each screen state delegates to its own handler function.
Asset and UI integration added as teammate branches merge.
─────────────────────────────────────────────────────────────
Sprint 3 — Abu Huraira (dev1-hurairiam-core)
"""

import sys
import pygame

from engine.game_session import GameSession
from engine.game_clock import GameClock
from engine.registration_manager import RegistrationManager
from engine.screen_manager import ScreenManager, ScreenState

# ── Constants ─────────────────────────────────────────────────────
SCREEN_WIDTH:  int = 1280
SCREEN_HEIGHT: int = 720
FPS:           int = 60
WINDOW_TITLE:  str = "CSE Life: Compile & Conquer"

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
    Renders the main menu and handles input.
    SPACE advances to registration screen.
    [Sprint 3 — placeholder until full menu art is added]
    """
    screen.fill(BG_COLOUR)

    title = fonts["title"].render(
        "CSE Life: Compile & Conquer", True, TEXT_COLOUR)
    sub = fonts["body"].render(
        "An OOP Lifecycle Simulation RPG", True, ACCENT_COLOUR)
    prompt = fonts["small"].render(
        "Press SPACE to begin", True, DIM_COLOUR)

    cx = SCREEN_WIDTH // 2
    screen.blit(title, (cx - title.get_width() // 2, 280))
    screen.blit(sub,   (cx - sub.get_width() // 2, 330))
    screen.blit(prompt, (cx - prompt.get_width() // 2, 420))

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                screen_mgr.queue_transition(ScreenState.REGISTRATION)


def handle_registration(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    session: GameSession,
    fonts: dict,
    events: list
) -> None:
    """
    Renders the registration screen placeholder.
    Nangiba's RegistrationScreen renders here in Sprint 3 integration.
    SPACE confirms registration and moves to exploration.
    [Sprint 3 — UI integration pending]
    """
    screen.fill((18, 20, 35))

    semester = session.get_active_semester()
    player = session.get_active_player()

    header = fonts["title"].render(
        f"Semester {semester.get_semester_number()} — Course Registration",
        True, TEXT_COLOUR)
    screen.blit(header, (40, 30))

    info = fonts["body"].render(
        f"Credits: {player.get_accumulated_credits()} / 140   "
        f"Wallet: {player.get_wallet_balance():,.0f} BDT",
        True, ACCENT_COLOUR)
    screen.blit(info, (40, 75))

    placeholder = fonts["body"].render(
        "[ Course catalog renders here — Nangiba's RegistrationScreen ]",
        True, DIM_COLOUR)
    screen.blit(placeholder,
                (SCREEN_WIDTH // 2 - placeholder.get_width() // 2,
                 SCREEN_HEIGHT // 2))

    hint = fonts["small"].render(
        "Press SPACE to confirm registration and begin semester",
        True, DIM_COLOUR)
    screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                       SCREEN_HEIGHT - 40))

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                screen_mgr.queue_transition(ScreenState.EXPLORATION)


def handle_exploration(
    screen: pygame.Surface,
    screen_mgr: ScreenManager,
    session: GameSession,
    game_clock: GameClock,
    fonts: dict,
    events: list
) -> None:
    """
    Renders the exploration phase placeholder.
    Checks the 15-day firewall every frame.
    E key simulates entering exam phase for testing.
    [Sprint 3 — map and NPC rendering pending]
    """
    screen.fill((20, 24, 38))

    semester = session.get_active_semester()

    # Check 15-day firewall
    if not game_clock.is_eligible_for_side_activities():
        screen_mgr.queue_transition(ScreenState.EXAM)
        return

    header = fonts["title"].render("Exploration Phase", True, TEXT_COLOUR)
    screen.blit(header, (40, 30))

    days_left = semester.get_time_pool_days()
    day_colour = (
        (70, 180, 70) if days_left > 30 else
        (220, 160, 40) if days_left > 15 else
        (210, 55, 55)
    )
    days_text = fonts["body"].render(
        f"Days remaining: {days_left} / 80", True, day_colour)
    screen.blit(days_text, (40, 75))

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
    Renders the exam phase placeholder.
    SPACE simulates completing a semester and advancing.
    [Sprint 3 — MainQuest pipeline integration pending]
    """
    screen.fill((25, 18, 35))

    semester = session.get_active_semester()

    header = fonts["title"].render("Exam Phase", True, TEXT_COLOUR)
    screen.blit(header, (40, 30))

    info = fonts["body"].render(
        f"Semester {semester.get_semester_number()}   "
        f"Days left: {semester.get_time_pool_days()}",
        True, ACCENT_COLOUR)
    screen.blit(info, (40, 75))

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
    Renders the endgame screen placeholder.
    Nangiba's EndgameScreen and Saif's EndgameEvaluationManager
    integrate here in Sprint 3.
    [Sprint 3 — pending integration]
    """
    screen.fill((8, 8, 18))

    title = fonts["title"].render("Game Over", True, (255, 215, 70))
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 200))

    placeholder = fonts["body"].render(
        "[ Endgame evaluation and epilogue renders here ]",
        True, DIM_COLOUR)
    screen.blit(placeholder,
                (SCREEN_WIDTH // 2 - placeholder.get_width() // 2, 300))

    hint = fonts["small"].render(
        "Press ESC to quit", True, DIM_COLOUR)
    screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                       SCREEN_HEIGHT - 40))


# ── Main ──────────────────────────────────────────────────────────

def main() -> None:
    """
    Initialises Pygame and runs the main game loop.
    ScreenManager routes each frame to the correct handler.
    """
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # Game systems
    session = GameSession()
    game_clock = GameClock(session)
    _registration_manager = RegistrationManager()
    screen_mgr = ScreenManager()

    # Fonts
    fonts = {
        "title": pygame.font.SysFont("Arial", 28, bold=True),
        "body":  pygame.font.SysFont("Arial", 16),
        "small": pygame.font.SysFont("Arial", 13),
    }

    running = True

    while running:

        # Apply any queued state transition from previous frame
        screen_mgr.apply_pending_transition()

        # Collect events once per frame
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # Route to correct screen handler
        state = screen_mgr.get_current_state()

        if state == ScreenState.MAIN_MENU:
            handle_main_menu(screen, screen_mgr, fonts, events)

        elif state == ScreenState.REGISTRATION:
            handle_registration(
                screen, screen_mgr, session, fonts, events)

        elif state == ScreenState.EXPLORATION:
            handle_exploration(
                screen, screen_mgr, session, game_clock, fonts, events)

        elif state == ScreenState.EXAM:
            handle_exam(
                screen, screen_mgr, session, game_clock, fonts, events)

        elif state == ScreenState.ENDGAME:
            handle_endgame(screen, fonts, events)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

"""
main.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
Entry point — Sprint 2 Pygame implementation.
Replaces the Sprint 1 boot check with a real game loop.

Sprint 2 goal: window opens, GameSession initialises,
60fps loop runs, ESC or close exits cleanly.

Screen state routing and asset loading added in Sprint 3
once teammate branches are integrated.
─────────────────────────────────────────────────────────────
Sprint 2 — Abu Huraira (dev1-hurairiam-core)
"""

import sys
import pygame

from engine.game_session import GameSession
from engine.game_clock import GameClock
from engine.registration_manager import RegistrationManager

# ── Constants ─────────────────────────────────────────────────────
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
FPS: int = 60
WINDOW_TITLE: str = "CSE Life: Compile & Conquer"

# ── Colours ───────────────────────────────────────────────────────
BG_COLOUR: tuple = (22, 22, 35)
HUD_COLOUR: tuple = (30, 30, 48)
TEXT_COLOUR: tuple = (200, 210, 255)
ACCENT_COLOUR: tuple = (80, 130, 200)


def main() -> None:
    """
    Main entry point. Initialises Pygame, creates the game session
    and clock, then runs the main loop until the player exits.
    """

    # ── Initialise Pygame ─────────────────────────────────────────
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    screen: pygame.Surface = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT)
    )
    clock: pygame.time.Clock = pygame.time.Clock()

    # ── Initialise Game Systems ───────────────────────────────────
    session: GameSession = GameSession()
    game_clock: GameClock = GameClock(session)
    registration_manager: RegistrationManager = RegistrationManager()

    font_title: pygame.font.Font = pygame.font.SysFont("Arial", 28, bold=True)
    font_body: pygame.font.Font = pygame.font.SysFont("Arial", 16)
    font_small: pygame.font.Font = pygame.font.SysFont("Arial", 13)

    # ── Main Loop ─────────────────────────────────────────────────
    running: bool = True

    while running:

        # ── Event Handling ────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # ── Update ────────────────────────────────────────────────
        # Session freeze check — stops loop if year cap hit
        if session.get_is_frozen():
            running = False

        player = session.get_active_player()
        semester = session.get_active_semester()

        # ── Render ────────────────────────────────────────────────
        screen.fill(BG_COLOUR)

        # Top status bar
        pygame.draw.rect(
            screen, HUD_COLOUR,
            pygame.Rect(0, 0, SCREEN_WIDTH, 48)
        )
        pygame.draw.line(
            screen, ACCENT_COLOUR,
            (0, 48), (SCREEN_WIDTH, 48), 1
        )

        # Game title — top left
        title_surf = font_title.render(
            "CSE Life: Compile & Conquer", True, TEXT_COLOUR
        )
        screen.blit(title_surf, (20, 10))

        # Semester info — top right
        sem_text = font_body.render(
            f"Semester {semester.get_semester_number()}   "
            f"Days: {semester.get_time_pool_days()} / 80   "
            f"Credits: {player.get_accumulated_credits()} / 140   "
            f"Wallet: {player.get_wallet_balance():,.0f} BDT",
            True, (160, 200, 255)
        )
        screen.blit(sem_text, (SCREEN_WIDTH - sem_text.get_width() - 20, 14))

        # Centre placeholder text
        placeholder = font_body.render(
            "Sprint 2 — Engine initialised. Screen routing coming in Sprint 3.",
            True, (100, 110, 140)
        )
        screen.blit(
            placeholder,
            (SCREEN_WIDTH // 2 - placeholder.get_width() // 2,
             SCREEN_HEIGHT // 2 - 10)
        )

        hint = font_small.render(
            "Press ESC to quit", True, (70, 75, 95)
        )
        screen.blit(
            hint,
            (SCREEN_WIDTH // 2 - hint.get_width() // 2,
             SCREEN_HEIGHT - 35)
        )

        # ── Flip ──────────────────────────────────────────────────
        pygame.display.flip()
        clock.tick(FPS)

    # ── Cleanup ───────────────────────────────────────────────────
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

"""
main.py — CSE Life: Compile & Conquer
Entry point only. All per-screen logic lives in engine/states/.
"""
import sys

import pygame

from engine.app_context import AppContext
from engine.state_router import StateRouter

SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
FPS: int = 60
WINDOW_TITLE: str = "CSE Life: Compile & Conquer"


def main() -> None:
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    ctx = AppContext(SCREEN_WIDTH, SCREEN_HEIGHT)
    router = StateRouter(ctx)

    while ctx.running:
        dt = clock.tick(FPS) / 1000.0
        ctx.playtime_seconds += dt

        ctx.screen_mgr.apply_pending_transition()
        router.sync()
        router.handle_events(pygame.event.get())
        router.update(dt)
        router.render(screen)

        pygame.display.flip()

    ctx.shutdown()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

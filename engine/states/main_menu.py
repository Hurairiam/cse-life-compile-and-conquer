"""Title screen. STAGE 3 replaces the body with ui/main_menu_screen.py."""
import pygame
from engine.screen_manager import ScreenState

BG = (22, 22, 35)
TEXT = (200, 210, 255)
ACCENT = (80, 130, 200)
DIM = (70, 75, 95)


def handle_events(ctx, events):
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                ctx.go(ScreenState.REGISTRATION)
            elif event.key == pygame.K_ESCAPE:
                ctx.quit()


def render(ctx, screen):
    screen.fill(BG)
    cx = ctx.screen_w // 2
    rows = ((ctx.fonts["title"], "CSE Life: Compile & Conquer", TEXT, 280),
            (ctx.fonts["body"], "An OOP Lifecycle Simulation RPG", ACCENT, 330),
            (ctx.fonts["small"], "Press SPACE to begin", DIM, 420))
    for font, text, colour, y in rows:
        surf = font.render(text, True, colour)
        screen.blit(surf, (cx - surf.get_width() // 2, y))

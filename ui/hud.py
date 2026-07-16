"""
Created by: Nangiba Tasnim (dev3)
This file contains NO game logic. It only draws the numbers
that are passed into render(). Abu Huraira's main loop calls render()
every frame and gives it the current values.
"""
from __future__ import annotations
import pygame


class HUD:
    __CAUTION_THRESHOLD: int = 30
    __FIREWALL_THRESHOLD: int = 15
    __MAX_DAYS: int = 80

    def __init__(self) -> None:
        self.__font: pygame.font.Font = pygame.font.SysFont("Arial", 16)

    def render(self, screen: pygame.Surface, time_pool: int,
               wallet: float, semester: int, credits: int) -> None:
        """
        Draw the whole HUD strip.

        screen    : the Pygame window we draw onto
        time_pool : days left in the semester (0-80)
        wallet    : money the player has, in BDT
        semester  : which semester the player is in
        credits   : credits earned so far (goal is 140)
        """
        screen_width: int = screen.get_width()

        # 1) The dark background strip across the top.
        pygame.draw.rect(screen, (15, 15, 25),
                         pygame.Rect(0, 0, screen_width, 42))

        # 2) The days bar.
        self.__draw_days_bar(screen, time_pool)

        # 3) The three text readouts: wallet, semester, credits.
        self.__draw_text(screen, f"Wallet: {wallet:,.0f} BDT",
                         240, (255, 215, 90))
        self.__draw_text(screen, f"Semester: {semester}",
                         470, (200, 200, 210))
        self.__draw_text(screen, f"Credits: {credits} / 140",
                         640, (160, 210, 255))

    def __draw_days_bar(self, screen: pygame.Surface,
                        time_pool: int) -> None:
        """
        Draw the coloured bar showing days left.
        Green when safe, amber when getting low, red when at the firewall.
        """
        # The empty grey bar (the "track" the fill sits inside).
        track = pygame.Rect(12, 11, 200, 20)
        pygame.draw.rect(screen, (45, 45, 60), track)

        # How much of the bar to fill, based on days left out of 80.
        fill_width: int = int(200 * time_pool / self.__MAX_DAYS)
        fill = pygame.Rect(12, 11, fill_width, 20)

        # Pick the colour based on how many days are left.
        if time_pool > self.__CAUTION_THRESHOLD:
            colour = (70, 180, 70)      # green  -- plenty of time
        elif time_pool > self.__FIREWALL_THRESHOLD:
            colour = (220, 160, 40)     # amber  -- getting low
        else:
            colour = (210, 55, 55)      # red    -- firewall active

        pygame.draw.rect(screen, colour, fill)

        # The "Days: 45 / 80" label sitting on top of the bar.
        label = self.__font.render(
            f"Days: {time_pool} / 80", True, (255, 255, 255))
        screen.blit(label, (16, 13))

    def __draw_text(self, screen: pygame.Surface, text: str,
                    x: int, colour: tuple) -> None:
        """A small helper so I don't repeat the same drawing code."""
        surface = self.__font.render(text, True, colour)
        screen.blit(surface, (x, 13))


# ---------------------------------------------------------------------
# STUB TEST -- this part is just so I can run the file on its own and
# see the HUD. Abu Huraira removes this when he plugs in the real game.
# Run this file to see three fake states: safe, caution, firewall.
# Press any key to switch between them.
# ---------------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()
    window = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("HUD test")
    hud = HUD()
    clock = pygame.time.Clock()

    fake_days = [45, 20, 8]   # green, amber, red
    index = 0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                index = (index + 1) % len(fake_days)   # switch state

        window.fill((30, 30, 40))          # plain background
        hud.render(window,
                   time_pool=fake_days[index],
                   wallet=15000.0,
                   semester=3,
                   credits=27)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

"""
ui/hud.py
CSE Life: Compile & Conquer
Created by: Nangiba Tasnim (dev4-ui-screens)

The HUD (Heads-Up Display) is the info strip across the top of the
screen during gameplay: days left, money, semester, and credits.

Style: neutral brown pastel, pixel font, with a small icon next to each
stat. Everything sits packed together on the left side of the strip.

This file has NO game logic. It only draws the numbers passed into
render(). Abu Huraira's main loop calls render() every frame and gives
it the current values. Icons and font load with a safety net, so the
game still runs even if an art file is missing.
"""
from __future__ import annotations
import pygame


# -------------------------------------------------------------
# COLOURS  (neutral brown pastel -- change any of these to restyle)
# Each colour is (Red, Green, Blue), each number from 0 to 255.
# -------------------------------------------------------------
PANEL_TAN   = (231, 214, 189)   # the strip background
BORDER_BROWN = (169, 130, 94)   # outline under the strip + around the bar
TEXT_COFFEE = (74, 53, 39)      # dark text so numbers stay readable
BAR_TRACK   = (214, 196, 168)   # empty part of the days bar

BAR_GREEN   = (167, 185, 133)   # days safe   (above 30)   -- soft sage
BAR_AMBER   = (217, 169, 106)   # days low    (16-30)      -- warm tan-gold
BAR_RED     = (199, 123, 107)   # days at firewall (15 or under) -- terracotta

PLACEHOLDER = (196, 178, 150)   # small square shown if an icon PNG is missing

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
STRIP_HEIGHT  = 44
ICON_SIZE     = 24
FONT_SIZE     = 10

START_X       = 10   # left edge where the first stat begins
GAP           = 22   # space between one stat and the next
ICON_TEXT_GAP = 6    # space between an icon and its text
BAR_WIDTH     = 84
BAR_HEIGHT    = 16


class HUD:
    """
    Persistent neutral-pastel status bar shown during gameplay.

    It never fetches its own data -- every number it draws is handed in
    through render(). That keeps my visual code fully separate from the
    game logic my teammates write (separation of concerns). The stats
    are drawn one after another, left to right, packed to the left.
    """

    def __init__(self) -> None:
        """Load the pixel font and the four stat icons once, up front."""
        self.__font: pygame.font.Font = self.__load_font()
        # A small dictionary: stat name -> its icon image (or None).
        self.__icons: dict[str, pygame.Surface | None] = {
            "days":     self.__load_icon("assets/ui/icon_days.png"),
            "wallet":   self.__load_icon("assets/ui/icon_wallet.png"),
            "semester": self.__load_icon("assets/ui/icon_semester.png"),
            "credits":  self.__load_icon("assets/ui/icon_credits.png"),
        }

    # -- loading helpers --------------------------------------
    def __load_font(self) -> pygame.font.Font:
        """
        Try to load the cute pixel font. If the file isn't there yet,
        fall back to a chunky built-in font so nothing crashes.
        """
        try:
            return pygame.font.Font("assets/ui/PressStart2P.ttf", FONT_SIZE)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", FONT_SIZE + 3, bold=True)

    def __load_icon(self, path: str) -> pygame.Surface | None:
        """
        Load one icon PNG and shrink it to icon size. Returns None if the
        file is missing -- the HUD then draws a placeholder square instead.
        """
        try:
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(image, (ICON_SIZE, ICON_SIZE))
        except (FileNotFoundError, OSError, pygame.error):
            return None

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, time_pool: int,
               wallet: float, semester: int, credits: int) -> None:
        """
        Draw the whole HUD strip.
        time_pool : days left (0-80)     wallet : money in BDT
        semester  : current semester     credits: credits earned (goal 140)
        """
        width: int = screen.get_width()

        # 1) tan background strip + its bottom outline
        pygame.draw.rect(screen, PANEL_TAN,
                         pygame.Rect(0, 0, width, STRIP_HEIGHT))
        pygame.draw.rect(screen, BORDER_BROWN,
                         pygame.Rect(0, STRIP_HEIGHT - 4, width, 4))

        # 2) the four stats, drawn left to right. Each helper returns the
        #    x position where the NEXT stat should start, so they pack
        #    tightly together instead of being spread across the screen.
        x = START_X
        x = self.__draw_days(screen, time_pool, x) + GAP
        x = self.__draw_stat(screen, "wallet",   f"{wallet:,.0f}",  x) + GAP
        x = self.__draw_stat(screen, "semester", f"Sem {semester}", x) + GAP
        x = self.__draw_stat(screen, "credits",  f"{credits}/140",  x)

    # -- piece-by-piece drawing -------------------------------
    def __draw_days(self, screen: pygame.Surface, time_pool: int,
                    x: int) -> int:
        """
        Draw the days icon, the colour-changing bar, and the number.
        Returns the x position just past the number.
        """
        self.__draw_icon(screen, "days", x)

        bar_x = x + ICON_SIZE + ICON_TEXT_GAP
        bar_y = (STRIP_HEIGHT - BAR_HEIGHT) // 2
        track = pygame.Rect(bar_x, bar_y, BAR_WIDTH, BAR_HEIGHT)
        pygame.draw.rect(screen, BAR_TRACK, track)

        # how full the bar is, based on days left out of 80
        fill_width = int(BAR_WIDTH * time_pool / 80)
        fill = pygame.Rect(bar_x, bar_y, fill_width, BAR_HEIGHT)

        # pick the colour from how many days remain
        if time_pool > 30:
            colour = BAR_GREEN
        elif time_pool > 15:
            colour = BAR_AMBER
        else:
            colour = BAR_RED

        pygame.draw.rect(screen, colour, fill)
        pygame.draw.rect(screen, BORDER_BROWN, track, 2)   # bar outline

        number_x = bar_x + BAR_WIDTH + ICON_TEXT_GAP
        self.__draw_text(screen, str(time_pool), number_x)
        return number_x + self.__font.size(str(time_pool))[0]

    def __draw_stat(self, screen: pygame.Surface, icon_key: str,
                    text: str, x: int) -> int:
        """
        Draw one icon followed by its text (wallet / semester / credits).
        Returns the x position just past the text.
        """
        self.__draw_icon(screen, icon_key, x)
        text_x = x + ICON_SIZE + ICON_TEXT_GAP
        self.__draw_text(screen, text, text_x)
        return text_x + self.__font.size(text)[0]

    def __draw_icon(self, screen: pygame.Surface, icon_key: str,
                    x: int) -> None:
        """Blit the icon image, or a placeholder square if it's missing."""
        y = (STRIP_HEIGHT - ICON_SIZE) // 2
        icon = self.__icons[icon_key]
        if icon is not None:
            screen.blit(icon, (x, y))
        else:
            pygame.draw.rect(screen, PLACEHOLDER,
                             pygame.Rect(x, y, ICON_SIZE, ICON_SIZE))

    def __draw_text(self, screen: pygame.Surface, text: str, x: int) -> None:
        """Draw text vertically centred in the strip."""
        surface = self.__font.render(text, True, TEXT_COFFEE)
        y = (STRIP_HEIGHT - self.__font.get_height()) // 2
        screen.blit(surface, (x, y))


# -------------------------------------------------------------
# STUB TEST -- lets me run this file on its own to see the HUD.
# Abu Huraira removes this block when he plugs in the real game.
# Press any key to cycle days: 45 (green) -> 20 (amber) -> 8 (red).
# -------------------------------------------------------------
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

        window.fill((203, 191, 166))       # neutral background
        hud.render(window,
                   time_pool=fake_days[index],
                   wallet=15000.0,
                   semester=3,
                   credits=27)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
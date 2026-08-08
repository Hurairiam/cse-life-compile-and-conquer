"""
CSE Life: Compile & Conquer
Created by: Nangiba Tasnim (Dev 3)

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

PANEL_TAN   = (231, 214, 189)   # the strip background+
BORDER_BROWN = (169, 130, 94)   # outline under the strip + around the bar
TEXT_COFFEE = (74, 53, 39)      # dark text so numbers stay readable
BAR_TRACK   = (214, 196, 168)   # empty part of the days bar

BAR_GREEN   = (167, 185, 133)   # days safe   (above 30)   -- soft sage
BAR_AMBER   = (217, 169, 106)   # days low    (16-30)      -- warm tan-gold
BAR_RED     = (199, 123, 107)   # days at firewall (15 or under) -- terracotta

PLACEHOLDER = (196, 178, 150)   # small square shown if an icon PNG is missing

WARN_FILL   = BAR_RED           # the low-days chip: same terracotta as the bar
WARN_TEXT   = (255, 246, 232)   # near-white, so the words read on the fill

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

LOCATION_PAD   = 12  # gap between the location label and the right edge
LOCATION_MIN_W = 40  # below this much free space the label is dropped

WARN_HEIGHT   = 22   # the low-days chip
WARN_PAD_X    = 8    # breathing room either side of its text
WARN_BORDER_W = 2


class HUD:
    """
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
        Try to load the chosen pixel font. If the file isn't there yet,
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
               wallet: float, semester: int, credits: int,
               location: str = "", low_days: int | None = None) -> None:
        """
        Draw the whole HUD strip.
        time_pool : days left (0-80)     wallet : money in BDT
        semester  : current semester     credits: credits earned (goal 140)
        location  : where the player is, drawn right-aligned ("" = hidden)
        low_days  : days left once the semester is running out, or None
                    to draw no warning chip at all

        `location` and `low_days` are both optional so every existing
        caller keeps working unchanged.

        `low_days` is None-or-a-number rather than a plain int because a
        semester can genuinely run down to ZERO days, and that is the
        moment the chip matters most -- 0 has to mean "no days left",
        never "nothing to say". Whether the count is low enough to show
        is not decided here: like every other number on this strip it is
        handed in (engine/day_warning.py decides), because the HUD never
        fetches its own data.
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
        x = self.__draw_stat(screen, "wallet",   f"{wallet:,.0f} BDT", x) + GAP
        x = self.__draw_stat(screen, "semester", f"Sem {semester}", x) + GAP
        x = self.__draw_stat(screen, "credits",  f"{credits}/140",  x)

        # 2b) the end-of-semester warning, in the same left run so it
        #     reads as part of the numbers rather than as decoration.
        #     It only exists near the end of a term, so it takes room
        #     from the location label (which already gives way) instead
        #     of being given a permanent slot that is empty all game.
        if low_days is not None:
            x = self.__draw_low_days(screen, low_days, x + GAP)

        # 3) the location, packed against the RIGHT edge. The stats grow
        #    rightwards as the numbers get longer (140/140, 200,000 BDT),
        #    so it is clipped to whatever room is left rather than
        #    allowed to collide with them.
        if location:
            self.__draw_location(screen, location, width, x)

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
        days_text = f"{time_pool}/80"
        self.__draw_text(screen, days_text, number_x)
        return number_x + self.__font.size(days_text)[0]

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

    def __draw_low_days(self, screen: pygame.Surface, days: int,
                        x: int) -> int:
        """
        Draw the "N DAYS LEFT" chip and return the x just past it.

        A filled terracotta pill rather than a fifth icon-and-number
        stat: the four stats are things that are always true, and this
        is an alarm. Same red the days bar turns, so the two read as one
        statement and not as two different warnings.

        No icon -- assets/ui/ has none for this and a PLACEHOLDER square
        inside an alarm chip would look like a bug, so the words carry
        it. The strip is 44 px and the chip is 22, centred in it.
        """
        text = "%d DAY%s LEFT" % (days, "" if days == 1 else "S")
        text_w = self.__font.size(text)[0]
        chip = pygame.Rect(x, (STRIP_HEIGHT - WARN_HEIGHT) // 2,
                           text_w + WARN_PAD_X * 2, WARN_HEIGHT)
        pygame.draw.rect(screen, WARN_FILL, chip)
        pygame.draw.rect(screen, BORDER_BROWN, chip, WARN_BORDER_W)
        surface = self.__font.render(text, True, WARN_TEXT)
        screen.blit(surface, (chip.x + WARN_PAD_X,
                              chip.y + (WARN_HEIGHT
                                        - self.__font.get_height()) // 2))
        return chip.right

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

    def __draw_location(self, screen: pygame.Surface, location: str,
                        width: int, stats_end_x: int) -> None:
        """
        Draw where the player is, right-aligned against the strip edge.

        Underscores become spaces and a bare slug is title-cased, so a
        level whose name was never filled in ("campus_library") still
        reads as "Indoor Library" instead of shouting its filename.
        A properly authored name ("Cafeteria & Lecture Hall") already
        has spaces and is left exactly as written.

        `stats_end_x` is where the numbers finish. The label is clipped
        to the gap after it rather than overlapping: the stats widen as
        the save progresses (200,000 BDT, 140/140) and the label must
        give way, never the numbers.
        """
        text = location.strip()
        if "_" in text or text.islower():
            text = text.replace("_", " ").title()

        available = width - LOCATION_PAD - stats_end_x - GAP
        if available < LOCATION_MIN_W:
            return
        while text and self.__font.size(text)[0] > available:
            text = text[:-1]
        if not text:
            return

        text_width = self.__font.size(text)[0]
        self.__draw_text(screen, text, width - LOCATION_PAD - text_width)


# -------------------------------------------------------------
# STUB TEST -- lets me run this file on its own to see the HUD.
# Abu Huraira removes this block when he plugs in the real game.
#   Press any key  -> cycle days: 45 (green) -> 20 (amber) -> 8 (red)
#                     8 and 0 also raise the "N DAYS LEFT" warning chip
#   Press F11      -> toggle windowed / fullscreen
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS   = pygame.SCALED                     # crisp scaling for pixel art
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("HUD test")
    hud = HUD()
    clock = pygame.time.Clock()

    fake_days = [45, 20, 8, 0]   # green, amber, red, and the floor
    index = 0
    WARN_AT = 15                 # engine/day_warning.py's own source is
    #                              GameClock.get_min_border(); this stub
    #                              has no clock, so it names the number.

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    # flip between windowed and fullscreen
                    is_fullscreen = not is_fullscreen
                    flags = FULLSCREEN_FLAGS if is_fullscreen else WINDOWED_FLAGS
                    window = pygame.display.set_mode(SIZE, flags)
                else:
                    index = (index + 1) % len(fake_days)   # switch colour state

        window.fill((203, 191, 166))       # neutral background
        days = fake_days[index]
        hud.render(window,
                   time_pool=days,
                   wallet=0.0,
                   semester=1,
                   credits=0,
                   location="campus_main",
                   low_days=days if days <= WARN_AT else None)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
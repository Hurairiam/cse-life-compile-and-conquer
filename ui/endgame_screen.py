"""
CSE Life: Compile & Conquer
Created by: Nangiba Tasnim (Dev 3)

The Endgame Screen is the final card the player sees, laid out like a
certificate: a framed panel with corner marks, the ending title, the
player's ID photo, a boxed stat block with a credit progress bar, and
the epilogue text written by Ayesha.

Each ending gets its own accent colour:
    TOP GRADUATE            -- dark + gold, the dramatic one
    AVERAGE GRADUATE        -- tan + bronze
    DROP OUT Strong Skills  -- tan + slate blue
    DROP OUT Weak Skills    -- tan + muted red

This file has NO game logic. render() only DRAWS what it is handed --
the ending title, the epilogue lines, and the final numbers. Abu
Huraira's EndgameEvaluationManager decides those values. The theme is
picked from the title, so render() keeps his original signature.

Base render() from Abu Huraira (engine). Themes, layout + test by Nangiba.
"""
from __future__ import annotations
import pygame

# -- shared colours -------------------------------------------
PANEL_TAN     = (231, 214, 189)   # tan background (3 of the 4 endings)
CARD_TAN      = (240, 228, 208)   # the certificate panel, lighter than bg
TEXT_COFFEE   = (74, 53, 39)      # body text on tan
STAT_BROWN    = (140, 110, 85)    # secondary text on tan
BAR_TRACK_TAN = (214, 196, 168)   # empty part of the credit bar on tan

DARK_BG       = (18, 16, 22)      # TOP GRADUATE background
DARK_CARD     = (28, 26, 34)      # TOP GRADUATE panel
DARK_TEXT     = (225, 220, 210)   # body text on dark
DARK_STAT     = (150, 145, 155)   # secondary text on dark
BAR_TRACK_DK  = (52, 48, 60)      # empty part of the credit bar on dark

PORTRAIT_BG   = (255, 255, 255)   # white behind the photo
PORTRAIT_FILL = (190, 165, 135)   # placeholder if the photo is missing

CREDIT_GOAL   = 140               # the graduation target

# -- one theme per ending -------------------------------------
THEMES: dict[str, dict] = {
    "TOP GRADUATE": {
        "bg": DARK_BG, "card": DARK_CARD, "accent": (255, 215, 90),
        "body": DARK_TEXT, "stat": DARK_STAT, "track": BAR_TRACK_DK,
        "subtitle": "FINAL EVALUATION  --  WITH DISTINCTION",
    },
    "AVERAGE GRADUATE": {
        "bg": PANEL_TAN, "card": CARD_TAN, "accent": (170, 120, 60),
        "body": TEXT_COFFEE, "stat": STAT_BROWN, "track": BAR_TRACK_TAN,
        "subtitle": "FINAL EVALUATION  --  DEGREE CONFERRED",
    },
    "DROP OUT Strong Skills": {
        "bg": PANEL_TAN, "card": CARD_TAN, "accent": (45, 58, 71),
        "body": TEXT_COFFEE, "stat": STAT_BROWN, "track": BAR_TRACK_TAN,
        "subtitle": "FINAL EVALUATION  --  NO DEGREE AWARDED",
    },
    "DROP OUT Weak Skills": {
        "bg": PANEL_TAN, "card": CARD_TAN, "accent": (160, 90, 80),
        "body": TEXT_COFFEE, "stat": STAT_BROWN, "track": BAR_TRACK_TAN,
        "subtitle": "FINAL EVALUATION  --  NO DEGREE AWARDED",
    },
}
DEFAULT_THEME = THEMES["AVERAGE GRADUATE"]   # used if a title is unknown

PORTRAIT_PATH = "assets/portraits/player_id.png"

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
CARD_MARGIN   = 46          # gap between screen edge and the card
CARD_PAD      = 18          # gap between the card and its inner border
CORNER_LEN    = 26          # length of each corner mark arm

TITLE_Y       = 82
SUBTITLE_Y    = 122
RULE_TOP_Y    = 148
PORTRAIT_SIZE = 150
PORTRAIT_Y    = 172

STATS_Y       = 340         # top of the stat box
STATS_W       = 520
STATS_H       = 104
BAR_H         = 14

RULE_BOT_Y    = 470
FIRST_LINE_Y  = 496
LINE_PITCH    = 32
HINT_Y        = 644

TITLE_SIZE    = 26
SUB_SIZE      = 11
BODY_SIZE     = 13
STAT_SIZE     = 12
LABEL_SIZE    = 10


class EndgameScreen:
    """
    Draws the final epilogue card as a framed certificate. It never
    fetches its own data -- render() is handed the ending title,
    epilogue lines, and final stats, keeping visuals separate from the
    game logic. The colour theme is chosen from the ending title, so
    the method signature stays the same as the engine's original.
    """

    def __init__(self) -> None:
        """Load the fonts and the player's ID photo once, up front."""
        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_sub: pygame.font.Font = self.__load_font(SUB_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_stat: pygame.font.Font = self.__load_font(STAT_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)
        self.__portrait: pygame.Surface | None = self.__load_portrait()

    # -- loading helpers --------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font("assets/ui/PressStart2P.ttf", size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    def __load_portrait(self) -> pygame.Surface | None:
        """
        Load the player's ID photo at portrait size.
        Returns None if the file isn't there -- a placeholder block is
        drawn instead so the screen never crashes.
        """
        try:
            image = pygame.image.load(PORTRAIT_PATH).convert_alpha()
            return pygame.transform.scale(
                image, (PORTRAIT_SIZE, PORTRAIT_SIZE))
        except (FileNotFoundError, OSError, pygame.error):
            return None

    def __theme_for(self, epilogue_title: str) -> dict:
        """Pick the colour theme that matches this ending."""
        return THEMES.get(epilogue_title, DEFAULT_THEME)

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, epilogue_title: str,
               epilogue_lines: list[str], final_credits: int,
               final_wallet: float) -> None:
        """
        Draw the whole endgame screen.
        epilogue_title : which of the four endings was reached
        epilogue_lines : the epilogue text, one string per line
        final_credits  : credits the player finished with
        final_wallet   : money the player finished with, in BDT
        """
        theme = self.__theme_for(epilogue_title)
        cx = screen.get_width() // 2
        screen.fill(theme["bg"])

        self.__draw_card(screen, theme)

        self.__blit_centred(screen, self.__font_title, epilogue_title,
                            theme["accent"], cx, TITLE_Y)
        self.__blit_centred(screen, self.__font_sub, theme["subtitle"],
                            theme["stat"], cx, SUBTITLE_Y)

        self.__draw_rule(screen, cx, RULE_TOP_Y, theme["accent"])
        self.__draw_portrait(screen, cx, theme["accent"])
        self.__draw_stat_box(screen, cx, final_credits, final_wallet, theme)
        self.__draw_rule(screen, cx, RULE_BOT_Y, theme["accent"])

        for i, line in enumerate(epilogue_lines):
            self.__blit_centred(screen, self.__font_body, line,
                                theme["body"], cx,
                                FIRST_LINE_Y + i * LINE_PITCH)

        self.__blit_centred(screen, self.__font_label, "Press ESC to exit",
                            theme["stat"], cx, HINT_Y)

    # -- piece-by-piece drawing -------------------------------
    def __draw_card(self, screen: pygame.Surface, theme: dict) -> None:
        """Draw the certificate panel, its inner border, and corner marks."""
        card = pygame.Rect(CARD_MARGIN, CARD_MARGIN,
                           screen.get_width() - CARD_MARGIN * 2,
                           screen.get_height() - CARD_MARGIN * 2)
        pygame.draw.rect(screen, theme["card"], card)
        pygame.draw.rect(screen, theme["accent"], card, 3)

        inner = card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
        pygame.draw.rect(screen, theme["stat"], inner, 1)

        self.__draw_corners(screen, inner, theme["accent"])

    def __draw_corners(self, screen: pygame.Surface, rect: pygame.Rect,
                       colour: tuple) -> None:
        """Draw short bracket marks at each corner of the inner border."""
        n = CORNER_LEN
        corners = [
            ((rect.left, rect.top), (n, 0), (0, n)),        # top-left
            ((rect.right, rect.top), (-n, 0), (0, n)),      # top-right
            ((rect.left, rect.bottom), (n, 0), (0, -n)),    # bottom-left
            ((rect.right, rect.bottom), (-n, 0), (0, -n)),  # bottom-right
        ]
        for (px, py), (dx1, dy1), (dx2, dy2) in corners:
            pygame.draw.line(screen, colour, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, colour, (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_rule(self, screen: pygame.Surface, cx: int, y: int,
                    colour: tuple) -> None:
        """Draw a centred horizontal divider with a small diamond mid-way."""
        half = 300
        pygame.draw.line(screen, colour, (cx - half, y), (cx - 14, y), 2)
        pygame.draw.line(screen, colour, (cx + 14, y), (cx + half, y), 2)
        pygame.draw.polygon(screen, colour,
                            [(cx, y - 6), (cx + 7, y), (cx, y + 6),
                             (cx - 7, y)])

    def __draw_portrait(self, screen: pygame.Surface, cx: int,
                        frame_colour: tuple) -> None:
        """Draw the ID photo (or a placeholder) centred under the title."""
        box = pygame.Rect(cx - PORTRAIT_SIZE // 2, PORTRAIT_Y,
                          PORTRAIT_SIZE, PORTRAIT_SIZE)
        if self.__portrait is not None:
            pygame.draw.rect(screen, PORTRAIT_BG, box)   # white backdrop
            screen.blit(self.__portrait, (box.x, box.y))
        else:
            pygame.draw.rect(screen, PORTRAIT_FILL, box)
        pygame.draw.rect(screen, frame_colour, box, 3)

    def __draw_stat_box(self, screen: pygame.Surface, cx: int,
                        credits: int, wallet: float, theme: dict) -> None:
        """Draw the boxed stat block: credit bar on the left, wallet right."""
        box = pygame.Rect(cx - STATS_W // 2, STATS_Y, STATS_W, STATS_H)
        pygame.draw.rect(screen, theme["track"], box, 0, border_radius=2)
        pygame.draw.rect(screen, theme["stat"], box, 1)

        # divider between the two halves
        mid_x = box.centerx
        pygame.draw.line(screen, theme["stat"],
                         (mid_x, box.top + 12), (mid_x, box.bottom - 12), 1)

        # left half -- credits, with a progress bar
        left_x = box.left + 24
        screen.blit(self.__font_label.render("CREDITS", True, theme["stat"]),
                    (left_x, box.top + 16))
        screen.blit(self.__font_stat.render(
            f"{credits} / {CREDIT_GOAL}", True, theme["body"]),
            (left_x, box.top + 38))

        bar_w = (STATS_W // 2) - 48
        bar = pygame.Rect(left_x, box.top + 70, bar_w, BAR_H)
        pygame.draw.rect(screen, theme["bg"], bar)
        filled = int(bar_w * min(credits / CREDIT_GOAL, 1.0))
        if filled > 0:
            pygame.draw.rect(screen, theme["accent"],
                             pygame.Rect(bar.x, bar.y, filled, BAR_H))
        pygame.draw.rect(screen, theme["stat"], bar, 1)

        # right half -- wallet
        right_x = mid_x + 24
        screen.blit(self.__font_label.render("WALLET", True, theme["stat"]),
                    (right_x, box.top + 16))
        screen.blit(self.__font_stat.render(
            f"{wallet:,.0f}", True, theme["body"]),
            (right_x, box.top + 38))
        screen.blit(self.__font_label.render("BDT", True, theme["stat"]),
                    (right_x, box.top + 72))

    def __blit_centred(self, screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: tuple, centre_x: int,
                       y: int) -> None:
        """Draw a line of text horizontally centred on centre_x."""
        surface = font.render(text, True, colour)
        screen.blit(surface, (centre_x - surface.get_width() // 2, y))


# -------------------------------------------------------------
# STUB TEST -- lets me run this file on its own to see the screen.
# Abu Huraira removes this block when he plugs in the real game.
#   Any key -> cycle through all four endings
#   F11     -> toggle windowed / fullscreen
#   ESC     -> quit
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS   = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Endgame screen test")
    endgame = EndgameScreen()
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 14)

    # fake endings: (title, lines, credits, wallet)
    endings = [
        ("TOP GRADUATE",
         ["You crossed the line with credits to spare.",
          "Three offers landed before you updated your CV.",
          "Every 80-day sprint was worth it."],
         143, 48200.0),
        ("AVERAGE GRADUATE",
         ["You made it. Barely, but you made it.",
          "The degree is real. The rest you'll figure out.",
          "Somewhere, a hiring manager is reading your name."],
         140, 9400.0),
        ("DROP OUT Strong Skills",
         ["No degree. But you can build almost anything.",
          "The clients don't ask which semester you left.",
          "You taught yourself what the syllabus skipped."],
         96, 31500.0),
        ("DROP OUT Weak Skills",
         ["The clock ran out before the credits did.",
          "There were semesters you meant to fix.",
          "Some stories end mid-sentence."],
         62, 1200.0),
    ]
    index = 0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    flags = (FULLSCREEN_FLAGS if is_fullscreen
                             else WINDOWED_FLAGS)
                    window = pygame.display.set_mode(SIZE, flags)
                else:
                    index = (index + 1) % len(endings)   # next ending

        title, lines, credits, wallet = endings[index]
        endgame.render(window, title, lines, credits, wallet)

        hint = hint_font.render(
            "Any key = next ending  |  F11 fullscreen  |  ESC quit",
            True, (120, 110, 100))
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
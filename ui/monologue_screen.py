"""
ui/monologue_screen.py
CSE Life: Compile & Conquer
Created by: Nangiba Tasnim (Dev 3)

Two things live here:

1. MonologueScreen -- a PURE renderer. Given a semester number, the days
   on the clock, the lines to show so far, and whether the "continue"
   hint should blink, it draws the framed monologue card. No game logic,
   no state of its own.

2. MonologueController -- a tiny state helper that runs the typewriter
   effect (revealing text a few characters at a time) and tracks which
   line we are on. The main loop drives it with start()/update()/advance()
   and reads back visible_lines()/is_done(). Pulling this state out of
   main.py keeps Abu Huraira's file thin -- he only calls a handful of
   methods here instead of hand-managing indices and timers.

Both are import-clean (only pygame). The actual monologue TEXT comes from
content/monologues.py (get_monologue), which the main loop looks up and
feeds into the controller -- this file never reaches for it itself.
"""
from __future__ import annotations

import os

import pygame

PANEL_TAN = (231, 214, 189)
CARD_TAN = (240, 228, 208)
BORDER_BROWN = (169, 130, 94)
TEXT_COFFEE = (74, 53, 39)
TITLE_SLATE = (45, 58, 71)
CREDIT_HL = (155, 110, 70)
STAT_BROWN = (140, 110, 85)
BAR_AMBER = (217, 169, 106)

TYPEWRITER_CPS = 30      # characters revealed per second

FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "ui", "PressStart2P.ttf")

CARD_MARGIN = 46
CARD_PAD = 18
CORNER_LEN = 26

TITLE_Y = 120
SUBTITLE_Y = 166
RULE_Y = 200
RULE_HALF = 300

FIRST_LINE_Y = 268
LINE_PITCH = 32

HINT_Y = 570
ARROW_Y = 606
ARROW_HALF_W = 8
ARROW_H = 9
ARROW_BOB = 3
ARROW_PERIOD_MS = 420

TITLE_SIZE = 26
SUB_SIZE = 11
BODY_SIZE = 13
LABEL_SIZE = 10

HINT_TEXT = "PRESS ANY KEY TO CONTINUE"


class MonologueController:
    """
    Runs the typewriter animation for one semester's monologue and tracks
    reading progress. Holds no Pygame surfaces -- it is pure state, safe
    to keep alive across frames in the main loop.

    Usage from the main loop:
        controller.start(semester_number, lines)   # once, on entering
        controller.update(dt)                       # every frame
        controller.advance()                        # on key/click
        controller.visible_lines()                  # feed into render()
        controller.is_done()                        # all lines revealed?
    """

    def __init__(self) -> None:
        self.__semester: int | None = None
        self.__lines: list[str] = []
        self.__line_index: int = 0
        self.__revealed: float = 0.0     # chars shown of the current line
        self.__done: bool = False

    def start(self, semester_number: int, lines: list[str]) -> None:
        """Begin a fresh monologue for the given semester."""
        self.__semester = semester_number
        # Guard against an empty list so indexing is always safe.
        self.__lines = list(lines) if lines else [""]
        self.__line_index = 0
        self.__revealed = 0.0
        self.__done = False

    def is_started_for(self, semester_number: int) -> bool:
        """True if this controller is already running that semester's text."""
        return self.__semester == semester_number

    def update(self, dt: float) -> None:
        """
        Reveal more characters based on elapsed time dt (seconds).
        Marks the whole monologue done once the last line is fully shown.
        """
        if self.__done or not self.__lines:
            return
        current_len = len(self.__lines[self.__line_index])
        self.__revealed = min(self.__revealed + TYPEWRITER_CPS * dt,
                              float(current_len))
        if (self.__line_index == len(self.__lines) - 1
                and self.__revealed >= current_len):
            self.__done = True

    def advance(self) -> None:
        """
        Player pressed a key / clicked:
        - if the current line is still typing, finish it instantly
        - else move to the next line
        - on the last line, mark the monologue done
        """
        if self.__done or not self.__lines:
            return
        current = self.__lines[self.__line_index]
        if self.__revealed < len(current):
            self.__revealed = float(len(current))
        elif self.__line_index < len(self.__lines) - 1:
            self.__line_index += 1
            self.__revealed = 0.0
        else:
            self.__done = True

    def is_done(self) -> bool:
        """True once every line has been fully revealed."""
        return self.__done

    def visible_lines(self) -> list[str]:
        """
        The lines to draw right now: every finished line in full, plus the
        current line truncated to however many characters have been typed.
        """
        if not self.__lines:
            return []
        shown = self.__lines[:self.__line_index]
        shown.append(self.__lines[self.__line_index][:int(self.__revealed)])
        return shown

    def reset(self) -> None:
        """Forget the current semester so the next start() always runs."""
        self.__semester = None
        self.__lines = []
        self.__line_index = 0
        self.__revealed = 0.0
        self.__done = False


class MonologueScreen:

    def __init__(self) -> None:
        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_sub: pygame.font.Font = self.__load_font(SUB_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)

    def __load_font(self, size: int) -> pygame.font.Font:
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    def render(self, screen: pygame.Surface, semester_number: int,
               time_pool: int, visible_lines: list[str],
               hint_visible: bool) -> None:
        screen.fill(PANEL_TAN)
        self.__draw_card(screen)

        cx = screen.get_width() // 2
        self.__blit_centred(screen, self.__font_title,
                            f"SEMESTER {semester_number}", TITLE_SLATE,
                            cx, TITLE_Y)
        self.__blit_centred(screen, self.__font_sub,
                            f"{time_pool} DAYS ON THE CLOCK", CREDIT_HL,
                            cx, SUBTITLE_Y)
        self.__draw_rule(screen, cx, RULE_Y)

        for i, line in enumerate(visible_lines):
            self.__blit_centred(screen, self.__font_body, line, TEXT_COFFEE,
                                cx, FIRST_LINE_Y + i * LINE_PITCH)

        if hint_visible:
            self.__blit_centred(screen, self.__font_label, HINT_TEXT,
                                STAT_BROWN, cx, HINT_Y)
            self.__draw_continue_arrow(screen, cx)

    def __draw_card(self, screen: pygame.Surface) -> None:
        card = pygame.Rect(CARD_MARGIN, CARD_MARGIN,
                           screen.get_width() - CARD_MARGIN * 2,
                           screen.get_height() - CARD_MARGIN * 2)
        pygame.draw.rect(screen, CARD_TAN, card)
        pygame.draw.rect(screen, BORDER_BROWN, card, 3)

        inner = card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
        pygame.draw.rect(screen, BORDER_BROWN, inner, 1)
        self.__draw_corners(screen, inner)

    def __draw_corners(self, screen: pygame.Surface,
                       rect: pygame.Rect) -> None:
        n = CORNER_LEN
        corners = [
            ((rect.left, rect.top), (n, 0), (0, n)),
            ((rect.right, rect.top), (-n, 0), (0, n)),
            ((rect.left, rect.bottom), (n, 0), (0, -n)),
            ((rect.right, rect.bottom), (-n, 0), (0, -n)),
        ]
        for (px, py), (dx1, dy1), (dx2, dy2) in corners:
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_rule(self, screen: pygame.Surface, cx: int, y: int) -> None:
        pygame.draw.line(screen, BORDER_BROWN,
                         (cx - RULE_HALF, y), (cx - 14, y), 2)
        pygame.draw.line(screen, BORDER_BROWN,
                         (cx + 14, y), (cx + RULE_HALF, y), 2)
        pygame.draw.polygon(screen, BORDER_BROWN,
                            [(cx, y - 6), (cx + 7, y), (cx, y + 6),
                             (cx - 7, y)])

    def __draw_continue_arrow(self, screen: pygame.Surface, cx: int) -> None:
        step = (pygame.time.get_ticks() // ARROW_PERIOD_MS) % 2
        y = ARROW_Y + (ARROW_BOB if step else 0)
        pygame.draw.polygon(screen, BAR_AMBER,
                            [(cx - ARROW_HALF_W, y),
                             (cx + ARROW_HALF_W, y),
                             (cx, y + ARROW_H)])

    def __blit_centred(self, screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: tuple, centre_x: int,
                       y: int) -> None:
        surface = font.render(text, True, colour)
        screen.blit(surface, (centre_x - surface.get_width() // 2, y))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see the monologue.
# Now driven by MonologueController, exactly like the real main loop.
#   SPACE / click -> advance     R -> next semester's text
#   F11 -> fullscreen            ESC -> quit
# -------------------------------------------------------------
if __name__ == "__main__":

    FAKE_MONOLOGUES: dict[int, list[str]] = {
        1: ["First semester. Nobody knows your name yet.",
            "Eighty days to change that, or not.",
            "The registration desk is already open."],
        2: ["You survived the first one. Barely counts.",
            "The courses get heavier from here.",
            "So does everything else."],
    }
    FAKE_FALLBACK: list[str] = [
        "Another term. The same eighty days.",
        "The catalogue is open and the clock is not.",
        "Spend it well.",
    ]

    def get_monologue(term: int) -> list[str]:
        return list(FAKE_MONOLOGUES.get(term, FAKE_FALLBACK))

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Monologue screen test")
    scene = MonologueScreen()
    controller = MonologueController()
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    semester = 1
    controller.start(semester, get_monologue(semester))

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

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
                elif event.key == pygame.K_r:
                    semester = semester % 6 + 1
                    controller.start(semester, get_monologue(semester))
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    controller.advance()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                controller.advance()

        controller.update(dt)

        scene.render(window, semester, 80, controller.visible_lines(),
                     controller.is_done())

        hint = hint_font.render(
            "SPACE = advance  |  R = next semester  |  F11 fullscreen"
            "  |  ESC quit", True, (150, 125, 100))
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        pygame.display.flip()

    pygame.quit()

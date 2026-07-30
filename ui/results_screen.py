"""
ui/results_screen.py
CSE Life: Compile & Conquer
Created by: Nangiba Tasnim (Dev 3)

The Results Screen is the recap card shown right after the exam phase,
before the semester rolls over. It lists every course the player sat
this term and whether it PASSED or went to the BACKLOG, then sums up
the term: credits earned this semester, running total toward 140, and
how many courses are now backlogged.

It matches the framed-certificate look of the monologue and endgame
screens (tan card, corner marks, pixel font, amber continue arrow).

This file has NO game logic. render() only DRAWS what it is handed. To
keep it fully separate from the academic code, it does NOT import Course
or any engine class -- the main loop builds a plain list of
(code, name, credits, status) tuples from the semester's registered
courses and passes it in. `status` is one of:

    "PASSED"   -- exam cleared, credits awarded   (green)
    "BACKLOG"  -- exam failed, course carried over (red)
    "PENDING"  -- not yet attempted / exam pipeline not wired (grey)

Base look + layout by Nangiba, following the shared screen style.
"""
from __future__ import annotations
import pygame

# -- palette (shared with the other tan screens) --------------
PANEL_TAN    = (231, 214, 189)   # background behind the card
CARD_TAN     = (240, 228, 208)   # the card itself
HEADER_TAN   = (214, 196, 168)   # table header + summary box
BORDER_BROWN = (169, 130, 94)    # frame, outlines, corner marks
TEXT_COFFEE  = (74, 53, 39)      # main text
TITLE_SLATE  = (45, 58, 71)      # screen title
CREDIT_HL    = (155, 110, 70)    # labels
STAT_BROWN   = (140, 110, 85)    # secondary text

ROW_WHITE    = (247, 243, 236)   # row background
STATUS_PASS  = (150, 180, 125)   # green  -- passed
STATUS_FAIL  = (199, 123, 107)   # red    -- backlog
STATUS_WAIT  = (196, 178, 150)   # grey   -- pending
BADGE_TEXT   = (40, 30, 24)      # text inside a status badge
BAR_AMBER    = (217, 169, 106)   # continue arrow

FONT_PATH = "assets/ui/PressStart2P.ttf"

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
CARD_MARGIN = 46
CARD_PAD    = 18
CORNER_LEN  = 26

TITLE_Y     = 76
SUBTITLE_Y  = 120
RULE_TOP_Y  = 150

# course table
TABLE_X     = 150
TABLE_W     = 980
HEADER_Y    = 178
HEADER_H    = 32
FIRST_ROW_Y = 220
ROW_H       = 34
ROW_PITCH   = 40
MAX_ROWS    = 6          # more than a 15-credit term can hold; safe cap

COL_CODE_X   = TABLE_X + 16
COL_NAME_X   = TABLE_X + 150
COL_STATUS_W = 150       # width of the status badge, right-aligned in the row

# summary box under the table
SUMMARY_Y   = 470
SUMMARY_W   = TABLE_W
SUMMARY_H   = 92

HINT_Y      = 600
ARROW_Y     = 634
ARROW_HALF_W = 8
ARROW_H     = 9
ARROW_BOB   = 3
ARROW_PERIOD_MS = 420

TITLE_SIZE = 26
SUB_SIZE   = 11
BODY_SIZE  = 12
BADGE_SIZE = 10
LABEL_SIZE = 10

HINT_TEXT = "PRESS ANY KEY TO CONTINUE"


class ResultsScreen:
    """
    Draws the end-of-semester results recap. Like my other screens it
    never fetches its own data -- render() is handed the per-course
    outcomes and the term totals, so the drawing stays fully separate
    from the academic logic my teammates own (separation of concerns).
    """

    def __init__(self) -> None:
        """Load the pixel fonts once, up front (with the usual fallback)."""
        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_sub: pygame.font.Font = self.__load_font(SUB_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_badge: pygame.font.Font = self.__load_font(BADGE_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)

    # -- loading helper ---------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, semester_number: int,
               results: list, credits_earned: int, total_credits: int,
               backlog_count: int, hint_visible: bool = True) -> None:
        """
        Draw the whole results screen.
        semester_number : which term just finished
        results         : list of (code, name, credits, status) tuples;
                          status in {"PASSED", "BACKLOG", "PENDING"}.
                          Only the first MAX_ROWS are drawn (a 15-credit
                          term never has more courses than that).
        credits_earned  : credits passed THIS semester
        total_credits   : running accumulated credits (goal 140)
        backlog_count   : how many courses are currently backlogged
        hint_visible    : whether to show the "press any key" prompt
        """
        cx = screen.get_width() // 2
        screen.fill(PANEL_TAN)
        self.__draw_card(screen)

        passed = sum(1 for r in results if r[3] == "PASSED")
        self.__blit_centred(screen, self.__font_title,
                            f"SEMESTER {semester_number} RESULTS",
                            TITLE_SLATE, cx, TITLE_Y)
        self.__blit_centred(screen, self.__font_sub,
                            f"{passed} / {len(results)} COURSES CLEARED",
                            CREDIT_HL, cx, SUBTITLE_Y)
        self.__draw_rule(screen, cx, RULE_TOP_Y)

        self.__draw_table_header(screen)
        for i, entry in enumerate(results[:MAX_ROWS]):
            self.__draw_result_row(screen, i, entry)

        self.__draw_summary(screen, credits_earned, total_credits,
                            backlog_count)

        if hint_visible:
            self.__blit_centred(screen, self.__font_label, HINT_TEXT,
                                STAT_BROWN, cx, HINT_Y)
            self.__draw_continue_arrow(screen, cx)

    # -- piece-by-piece drawing -------------------------------
    def __draw_card(self, screen: pygame.Surface) -> None:
        """Draw the framed card, its inner border, and corner marks."""
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
        """Draw short bracket marks at each corner of the inner border."""
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
        """Draw a centred horizontal divider with a small diamond mid-way."""
        half = 300
        pygame.draw.line(screen, BORDER_BROWN, (cx - half, y), (cx - 14, y), 2)
        pygame.draw.line(screen, BORDER_BROWN, (cx + 14, y), (cx + half, y), 2)
        pygame.draw.polygon(screen, BORDER_BROWN,
                            [(cx, y - 6), (cx + 7, y), (cx, y + 6),
                             (cx - 7, y)])

    def __draw_table_header(self, screen: pygame.Surface) -> None:
        """Draw the table header bar with column titles."""
        bar = pygame.Rect(TABLE_X, HEADER_Y, TABLE_W, HEADER_H)
        pygame.draw.rect(screen, HEADER_TAN, bar)
        pygame.draw.rect(screen, BORDER_BROWN, bar, 2)
        cy = bar.y + (HEADER_H - self.__font_body.get_height()) // 2
        screen.blit(self.__font_body.render("CODE", True, TEXT_COFFEE),
                    (COL_CODE_X, cy))
        screen.blit(self.__font_body.render("COURSE", True, TEXT_COFFEE),
                    (COL_NAME_X, cy))
        outcome = self.__font_body.render("OUTCOME", True, TEXT_COFFEE)
        screen.blit(outcome,
                    (bar.right - COL_STATUS_W - 4, cy))

    def __draw_result_row(self, screen: pygame.Surface, i: int,
                          entry) -> None:
        """Draw one course row: code, name, and a coloured status badge."""
        code, name, credits, status = entry
        row = pygame.Rect(TABLE_X, FIRST_ROW_Y + i * ROW_PITCH,
                          TABLE_W, ROW_H)
        pygame.draw.rect(screen, ROW_WHITE, row)
        pygame.draw.rect(screen, BORDER_BROWN, row, 2)

        cy = row.y + (ROW_H - self.__font_body.get_height()) // 2
        screen.blit(self.__font_body.render(code, True, TEXT_COFFEE),
                    (COL_CODE_X, cy))
        screen.blit(self.__font_body.render(
            f"{name}  ({credits} cr)", True, TEXT_COFFEE), (COL_NAME_X, cy))

        self.__draw_status_badge(screen, row, status)

    def __draw_status_badge(self, screen: pygame.Surface, row: pygame.Rect,
                            status: str) -> None:
        """Draw the right-aligned PASSED / BACKLOG / PENDING badge."""
        if status == "PASSED":
            colour, label = STATUS_PASS, "PASSED"
        elif status == "BACKLOG":
            colour, label = STATUS_FAIL, "BACKLOG"
        else:
            colour, label = STATUS_WAIT, "PENDING"

        badge = pygame.Rect(row.right - COL_STATUS_W - 6,
                            row.y + 4, COL_STATUS_W, ROW_H - 8)
        pygame.draw.rect(screen, colour, badge)
        pygame.draw.rect(screen, BORDER_BROWN, badge, 2)
        text = self.__font_badge.render(label, True, BADGE_TEXT)
        screen.blit(text, (badge.centerx - text.get_width() // 2,
                           badge.centery - text.get_height() // 2))

    def __draw_summary(self, screen: pygame.Surface, credits_earned: int,
                       total_credits: int, backlog_count: int) -> None:
        """Draw the boxed term summary: credits this term, total, backlog."""
        box = pygame.Rect(TABLE_X, SUMMARY_Y, SUMMARY_W, SUMMARY_H)
        pygame.draw.rect(screen, HEADER_TAN, box)
        pygame.draw.rect(screen, BORDER_BROWN, box, 2)

        third = SUMMARY_W // 3
        self.__draw_summary_cell(screen, box.x, box.y, third,
                                 "CREDITS THIS TERM", f"+{credits_earned}",
                                 TEXT_COFFEE)
        self.__draw_summary_cell(screen, box.x + third, box.y, third,
                                 "TOTAL CREDITS", f"{total_credits} / 140",
                                 TEXT_COFFEE)
        backlog_colour = STATUS_FAIL if backlog_count > 0 else TEXT_COFFEE
        self.__draw_summary_cell(screen, box.x + third * 2, box.y, third,
                                 "BACKLOG", str(backlog_count),
                                 backlog_colour)

        # two thin dividers between the three cells
        for k in (1, 2):
            dx = box.x + third * k
            pygame.draw.line(screen, BORDER_BROWN,
                             (dx, box.top + 12), (dx, box.bottom - 12), 1)

    def __draw_summary_cell(self, screen: pygame.Surface, x: int, y: int,
                            w: int, label: str, value: str,
                            value_colour: tuple) -> None:
        """Draw one summary cell: a small label above a bigger value."""
        label_surface = self.__font_label.render(label, True, CREDIT_HL)
        screen.blit(label_surface,
                    (x + w // 2 - label_surface.get_width() // 2, y + 22))
        value_surface = self.__font_sub.render(value, True, value_colour)
        screen.blit(value_surface,
                    (x + w // 2 - value_surface.get_width() // 2, y + 50))

    def __draw_continue_arrow(self, screen: pygame.Surface, cx: int) -> None:
        """Draw the small bobbing 'continue' arrow under the hint."""
        step = (pygame.time.get_ticks() // ARROW_PERIOD_MS) % 2
        y = ARROW_Y + (ARROW_BOB if step else 0)
        pygame.draw.polygon(screen, BAR_AMBER,
                            [(cx - ARROW_HALF_W, y),
                             (cx + ARROW_HALF_W, y),
                             (cx, y + ARROW_H)])

    def __blit_centred(self, screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: tuple, centre_x: int,
                       y: int) -> None:
        """Draw a line of text horizontally centred on centre_x."""
        surface = font.render(text, True, colour)
        screen.blit(surface, (centre_x - surface.get_width() // 2, y))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see the results card.
# Abu Huraira removes this block when he plugs in the real game.
#   Any key -> cycle through a few fake result sets
#   F11     -> toggle windowed / fullscreen   |   ESC -> quit
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS   = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Results screen test")
    results_screen = ResultsScreen()
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    # (semester, results, credits_earned, total, backlog)
    cases = [
        (1,
         [("CSE101", "Intro to Programming", 3, "PASSED"),
          ("MAT120", "Discrete Math", 3, "PASSED"),
          ("EEE101", "Digital Logic", 3, "BACKLOG"),
          ("ENG101", "English Composition", 2, "PASSED")],
         8, 8, 1),
        (4,
         [("CSE102", "Data Structures", 3, "PASSED"),
          ("CSE203", "Algorithms", 3, "BACKLOG"),
          ("MAT130", "Calculus II", 3, "BACKLOG"),
          ("PHY101", "Physics I", 3, "PENDING")],
         3, 41, 3),
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
                    index = (index + 1) % len(cases)

        sem, results, earned, total, backlog = cases[index]
        results_screen.render(window, sem, results, earned, total, backlog,
                              hint_visible=True)

        hint = hint_font.render(
            "Any key = next case  |  F11 fullscreen  |  ESC quit",
            True, (150, 125, 100))
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

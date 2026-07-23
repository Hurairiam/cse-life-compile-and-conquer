"""
CSE Life: Compile & Conquer
Created by: Nangiba Tasnim (Dev 3)

The Registration Screen is where the player picks courses for the
semester. Left side: a table of courses (ID / Name / Credits). Right
side: the player's portrait and info. Bottom: the running credit total
and the Confirm / Cancel buttons.

Row states:
    white = not picked      blue = selected      green = confirmed (locked)

This file has NO game logic. render() only DRAWS the state it is handed:
which courses exist, which are selected, which are confirmed, and the
totals. Abu Huraira's engine decides those values during integration.
For now, the stub test at the bottom fakes the clicking so I can see it
work on its own.

Base idea from Abu Huraira (engine). Layout, styling + test by Nangiba.
"""
from __future__ import annotations
import pygame

# -- palette (matches the HUD) --------------------------------
PANEL_TAN     = (231, 214, 189)   # screen background
HEADER_TAN    = (214, 196, 168)   # table header bar
BORDER_BROWN  = (169, 130, 94)    # outlines
TEXT_COFFEE   = (74, 53, 39)      # main text
CREDIT_HL     = (155, 110, 70)    # the "credit limit" line

ROW_WHITE     = (247, 243, 236)   # course not picked
ROW_BLUE      = (120, 150, 190)   # course selected
ROW_GREEN     = (150, 180, 125)   # course confirmed (locked)

PORTRAIT_FILL = (190, 165, 135)   # placeholder block until a real photo exists
PORTRAIT_LABEL = (120, 95, 75)    # faded text inside the placeholder

BTN_CONFIRM   = (150, 180, 125)   # confirm button
BTN_CANCEL    = (199, 123, 107)   # cancel button

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
TABLE_X       = 40
TABLE_W       = 760
HEADER_Y      = 128
HEADER_H      = 34
FIRST_ROW_Y   = 170
ROW_H         = 38
ROW_PITCH     = 44          # row height + the gap below it

COL_ID_X      = TABLE_X + 15
COL_NAME_X    = TABLE_X + 150
COL_CREDITS_X = TABLE_X + 620

TITLE_SIZE    = 20
BODY_SIZE     = 12
TOTAL_SIZE    = 16


class RegistrationScreen:
    """
    Draws the course registration screen. It never fetches its own data
    -- render() is handed the course list and the selection state, so
    the visuals stay fully separate from the game logic (separation of
    concerns). Button and row rectangles are exposed through getters so
    click-detection can live outside this class.
    """

    def __init__(self, screen_w: int, screen_h: int) -> None:
        """Store screen size, load fonts, and fix the button rectangles."""
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h
        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_total: pygame.font.Font = self.__load_font(TOTAL_SIZE)
        self.__confirm_rect: pygame.Rect = pygame.Rect(40, 660, 200, 44)
        self.__cancel_rect: pygame.Rect = pygame.Rect(260, 660, 200, 44)

    # -- loading helper ---------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font("assets/ui/PressStart2P.ttf", size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    # -- rectangle getters (for click detection outside this file) ---
    def __row_rect(self, i: int) -> pygame.Rect:
        """The rectangle for the i-th course row."""
        return pygame.Rect(TABLE_X, FIRST_ROW_Y + i * ROW_PITCH,
                           TABLE_W, ROW_H)

    def get_course_row_rects(self, count: int) -> list[pygame.Rect]:
        """Return one rectangle per course row, so clicks can be matched."""
        return [self.__row_rect(i) for i in range(count)]

    def get_confirm_rect(self) -> pygame.Rect:
        """Return the Confirm button rectangle."""
        return self.__confirm_rect

    def get_cancel_rect(self) -> pygame.Rect:
        """Return the Cancel button rectangle."""
        return self.__cancel_rect

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, visible_courses: list,
               selected: list, confirmed: list, current_credits: int,
               credit_limit: int, player_name: str, student_id: str,
               semester: int) -> None:
        """
        Draw the whole registration screen from the state handed in.
        visible_courses : courses to list
        selected        : courses drawn blue
        confirmed       : courses drawn green (locked)
        current_credits : running total to show at the bottom
        credit_limit    : the cap to display above the table
        player_name / student_id / semester : right-panel info
        """
        screen.fill(PANEL_TAN)

        title = self.__font_title.render("Course Registration", True, TEXT_COFFEE)
        screen.blit(title, (40, 28))

        limit_text = self.__font_body.render(
            f"Credit Limit: {credit_limit}", True, CREDIT_HL)
        screen.blit(limit_text, (40, 96))

        self.__draw_header(screen)

        for i, course in enumerate(visible_courses):
            row = self.__row_rect(i)
            if course in confirmed:
                colour = ROW_GREEN
            elif course in selected:
                colour = ROW_BLUE
            else:
                colour = ROW_WHITE
            pygame.draw.rect(screen, colour, row)
            pygame.draw.rect(screen, BORDER_BROWN, row, 2)
            self.__draw_row_text(screen, course, row)

        self.__draw_player_panel(screen, player_name, student_id, semester)

        total_text = self.__font_total.render(
            f"Credits Selected: {current_credits}", True, TEXT_COFFEE)
        screen.blit(total_text, (40, 612))

        self.__draw_button(screen, self.__confirm_rect, "CONFIRM", BTN_CONFIRM)
        self.__draw_button(screen, self.__cancel_rect, "CANCEL", BTN_CANCEL)

    # -- piece-by-piece drawing -------------------------------
    def __draw_header(self, screen: pygame.Surface) -> None:
        """Draw the table header bar with the three column titles."""
        bar = pygame.Rect(TABLE_X, HEADER_Y, TABLE_W, HEADER_H)
        pygame.draw.rect(screen, HEADER_TAN, bar)
        pygame.draw.rect(screen, BORDER_BROWN, bar, 2)
        cy = bar.y + (HEADER_H - self.__font_body.get_height()) // 2
        screen.blit(self.__font_body.render("ID", True, TEXT_COFFEE),
                    (COL_ID_X, cy))
        screen.blit(self.__font_body.render("COURSE NAME", True, TEXT_COFFEE),
                    (COL_NAME_X, cy))
        screen.blit(self.__font_body.render("CREDITS", True, TEXT_COFFEE),
                    (COL_CREDITS_X, cy))

    def __draw_row_text(self, screen: pygame.Surface, course,
                        row: pygame.Rect) -> None:
        """Draw one course's ID, name, and credits inside its row."""
        cy = row.y + (ROW_H - self.__font_body.get_height()) // 2
        screen.blit(self.__font_body.render(
            course.get_course_id(), True, TEXT_COFFEE), (COL_ID_X, cy))
        screen.blit(self.__font_body.render(
            course.get_course_name(), True, TEXT_COFFEE), (COL_NAME_X, cy))
        screen.blit(self.__font_body.render(
            str(course.get_credit_value()), True, TEXT_COFFEE),
            (COL_CREDITS_X, cy))

    def __draw_player_panel(self, screen: pygame.Surface, name: str,
                            student_id: str, semester: int) -> None:
        """Draw the portrait placeholder and the player's info on the right."""
        portrait = pygame.Rect(910, 90, 230, 230)
        pygame.draw.rect(screen, PORTRAIT_FILL, portrait)
        pygame.draw.rect(screen, BORDER_BROWN, portrait, 3)
        self.__blit_centered(screen, self.__font_body, "PHOTO",
                             PORTRAIT_LABEL, portrait)

        screen.blit(self.__font_body.render(name, True, TEXT_COFFEE),
                    (910, 340))
        screen.blit(self.__font_body.render(f"ID: {student_id}", True,
                    TEXT_COFFEE), (910, 372))
        screen.blit(self.__font_body.render(f"Semester {semester}", True,
                    TEXT_COFFEE), (910, 404))

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, colour: tuple) -> None:
        """Draw a labelled button."""
        pygame.draw.rect(screen, colour, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, 3)
        self.__blit_centered(screen, self.__font_body, label,
                             TEXT_COFFEE, rect)

    def __blit_centered(self, screen: pygame.Surface, font: pygame.font.Font,
                        text: str, colour: tuple, rect: pygame.Rect) -> None:
        """Draw text centred inside a rectangle."""
        surface = font.render(text, True, colour)
        x = rect.x + (rect.w - surface.get_width()) // 2
        y = rect.y + (rect.h - surface.get_height()) // 2
        screen.blit(surface, (x, y))


# -------------------------------------------------------------
# STUB TEST -- lets me run this file on its own to see the screen.
# Abu Huraira removes this block when he plugs in the real game.
#   Click a course row -> select (blue)   |   click again -> deselect
#   CONFIRM -> selected rows turn green + lock
#   CANCEL  -> reset everything back to white
#   F11     -> toggle windowed / fullscreen
# -------------------------------------------------------------
if __name__ == "__main__":

    class _FakeCourse:
        """Stand-in for a real Course, just for testing the layout."""
        def __init__(self, cid: str, name: str, credits: int) -> None:
            self.__cid = cid
            self.__name = name
            self.__credits = credits
        def get_course_id(self) -> str:
            return self.__cid
        def get_course_name(self) -> str:
            return self.__name
        def get_credit_value(self) -> int:
            return self.__credits

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS   = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Registration screen test")
    reg = RegistrationScreen(1280, 720)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 14)

    courses = [
        _FakeCourse("CSE101", "Intro to Programming", 3),
        _FakeCourse("MAT120", "Discrete Math", 3),
        _FakeCourse("CSE102", "Data Structures", 3),
        _FakeCourse("EEE101", "Digital Logic", 3),
        _FakeCourse("MAT130", "Calculus II", 3),
        _FakeCourse("ENG101", "English Composition", 2),
    ]
    selected: list = []    # courses clicked (blue)
    confirmed: list = []   # courses confirmed (green, locked)
    CREDIT_LIMIT = 15

    def total_credits() -> int:
        """Add up the credits of everything selected or confirmed."""
        return sum(c.get_credit_value() for c in selected + confirmed)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                flags = FULLSCREEN_FLAGS if is_fullscreen else WINDOWED_FLAGS
                window = pygame.display.set_mode(SIZE, flags)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if reg.get_confirm_rect().collidepoint(pos):
                    confirmed.extend(selected)      # blue -> green
                    selected.clear()
                elif reg.get_cancel_rect().collidepoint(pos):
                    selected.clear()                # full reset
                    confirmed.clear()
                else:
                    row_rects = reg.get_course_row_rects(len(courses))
                    for i, r in enumerate(row_rects):
                        if r.collidepoint(pos):
                            course = courses[i]
                            if course in confirmed:
                                pass                # locked, ignore
                            elif course in selected:
                                selected.remove(course)
                            else:
                                selected.append(course)
                            break

        reg.render(window, courses, selected, confirmed, total_credits(),
                   CREDIT_LIMIT, "STUDENT NAME", "CSE-00000000", 3)

        hint = hint_font.render(
            "Click rows to select  |  CONFIRM / CANCEL  |  F11 fullscreen",
            True, (120, 95, 75))
        window.blit(hint, (40, 700))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
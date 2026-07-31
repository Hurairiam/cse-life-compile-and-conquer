"""
CSE Life: Compile & Conquer
Created by: Nangiba Tasnim (Dev 3)

The Registration Screen is where the player picks courses for the
semester. It is laid out as a framed card: a table of courses on the
left (ID / Name / Credits), the player's ID photo, info and buttons on
the right, and a boxed credit total with a progress bar underneath.

Row states:
    white = not picked      blue = selected      green = confirmed (locked)

Credit bar:
    blue = under the limit   amber = exactly at it   red = over it

This file has NO game logic. render() only DRAWS the state it is handed:
which courses exist, which are selected, which are confirmed, and the
totals. Abu Huraira's engine decides those values during integration.
The over-limit warning popup lives entirely in the stub test below, so
this class stays a pure drawing layer.

Base idea from Abu Huraira (engine). Layout, styling + test by Nangiba.

─────────────────────────────────────────────────────────────
REVISION — phase R2 (REGISTRATION_CATALOG_PLAN.md, branch
nangiba-temp-01). The one sanctioned edit of that plan (§0.1).

WHY: 43 of the 65 courses are already unlocked at semester 1, but
only the first six could ever be seen. The rest were thrown away
every frame, and a failed course sat somewhere in the middle of
the list with nothing marking it as a retake.

WHAT WAS ADDED — all of it additive:
  * scrolling: VISIBLE_ROWS at a time over a catalog of any
    length, with a scrollbar in the previously empty x 800-900
    gutter and a "SHOWING 1-6 OF 43" counter in the unused
    row-6 band. Neither displaces a single existing element.
  * a backlog accent: a BAR_OVER left stripe, a BAR_OVER row
    border at the SAME 2 px weight, and a RETAKE tag. The state
    fill (white / blue / green) is untouched, so selection stays
    legible underneath.
  * a NEW tag for courses a fresh prerequisite just unlocked.
  * eight pure-layout methods (clamp_scroll, get_row_index_at,
    the four scrollbar rects, and two counters).

WHAT DID NOT CHANGE. Every name main.py imports or calls is
byte-identical: FIRST_ROW_Y (190), FOOTER_Y (496), ROW_PITCH (44),
RegistrationScreen(screen_w, screen_h), get_course_row_rects(count),
get_confirm_rect(), get_cancel_rect(), and render()'s original nine
keyword parameters. The three new render() parameters are
keyword-with-default and appended last, so main.py's existing call
keeps working untouched and its screen looks exactly as it did.

Scroll state is NOT held here. The caller owns the offset integer
and hands it in every frame like every other value (§6.1); this
class only does the arithmetic. Still no game logic.
─────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import pygame

# -- palette --------------------------------------------------
PANEL_TAN     = (231, 214, 189)   # screen background, behind the card
CARD_TAN      = (240, 228, 208)   # the card itself, slightly lighter
HEADER_TAN    = (214, 196, 168)   # table header bar
TITLE_SLATE   = (45, 58, 71)      # #2D3A47 -- screen title
BORDER_BROWN  = (169, 130, 94)    # card frame, outlines, corner marks
TEXT_COFFEE   = (74, 53, 39)      # main text
CREDIT_HL     = (155, 110, 70)    # the "credit limit" line + labels
STAT_BROWN    = (140, 110, 85)    # muted secondary text (scroll counter)

ROW_WHITE     = (247, 243, 236)   # course not picked
ROW_BLUE      = (120, 150, 190)   # course selected
ROW_GREEN     = (150, 180, 125)   # course confirmed (locked)

BAR_TRACK     = (222, 208, 186)   # empty part of the credit bar
BAR_FULL      = (217, 169, 106)   # bar colour exactly at the limit
BAR_OVER      = (186, 74, 62)     # bar colour once the limit is passed

PORTRAIT_BG    = (255, 255, 255)  # solid white behind the ID photo
PORTRAIT_FILL  = (190, 165, 135)  # placeholder if the photo is missing
PORTRAIT_LABEL = (120, 95, 75)    # faded text inside the placeholder

BTN_CONFIRM   = (150, 180, 125)   # confirm button
BTN_CANCEL    = (199, 123, 107)   # cancel button

PORTRAIT_PATH = "assets/portraits/player_id.png"
FONT_PATH     = "assets/ui/PressStart2P.ttf"

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
CARD_MARGIN   = 24          # gap between screen edge and the card
CARD_PAD      = 14          # gap between the card and its inner border
CORNER_LEN    = 22          # length of each corner mark arm

TITLE_Y       = 50
LIMIT_Y       = 112

# left column -- the course table
TABLE_X       = 60
TABLE_W       = 740
HEADER_Y      = 148
HEADER_H      = 34
FIRST_ROW_Y   = 190
ROW_H         = 38
ROW_PITCH     = 44          # row height + the gap below it

COL_ID_X      = TABLE_X + 15
COL_NAME_X    = TABLE_X + 150
COL_CREDITS_X = TABLE_X + 620
SEP_1_X       = TABLE_X + 135   # divider between ID and NAME
SEP_2_X       = TABLE_X + 605   # divider between NAME and CREDITS

# left column -- the boxed credit total underneath the table
FOOTER_X      = TABLE_X
FOOTER_Y      = 496
FOOTER_W      = TABLE_W
FOOTER_H      = 112
BAR_W         = 420
BAR_H         = 16

# right column -- photo, info, buttons (all share the same x + width)
RIGHT_X       = 900
RIGHT_W       = 230
PORTRAIT_Y    = HEADER_Y            # photo top lines up with the table top
PORTRAIT_SIZE = RIGHT_W
INFO_Y        = PORTRAIT_Y + PORTRAIT_SIZE + 22
INFO_PITCH    = 30
CONFIRM_Y     = 512
CANCEL_Y      = 564
BTN_H         = 44

TITLE_SIZE    = 28
BODY_SIZE     = 12
LABEL_SIZE    = 10
TOTAL_SIZE    = 16

# -------------------------------------------------------------
# SCROLLING + BACKLOG ACCENT  (R2 additions)
# -------------------------------------------------------------
# Six rows is what the player sees today and what main.py's
# (FOOTER_Y - FIRST_ROW_Y) // ROW_PITCH math already yields, so the
# screen keeps its current shape exactly. A seventh row would
# physically fit (454-492) but that band is worth more as the scroll
# counter than as one extra course.
VISIBLE_ROWS     = 6

# The scrollbar lives entirely in the 100 px gutter between the table
# (ends at x 800) and the right panel (starts at x 900), so NO existing
# element moves by a pixel.
SCROLL_X         = TABLE_X + TABLE_W + 10     # 810
SCROLL_W         = 12
SCROLL_ARROW_H   = 14
SCROLL_MIN_THUMB = 24         # a thumb never shrinks below this

ACCENT_W         = 4          # backlog stripe down the row's left edge
TAG_W            = 62         # the RETAKE / NEW tag box
TAG_H            = 18
TAG_INSET        = 15         # gap from the row's right edge to the tag

COUNTER_Y        = 454        # the freed row-6 band (454-492)


class RegistrationScreen:
    """
    Draws the course registration screen. It never fetches its own data
    -- render() is handed the course list and the selection state, so
    the visuals stay fully separate from the game logic (separation of
    concerns). Button and row rectangles are exposed through getters so
    click-detection can live outside this class.
    """

    def __init__(self, screen_w: int, screen_h: int) -> None:
        """Store screen size, load fonts + photo, fix the button rects."""
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h
        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)
        self.__font_total: pygame.font.Font = self.__load_font(TOTAL_SIZE)
        self.__portrait_rect: pygame.Rect = pygame.Rect(
            RIGHT_X, PORTRAIT_Y, PORTRAIT_SIZE, PORTRAIT_SIZE)
        self.__portrait: pygame.Surface | None = self.__load_portrait()
        self.__confirm_rect: pygame.Rect = pygame.Rect(
            RIGHT_X, CONFIRM_Y, RIGHT_W, BTN_H)
        self.__cancel_rect: pygame.Rect = pygame.Rect(
            RIGHT_X, CANCEL_Y, RIGHT_W, BTN_H)

    # -- loading helpers --------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    def __load_portrait(self) -> pygame.Surface | None:
        """
        Load the player's ID photo and fit it to the portrait box.
        Returns None if the file isn't there yet -- the screen then draws
        a placeholder block instead of crashing.
        """
        try:
            image = pygame.image.load(PORTRAIT_PATH).convert_alpha()
            return pygame.transform.scale(
                image, (self.__portrait_rect.w, self.__portrait_rect.h))
        except (FileNotFoundError, OSError, pygame.error):
            return None

    # -- rectangle getters (for click detection outside this file) ---
    def __row_rect(self, i: int) -> pygame.Rect:
        """The rectangle for the i-th course row."""
        return pygame.Rect(TABLE_X, FIRST_ROW_Y + i * ROW_PITCH,
                           TABLE_W, ROW_H)

    def get_course_row_rects(self, count: int) -> list[pygame.Rect]:
        """
        Return one rectangle per visible course row, so clicks can be
        matched.

        R2: capped at VISIBLE_ROWS. main.py only ever passes 6, so its
        behaviour is unchanged; the cap simply stops a long catalog from
        drawing rects down over the credit-total footer. These are
        SCREEN rows -- with a scroll offset in play, row 0 is whatever
        course is currently at the top, so use get_row_index_at() to
        turn a click into a catalog index.
        """
        return [self.__row_rect(i)
                for i in range(max(0, min(int(count), VISIBLE_ROWS)))]

    def get_confirm_rect(self) -> pygame.Rect:
        """Return the Confirm button rectangle."""
        return self.__confirm_rect

    def get_cancel_rect(self) -> pygame.Rect:
        """Return the Cancel button rectangle."""
        return self.__cancel_rect

    # -- scrolling maths (R2) ---------------------------------
    # Pure arithmetic over the layout constants above. No game state,
    # no decisions about validity, and no scroll position is stored --
    # the caller owns the offset integer and hands it in each frame,
    # exactly like every other value render() draws (§6.1, §6.2).

    def get_visible_row_count(self) -> int:
        """How many course rows fit on screen at once."""
        return VISIBLE_ROWS

    def get_max_scroll(self, total: int) -> int:
        """
        The largest useful scroll offset for a catalog of `total`
        courses. Zero when everything already fits.
        """
        return max(0, int(total) - VISIBLE_ROWS)

    def clamp_scroll(self, offset: int, total: int) -> int:
        """
        Pull an offset back into range. Never raises on a bad value --
        a nonsense offset clamps to a valid one rather than blanking
        the table.
        """
        try:
            wanted = int(offset)
        except (TypeError, ValueError):
            return 0
        return max(0, min(wanted, self.get_max_scroll(total)))

    def get_row_index_at(self, pos, scroll_offset: int = 0,
                         total: int = 0) -> int:
        """
        The ABSOLUTE catalog index under a click, or -1 for a miss.

        This is the method that makes scrolling safe: it adds the offset
        back on, so clicking the top row while scrolled to 12 selects
        course 12 and not course 0. A caller that matches screen rects
        itself will select the wrong course the moment the list moves.
        """
        offset = self.clamp_scroll(scroll_offset, total)
        showing = max(0, min(VISIBLE_ROWS, int(total) - offset))
        for index in range(showing):
            if self.__row_rect(index).collidepoint(pos):
                return offset + index
        return -1

    def get_scrollbar_track_rect(self) -> pygame.Rect:
        """
        The scrollbar groove: from the first row's top to the last
        visible row's bottom, in the free gutter beside the table.
        """
        height = (VISIBLE_ROWS - 1) * ROW_PITCH + ROW_H
        return pygame.Rect(SCROLL_X, FIRST_ROW_Y, SCROLL_W, height)

    def get_scroll_up_rect(self) -> pygame.Rect:
        """The up-arrow button, directly above the track."""
        track = self.get_scrollbar_track_rect()
        return pygame.Rect(SCROLL_X, track.top - SCROLL_ARROW_H,
                           SCROLL_W, SCROLL_ARROW_H)

    def get_scroll_down_rect(self) -> pygame.Rect:
        """The down-arrow button, directly below the track."""
        track = self.get_scrollbar_track_rect()
        return pygame.Rect(SCROLL_X, track.bottom, SCROLL_W, SCROLL_ARROW_H)

    def get_scrollbar_thumb_rect(self, scroll_offset: int,
                                 total: int) -> pygame.Rect:
        """
        The draggable thumb, sized by how much of the catalog is on
        screen and positioned by how far down it is.

        Floored at SCROLL_MIN_THUMB so a 200-course catalog still leaves
        something grabbable. When everything fits, returns the full
        track -- the scrollbar is not drawn at all in that case, but the
        getter stays total so a caller never has to special-case it.
        """
        track = self.get_scrollbar_track_rect()
        if int(total) <= VISIBLE_ROWS:
            return track
        span = max(SCROLL_MIN_THUMB,
                   int(track.h * VISIBLE_ROWS / int(total)))
        span = min(span, track.h)
        travel = track.h - span
        limit = self.get_max_scroll(total)
        offset = self.clamp_scroll(scroll_offset, total)
        top = track.y + (int(travel * offset / limit) if limit > 0 else 0)
        return pygame.Rect(track.x, top, track.w, span)

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, visible_courses: list,
               selected: list, confirmed: list, current_credits: int,
               credit_limit: int, player_name: str, student_id: str,
               semester: int,
               backlogged: list | None = None,
               scroll_offset: int = 0,
               newly_unlocked: list | None = None) -> None:
        """
        Draw the whole registration screen from the state handed in.
        visible_courses : courses to list -- the WHOLE catalog, not a
                          pre-sliced page; this method does the slicing
        selected        : courses drawn blue
        confirmed       : courses drawn green (locked)
        current_credits : running total shown in the footer box
        credit_limit    : the cap displayed above the table
        player_name / student_id / semester : right-panel info

        R2 additions, all keyword-with-default so main.py's existing
        nine-keyword call keeps working byte-for-byte:
        backlogged      : courses drawn with the red retake accent
        scroll_offset   : index of the top visible row; clamped here
        newly_unlocked  : courses drawn with the blue NEW tag
        """
        backlog_list: list = backlogged or []
        new_list: list = newly_unlocked or []
        total: int = len(visible_courses)
        offset: int = self.clamp_scroll(scroll_offset, total)
        window: list = visible_courses[offset:offset + VISIBLE_ROWS]

        screen.fill(PANEL_TAN)
        self.__draw_card(screen)

        title = self.__font_title.render("Course Registration", True,
                                         TITLE_SLATE)
        screen.blit(title, (TABLE_X, TITLE_Y))

        limit_text = self.__font_body.render(
            f"Credit Limit: {credit_limit}", True, CREDIT_HL)
        screen.blit(limit_text, (TABLE_X, LIMIT_Y))

        self.__draw_header(screen)

        # Row state is resolved by MEMBERSHIP, not by index, which is
        # what makes a blue selection stay blue when the list scrolls
        # under it. The index is only ever screen-relative here; clicks
        # come back through get_row_index_at(), which re-adds the offset.
        for i, course in enumerate(window):
            row = self.__row_rect(i)
            if course in confirmed:
                colour = ROW_GREEN
            elif course in selected:
                colour = ROW_BLUE
            else:
                colour = ROW_WHITE
            is_retake = course in backlog_list
            pygame.draw.rect(screen, colour, row)
            if is_retake:
                # Stripe first, border second: the border draws over the
                # stripe's outer edge and the two read as one frame.
                pygame.draw.rect(screen, BAR_OVER,
                                 pygame.Rect(row.x, row.y, ACCENT_W, ROW_H))
            pygame.draw.rect(screen, BAR_OVER if is_retake else BORDER_BROWN,
                             row, 2)
            self.__draw_column_separators(screen, row)
            self.__draw_row_text(screen, course, row)
            if is_retake:
                self.__draw_tag(screen, row, "RETAKE", BAR_OVER)
            elif course in new_list:
                self.__draw_tag(screen, row, "NEW", ROW_BLUE)

        self.__draw_scrollbar(screen, offset, total)
        self.__draw_scroll_counter(screen, offset, total)
        self.__draw_credit_footer(screen, current_credits, credit_limit)
        self.__draw_player_panel(screen, player_name, student_id, semester)

        self.__draw_button(screen, self.__confirm_rect, "CONFIRM", BTN_CONFIRM)
        self.__draw_button(screen, self.__cancel_rect, "CANCEL", BTN_CANCEL)

    # -- piece-by-piece drawing -------------------------------
    def __draw_card(self, screen: pygame.Surface) -> None:
        """Draw the framed card panel, inner border, and corner marks."""
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
            ((rect.left, rect.top), (n, 0), (0, n)),        # top-left
            ((rect.right, rect.top), (-n, 0), (0, n)),      # top-right
            ((rect.left, rect.bottom), (n, 0), (0, -n)),    # bottom-left
            ((rect.right, rect.bottom), (-n, 0), (0, -n)),  # bottom-right
        ]
        for (px, py), (dx1, dy1), (dx2, dy2) in corners:
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_header(self, screen: pygame.Surface) -> None:
        """Draw the table header bar with the three column titles."""
        bar = pygame.Rect(TABLE_X, HEADER_Y, TABLE_W, HEADER_H)
        pygame.draw.rect(screen, HEADER_TAN, bar)
        pygame.draw.rect(screen, BORDER_BROWN, bar, 2)
        self.__draw_column_separators(screen, bar)
        cy = bar.y + (HEADER_H - self.__font_body.get_height()) // 2
        screen.blit(self.__font_body.render("ID", True, TEXT_COFFEE),
                    (COL_ID_X, cy))
        screen.blit(self.__font_body.render("COURSE NAME", True, TEXT_COFFEE),
                    (COL_NAME_X, cy))
        screen.blit(self.__font_body.render("CREDITS", True, TEXT_COFFEE),
                    (COL_CREDITS_X, cy))

    def __draw_column_separators(self, screen: pygame.Surface,
                                 rect: pygame.Rect) -> None:
        """Draw the two vertical column dividers inside a row or header."""
        for x in (SEP_1_X, SEP_2_X):
            pygame.draw.line(screen, BORDER_BROWN,
                             (x, rect.y), (x, rect.bottom - 1), 2)

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

    def __draw_tag(self, screen: pygame.Surface, row: pygame.Rect,
                   label: str, colour: tuple) -> None:
        """
        Draw a RETAKE / NEW tag in the credits column's dead space.

        Right-aligned inside the row, vertically centred, so a tagged
        row lines up with an untagged one to the pixel -- same rect,
        same pitch, same separators, same text positions. Nothing about
        the row moves; the tag only fills space that was already empty.
        """
        box = pygame.Rect(row.right - TAG_INSET - TAG_W,
                          row.y + (ROW_H - TAG_H) // 2, TAG_W, TAG_H)
        pygame.draw.rect(screen, colour, box)
        pygame.draw.rect(screen, BORDER_BROWN, box, 2)
        self.__blit_centered(screen, self.__font_label, label,
                             CARD_TAN, box)

    def __draw_scrollbar(self, screen: pygame.Surface, offset: int,
                         total: int) -> None:
        """
        Draw the track, thumb and two arrows in the free gutter.

        Nothing is drawn when the catalog already fits -- no track, no
        arrows, no thumb -- so a short list renders exactly as it did
        before this feature existed.
        """
        if total <= VISIBLE_ROWS:
            return

        track = self.get_scrollbar_track_rect()
        pygame.draw.rect(screen, HEADER_TAN, track)
        pygame.draw.rect(screen, BORDER_BROWN, track, 2)

        thumb = self.get_scrollbar_thumb_rect(offset, total)
        pygame.draw.rect(screen, BORDER_BROWN, thumb)
        pygame.draw.rect(screen, BORDER_BROWN, thumb, 2)

        up = self.get_scroll_up_rect()
        pygame.draw.polygon(screen, BORDER_BROWN, [
            (up.centerx, up.top), (up.right, up.bottom), (up.left, up.bottom)])
        down = self.get_scroll_down_rect()
        pygame.draw.polygon(screen, BORDER_BROWN, [
            (down.centerx, down.bottom), (down.right, down.top),
            (down.left, down.top)])

    def __draw_scroll_counter(self, screen: pygame.Surface, offset: int,
                              total: int) -> None:
        """
        `SHOWING 1-6 OF 43`, right-aligned under the table in the band
        the seventh row would have occupied.

        Omitted entirely when the catalog fits, for the same reason the
        scrollbar is: a short list must look untouched.
        """
        if total <= VISIBLE_ROWS:
            return
        first = offset + 1
        last = min(offset + VISIBLE_ROWS, total)
        text = self.__font_label.render(
            f"SHOWING {first}-{last} OF {total}", True, STAT_BROWN)
        screen.blit(text, (TABLE_X + TABLE_W - text.get_width(), COUNTER_Y))

    def __draw_credit_footer(self, screen: pygame.Surface, current: int,
                             limit: int) -> None:
        """
        Draw the boxed credit total with a fill bar toward the limit.
        The bar and the count go blue / amber / red depending on whether
        the total is under, exactly at, or over the limit. This only
        picks a colour from numbers already handed in -- it does not
        decide anything about whether the selection is allowed.
        """
        box = pygame.Rect(FOOTER_X, FOOTER_Y, FOOTER_W, FOOTER_H)
        pygame.draw.rect(screen, HEADER_TAN, box)
        pygame.draw.rect(screen, BORDER_BROWN, box, 2)

        if current > limit:
            bar_colour = BAR_OVER
            count_colour = BAR_OVER
        elif current == limit:
            bar_colour = BAR_FULL
            count_colour = TEXT_COFFEE
        else:
            bar_colour = ROW_BLUE
            count_colour = TEXT_COFFEE

        screen.blit(self.__font_label.render(
            "CREDITS SELECTED", True, CREDIT_HL), (box.x + 24, box.y + 18))
        screen.blit(self.__font_total.render(
            f"{current} / {limit}", True, count_colour),
            (box.x + 24, box.y + 40))

        bar = pygame.Rect(box.x + 24, box.y + 76, BAR_W, BAR_H)
        pygame.draw.rect(screen, BAR_TRACK, bar)
        filled = int(BAR_W * min(current / limit, 1.0)) if limit > 0 else 0
        if filled > 0:
            pygame.draw.rect(screen, bar_colour,
                             pygame.Rect(bar.x, bar.y, filled, BAR_H))
        pygame.draw.rect(screen, BORDER_BROWN, bar, 2)

    def __draw_player_panel(self, screen: pygame.Surface, name: str,
                            student_id: str, semester: int) -> None:
        """Draw the ID photo (or placeholder) and the player's info."""
        box = self.__portrait_rect
        if self.__portrait is not None:
            pygame.draw.rect(screen, PORTRAIT_BG, box)   # white backdrop
            screen.blit(self.__portrait, (box.x, box.y))
        else:
            pygame.draw.rect(screen, PORTRAIT_FILL, box)
            self.__blit_centered(screen, self.__font_body, "PHOTO",
                                 PORTRAIT_LABEL, box)
        pygame.draw.rect(screen, BORDER_BROWN, box, 3)

        screen.blit(self.__font_body.render(
            f"Student Name: {name}", True, TEXT_COFFEE),
            (RIGHT_X, INFO_Y))
        screen.blit(self.__font_body.render(
            f"ID: {student_id}", True, TEXT_COFFEE),
            (RIGHT_X, INFO_Y + INFO_PITCH))
        screen.blit(self.__font_body.render(
            f"Semester: {semester}", True, TEXT_COFFEE),
            (RIGHT_X, INFO_Y + INFO_PITCH * 2))

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
#   Wheel / up-down arrows / the two arrow buttons -> scroll
#   CONFIRM -> selected rows turn green + lock
#             (blocked with a warning popup if over the credit limit)
#   CANCEL  -> reset everything back to white
#   B       -> toggle the backlog set, to eyeball the red accent
#              against a white, a blue and a green row
#   F11     -> toggle windowed / fullscreen
#
# 22 fake courses, four of them backlogged and pinned to the top,
# two flagged newly unlocked -- enough to scroll four pages. The
# regression this whole phase turns on is the click: scroll down,
# click a row, and the course that lights up must be the one under
# the cursor. That is get_row_index_at()'s entire job.
#
# The popup, the over-limit check and the scroll offset all live
# HERE, not in the class -- in the real game RegistrationManager
# decides the first two and main.py owns the third.
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

    def _stub_font(size: int) -> pygame.font.Font:
        """Same font-loading safety net the class uses."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS   = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Registration screen test")
    reg = RegistrationScreen(1280, 720)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    popup_title_font = _stub_font(16)
    popup_body_font = _stub_font(11)

    # Four retakes pinned to the top, exactly the order R1's
    # SemesterCatalogBuilder.build() produces, then the regular block.
    retakes = [
        _FakeCourse("CSE102", "Data Structures", 3),
        _FakeCourse("MAT120", "Discrete Math", 3),
        _FakeCourse("PHY101", "Physics I", 3),
        _FakeCourse("EEE101", "Digital Logic", 3),
    ]
    regulars = [
        _FakeCourse("CSE101", "Intro to Programming", 3),
        _FakeCourse("MAT130", "Calculus II", 3),
        _FakeCourse("ENG101", "English Composition", 2),
        _FakeCourse("CSE201", "Algorithms", 3),
        _FakeCourse("CSE202", "Algorithms Lab", 1),
        _FakeCourse("CSE203", "Object Oriented Programming", 3),
        _FakeCourse("CSE204", "OOP Lab", 1),
        _FakeCourse("MAT210", "Linear Algebra", 3),
        _FakeCourse("STA201", "Probability and Statistics", 3),
        _FakeCourse("CSE301", "Database Systems", 3),
        _FakeCourse("CSE302", "Database Systems Lab", 1),
        _FakeCourse("CSE303", "Operating Systems", 3),
        _FakeCourse("CSE304", "Computer Networks", 3),
        _FakeCourse("CSE305", "Software Engineering", 3),
        _FakeCourse("ENG201", "Technical Writing", 2),
        _FakeCourse("UCC101", "Bangla Bhasa", 3),
        _FakeCourse("ESK110", "Study Skills", 0),
        _FakeCourse("CSE401", "Machine Learning", 3),
    ]
    courses = retakes + regulars
    backlogged: list = list(retakes)          # drawn with the red accent
    newly_unlocked: list = [regulars[7], regulars[8]]   # the NEW tag

    selected: list = []    # courses clicked (blue)
    confirmed: list = []   # courses confirmed (green, locked)
    scroll_offset = 0      # the caller owns this, not the screen
    CREDIT_LIMIT = 15
    show_warning = False   # True while the over-limit popup is open

    POPUP_RECT = pygame.Rect(340, 248, 600, 224)
    OK_RECT = pygame.Rect(POPUP_RECT.centerx - 80,
                          POPUP_RECT.bottom - 66, 160, 42)
    POPUP_LINES = [
        "You can register a maximum of",
        f"{CREDIT_LIMIT} credits per semester.",
        "Deselect a course and try again.",
    ]

    def total_credits() -> int:
        """Add up the credits of everything selected or confirmed."""
        return sum(c.get_credit_value() for c in selected + confirmed)

    def draw_popup(surface: pygame.Surface) -> None:
        """Dim the screen and draw the over-limit warning box on top."""
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((25, 18, 12, 160))
        surface.blit(shade, (0, 0))

        pygame.draw.rect(surface, CARD_TAN, POPUP_RECT)
        pygame.draw.rect(surface, BAR_OVER, POPUP_RECT, 4)

        title = popup_title_font.render("TOO MANY CREDITS", True, BAR_OVER)
        surface.blit(title, (POPUP_RECT.centerx - title.get_width() // 2,
                             POPUP_RECT.y + 30))

        for i, line in enumerate(POPUP_LINES):
            text = popup_body_font.render(line, True, TEXT_COFFEE)
            surface.blit(text, (POPUP_RECT.centerx - text.get_width() // 2,
                                POPUP_RECT.y + 78 + i * 26))

        pygame.draw.rect(surface, BTN_CANCEL, OK_RECT)
        pygame.draw.rect(surface, BORDER_BROWN, OK_RECT, 3)
        ok = popup_body_font.render("OK", True, TEXT_COFFEE)
        surface.blit(ok, (OK_RECT.centerx - ok.get_width() // 2,
                          OK_RECT.centery - ok.get_height() // 2))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    flags = (FULLSCREEN_FLAGS if is_fullscreen
                             else WINDOWED_FLAGS)
                    window = pygame.display.set_mode(SIZE, flags)
                elif event.key == pygame.K_DOWN:
                    scroll_offset = reg.clamp_scroll(scroll_offset + 1,
                                                     len(courses))
                elif event.key == pygame.K_UP:
                    scroll_offset = reg.clamp_scroll(scroll_offset - 1,
                                                     len(courses))
                elif event.key == pygame.K_b:
                    # Toggle the accent so it can be judged against a
                    # white, a blue and a green row on the same screen.
                    backlogged = [] if backlogged else list(retakes)

            elif event.type == pygame.MOUSEWHEEL:
                # The three-line pattern the lead copies into main.py:
                # the CALLER owns the offset, the screen owns the maths.
                scroll_offset = reg.clamp_scroll(scroll_offset - event.y,
                                                 len(courses))

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                if show_warning:
                    # popup is open -- only the OK button responds
                    if OK_RECT.collidepoint(pos):
                        show_warning = False

                elif reg.get_confirm_rect().collidepoint(pos):
                    if total_credits() > CREDIT_LIMIT:
                        show_warning = True         # block + warn
                    else:
                        confirmed.extend(selected)  # blue -> green
                        selected.clear()

                elif reg.get_cancel_rect().collidepoint(pos):
                    selected.clear()                # full reset
                    confirmed.clear()

                elif reg.get_scroll_up_rect().collidepoint(pos):
                    scroll_offset = reg.clamp_scroll(scroll_offset - 1,
                                                     len(courses))

                elif reg.get_scroll_down_rect().collidepoint(pos):
                    scroll_offset = reg.clamp_scroll(scroll_offset + 1,
                                                     len(courses))

                else:
                    # ABSOLUTE index, not a screen row -- this is what
                    # keeps the click correct at any scroll position.
                    index = reg.get_row_index_at(pos, scroll_offset,
                                                 len(courses))
                    if index >= 0:
                        course = courses[index]
                        if course in confirmed:
                            pass                    # locked, ignore
                        elif course in selected:
                            selected.remove(course)
                        else:
                            selected.append(course)

        reg.render(window, courses, selected, confirmed, total_credits(),
                   CREDIT_LIMIT, "Player", "8324782", 3,
                   backlogged=backlogged, scroll_offset=scroll_offset,
                   newly_unlocked=newly_unlocked)

        # hint text, bottom-right, tucked inside the card frame
        hint = hint_font.render(
            "Wheel/arrows scroll  |  Click rows  |  CONFIRM / CANCEL"
            "  |  B backlog  |  F11",
            True, (150, 125, 100))
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        if show_warning:
            draw_popup(window)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
"""
CSE Life: Compile & Conquer
ui/load_game_screen.py

The save-slot browser: a four-row table of SLOT 1-3 plus AUTOSAVE,
with LOAD, DELETE and BACK underneath.

This file has NO game logic. render() only DRAWS what it is handed:
four rows of already-formatted strings and which one is selected. It
does not read the disk, does not load a game, and does not delete
anything -- engine/save_manager.py owns the files and the caller owns
the decisions (§6.1, §6.2).

The quarry's version showed a "SAVE SYSTEM COMING SOON" notice
because there was no save system. There is one now, so the notice is
gone and the rows carry real SaveSlot data. Formatting slots into
row strings is the module-level format_slot_row() helper below,
outside the class, so the class still never fetches its own data.

Style: Nangiba Tasnim's dense card + registration-table pattern,
ported from the quarry's main_menu_system/load_game_screen.py.
Abu Huraira removes the stub test block when he plugs in the real game.
"""
from __future__ import annotations

import os
from typing import List, Optional, Sequence

import pygame

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues, and no
# colours imported from another screen (Build Plan §0.5).
PANEL_TAN = (231, 214, 189)     # screen background behind the card
CARD_TAN = (240, 228, 208)      # the dense card
HEADER_TAN = (214, 196, 168)    # the table header bar, the BACK button
BORDER_BROWN = (169, 130, 94)   # frame, corner marks, row borders
TEXT_COFFEE = (74, 53, 39)      # populated row text
TITLE_SLATE = (45, 58, 71)      # the screen title
STAT_BROWN = (140, 110, 85)     # empty-slot text
ROW_WHITE = (247, 243, 236)     # an unselected row
ROW_BLUE = (120, 150, 190)      # the selected row
BTN_CONFIRM = (150, 180, 125)   # LOAD
BTN_CANCEL = (199, 123, 107)    # DELETE
HINT_BROWN = (150, 125, 100)    # stub-test hint line only

# Game rules, fixed by IMPLEMENTATION_PLAN §3 and shown as N / MAX (§7).
CREDIT_GOAL = 140
SEMESTER_DAYS = 80

# Anchored to the project, not to the working directory.
FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "ui", "PressStart2P.ttf")

TITLE_TEXT = "LOAD GAME"
EMPTY_TEXT = "EMPTY SLOT"
EMPTY_FIELD = "—"
COLUMN_TITLES: tuple = ("SLOT", "DETAILS", "SAVED")

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
CARD_MARGIN = 24        # dense inset (§4.2)
CARD_PAD = 14
CORNER_LEN = 22

TITLE_Y = 50

# Column positions are measured, not guessed. PressStart2P advances one
# size-width per character, so at BODY_SIZE = 12:
#   SLOT    "AUTOSAVE" is 8 chars = 96 px  -> 110 px of room
#   SAVED   "2026-07-31 05:42" = 16 chars = 192 px -> 195 px of room
#   DETAILS the fixed part (" · Sem 12 · 140/140 cr · 80/80 d ·
#           200,000 BDT") is 46 chars, so 670 px fits a name of 9
#           characters at the absolute worst-case numbers. Longer names
#           ellipsis through __truncate() rather than crossing into the
#           SAVED column -- §3 clips, it never reflows.
TABLE_X = 120
TABLE_W = 1040
HEADER_Y = 148
HEADER_H = 34
FIRST_ROW_Y = 190
ROW_H = 38
ROW_PITCH = 44

COL_SLOT_X = TABLE_X + 15
COL_DETAILS_X = TABLE_X + 140
COL_SAVED_X = TABLE_X + 835
SEP_1_X = TABLE_X + 125
SEP_2_X = TABLE_X + 820

BTN_W = 160
BTN_H = 44
BTN_GAP = 22
BTN_Y = 600

TITLE_SIZE = 28
BODY_SIZE = 12
LABEL_SIZE = 10

MAX_NAME_CHARS = 12     # keeps DETAILS inside its column for real names


def format_wallet(amount: float) -> str:
    """Wallet in BDT with thousands commas, no decimals (§7)."""
    try:
        return f"{float(amount):,.0f} BDT"
    except (TypeError, ValueError):
        return "0 BDT"


def format_saved_at(iso_timestamp: str) -> str:
    """
    Turn an ISO-8601 stamp into "YYYY-MM-DD HH:MM" for the table.

    Anything unparseable falls back to the em dash rather than showing
    the player a raw timestamp with a timezone offset in it.
    """
    text = str(iso_timestamp or "")
    if len(text) < 16 or "T" not in text:
        return EMPTY_FIELD
    return text[:16].replace("T", " ")


def format_slot_row(slot) -> List[str]:
    """
    Turn one engine.save_manager.SaveSlot into three column strings.

    Module-level and outside the class on purpose: the screen must not
    reach into a domain object (§6.1). The caller maps its slots through
    this and hands the result to render().

    An empty (or corrupt, or future-version) slot becomes
    ["SLOT n", "EMPTY SLOT", "—"].
    """
    label = slot.get_label()
    if slot.is_empty():
        return [label, EMPTY_TEXT, EMPTY_FIELD]
    name = str(slot.get_player_name() or "-")[:MAX_NAME_CHARS]
    details = (f"{name} · Sem {slot.get_semester()} · "
               f"{slot.get_credits()}/{CREDIT_GOAL} cr · "
               f"{slot.get_days_remaining()}/{SEMESTER_DAYS} d · "
               f"{format_wallet(slot.get_wallet())}")
    return [label, details, format_saved_at(slot.get_saved_at())]


class LoadGameScreen:
    """
    Draws the save-slot table.

    Rows arrive as plain strings, already formatted -- the screen has no
    idea what a save file is. Selection is passed in per frame, so the
    caller stays the single source of truth for what is highlighted.
    """

    def __init__(self, screen_w: int = 1280, screen_h: int = 720,
                 audio=None) -> None:
        """Load fonts and fix the three button rects."""
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h
        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)
        self.__audio = audio

        self.__load_rect: pygame.Rect = pygame.Rect(
            TABLE_X, BTN_Y, BTN_W, BTN_H)
        self.__delete_rect: pygame.Rect = pygame.Rect(
            TABLE_X + BTN_W + BTN_GAP, BTN_Y, BTN_W, BTN_H)
        self.__back_rect: pygame.Rect = pygame.Rect(
            TABLE_X + TABLE_W - BTN_W, BTN_Y, BTN_W, BTN_H)

    # -- loading helpers --------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    # -- rectangle getters (for click detection outside this file) ---
    def __row_rect(self, index: int) -> pygame.Rect:
        """The rectangle for the i-th slot row."""
        return pygame.Rect(TABLE_X, FIRST_ROW_Y + index * ROW_PITCH,
                           TABLE_W, ROW_H)

    def get_slot_row_rects(self, count: int) -> List[pygame.Rect]:
        """One rectangle per slot row, so clicks can be matched."""
        return [self.__row_rect(i) for i in range(max(0, int(count)))]

    def get_row_index_at(self, pos: tuple, count: int) -> int:
        """Index of the row under a screen position, or -1."""
        for index, rect in enumerate(self.get_slot_row_rects(count)):
            if rect.collidepoint(pos):
                return index
        return -1

    def get_load_rect(self) -> pygame.Rect:
        """The LOAD button."""
        return self.__load_rect

    def get_delete_rect(self) -> pygame.Rect:
        """The DELETE button."""
        return self.__delete_rect

    def get_back_rect(self) -> pygame.Rect:
        """The BACK button."""
        return self.__back_rect

    # -- audio hooks (optional, F1 convention) ----------------
    def notify_selected(self) -> None:
        """Play the focus-move cue."""
        if self.__audio:
            self.__audio.play_sfx("select")

    def notify_clicked(self) -> None:
        """Play the click cue."""
        if self.__audio:
            self.__audio.play_sfx("click")

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, rows: Sequence[Sequence[str]],
               selected_index: int, can_load: bool = True,
               can_delete: bool = True) -> None:
        """
        Draw the slot table from the state handed in.

        rows           : one [slot, details, saved] triple per slot,
                         already formatted by format_slot_row()
        selected_index : which row is highlighted, or -1 for none
        can_load       : draws LOAD muted when there is nothing to load
        can_delete     : draws DELETE muted when there is nothing to erase
        """
        screen.fill(PANEL_TAN)
        self.__draw_card(screen)

        screen.blit(self.__font_title.render(TITLE_TEXT, True, TITLE_SLATE),
                    (TABLE_X, TITLE_Y))

        self.__draw_header(screen)
        for index, cells in enumerate(rows):
            self.__draw_row(screen, index, cells, index == selected_index)

        self.__draw_button(screen, self.__load_rect, "LOAD", BTN_CONFIRM,
                           can_load)
        self.__draw_button(screen, self.__delete_rect, "DELETE", BTN_CANCEL,
                           can_delete)
        self.__draw_button(screen, self.__back_rect, "BACK", HEADER_TAN, True)

    # -- piece-by-piece drawing -------------------------------
    def __draw_card(self, screen: pygame.Surface) -> None:
        """Draw the framed card, inner border, and corner marks."""
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

    def __draw_header(self, screen: pygame.Surface) -> None:
        """Draw the 34 px header bar with the three column titles."""
        bar = pygame.Rect(TABLE_X, HEADER_Y, TABLE_W, HEADER_H)
        pygame.draw.rect(screen, HEADER_TAN, bar)
        pygame.draw.rect(screen, BORDER_BROWN, bar, 2)
        self.__draw_column_separators(screen, bar)

        cy = bar.y + (HEADER_H - self.__font_body.get_height()) // 2
        for title, x in zip(COLUMN_TITLES,
                            (COL_SLOT_X, COL_DETAILS_X, COL_SAVED_X)):
            screen.blit(self.__font_body.render(title, True, TEXT_COFFEE),
                        (x, cy))

    def __draw_column_separators(self, screen: pygame.Surface,
                                 rect: pygame.Rect) -> None:
        """Draw the two 2 px column dividers through a header or row."""
        for x in (SEP_1_X, SEP_2_X):
            pygame.draw.line(screen, BORDER_BROWN,
                             (x, rect.y), (x, rect.bottom - 1), 2)

    def __draw_row(self, screen: pygame.Surface, index: int,
                   cells: Sequence[str], selected: bool) -> None:
        """Draw one slot row and its three cells."""
        row = self.__row_rect(index)
        is_empty = len(cells) > 1 and cells[1] == EMPTY_TEXT

        pygame.draw.rect(screen, ROW_BLUE if selected else ROW_WHITE, row)
        pygame.draw.rect(screen, BORDER_BROWN, row, 2)
        self.__draw_column_separators(screen, row)

        if selected:
            colour = ROW_WHITE
        elif is_empty:
            colour = STAT_BROWN
        else:
            colour = TEXT_COFFEE

        cy = row.y + (ROW_H - self.__font_body.get_height()) // 2
        limits = (SEP_1_X - COL_SLOT_X - 10,
                  SEP_2_X - COL_DETAILS_X - 10,
                  row.right - COL_SAVED_X - 10)
        for cell, x, limit in zip(cells,
                                  (COL_SLOT_X, COL_DETAILS_X, COL_SAVED_X),
                                  limits):
            screen.blit(self.__font_body.render(
                self.__truncate(str(cell), limit), True, colour), (x, cy))

    def __truncate(self, text: str, max_px: int) -> str:
        """
        Clip an over-long cell with an ellipsis.

        The style guide forbids reflow inside a row (§3), so a cell that
        does not fit is shortened rather than wrapped into the next one.
        """
        if max_px <= 0:
            return ""
        if self.__font_body.size(text)[0] <= max_px:
            return text
        while text and self.__font_body.size(text + "...")[0] > max_px:
            text = text[:-1]
        return text + "..."

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, colour: tuple, enabled: bool) -> None:
        """
        Draw a labelled button. A disabled one desaturates toward the
        panel tan instead of changing shape (§4.6).
        """
        if enabled:
            fill = colour
            text_colour = TEXT_COFFEE
        else:
            fill = tuple(int(c + (PANEL_TAN[i] - c) * 0.6)
                         for i, c in enumerate(colour))
            text_colour = STAT_BROWN
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, 3)
        surface = self.__font_body.render(label, True, text_colour)
        screen.blit(surface, (rect.centerx - surface.get_width() // 2,
                              rect.centery - surface.get_height() // 2))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   UP / DOWN or hover -> select a row
#   LOAD               -> prints the slot that would be loaded
#   DELETE             -> ui.popup.ConfirmPopup, then really deletes it
#   BACK               -> prints BACK
#   W                  -> write a fake save into the selected slot
#   F11                -> toggle windowed / fullscreen
#   ESC                -> quit
#
# This runs against a REAL SaveManager pointed at a throwaway
# temporary directory, never at the project's saves/ folder, so the
# round trip is genuine and nobody's playthrough is at risk.
# -------------------------------------------------------------
if __name__ == "__main__":
    import shutil
    import sys
    import tempfile

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    from engine.save_manager import SaveManager, build_state
    from ui.popup import RESULT_CONFIRM, SEVERITY_DANGER, ConfirmPopup

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Load game screen test")

    workspace = tempfile.mkdtemp(prefix="cse_life_saves_")
    manager = SaveManager(workspace)
    screen_ui = LoadGameScreen(*SIZE)
    confirm = ConfirmPopup(*SIZE)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    # Two slots start populated so the table shows both states at once.
    manager.save(1, build_state(display_name="Nangiba", current_semester=7,
                                accumulated_credits=84, time_pool_days=46,
                                wallet_balance=48200.0,
                                level_id="campus_main"))
    manager.autosave(build_state(display_name="Nangiba", current_semester=7,
                                 accumulated_credits=84, time_pool_days=46,
                                 wallet_balance=48200.0,
                                 level_id="campus_main"))

    slots = manager.list_slots()
    selected = 0
    last_action = "-"

    def refresh() -> None:
        """Re-read every slot from disk after a write or a delete."""
        global slots
        slots = manager.list_slots()

    running = True
    while running:
        rows = [format_slot_row(slot) for slot in slots]
        chosen = slots[selected] if 0 <= selected < len(slots) else None
        has_save = chosen is not None and not chosen.is_empty()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            # The popup eats every event while it is open (§4.7).
            if confirm.handle_event(event):
                if confirm.take_result() == RESULT_CONFIRM and chosen:
                    ok = manager.delete(chosen.get_slot_id())
                    last_action = (f"DELETE {chosen.get_label()} -> {ok}"
                                   if ok else
                                   f"DELETE failed: "
                                   f"{manager.get_last_error()}")
                    print(last_action)
                    refresh()
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    window = pygame.display.set_mode(
                        SIZE, FULLSCREEN_FLAGS if is_fullscreen
                        else WINDOWED_FLAGS)
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(slots)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(slots)
                elif event.key == pygame.K_w and chosen is not None:
                    manager.save(chosen.get_slot_id(), build_state(
                        display_name="Rafi", current_semester=3,
                        accumulated_credits=42, time_pool_days=61,
                        wallet_balance=4500.0, level_id="campus_main"))
                    last_action = f"WROTE {chosen.get_label()}"
                    print(last_action)
                    refresh()

            elif event.type == pygame.MOUSEMOTION:
                index = screen_ui.get_row_index_at(event.pos, len(slots))
                if index >= 0:
                    selected = index

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                index = screen_ui.get_row_index_at(event.pos, len(slots))
                if index >= 0:
                    selected = index
                elif screen_ui.get_load_rect().collidepoint(event.pos):
                    if has_save:
                        state = manager.load(chosen.get_slot_id())
                        last_action = (f"LOAD {chosen.get_label()} -> "
                                       f"{'ok' if state else 'failed'}")
                        print(last_action)
                elif screen_ui.get_delete_rect().collidepoint(event.pos):
                    if has_save:
                        confirm.open(
                            "DELETE SAVE?",
                            [f"{chosen.get_label()} will be erased.",
                             "This cannot be undone."],
                            SEVERITY_DANGER)
                elif screen_ui.get_back_rect().collidepoint(event.pos):
                    last_action = "BACK"
                    print(last_action)

        screen_ui.render(window, rows, selected, has_save, has_save)

        window.blit(hint_font.render(
            f"save dir: {os.path.basename(workspace)}   |   last: "
            f"{last_action}", True, STAT_BROWN), (TABLE_X, 110))

        hint = hint_font.render(
            "arrows / hover = select  |  W writes a save  |  LOAD / DELETE"
            "  |  F11 fullscreen  |  ESC quit", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        confirm.render(window)

        pygame.display.flip()
        clock.tick(60)

    shutil.rmtree(workspace, ignore_errors=True)
    pygame.quit()

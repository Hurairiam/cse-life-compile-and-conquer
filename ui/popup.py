"""
ui/popup.py
CSE Life: Compile & Conquer — Shared game-side modals, phase F0
─────────────────────────────────────────────────────────────
The blocking message and confirmation boxes the game screens
share: Modal (the base), MessagePopup (one OK) and
ConfirmPopup (CONFIRM / CANCEL).

This file has NO game logic. A popup is *shown* by the UI but
*decided* by the caller — the modal records which button was
pressed and nothing else. Deleting a save, spending days at a
gate or discarding settings all happen outside this file
(UI_STYLE_GUIDE §6.1).

While a modal is open it consumes every event, so the screen
underneath cannot be clicked through it (§4.7). Callers check
consumes_input() before handling their own input.

Self-contained by owner ruling (Build Plan §0.5): the palette
and layout constants below are copied verbatim from
UI_STYLE_GUIDE.md §2-§4 rather than imported from another
screen. The editor keeps its own, separate Modal inside
tools/editor_popups.py (Build Plan §1.5.1); the two are
deliberately not unified.

Adapted from the quarry's main_menu_system/confirm_popup.py.
Layout, severity theming + test by Nangiba Tasnim (Dev 3).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Tuple

import pygame

# -------------------------------------------------------------
# PATHS
# -------------------------------------------------------------
# Anchored to this file so the font resolves the same way whatever
# directory the game was launched from.
# -------------------------------------------------------------
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues.
PANEL_TAN     = (231, 214, 189)   # only used by this file's stub test
CARD_TAN      = (240, 228, 208)   # the popup box fill
HEADER_TAN    = (214, 196, 168)   # neutral button fill
BORDER_BROWN  = (169, 130, 94)    # button outlines, neutral severity accent
TEXT_COFFEE   = (74, 53, 39)      # body lines and button labels
STAT_BROWN    = (140, 110, 85)    # muted secondary text
BAR_AMBER     = (217, 169, 106)   # warning severity accent
BAR_OVER      = (186, 74, 62)     # danger severity accent (§2.2)
BTN_CONFIRM   = (150, 180, 125)   # confirm button fill
BTN_CANCEL    = (199, 123, 107)   # cancel button fill
HINT_BROWN    = (150, 125, 100)   # stub-test hint line only

OVERLAY_RGBA  = (25, 18, 12, 160)  # modal dim overlay (§2.6)

# Severity accents, so callers name an intent instead of an RGB triple.
SEVERITY_DANGER: Tuple[int, int, int] = BAR_OVER
SEVERITY_WARNING: Tuple[int, int, int] = BAR_AMBER
SEVERITY_INFO: Tuple[int, int, int] = BORDER_BROWN

# -------------------------------------------------------------
# LAYOUT  (UI_STYLE_GUIDE §4.7 — fixed pixel constants)
# -------------------------------------------------------------
BOX_W          = 600        # default popup width
BOX_H          = 224        # default popup height
BORDER_W       = 4          # popup frame, thicker than a card's 3 px
TITLE_Y        = 30         # title baseline, from the box top
FIRST_LINE_Y   = 78         # first body line, from the box top
LINE_PITCH     = 26         # gap between body lines
MAX_BODY_LINES = 3          # §4.7 allows 2-3 centred lines

BTN_W          = 160        # button strip width
BTN_H          = 44         # every button is 44 px tall (§4.6)
BTN_GAP        = 22         # gap between CONFIRM and CANCEL
BTN_BOTTOM_GAP = 24         # gap from the buttons to the box bottom
BORDER_BTN     = 3          # button outline weight

SIZE_TITLE     = 16         # popup title
SIZE_BODY      = 11         # body lines and button labels

# Result codes. get_result() returns one of these, or None while the
# popup is still open and undecided.
RESULT_OK      = "ok"
RESULT_CONFIRM = "confirm"
RESULT_CANCEL  = "cancel"
VALID_RESULTS: Tuple[str, ...] = (RESULT_OK, RESULT_CONFIRM, RESULT_CANCEL)

_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def load_font(size: int) -> pygame.font.Font:
    """
    Return the pixel font at `size`, cached across the module.

    Falls back to the mandatory Courier substitute so a missing TTF
    can never crash a popup (UI_STYLE_GUIDE §3).
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


class Modal:
    """
    The base modal: dim overlay, centred card, ALL-CAPS title in the
    severity colour, up to three centred body lines, button strip.

    Subclasses decide only which buttons exist. Everything else —
    geometry, the overlay, the title, the body, the result bookkeeping
    and the input firewall — lives here so the two game popups can
    never drift apart visually.
    """

    def __init__(self, screen_w: int, screen_h: int,
                 box_w: int = BOX_W, box_h: int = BOX_H) -> None:
        """Centre a `box_w` x `box_h` popup inside the given screen."""
        self.__screen_w: int = int(screen_w)
        self.__screen_h: int = int(screen_h)
        self.__box_rect: pygame.Rect = pygame.Rect(
            (self.__screen_w - box_w) // 2, (self.__screen_h - box_h) // 2,
            box_w, box_h)

        buttons_y = self.__box_rect.bottom - BTN_BOTTOM_GAP - BTN_H
        centre_x = self.__box_rect.centerx
        self.__confirm_rect: pygame.Rect = pygame.Rect(
            centre_x - BTN_GAP // 2 - BTN_W, buttons_y, BTN_W, BTN_H)
        self.__cancel_rect: pygame.Rect = pygame.Rect(
            centre_x + BTN_GAP // 2, buttons_y, BTN_W, BTN_H)
        self.__ok_rect: pygame.Rect = pygame.Rect(
            centre_x - BTN_W // 2, buttons_y, BTN_W, BTN_H)

        self.__open: bool = False
        self.__title: str = ""
        self.__lines: List[str] = []
        self.__accent: Tuple[int, int, int] = SEVERITY_DANGER
        self.__result: Optional[str] = None

    # -- opening and closing ----------------------------------
    def open(self, title: str, lines: Sequence[str],
             accent: Tuple[int, int, int] = SEVERITY_DANGER) -> None:
        """
        Show the popup with a title, body lines and a severity accent.

        More than three lines are dropped rather than overflowing the
        box — §4.7 fixes the height, and callers pre-split their text.
        """
        self.__title = str(title).upper()
        self.__lines = [str(line) for line in lines][:MAX_BODY_LINES]
        self.__accent = accent
        self.__result = None
        self.__open = True

    def close(self) -> None:
        """Hide the popup, keeping the last result readable."""
        self.__open = False

    def is_open(self) -> bool:
        """True while the popup is showing."""
        return self.__open

    def consumes_input(self) -> bool:
        """
        True while the popup must swallow every event (§4.7).

        Callers check this before running their own input handling, so
        a click can never fall through onto the screen underneath.
        """
        return self.__open

    # -- result -----------------------------------------------
    def get_result(self) -> Optional[str]:
        """The button that was pressed, or None while undecided."""
        return self.__result

    def set_result(self, result: Optional[str]) -> bool:
        """
        Record a result and close the popup.

        Returns False for an unknown code, leaving the popup exactly as
        it was — a bad value never corrupts modal state (§0.8).
        Passing None clears the result without closing.
        """
        if result is None:
            self.__result = None
            return True
        if result not in VALID_RESULTS:
            return False
        self.__result = result
        self.__open = False
        return True

    def take_result(self) -> Optional[str]:
        """Read the result once and clear it, so it fires exactly once."""
        result, self.__result = self.__result, None
        return result

    # -- content getters --------------------------------------
    def get_title(self) -> str:
        """The ALL-CAPS title currently shown."""
        return self.__title

    def get_lines(self) -> List[str]:
        """The body lines currently shown."""
        return list(self.__lines)

    def get_accent(self) -> Tuple[int, int, int]:
        """The severity colour driving the border and title."""
        return self.__accent

    # -- rectangle getters (for click detection outside this file) ---
    def get_box_rect(self) -> pygame.Rect:
        """The popup box rectangle."""
        return self.__box_rect

    def get_confirm_rect(self) -> pygame.Rect:
        """The CONFIRM button rectangle (left of centre)."""
        return self.__confirm_rect

    def get_cancel_rect(self) -> pygame.Rect:
        """The CANCEL button rectangle (right of centre)."""
        return self.__cancel_rect

    def get_ok_rect(self) -> pygame.Rect:
        """The single OK button rectangle (centred)."""
        return self.__ok_rect

    # -- input ------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Route one event. Returns True whenever the popup consumed it.

        A closed popup consumes nothing. An open one consumes
        everything, which is the whole point of a modal.
        """
        if not self.__open:
            return False
        self._handle_open_event(event)
        return True

    def _handle_open_event(self, event: pygame.event.Event) -> None:
        """Subclass hook: interpret one event while the popup is open."""
        raise NotImplementedError

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface) -> None:
        """Draw the overlay, the box, the title, the body and the buttons."""
        if not self.__open:
            return
        self.__draw_overlay(screen)
        pygame.draw.rect(screen, CARD_TAN, self.__box_rect)
        pygame.draw.rect(screen, self.__accent, self.__box_rect, BORDER_W)

        self._blit_centred(screen, load_font(SIZE_TITLE), self.__title,
                           self.__accent, self.__box_rect.centerx,
                           self.__box_rect.y + TITLE_Y)
        body_font = load_font(SIZE_BODY)
        for index, line in enumerate(self.__lines):
            self._blit_centred(screen, body_font, line, TEXT_COFFEE,
                               self.__box_rect.centerx,
                               self.__box_rect.y + FIRST_LINE_Y
                               + index * LINE_PITCH)
        self._draw_buttons(screen)

    def _draw_buttons(self, screen: pygame.Surface) -> None:
        """Subclass hook: draw the button strip."""
        raise NotImplementedError

    def __draw_overlay(self, screen: pygame.Surface) -> None:
        """Dim the whole screen behind the box (§2.6)."""
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill(OVERLAY_RGBA)
        screen.blit(shade, (0, 0))

    def _draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                     label: str, colour: Tuple[int, int, int]) -> None:
        """Draw one flat button: fill, 3 px border, ALL-CAPS label (§4.6)."""
        pygame.draw.rect(screen, colour, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_BTN)
        font = load_font(SIZE_BODY)
        rendered = font.render(label.upper(), True, TEXT_COFFEE)
        screen.blit(rendered, (rect.centerx - rendered.get_width() // 2,
                               rect.centery - rendered.get_height() // 2))

    def _blit_centred(self, screen: pygame.Surface, font: pygame.font.Font,
                      text: str, colour: Tuple[int, int, int],
                      centre_x: int, y: int) -> None:
        """Draw text horizontally centred on `centre_x` at `y`."""
        rendered = font.render(text, True, colour)
        screen.blit(rendered, (centre_x - rendered.get_width() // 2, y))


class MessagePopup(Modal):
    """
    A one-button notice: "TOO MANY CREDITS", "SAVE FAILED", a prop
    reward line. There is nothing to decide, only something to read,
    so it closes on OK, ENTER, SPACE or ESC alike.
    """

    def __init__(self, screen_w: int, screen_h: int,
                 box_w: int = BOX_W, box_h: int = BOX_H) -> None:
        """Centre a message popup inside the given screen."""
        super().__init__(screen_w, screen_h, box_w, box_h)
        self.__ok_label: str = "OK"
        self.__ok_colour: Tuple[int, int, int] = BTN_CANCEL

    def open(self, title: str, lines: Sequence[str],
             accent: Tuple[int, int, int] = SEVERITY_DANGER,
             ok_label: str = "OK",
             ok_colour: Tuple[int, int, int] = BTN_CANCEL) -> None:
        """Show the notice, optionally relabelling or recolouring OK."""
        self.__ok_label = str(ok_label).upper()
        self.__ok_colour = ok_colour
        super().open(title, lines, accent)

    def get_ok_label(self) -> str:
        """The label currently drawn on the OK button."""
        return self.__ok_label

    def _handle_open_event(self, event: pygame.event.Event) -> None:
        """OK, ENTER, SPACE or ESC all dismiss the notice."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.get_ok_rect().collidepoint(event.pos):
                self.set_result(RESULT_OK)
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                             pygame.K_SPACE, pygame.K_ESCAPE):
                self.set_result(RESULT_OK)

    def _draw_buttons(self, screen: pygame.Surface) -> None:
        """Draw the single centred OK button."""
        self._draw_button(screen, self.get_ok_rect(), self.__ok_label,
                          self.__ok_colour)


class ConfirmPopup(Modal):
    """
    A two-button question: "DELETE SAVE?", "EXIT GAME?", "ENTER
    (-10 DAYS)?".

    The popup records CONFIRM or CANCEL. Whether the save is actually
    deleted or the days are actually charged is decided by the engine,
    never here.
    """

    def __init__(self, screen_w: int, screen_h: int,
                 box_w: int = BOX_W, box_h: int = BOX_H) -> None:
        """Centre a confirmation popup inside the given screen."""
        super().__init__(screen_w, screen_h, box_w, box_h)
        self.__confirm_label: str = "CONFIRM"
        self.__cancel_label: str = "CANCEL"
        self.__confirm_colour: Tuple[int, int, int] = BTN_CANCEL
        self.__cancel_colour: Tuple[int, int, int] = HEADER_TAN

    def open(self, title: str, lines: Sequence[str],
             accent: Tuple[int, int, int] = SEVERITY_DANGER,
             confirm_label: str = "CONFIRM",
             cancel_label: str = "CANCEL",
             confirm_colour: Tuple[int, int, int] = BTN_CANCEL,
             cancel_colour: Tuple[int, int, int] = HEADER_TAN) -> None:
        """
        Show the question.

        The confirm button defaults to the terracotta cancel colour
        because most confirmations in this game are destructive
        (delete a save, discard settings, quit). A constructive
        confirmation passes BTN_CONFIRM instead.
        """
        self.__confirm_label = str(confirm_label).upper()
        self.__cancel_label = str(cancel_label).upper()
        self.__confirm_colour = confirm_colour
        self.__cancel_colour = cancel_colour
        super().open(title, lines, accent)

    def get_confirm_label(self) -> str:
        """The label currently drawn on the CONFIRM button."""
        return self.__confirm_label

    def get_cancel_label(self) -> str:
        """The label currently drawn on the CANCEL button."""
        return self.__cancel_label

    def _handle_open_event(self, event: pygame.event.Event) -> None:
        """Click either button; ENTER confirms, ESC cancels."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.get_confirm_rect().collidepoint(event.pos):
                self.set_result(RESULT_CONFIRM)
            elif self.get_cancel_rect().collidepoint(event.pos):
                self.set_result(RESULT_CANCEL)
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.set_result(RESULT_CONFIRM)
            elif event.key == pygame.K_ESCAPE:
                self.set_result(RESULT_CANCEL)

    def _draw_buttons(self, screen: pygame.Surface) -> None:
        """Draw the CONFIRM / CANCEL strip."""
        self._draw_button(screen, self.get_confirm_rect(),
                          self.__confirm_label, self.__confirm_colour)
        self._draw_button(screen, self.get_cancel_rect(),
                          self.__cancel_label, self.__cancel_colour)


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   SPACE  -> next case (message -> confirm -> warning -> info)
#   Click a button, or ENTER / ESC -> resolves and prints the result
#   R      -> reopen the current case
#   F11    -> toggle windowed / fullscreen
#   ESC    -> resolves the popup; ESC again with none open quits
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Popup test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    message = MessagePopup(*SIZE)
    confirm = ConfirmPopup(*SIZE)

    # (kind, title, lines, accent, confirm colour) -- the severity ladder.
    cases = [
        ("message", "TOO MANY CREDITS",
         ["You can register a maximum of", "15 credits per semester.",
          "Deselect a course and try again."],
         SEVERITY_DANGER, BTN_CANCEL),
        ("confirm", "DELETE SAVE?",
         ["Slot 2 will be erased.", "This cannot be undone."],
         SEVERITY_DANGER, BTN_CANCEL),
        ("confirm", "UNSAVED CHANGES",
         ["Your settings have not been applied.", "Discard them?"],
         SEVERITY_WARNING, BTN_CANCEL),
        ("confirm", "ENTER LAB BLOCK?",
         ["Entry costs 10 days.", "You have 46 days left."],
         SEVERITY_INFO, BTN_CONFIRM),
        ("message", "PROGRESS SAVED",
         ["Slot 1 updated."], SEVERITY_INFO, BTN_CONFIRM),
    ]
    index = 0
    last_result = "-"

    def _show(case_index: int) -> None:
        """Open whichever popup this case calls for."""
        kind, title, lines, accent, confirm_colour = cases[case_index]
        if kind == "message":
            message.open(title, lines, accent, "OK", confirm_colour)
        else:
            confirm.open(title, lines, accent, "CONFIRM", "CANCEL",
                         confirm_colour, HEADER_TAN)

    def _active() -> Modal:
        """Whichever popup this case is using."""
        return message if cases[index][0] == "message" else confirm

    _show(index)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            popup = _active()
            if popup.handle_event(event):
                result = popup.take_result()
                if result is not None:
                    last_result = f"{cases[index][1]} -> {result}"
                    print(last_result)
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    flags = (FULLSCREEN_FLAGS if is_fullscreen
                             else WINDOWED_FLAGS)
                    window = pygame.display.set_mode(SIZE, flags)
                elif event.key == pygame.K_SPACE:
                    index = (index + 1) % len(cases)
                    _show(index)
                elif event.key == pygame.K_r:
                    _show(index)

        window.fill(PANEL_TAN)
        title_font = load_font(SIZE_TITLE)
        window.blit(title_font.render("POPUP GALLERY", True, TEXT_COFFEE),
                    (60, 60))
        body_font = load_font(SIZE_BODY)
        window.blit(body_font.render(f"CASE {index + 1} / {len(cases)}",
                                     True, STAT_BROWN), (60, 108))
        window.blit(body_font.render(f"LAST RESULT: {last_result}", True,
                                     STAT_BROWN), (60, 138))
        if not _active().is_open():
            window.blit(body_font.render("PRESS R TO REOPEN", True,
                                         STAT_BROWN), (60, 168))

        message.render(window)
        confirm.render(window)

        hint = hint_font.render(
            "SPACE next case  |  R reopen  |  click / ENTER / ESC resolve"
            "  |  F11 fullscreen", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

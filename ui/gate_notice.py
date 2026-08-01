"""
ui/gate_notice.py
CSE Life: Compile & Conquer — phase F8  (Feature 6, the player's view)
─────────────────────────────────────────────────────────────
The popup a player meets at a locked door: the door's ALL-CAPS
title, a lock icon, a two-column requirement table (what the door
asks for / what you have), the author's flavour lines, and — once
every requirement is met and a toll applies — an ENTER / CANCEL
confirmation naming the cost.

This file has NO game logic. It never weighs a gate, never charges
a player, never decides whether the door opens. engine/gate_evaluator.py
makes those calls and hands this popup finished values; the popup only
draws them and records which button was pressed
(UI_STYLE_GUIDE §6.1).

It extends ui/popup.py::Modal — one of the two shared game-side
modules the Build Plan allows (§0.5, §1.5.1) — for the overlay,
the result bookkeeping and the input firewall, but declares its
OWN palette and layout blocks below (copied verbatim from
UI_STYLE_GUIDE.md §2-§4) and draws its own requirement table, so
it never imports another screen's colours.

Layout + tests by Nangiba Tasnim (Dev 3), branch nangiba-temp-01.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Tuple

import pygame

from ui.popup import (RESULT_CANCEL, RESULT_CONFIRM, RESULT_OK, Modal)

# -------------------------------------------------------------
# PATHS
# -------------------------------------------------------------
# Anchored to this file, never the working directory, so the font and
# the lock icon resolve the same way whatever launched the game.
# -------------------------------------------------------------
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")
LOCK_ICON_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui", "icon_lock.png")

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues (§0.5).
CARD_TAN      = (240, 228, 208)   # the popup box fill
HEADER_TAN    = (214, 196, 168)   # table header strip
BORDER_BROWN  = (169, 130, 94)    # every outline and column separator
TEXT_COFFEE   = (74, 53, 39)      # requirement text, button labels
STAT_BROWN    = (140, 110, 85)    # column captions, flavour lines
BAR_OVER      = (186, 74, 62)     # danger severity: title + 4 px frame (§2.2)
BAR_RED       = (199, 123, 107)   # unmet-row outline (§2.2)
ROW_WHITE     = (247, 243, 236)   # an unmet requirement row
ROW_GREEN     = (150, 180, 125)   # a met requirement row
BTN_CONFIRM   = (150, 180, 125)   # ENTER button fill
BTN_CANCEL    = (199, 123, 107)   # CANCEL / CLOSE button fill
PLACEHOLDER   = (196, 178, 150)   # square drawn where the lock PNG is missing
PORTRAIT_LABEL = (120, 95, 75)    # faded caption inside a placeholder square
PANEL_TAN     = (231, 214, 189)   # stub-test background only
HINT_BROWN    = (150, 125, 100)   # stub-test hint line only

# -------------------------------------------------------------
# LAYOUT  (UI_STYLE_GUIDE §4 — fixed pixel constants)
# -------------------------------------------------------------
BOX_W          = 680        # wider than a plain popup to fit the table
BOX_H          = 452
BORDER_W       = 4          # popup frame, thicker than a card's 3 px (§4.7)
PAD            = 26         # inset from the box edge to its content

ICON_SIZE      = 24         # the lock icon, per §5.3
TITLE_TOP      = 24         # title baseline from the box top
TITLE_GAP      = 12         # gap between the icon and the title text

CAPTION_Y      = 74         # the REQUIREMENT / YOU HAVE column captions
TABLE_TOP      = 96         # first requirement row, from the box top
ROW_H          = 30         # requirement row height (§4.4)
ROW_PITCH      = 36         # row height + a 6 px gap
BORDER_ROW     = 2          # row borders and column separators (§4.4)
COL_SPLIT      = 0.60       # the YOU HAVE column starts at 60 % of the row
MAX_ROWS       = 7          # more than this and the door is over-authored

FLAVOUR_PITCH  = 24         # gap between flavour lines
MAX_FLAVOUR    = 3          # matches GateData's locked-lines cap

BTN_H          = 44         # every button is 44 px tall (§4.6)
BTN_GAP        = 22         # gap inside the button strip
BTN_BOTTOM_GAP = 24         # gap from the strip to the box bottom
BORDER_BTN     = 3          # button outline weight
CONFIRM_W      = 320        # the ENTER button carries a long cost label
CANCEL_W       = 160
OK_W           = 220        # the single CLOSE button on a locked door

SIZE_TITLE     = 16         # popup title
SIZE_ROW       = 11         # requirement rows and button labels
SIZE_CAPTION   = 10         # column captions and flavour lines

# The two things this popup can be: a wall you cannot pass yet, or a
# toll you may choose to pay.
MODE_LOCKED: str = "locked"
MODE_CONFIRM: str = "confirm"

_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def load_font(size: int) -> pygame.font.Font:
    """
    Return the pixel font at `size`, cached across the module.

    Falls back to the mandatory Courier substitute so a missing TTF can
    never crash the notice (UI_STYLE_GUIDE §3). Self-contained rather
    than imported, so this popup runs with no other new file present.
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


def format_cost_label(costs: Tuple[int, float]) -> str:
    """
    The ENTER button's label for a (days, money) cost.

    `(10, 1000.0)` -> `ENTER (-10 DAYS, -1,000 BDT)`; a single cost drops
    the comma; a free door is just `ENTER`. Kept here, not in the caller,
    so the button and any confirmation text read identically.
    """
    days, money = int(costs[0]), float(costs[1])
    parts: List[str] = []
    if days > 0:
        parts.append(f"-{days} DAY" + ("" if days == 1 else "S"))
    if money > 0:
        parts.append(f"-{money:,.0f} BDT")
    if not parts:
        return "ENTER"
    return "ENTER (" + ", ".join(parts) + ")"


class GateNotice(Modal):
    """
    The locked-door popup. Two modes, chosen by the caller:

        MODE_LOCKED   the door is shut — a requirement table and one
                      CLOSE button; the player cannot pass.
        MODE_CONFIRM  every requirement is met and a toll applies —
                      the same table (now all green) plus ENTER / CANCEL
                      naming the cost.

    Everything drawn is handed to render(); the popup stores only which
    mode it is in (for input) and the Modal open/result state it
    inherits. gate_locked / confirm SFX are the caller's to fire.
    """

    def __init__(self, screen_w: int, screen_h: int) -> None:
        """Centre the notice inside the given screen and size its buttons."""
        super().__init__(screen_w, screen_h, BOX_W, BOX_H)
        self.__mode: str = MODE_LOCKED
        self.__lock_icon: Optional[pygame.Surface] = None
        self.__icon_loaded: bool = False

        # Own button rectangles: Modal's are a fixed 160 px, but the ENTER
        # label carries a full cost string, so the strip is re-laid here.
        box = self.get_box_rect()
        strip_y = box.bottom - BTN_BOTTOM_GAP - BTN_H
        pair_w = CONFIRM_W + BTN_GAP + CANCEL_W
        left = box.centerx - pair_w // 2
        self.__confirm_rect = pygame.Rect(left, strip_y, CONFIRM_W, BTN_H)
        self.__cancel_rect = pygame.Rect(
            left + CONFIRM_W + BTN_GAP, strip_y, CANCEL_W, BTN_H)
        self.__ok_rect = pygame.Rect(
            box.centerx - OK_W // 2, strip_y, OK_W, BTN_H)

    # -- opening ----------------------------------------------
    def open(self, mode: str) -> None:                     # type: ignore[override]
        """
        Show the notice in MODE_LOCKED or MODE_CONFIRM.

        The visible content (title, rows, flavour, costs) is passed to
        render() each frame per §6.1; open() stores only the mode, which
        input handling needs, and reuses Modal's open/result machinery.
        """
        self.__mode = mode if mode in (MODE_LOCKED, MODE_CONFIRM) \
            else MODE_LOCKED
        super().open("", [], BAR_OVER)

    def get_mode(self) -> str:
        """MODE_LOCKED or MODE_CONFIRM — whichever it was opened with."""
        return self.__mode

    # -- own button rectangles --------------------------------
    def get_confirm_rect(self) -> pygame.Rect:
        """The ENTER button rectangle (confirm mode)."""
        return self.__confirm_rect

    def get_cancel_rect(self) -> pygame.Rect:
        """The CANCEL button rectangle (confirm mode)."""
        return self.__cancel_rect

    def get_ok_rect(self) -> pygame.Rect:
        """The single CLOSE button rectangle (locked mode)."""
        return self.__ok_rect

    # -- input ------------------------------------------------
    def _handle_open_event(self, event: pygame.event.Event) -> None:
        """
        Interpret one event for the current mode.

        Confirm mode: ENTER / a click on ENTER confirms; ESC / a click on
        CANCEL backs out. Locked mode: anything that dismisses — OK click,
        ENTER, SPACE or ESC — closes with OK, since a wall offers no choice.
        """
        if self.__mode == MODE_CONFIRM:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.__confirm_rect.collidepoint(event.pos):
                    self.set_result(RESULT_CONFIRM)
                elif self.__cancel_rect.collidepoint(event.pos):
                    self.set_result(RESULT_CANCEL)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.set_result(RESULT_CONFIRM)
                elif event.key == pygame.K_ESCAPE:
                    self.set_result(RESULT_CANCEL)
        else:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.__ok_rect.collidepoint(event.pos):
                    self.set_result(RESULT_OK)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                 pygame.K_SPACE, pygame.K_ESCAPE):
                    self.set_result(RESULT_OK)

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface,               # type: ignore[override]
               title: str = "",
               requirements: Sequence[Tuple[str, str, bool]] = (),
               flavour_lines: Sequence[str] = (),
               costs: Tuple[int, float] = (0, 0.0),
               mode: str = MODE_LOCKED) -> None:
        """
        Draw the whole notice from handed-in values (§6.1).

        `requirements` is a sequence of (label, actual, is_met) rows;
        `flavour_lines` the author's locked text; `costs` the (days, money)
        the ENTER button names in confirm mode. Nothing here is read from
        game state.
        """
        if not self.is_open():
            return
        box = self.get_box_rect()
        self.__draw_overlay(screen)
        pygame.draw.rect(screen, CARD_TAN, box)
        pygame.draw.rect(screen, BAR_OVER, box, BORDER_W)

        self.__draw_title(screen, box, str(title).upper())
        bottom = self.__draw_table(screen, box, requirements)
        self.__draw_flavour(screen, box, flavour_lines, bottom)
        self.__draw_buttons(screen, costs, mode)

    def __draw_overlay(self, screen: pygame.Surface) -> None:
        """Dim the whole screen behind the box (§2.6)."""
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((25, 18, 12, 160))
        screen.blit(shade, (0, 0))

    def __draw_title(self, screen: pygame.Surface, box: pygame.Rect,
                     title: str) -> None:
        """Draw the lock icon and the ALL-CAPS title beside it."""
        icon = self.__get_lock_icon()
        icon_x = box.x + PAD
        icon_y = box.y + TITLE_TOP
        if icon is not None:
            screen.blit(icon, (icon_x, icon_y))
        else:
            self.__draw_placeholder(screen, icon_x, icon_y)
        font = load_font(SIZE_TITLE)
        rendered = font.render(title, True, BAR_OVER)
        screen.blit(rendered, (icon_x + ICON_SIZE + TITLE_GAP,
                               icon_y + (ICON_SIZE - rendered.get_height()) // 2))

    def __draw_table(self, screen: pygame.Surface, box: pygame.Rect,
                     requirements: Sequence[Tuple[str, str, bool]]) -> int:
        """
        Draw the requirement table and return the y just below it.

        Met rows are ROW_GREEN with a plain brown border; unmet rows are
        ROW_WHITE ringed in BAR_RED, so the failures read at a glance
        (§4.4 tri-colour rows). A 2 px column separator splits REQUIREMENT
        from YOU HAVE. An empty list draws nothing — a pure toll has no
        table — and returns the table's top.
        """
        rows = list(requirements)[:MAX_ROWS]
        if not rows:
            return box.y + TABLE_TOP
        cap_font = load_font(SIZE_CAPTION)
        left = box.x + PAD
        width = box.w - PAD * 2
        split_x = left + int(width * COL_SPLIT)
        screen.blit(cap_font.render("REQUIREMENT", True, STAT_BROWN),
                    (left + 6, box.y + CAPTION_Y))
        you_have = cap_font.render("YOU HAVE", True, STAT_BROWN)
        screen.blit(you_have, (split_x + 6, box.y + CAPTION_Y))

        row_font = load_font(SIZE_ROW)
        y = box.y + TABLE_TOP
        for label, actual, is_met in rows:
            rect = pygame.Rect(left, y, width, ROW_H)
            pygame.draw.rect(screen, ROW_GREEN if is_met else ROW_WHITE, rect)
            pygame.draw.rect(screen, BORDER_BROWN if is_met else BAR_RED,
                             rect, BORDER_ROW)
            pygame.draw.line(screen, BORDER_BROWN, (split_x, y),
                             (split_x, y + ROW_H), BORDER_ROW)
            self.__blit_vcenter(screen, row_font, str(label), TEXT_COFFEE,
                                left + 8, rect)
            self.__blit_vcenter(screen, row_font, str(actual), TEXT_COFFEE,
                                split_x + 8, rect)
            y += ROW_PITCH
        return y

    def __draw_flavour(self, screen: pygame.Surface, box: pygame.Rect,
                       flavour_lines: Sequence[str], table_bottom: int) -> None:
        """Draw the author's locked-message lines under the table."""
        font = load_font(SIZE_CAPTION)
        y = table_bottom + 8
        for line in list(flavour_lines)[:MAX_FLAVOUR]:
            text = str(line).strip()
            if not text:
                continue
            screen.blit(font.render(text, True, STAT_BROWN),
                        (box.x + PAD + 2, y))
            y += FLAVOUR_PITCH

    def __draw_buttons(self, screen: pygame.Surface, costs: Tuple[int, float],
                       mode: str) -> None:
        """Draw the confirm strip or the single CLOSE button, per mode."""
        if mode == MODE_CONFIRM:
            self.__draw_button(screen, self.__confirm_rect,
                               format_cost_label(costs), BTN_CONFIRM,
                               SIZE_ROW)
            self.__draw_button(screen, self.__cancel_rect, "CANCEL",
                               BTN_CANCEL, SIZE_ROW)
        else:
            self.__draw_button(screen, self.__ok_rect, "CLOSE",
                               BTN_CANCEL, SIZE_ROW)

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, colour: Tuple[int, int, int],
                      size: int) -> None:
        """One flat button: fill, 3 px border, ALL-CAPS label (§4.6)."""
        pygame.draw.rect(screen, colour, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_BTN)
        font = load_font(size)
        rendered = font.render(label.upper(), True, TEXT_COFFEE)
        screen.blit(rendered, (rect.centerx - rendered.get_width() // 2,
                               rect.centery - rendered.get_height() // 2))

    def __blit_vcenter(self, screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: Tuple[int, int, int],
                       x: int, rect: pygame.Rect) -> None:
        """Draw text left-aligned at `x`, vertically centred in `rect`."""
        rendered = font.render(text, True, colour)
        screen.blit(rendered, (x, rect.centery - rendered.get_height() // 2))

    def __draw_placeholder(self, screen: pygame.Surface, x: int,
                           y: int) -> None:
        """The flat square the placeholder protocol draws for a missing icon."""
        pygame.draw.rect(screen, PLACEHOLDER, (x, y, ICON_SIZE, ICON_SIZE))
        pygame.draw.rect(screen, BORDER_BROWN, (x, y, ICON_SIZE, ICON_SIZE), 2)

    def __get_lock_icon(self) -> Optional[pygame.Surface]:
        """
        The 24×24 lock icon, loaded once, or None while the PNG is missing.

        # [ICON PLACEHOLDER: assets/ui/icon_lock.png — firewall / locked
        #  action, a padlock read at 24×24] (§5.2/§5.3)
        """
        if self.__icon_loaded:
            return self.__lock_icon
        self.__icon_loaded = True
        try:
            surface = pygame.image.load(LOCK_ICON_PATH).convert_alpha()
            self.__lock_icon = pygame.transform.scale(surface,
                                                      (ICON_SIZE, ICON_SIZE))
        except (FileNotFoundError, OSError, pygame.error):
            self.__lock_icon = None
        return self.__lock_icon


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   SPACE  -> next case (locked door -> paid door -> pure toll)
#   click a button, or ENTER / ESC -> resolves and prints the result
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
    pygame.display.set_caption("Gate notice test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    notice = GateNotice(*SIZE)

    # (title, rows, flavour, costs, mode) -- a locked door, a paid door
    # you now qualify for, and a pure toll with no requirements.
    cases = [
        ("LAB WING SEALED",
         [("SEMESTER 5", "NOW 3", False),
          ("CREDITS 60", "NOW 42", False),
          ("DSA LV 4", "NOW LV 1", False)],
         ["The second-year lab wing is not open to you yet.",
          "Come back when you have the credits."],
         (0, 0.0), MODE_LOCKED),
        ("DEAN'S OFFICE",
         [("SEMESTER 5", "NOW 5", True),
          ("CREDITS 60", "NOW 66", True)],
         ["The dean will see you now.", "An appointment is not free."],
         (10, 1000.0), MODE_CONFIRM),
        ("PARKING BARRIER",
         [],
         ["Pay the attendant to raise the barrier."],
         (0, 500.0), MODE_CONFIRM),
    ]
    index = 0
    last_result = "-"

    def _show(case_index: int) -> None:
        """Open the notice in whichever mode this case needs."""
        notice.open(cases[case_index][4])

    _show(index)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if notice.handle_event(event):
                result = notice.take_result()
                if result is not None:
                    last_result = f"{cases[index][0]} -> {result}"
                    print(last_result)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    window = pygame.display.set_mode(
                        SIZE,
                        FULLSCREEN_FLAGS if is_fullscreen else WINDOWED_FLAGS)
                elif event.key == pygame.K_SPACE:
                    index = (index + 1) % len(cases)
                    _show(index)
                elif event.key == pygame.K_r:
                    _show(index)

        window.fill(PANEL_TAN)
        title_font = load_font(SIZE_TITLE)
        window.blit(title_font.render("GATE NOTICE GALLERY", True, TEXT_COFFEE),
                    (60, 60))
        body_font = load_font(SIZE_ROW)
        window.blit(body_font.render(f"CASE {index + 1} / {len(cases)}",
                                     True, STAT_BROWN), (60, 108))
        window.blit(body_font.render(f"LAST RESULT: {last_result}", True,
                                     STAT_BROWN), (60, 138))
        if not notice.is_open():
            window.blit(body_font.render("PRESS R TO REOPEN", True,
                                         STAT_BROWN), (60, 168))

        title, rows, flavour, costs, mode = cases[index]
        notice.render(window, title, rows, flavour, costs, mode)

        hint = hint_font.render(
            "SPACE next case  |  R reopen  |  click / ENTER / ESC resolve"
            "  |  F11 fullscreen", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

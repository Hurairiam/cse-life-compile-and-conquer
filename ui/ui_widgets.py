"""
ui/ui_widgets.py
CSE Life: Compile & Conquer — Shared game-side widgets, phase F0
─────────────────────────────────────────────────────────────
The four controls the game screens are built from: Button,
Slider, ChipRow and RowTable.

This file has NO game logic. A widget owns only its OWN
interaction state (pressed, dragging, selected row, scroll
offset) and draws that state. It never reads the player, the
clock or the course catalog, and it never decides whether an
action is allowed — the screen above it reads a widget's value
and the state manager acts on it.

Self-contained by owner ruling (Build Plan §0.5): the palette
and layout constants below are copied verbatim from
_special_docs/UI_STYLE_GUIDE.md §2-§4 rather than imported from
another screen, so this module runs with no other new file
present. The duplication is deliberate; if a value here ever
disagrees with the style guide, the style guide wins.

The editor keeps its own, larger widget set in
tools/editor_widgets.py (Build Plan §1.5.1). These two are
intentionally NOT unified — ui/ must never import tools/.

Behaviour patterns follow the quarry's editor widgets.
Styling, trimming + tests by Nangiba Tasnim (Dev 3).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Tuple

import pygame

# -------------------------------------------------------------
# PATHS
# -------------------------------------------------------------
# Anchored to this file, never to the working directory: the game
# must find the same font whether it was launched from the repo
# root, from an IDE, or from a shortcut.
# -------------------------------------------------------------
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues.
PANEL_TAN     = (231, 214, 189)   # screen background behind cards
CARD_TAN      = (240, 228, 208)   # card / panel fill
HEADER_TAN    = (214, 196, 168)   # table headers, neutral buttons, chips
BORDER_BROWN  = (169, 130, 94)    # every outline, separator and corner mark
TEXT_COFFEE   = (74, 53, 39)      # primary text
CREDIT_HL     = (155, 110, 70)    # emphasised labels
STAT_BROWN    = (140, 110, 85)    # secondary / muted / disabled text
BAR_TRACK     = (214, 196, 168)   # empty part of a progress bar or track

ROW_WHITE     = (247, 243, 236)   # unselected list row, inactive chip text
ROW_BLUE      = (120, 150, 190)   # selected row, active chip, slider fill
ROW_GREEN     = (150, 180, 125)   # confirmed / locked row

BTN_CONFIRM   = (150, 180, 125)   # confirm buttons
BTN_CANCEL    = (199, 123, 107)   # cancel buttons
BAR_AMBER     = (217, 169, 106)   # warning / at-the-limit accent

PLACEHOLDER   = (196, 178, 150)   # square drawn where art is missing
HINT_BROWN    = (150, 125, 100)   # stub-test hint line only

# -------------------------------------------------------------
# LAYOUT  (UI_STYLE_GUIDE §4 — fixed pixel constants)
# -------------------------------------------------------------
BTN_H         = 44          # every button is 44 px tall (§4.6)
ROW_H         = 38          # table row height (§4.4)
ROW_PITCH     = 44          # row height + the 6 px gap below it
HEADER_H      = 34          # table header bar height
BORDER_CARD   = 3           # card frames and button outlines
BORDER_ROW    = 2           # row borders, bar outlines, separators
SCROLLBAR_W   = 8           # slim scrollbar for overflowing tables

CARD_MARGIN   = 24          # dense-screen card inset
CARD_PAD      = 14          # gap between card and inner border
CORNER_LEN    = 22          # corner bracket arm length

SLIDER_TRACK_H = 16         # slider / progress track height (§4.5)
SLIDER_HANDLE  = 16         # square handle, matching the track height
CHIP_GAP       = 6          # gap between chips in a row

PRESS_DARKEN   = 0.10       # pressed fills darken 10 %, nothing else (§4.6)

SIZE_TITLE    = 28          # screen title
SIZE_TOTAL    = 16          # big number / popup title
SIZE_BODY_LG  = 13          # body, roomy
SIZE_BODY     = 12          # body, buttons, table cells
SIZE_SUB      = 11          # sub-text
SIZE_LABEL    = 10          # labels, hints, chip text

_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def load_font(size: int) -> pygame.font.Font:
    """
    Return the pixel font at `size`, cached across the module.

    Falls back to the mandatory Courier substitute so a missing TTF
    can never crash a screen (UI_STYLE_GUIDE §3).
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


def darken(colour: Tuple[int, int, int],
           amount: float = PRESS_DARKEN) -> Tuple[int, int, int]:
    """
    Darken a fill by `amount` for a pressed state.

    This is the only visual change the style guide permits on a button
    — the shape and the border never move (§4.6).
    """
    return (max(0, int(colour[0] * (1.0 - amount))),
            max(0, int(colour[1] * (1.0 - amount))),
            max(0, int(colour[2] * (1.0 - amount))))


def _blend(a: Tuple[int, int, int], b: Tuple[int, int, int],
           t: float) -> Tuple[int, int, int]:
    """Mix two palette colours — only used to mute a disabled control."""
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def truncate(font: pygame.font.Font, text: str, max_w: int) -> str:
    """
    Clip `text` with a trailing ellipsis until it fits `max_w` pixels.

    The style guide forbids reflow inside a widget (§3), so long cell
    text is shortened, never wrapped.
    """
    if max_w <= 0:
        return ""
    if font.size(text)[0] <= max_w:
        return text
    while text and font.size(text + "...")[0] > max_w:
        text = text[:-1]
    return text + "..."


def _draw_text_centered(surface: pygame.Surface, font: pygame.font.Font,
                        text: str, rect: pygame.Rect,
                        colour: Tuple[int, int, int]) -> None:
    """Draw text centred inside a rectangle."""
    rendered = font.render(text, True, colour)
    surface.blit(rendered, (rect.x + (rect.w - rendered.get_width()) // 2,
                            rect.y + (rect.h - rendered.get_height()) // 2))


def _draw_text_vcenter(surface: pygame.Surface, font: pygame.font.Font,
                       text: str, x: int, rect: pygame.Rect,
                       colour: Tuple[int, int, int]) -> None:
    """Draw text at `x`, vertically centred in a row."""
    rendered = font.render(text, True, colour)
    surface.blit(rendered, (x, rect.y + (rect.h - rendered.get_height()) // 2))


# -------------------------------------------------------------
# BUTTON
# -------------------------------------------------------------


class Button:
    """
    A flat 44 px button: fill, 3 px border, ALL-CAPS centred label.

    The button reports that it was clicked; it never performs the
    action. The screen above it calls take_clicked() and decides what
    that means, which keeps every decision outside ui/ (§6.1, §6.2).
    """

    def __init__(self, rect: pygame.Rect, label: str,
                 fill: Tuple[int, int, int] = BTN_CONFIRM,
                 enabled: bool = True) -> None:
        """Create a button at `rect` with an ALL-CAPS `label`."""
        self.__rect: pygame.Rect = pygame.Rect(rect)
        self.__label: str = label.upper()
        self.__fill: Tuple[int, int, int] = fill
        self.__enabled: bool = bool(enabled)
        self.__pressed: bool = False
        self.__clicked: bool = False

    # -- state ------------------------------------------------
    def get_rect(self) -> pygame.Rect:
        """The button's rectangle, for outside click detection."""
        return self.__rect

    def set_rect(self, rect: pygame.Rect) -> None:
        """Move or resize the button (used when a screen relayouts)."""
        self.__rect = pygame.Rect(rect)

    def get_label(self) -> str:
        """The ALL-CAPS label currently drawn."""
        return self.__label

    def set_label(self, label: str) -> None:
        """Replace the label; it is upper-cased on the way in (§3)."""
        self.__label = str(label).upper()

    def get_fill(self) -> Tuple[int, int, int]:
        """The button's fill colour."""
        return self.__fill

    def set_fill(self, fill: Tuple[int, int, int]) -> None:
        """Re-colour the button (e.g. confirm green to cancel red)."""
        self.__fill = fill

    def is_enabled(self) -> bool:
        """True while the button accepts input."""
        return self.__enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable; disabling also drops any pressed state."""
        self.__enabled = bool(enabled)
        if not self.__enabled:
            self.__pressed = False

    def is_pressed(self) -> bool:
        """True while the mouse is held down on the button."""
        return self.__pressed

    def take_clicked(self) -> bool:
        """True once after a completed click — clears the flag."""
        was, self.__clicked = self.__clicked, False
        return was

    # -- input ------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Press on mouse-down inside, click on mouse-up inside.

        Returns True when the event was consumed. Releasing outside the
        button cancels the press without firing, which is what every
        desktop button does and costs one extra branch.
        """
        if not self.__enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.__rect.collidepoint(event.pos):
                self.__pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.__pressed:
                self.__pressed = False
                if self.__rect.collidepoint(event.pos):
                    self.__clicked = True
                return True
        return False

    # -- drawing ----------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        """Draw the button in its current fill / pressed / disabled state."""
        if not self.__enabled:
            body = _blend(self.__fill, PANEL_TAN, 0.6)
            text_colour = STAT_BROWN
        elif self.__pressed:
            body = darken(self.__fill)
            text_colour = TEXT_COFFEE
        else:
            body = self.__fill
            text_colour = TEXT_COFFEE
        pygame.draw.rect(surface, body, self.__rect)
        pygame.draw.rect(surface, BORDER_BROWN, self.__rect, BORDER_CARD)
        font = load_font(SIZE_BODY)
        _draw_text_centered(surface, font,
                            truncate(font, self.__label, self.__rect.w - 12),
                            self.__rect, text_colour)


# -------------------------------------------------------------
# SLIDER
# -------------------------------------------------------------


class Slider:
    """
    A horizontal value slider: track, left-anchored fill, square handle
    and a numeric readout to the right of the track (§4.5).

    Built for the settings screen's 0-100 volumes, so it quantises to
    an integer step and clamps on every path. A caller can never read
    an out-of-range value back out.
    """

    def __init__(self, rect: pygame.Rect, value: int = 0,
                 minimum: int = 0, maximum: int = 100, step: int = 5,
                 suffix: str = "") -> None:
        """Create a slider over the inclusive range `minimum`-`maximum`."""
        self.__rect: pygame.Rect = pygame.Rect(rect)
        self.__min: int = int(minimum)
        self.__max: int = int(max(minimum, maximum))
        self.__step: int = max(1, int(step))
        self.__suffix: str = suffix
        self.__value: int = self.__min
        self.__dragging: bool = False
        self.__enabled: bool = True
        self.__changed: bool = False
        self.set_value(value)

    # -- state ------------------------------------------------
    def get_rect(self) -> pygame.Rect:
        """The slider's rectangle."""
        return self.__rect

    def set_rect(self, rect: pygame.Rect) -> None:
        """Move or resize the slider."""
        self.__rect = pygame.Rect(rect)

    def get_track_rect(self) -> pygame.Rect:
        """The bar the handle rides on, for outside hit-testing."""
        return pygame.Rect(self.__rect.x,
                           self.__rect.centery - SLIDER_TRACK_H // 2,
                           self.__rect.w, SLIDER_TRACK_H)

    def get_handle_rect(self) -> pygame.Rect:
        """The square handle at the current value."""
        track = self.get_track_rect()
        span = max(1, self.__max - self.__min)
        ratio = (self.__value - self.__min) / span
        handle = pygame.Rect(0, 0, SLIDER_HANDLE, SLIDER_HANDLE)
        handle.center = (track.x + int(track.w * ratio), track.centery)
        handle.x = max(track.x, min(track.right - SLIDER_HANDLE, handle.x))
        return handle

    def get_value(self) -> int:
        """The current value, always inside the range and on the step."""
        return self.__value

    def set_value(self, value: int) -> bool:
        """
        Clamp, quantise to the step, and store.

        Returns True when the stored value actually changed. Invalid
        input is clamped rather than rejected — no mutator on this
        screen layer ever raises (Build Plan §0.8).
        """
        try:
            raw = float(value)
        except (TypeError, ValueError):
            return False
        raw = max(self.__min, min(self.__max, raw))
        stepped = self.__min + round((raw - self.__min) / self.__step) \
            * self.__step
        stepped = int(max(self.__min, min(self.__max, stepped)))
        if stepped == self.__value:
            return False
        self.__value = stepped
        self.__changed = True
        return True

    def get_range(self) -> Tuple[int, int, int]:
        """The (minimum, maximum, step) triple this slider clamps to."""
        return (self.__min, self.__max, self.__step)

    def is_enabled(self) -> bool:
        """True while the slider accepts input."""
        return self.__enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable; disabling also ends any drag."""
        self.__enabled = bool(enabled)
        if not self.__enabled:
            self.__dragging = False

    def is_dragging(self) -> bool:
        """True while the handle is being scrubbed."""
        return self.__dragging

    def take_changed(self) -> bool:
        """True once after the value changed — clears the flag."""
        was, self.__changed = self.__changed, False
        return was

    def value_from_x(self, x: int) -> int:
        """
        Map a screen x position onto a clamped, stepped value.

        Public because the settings screen drives its own click handling
        against the same maths (Build Plan §F4.3).
        """
        track = self.get_track_rect()
        ratio = (x - track.x) / max(1, track.w)
        raw = self.__min + ratio * (self.__max - self.__min)
        raw = max(self.__min, min(self.__max, raw))
        stepped = self.__min + round((raw - self.__min) / self.__step) \
            * self.__step
        return int(max(self.__min, min(self.__max, stepped)))

    # -- input ------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Click the track to jump, drag to scrub, arrow keys to nudge.

        Returns True when the event was consumed.
        """
        if not self.__enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.__rect.inflate(0, 12).collidepoint(event.pos):
                self.__dragging = True
                self.set_value(self.value_from_x(event.pos[0]))
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.__dragging:
                self.__dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.__dragging:
            self.set_value(self.value_from_x(event.pos[0]))
            return True
        elif event.type == pygame.MOUSEWHEEL:
            if self.__rect.inflate(0, 12).collidepoint(pygame.mouse.get_pos()):
                self.set_value(self.__value + self.__step * event.y)
                return True
        return False

    def nudge(self, steps: int) -> bool:
        """Move the value by `steps` increments; returns True if it moved."""
        return self.set_value(self.__value + self.__step * int(steps))

    # -- drawing ----------------------------------------------
    def render(self, surface: pygame.Surface,
               show_value: bool = True) -> None:
        """Draw the track, fill, handle and the numeric readout."""
        track = self.get_track_rect()
        span = max(1, self.__max - self.__min)
        ratio = (self.__value - self.__min) / span

        pygame.draw.rect(surface, BAR_TRACK, track)
        filled = int(track.w * max(0.0, min(1.0, ratio)))
        if filled > 0:
            fill = ROW_BLUE if self.__enabled else BAR_TRACK
            pygame.draw.rect(surface, fill,
                             pygame.Rect(track.x, track.y, filled, track.h))
        pygame.draw.rect(surface, BORDER_BROWN, track, BORDER_ROW)

        handle = self.get_handle_rect()
        pygame.draw.rect(surface,
                         CARD_TAN if self.__enabled else HEADER_TAN, handle)
        pygame.draw.rect(surface, BORDER_BROWN, handle, BORDER_ROW)

        if show_value:
            font = load_font(SIZE_LABEL)
            colour = TEXT_COFFEE if self.__enabled else STAT_BROWN
            _draw_text_vcenter(surface, font,
                               f"{self.__value}{self.__suffix}",
                               track.right + 12, track, colour)


# -------------------------------------------------------------
# CHIP ROW
# -------------------------------------------------------------


class ChipRow:
    """
    A row of mutually-exclusive toggle chips — display mode, text
    speed, yes/no answers. Exactly one option is always active.

    The chip row stores which option is active, not what that option
    means. Translating "FULLSCREEN" into a display flag is the caller's
    job.
    """

    def __init__(self, rect: pygame.Rect, options: Sequence[str],
                 value: str = "", gap: int = CHIP_GAP) -> None:
        """Create a chip row over `options`, starting on `value`."""
        self.__rect: pygame.Rect = pygame.Rect(rect)
        self.__options: List[str] = [str(option) for option in options]
        self.__gap: int = int(gap)
        self.__changed: bool = False
        if value in self.__options:
            self.__value: str = value
        else:
            self.__value = self.__options[0] if self.__options else ""

    # -- state ------------------------------------------------
    def get_rect(self) -> pygame.Rect:
        """The row's rectangle."""
        return self.__rect

    def set_rect(self, rect: pygame.Rect) -> None:
        """Move or resize the row; chips re-divide the new width."""
        self.__rect = pygame.Rect(rect)

    def get_options(self) -> List[str]:
        """Every option, in draw order."""
        return list(self.__options)

    def set_options(self, options: Sequence[str]) -> None:
        """Replace the options, keeping the current value when possible."""
        current = self.__value
        self.__options = [str(option) for option in options]
        if current not in self.__options:
            self.__value = self.__options[0] if self.__options else ""

    def get_value(self) -> str:
        """The active option, or "" when the row is empty."""
        return self.__value

    def set_value(self, value: str) -> bool:
        """Activate an option; an unknown option is ignored, never raised."""
        if value not in self.__options or value == self.__value:
            return False
        self.__value = value
        self.__changed = True
        return True

    def get_index(self) -> int:
        """Index of the active option, or -1 when the row is empty."""
        return self.__options.index(self.__value) \
            if self.__value in self.__options else -1

    def take_changed(self) -> bool:
        """True once after the active option changed — clears the flag."""
        was, self.__changed = self.__changed, False
        return was

    def get_chip_rect(self, index: int) -> pygame.Rect:
        """The hit box of one chip, so clicks can be matched outside."""
        count = max(1, len(self.__options))
        width = (self.__rect.w - self.__gap * (count - 1)) // count
        return pygame.Rect(self.__rect.x + index * (width + self.__gap),
                           self.__rect.y, width, self.__rect.h)

    def get_chip_rects(self) -> List[pygame.Rect]:
        """One rectangle per chip, in draw order."""
        return [self.get_chip_rect(i) for i in range(len(self.__options))]

    # -- input ------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Click a chip to activate it. Returns True when consumed."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, option in enumerate(self.__options):
                if self.get_chip_rect(index).collidepoint(event.pos):
                    self.set_value(option)
                    return True
        return False

    def cycle(self, direction: int = 1) -> bool:
        """Step to the next/previous option, wrapping at both ends."""
        if not self.__options:
            return False
        index = (self.get_index() + int(direction)) % len(self.__options)
        return self.set_value(self.__options[index])

    # -- drawing ----------------------------------------------
    def render(self, surface: pygame.Surface,
               active_fill: Tuple[int, int, int] = ROW_BLUE) -> None:
        """Draw every chip, the active one in the accent fill."""
        for index, option in enumerate(self.__options):
            rect = self.get_chip_rect(index)
            active = option == self.__value
            pygame.draw.rect(surface, active_fill if active else ROW_WHITE,
                             rect)
            pygame.draw.rect(surface, BORDER_BROWN, rect, BORDER_ROW)
            label = option.replace("_", " ").upper()
            font = load_font(SIZE_LABEL)
            _draw_text_centered(surface, font,
                                truncate(font, label, rect.w - 8), rect,
                                ROW_WHITE if active else TEXT_COFFEE)


# -------------------------------------------------------------
# ROW TABLE
# -------------------------------------------------------------


class RowTable:
    """
    The registration-table pattern (§4.4) as a reusable control:
    a 34 px header bar, 38 px rows on a 44 px pitch, 2 px borders,
    fixed column separators, a blue selected row and wheel scrolling.

    Rows are handed in as plain strings per column. The table has no
    idea what a "slot" or a "course" is — it draws cells.
    """

    def __init__(self, rect: pygame.Rect,
                 headers: Sequence[str] = (),
                 column_offsets: Sequence[int] = (),
                 row_h: int = ROW_H, pitch: int = ROW_PITCH) -> None:
        """
        Create a table at `rect`.

        headers        : column titles; an empty sequence draws no header bar
        column_offsets : x offset of each column's text, relative to rect.x
        """
        self.__rect: pygame.Rect = pygame.Rect(rect)
        self.__headers: List[str] = [str(h).upper() for h in headers]
        self.__offsets: List[int] = [int(x) for x in column_offsets] \
            or [12] * max(1, len(self.__headers))
        self.__row_h: int = int(row_h)
        self.__pitch: int = int(pitch)
        self.__rows: List[List[str]] = []
        self.__colours: List[Optional[Tuple[int, int, int]]] = []
        self.__selected: int = -1
        self.__scroll: int = 0

    # -- state ------------------------------------------------
    def get_rect(self) -> pygame.Rect:
        """The table's rectangle."""
        return self.__rect

    def set_rect(self, rect: pygame.Rect) -> None:
        """Move or resize the table and re-clamp the scroll offset."""
        self.__rect = pygame.Rect(rect)
        self.__clamp_scroll()

    def set_columns(self, headers: Sequence[str],
                    column_offsets: Sequence[int]) -> None:
        """Replace the column titles and their text offsets."""
        self.__headers = [str(h).upper() for h in headers]
        self.__offsets = [int(x) for x in column_offsets] \
            or [12] * max(1, len(self.__headers))

    def set_rows(self, rows: Sequence[Sequence[str]],
                 colours: Optional[Sequence[Optional[
                     Tuple[int, int, int]]]] = None) -> None:
        """
        Replace the row contents.

        A selection past the new end collapses to the last row rather
        than dangling, so a shrinking list can never leave the table
        pointing at nothing.
        """
        self.__rows = [[str(cell) for cell in row] for row in rows]
        self.__colours = list(colours) if colours \
            else [None] * len(self.__rows)
        if len(self.__colours) < len(self.__rows):
            self.__colours += [None] * (len(self.__rows)
                                        - len(self.__colours))
        if self.__selected >= len(self.__rows):
            self.__selected = len(self.__rows) - 1
        self.__clamp_scroll()

    def get_rows(self) -> List[List[str]]:
        """The current row contents."""
        return [list(row) for row in self.__rows]

    def get_row_count(self) -> int:
        """How many rows the table holds."""
        return len(self.__rows)

    def get_selected(self) -> int:
        """The selected row index, or -1 when nothing is selected."""
        return self.__selected

    def set_selected(self, index: int) -> bool:
        """Select a row (-1 clears) and scroll it into view."""
        new = index if 0 <= index < len(self.__rows) else -1
        changed = new != self.__selected
        self.__selected = new
        self.__scroll_into_view()
        return changed

    def get_scroll(self) -> int:
        """The current scroll offset in pixels."""
        return self.__scroll

    # -- geometry ---------------------------------------------
    def __body(self) -> pygame.Rect:
        """The scrolling area below the header bar."""
        top = self.__rect.y + (HEADER_H if self.__headers else 0)
        return pygame.Rect(self.__rect.x, top, self.__rect.w,
                           max(0, self.__rect.bottom - top))

    def __content_height(self) -> int:
        """Total height of every row, scrolled or not."""
        return len(self.__rows) * self.__pitch

    def __clamp_scroll(self) -> None:
        """Keep the scroll offset inside the content."""
        limit = max(0, self.__content_height() - self.__body().h)
        self.__scroll = max(0, min(limit, self.__scroll))

    def __scroll_into_view(self) -> None:
        """Bring the selected row inside the visible band."""
        if self.__selected < 0:
            return
        body = self.__body()
        top = self.__selected * self.__pitch
        if top < self.__scroll:
            self.__scroll = top
        elif top + self.__row_h > self.__scroll + body.h:
            self.__scroll = top + self.__row_h - body.h
        self.__clamp_scroll()

    def get_row_rect(self, index: int) -> pygame.Rect:
        """The screen rect of a row — it may be scrolled out of view."""
        body = self.__body()
        return pygame.Rect(body.x,
                           body.y + index * self.__pitch - self.__scroll,
                           body.w, self.__row_h)

    def get_row_rects(self, count: Optional[int] = None) -> List[pygame.Rect]:
        """One rectangle per row, so clicks can be matched outside."""
        total = len(self.__rows) if count is None else int(count)
        return [self.get_row_rect(i) for i in range(total)]

    def row_at(self, pos: Tuple[int, int]) -> int:
        """Index of the row under a screen position, or -1."""
        if not self.__body().collidepoint(pos):
            return -1
        for index in range(len(self.__rows)):
            if self.get_row_rect(index).collidepoint(pos):
                return index
        return -1

    # -- input ------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Click selects a row, the wheel scrolls, up/down step. """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self.row_at(event.pos)
            if index >= 0:
                self.set_selected(index)
                return True
        elif event.type == pygame.MOUSEWHEEL:
            if self.__rect.collidepoint(pygame.mouse.get_pos()):
                self.__scroll -= event.y * self.__pitch
                self.__clamp_scroll()
                return True
        elif event.type == pygame.KEYDOWN and self.__rows:
            if event.key == pygame.K_DOWN:
                self.set_selected(min(len(self.__rows) - 1,
                                      self.__selected + 1))
                return True
            if event.key == pygame.K_UP:
                self.set_selected(max(0, self.__selected - 1))
                return True
        return False

    # -- drawing ----------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        """Draw the header bar, the visible rows, then the scrollbar."""
        font = load_font(SIZE_BODY)
        if self.__headers:
            bar = pygame.Rect(self.__rect.x, self.__rect.y, self.__rect.w,
                              HEADER_H)
            pygame.draw.rect(surface, HEADER_TAN, bar)
            pygame.draw.rect(surface, BORDER_BROWN, bar, BORDER_ROW)
            self.__draw_separators(surface, bar)
            for index, title in enumerate(self.__headers):
                if index < len(self.__offsets):
                    _draw_text_vcenter(surface, font, title,
                                       self.__rect.x + self.__offsets[index],
                                       bar, TEXT_COFFEE)

        body = self.__body()
        previous_clip = surface.get_clip()
        surface.set_clip(body)
        for index, cells in enumerate(self.__rows):
            row = self.get_row_rect(index)
            if row.bottom < body.y or row.y > body.bottom:
                continue
            if index == self.__selected:
                fill: Tuple[int, int, int] = ROW_BLUE
                colour: Tuple[int, int, int] = ROW_WHITE
            else:
                fill = self.__colours[index] or ROW_WHITE
                colour = TEXT_COFFEE
            pygame.draw.rect(surface, fill, row)
            pygame.draw.rect(surface, BORDER_BROWN, row, BORDER_ROW)
            self.__draw_separators(surface, row)
            self.__draw_cells(surface, font, cells, row, colour)
        surface.set_clip(previous_clip)
        self.__draw_scrollbar(surface, body)

    def __draw_cells(self, surface: pygame.Surface, font: pygame.font.Font,
                     cells: Sequence[str], row: pygame.Rect,
                     colour: Tuple[int, int, int]) -> None:
        """Draw one row's cells at the fixed column offsets."""
        for index, cell in enumerate(cells):
            if index >= len(self.__offsets):
                break
            x = self.__rect.x + self.__offsets[index]
            if index + 1 < len(self.__offsets):
                width = self.__offsets[index + 1] - self.__offsets[index] - 12
            else:
                width = self.__rect.right - x - 12
            _draw_text_vcenter(surface, font, truncate(font, cell, width),
                               x, row, colour)

    def __draw_separators(self, surface: pygame.Surface,
                          rect: pygame.Rect) -> None:
        """Draw the 2 px column dividers through a header or row."""
        for offset in self.__offsets[1:]:
            x = self.__rect.x + offset - 12
            pygame.draw.line(surface, BORDER_BROWN, (x, rect.y),
                             (x, rect.bottom - 1), BORDER_ROW)

    def __draw_scrollbar(self, surface: pygame.Surface,
                         body: pygame.Rect) -> None:
        """Slim 8 px scrollbar, drawn only when the content overflows."""
        content = self.__content_height()
        if content <= body.h or body.h <= 0:
            return
        track = pygame.Rect(body.right - SCROLLBAR_W, body.y,
                            SCROLLBAR_W, body.h)
        pygame.draw.rect(surface, BAR_TRACK, track)
        height = max(24, int(track.h * body.h / content))
        offset = int((track.h - height) * self.__scroll
                     / max(1, content - body.h))
        pygame.draw.rect(surface, BORDER_BROWN,
                         pygame.Rect(track.x, track.y + offset,
                                     SCROLLBAR_W, height))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   Click buttons  -> the pressed fill darkens 10%, prints on release
#   Drag sliders   -> live value readout (music / sfx style, 0-100)
#   Click chips    -> exactly one stays active per row
#   Click rows     -> blue selection; wheel or up/down scrolls
#   TAB            -> toggle the disabled-state demo button
#   F11            -> toggle windowed / fullscreen
#   ESC            -> quit
# -------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Widget gallery test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    CARD = pygame.Rect(CARD_MARGIN, CARD_MARGIN,
                       SIZE[0] - CARD_MARGIN * 2, SIZE[1] - CARD_MARGIN * 2)
    INNER = CARD.inflate(-CARD_PAD * 2, -CARD_PAD * 2)

    demo_buttons = [
        Button(pygame.Rect(60, 120, 200, BTN_H), "CONFIRM", BTN_CONFIRM),
        Button(pygame.Rect(280, 120, 200, BTN_H), "CANCEL", BTN_CANCEL),
        Button(pygame.Rect(500, 120, 200, BTN_H), "NEUTRAL", HEADER_TAN),
        Button(pygame.Rect(720, 120, 200, BTN_H), "DISABLED", BTN_CONFIRM,
               enabled=False),
    ]
    music_slider = Slider(pygame.Rect(60, 226, 420, 24), 70, 0, 100, 5)
    sfx_slider = Slider(pygame.Rect(60, 282, 420, 24), 80, 0, 100, 5)
    display_chips = ChipRow(pygame.Rect(60, 356, 412, 36),
                            ("WINDOWED", "FULLSCREEN"), "WINDOWED")
    speed_chips = ChipRow(pygame.Rect(60, 420, 412, 36),
                          ("SLOW", "NORMAL", "FAST"), "NORMAL")
    table = RowTable(pygame.Rect(620, 190, 600, 400),
                     ("SLOT", "DETAILS", "SAVED"), (12, 150, 430))
    table.set_rows([
        ["SLOT 1", "Rafi  Sem 3  42/140 cr", "2026-07-30"],
        ["SLOT 2", "Nabila  Sem 7  96/140 cr", "2026-07-28"],
        ["SLOT 3", "EMPTY SLOT", "-"],
        ["AUTOSAVE", "Rafi  Sem 3  42/140 cr", "2026-07-31"],
        ["ARCHIVE 1", "Zayan  Sem 11  132/140 cr", "2026-06-02"],
        ["ARCHIVE 2", "Kabir  Sem 2  18/140 cr", "2026-05-19"],
        ["ARCHIVE 3", "Roya  Sem 9  118/140 cr", "2026-04-11"],
        ["ARCHIVE 4", "Purnno  Sem 1  0/140 cr", "2026-03-30"],
        ["ARCHIVE 5", "Hoque  Sem 12  140/140 cr", "2026-02-14"],
        ["ARCHIVE 6", "EMPTY SLOT", "-"],
    ], [None, None, None, None, ROW_GREEN, None, None, None, ROW_GREEN, None])
    table.set_selected(0)

    def _draw_card(surface: pygame.Surface) -> None:
        """The signature framed card with corner bracket marks (§4.2)."""
        pygame.draw.rect(surface, CARD_TAN, CARD)
        pygame.draw.rect(surface, BORDER_BROWN, CARD, BORDER_CARD)
        pygame.draw.rect(surface, BORDER_BROWN, INNER, 1)
        n = CORNER_LEN
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((INNER.left, INNER.top), (n, 0), (0, n)),
                ((INNER.right, INNER.top), (-n, 0), (0, n)),
                ((INNER.left, INNER.bottom), (n, 0), (0, -n)),
                ((INNER.right, INNER.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(surface, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(surface, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 3)

    def _label(surface: pygame.Surface, text: str, x: int, y: int) -> None:
        """A small ALL-CAPS section label in the emphasis brown."""
        surface.blit(load_font(SIZE_LABEL).render(text, True, CREDIT_HL),
                     (x, y))

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
                elif event.key == pygame.K_TAB:
                    demo_buttons[3].set_enabled(
                        not demo_buttons[3].is_enabled())

            for button in demo_buttons:
                if button.handle_event(event):
                    break
            else:
                if not music_slider.handle_event(event):
                    if not sfx_slider.handle_event(event):
                        if not display_chips.handle_event(event):
                            if not speed_chips.handle_event(event):
                                table.handle_event(event)

        for button in demo_buttons:
            if button.take_clicked():
                print(f"{button.get_label()} pressed")
        if music_slider.take_changed():
            print(f"music volume -> {music_slider.get_value()}")
        if sfx_slider.take_changed():
            print(f"sfx volume -> {sfx_slider.get_value()}")
        if display_chips.take_changed():
            print(f"display mode -> {display_chips.get_value()}")
        if speed_chips.take_changed():
            print(f"text speed -> {speed_chips.get_value()}")

        window.fill(PANEL_TAN)
        _draw_card(window)

        window.blit(load_font(SIZE_TITLE).render("WIDGET GALLERY", True,
                                                 (45, 58, 71)), (60, 56))
        _label(window, "BUTTONS", 60, 102)
        for button in demo_buttons:
            button.render(window)

        _label(window, "MUSIC VOLUME", 60, 204)
        music_slider.render(window)
        _label(window, "SFX VOLUME", 60, 260)
        sfx_slider.render(window)

        _label(window, "DISPLAY MODE", 60, 336)
        display_chips.render(window)
        _label(window, "TEXT SPEED", 60, 400)
        speed_chips.render(window)

        _label(window, "ROW TABLE", 620, 170)
        table.render(window)

        hint = hint_font.render(
            "Click / drag widgets  |  TAB disabled demo  |  "
            "F11 fullscreen  |  ESC quit", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

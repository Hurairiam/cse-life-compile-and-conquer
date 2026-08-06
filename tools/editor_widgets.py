"""
tools/editor_widgets.py
CSE Life: Compile & Conquer — Level editor, phase E2/E3
─────────────────────────────────────────────────────────────
The reusable controls the editor is built from: text inputs,
steppers, the speed slider, the palette grid and the row table.

Every one of them follows the same contract, which is the same
contract ui/ screens use (Style Guide §6):

    handle_event(event) -> bool      True when the event was consumed
    render(surface)                  draws from its own widget state

Widgets own only their OWN interaction state (focus, caret,
scroll offset). They never touch the level document — the editor
reads a widget's value and applies it, so undo has exactly one
place to hook into.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple

import pygame

from tools import editor_theme as th

SCROLLBAR_W = 8


# ─────────────────────────────────────────────────────────────
# TEXT INPUT
# ─────────────────────────────────────────────────────────────


class TextInput:
    """
    A framed one-line text field (Spec §4.4). Instant text — the
    typewriter effect belongs to the in-game dialog box, never here.
    """

    def __init__(self, rect: pygame.Rect, text: str = "",
                 max_length: int = 64,
                 char_filter: Optional[Callable[[str], bool]] = None) -> None:
        self.__rect: pygame.Rect = rect
        self.__text: str = text
        self.__max_length: int = max_length
        self.__filter: Optional[Callable[[str], bool]] = char_filter
        self.__focused: bool = False
        self.__caret_timer: float = 0.0
        self.__changed: bool = False

    def get_rect(self) -> pygame.Rect:
        """The field's rectangle."""
        return self.__rect

    def set_rect(self, rect: pygame.Rect) -> None:
        """Move the field (used when a popup relayouts)."""
        self.__rect = rect

    def get_text(self) -> str:
        """Current contents."""
        return self.__text

    def set_text(self, text: str) -> None:
        """Replace the contents without raising a change event."""
        self.__text = text[:self.__max_length]

    def is_focused(self) -> bool:
        """True while this field has the keyboard."""
        return self.__focused

    def set_focused(self, focused: bool) -> None:
        """Give or take the keyboard focus."""
        self.__focused = focused
        self.__caret_timer = 0.0

    def take_changed(self) -> bool:
        """True once after the text was edited — clears the flag."""
        was, self.__changed = self.__changed, False
        return was

    def update(self, dt: float) -> None:
        """Advance the caret blink."""
        self.__caret_timer = (self.__caret_timer + dt) % 1.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Focus on click; type/backspace while focused."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.set_focused(self.__rect.collidepoint(event.pos))
            return self.__focused
        if event.type != pygame.KEYDOWN or not self.__focused:
            return False
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            self.set_focused(False)
            return True
        if event.key == pygame.K_ESCAPE:
            self.set_focused(False)
            return False            # let ESC also close the popup
        if event.key == pygame.K_BACKSPACE:
            self.__text = self.__text[:-1]
            self.__changed = True
            return True
        char = event.unicode
        if char and char.isprintable() and len(self.__text) < self.__max_length:
            if self.__filter is None or self.__filter(char):
                self.__text += char
                self.__changed = True
        return True

    def render(self, surface: pygame.Surface,
               placeholder: str = "") -> None:
        """Draw the box, its text and a blinking caret when focused."""
        th.draw_panel(surface, self.__rect, th.ROW_WHITE,
                      th.BORDER_CARD if self.__focused else th.BORDER_ROW,
                      th.ROW_BLUE if self.__focused else th.BORDER_BROWN)
        font = th.load_font(th.SIZE_SUB)
        shown = self.__text or placeholder
        colour = th.TEXT_COFFEE if self.__text else th.STAT_BROWN
        text = th.truncate(font, shown, self.__rect.w - 14)
        th.draw_text_vcenter(surface, font, text, self.__rect.x + 7,
                             self.__rect, colour)
        if self.__focused and self.__caret_timer < 0.5:
            caret_x = self.__rect.x + 7 + font.size(text)[0] + 2
            caret_x = min(caret_x, self.__rect.right - 6)
            pygame.draw.rect(surface, th.TEXT_COFFEE,
                             pygame.Rect(caret_x, self.__rect.y + 6, 2,
                                         self.__rect.h - 12))


# ─────────────────────────────────────────────────────────────
# STEPPER
# ─────────────────────────────────────────────────────────────


class Stepper:
    """
    A `-` / value / `+` control (Spec §4.4, §5.3). Clamps to its range;
    the caller never has to bounds-check what it reads back.
    """

    def __init__(self, rect: pygame.Rect, value: float, minimum: float,
                 maximum: float, step: float, decimals: int = 0,
                 suffix: str = "") -> None:
        self.__rect: pygame.Rect = rect
        self.__min: float = minimum
        self.__max: float = maximum
        self.__step: float = step
        self.__decimals: int = decimals
        self.__suffix: str = suffix
        self.__value: float = 0.0
        self.set_value(value)

    def __button_rects(self) -> Tuple[pygame.Rect, pygame.Rect]:
        """The minus and plus hit boxes."""
        size = self.__rect.h
        return (pygame.Rect(self.__rect.x, self.__rect.y, size, size),
                pygame.Rect(self.__rect.right - size, self.__rect.y, size,
                            size))

    def get_value(self) -> float:
        """Current value, always inside the range."""
        return self.__value

    def set_value(self, value: float) -> None:
        """Clamp and store."""
        self.__value = max(self.__min, min(self.__max, float(value)))
        if self.__decimals == 0:
            self.__value = float(int(round(self.__value)))

    def set_range(self, minimum: float, maximum: float, step: float,
                  decimals: int, suffix: str) -> None:
        """Re-target the stepper when its meaning changes (money <-> EXP)."""
        self.__min, self.__max = minimum, maximum
        self.__step, self.__decimals, self.__suffix = step, decimals, suffix
        self.set_value(self.__value)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Click a button, or wheel over the control."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            minus, plus = self.__button_rects()
            if minus.collidepoint(event.pos):
                self.set_value(self.__value - self.__step)
                return True
            if plus.collidepoint(event.pos):
                self.set_value(self.__value + self.__step)
                return True
        elif event.type == pygame.MOUSEWHEEL:
            if self.__rect.collidepoint(pygame.mouse.get_pos()):
                self.set_value(self.__value + self.__step * event.y)
                return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        """Draw both buttons and the framed value between them."""
        minus, plus = self.__button_rects()
        font = th.load_font(th.SIZE_BODY)
        th.draw_button(surface, minus, "-", th.HEADER_TAN, font,
                       self.__value > self.__min)
        th.draw_button(surface, plus, "+", th.HEADER_TAN, font,
                       self.__value < self.__max)
        field = pygame.Rect(minus.right + 4, self.__rect.y,
                            self.__rect.w - minus.w * 2 - 8, self.__rect.h)
        th.draw_panel(surface, field, th.ROW_WHITE, th.BORDER_ROW)
        if self.__decimals:
            text = f"{self.__value:.{self.__decimals}f}{self.__suffix}"
        else:
            text = f"{int(self.__value):,}{self.__suffix}"
        th.draw_text_centered(surface, font, text, field, th.TEXT_COFFEE)


# ─────────────────────────────────────────────────────────────
# SLIDER
# ─────────────────────────────────────────────────────────────


class Slider:
    """
    The speed-modifier slider (Spec §5.3): progress-bar track, square
    handle, live value label, and a snap notch at the base value.
    """

    SNAP_TOLERANCE = 0.06

    def __init__(self, rect: pygame.Rect, value: float, minimum: float,
                 maximum: float, step: float,
                 snap_to: Optional[float] = None) -> None:
        self.__rect: pygame.Rect = rect
        self.__min: float = minimum
        self.__max: float = maximum
        self.__step: float = step
        self.__snap_to: Optional[float] = snap_to
        self.__value: float = value
        self.__dragging: bool = False
        self.__enabled: bool = True
        self.set_value(value)

    def get_value(self) -> float:
        """Current value, quantised to the step."""
        return self.__value

    def set_value(self, value: float) -> None:
        """Clamp, quantise, then snap if close to the notch."""
        value = max(self.__min, min(self.__max, float(value)))
        value = round(round(value / self.__step) * self.__step, 4)
        if self.__snap_to is not None and \
                abs(value - self.__snap_to) < self.SNAP_TOLERANCE:
            value = self.__snap_to
        self.__value = value

    def set_enabled(self, enabled: bool) -> None:
        """Grey the slider out — a blocking prop cannot carry a modifier."""
        self.__enabled = enabled
        if not enabled:
            self.__dragging = False

    def is_enabled(self) -> bool:
        """Whether the slider accepts input."""
        return self.__enabled

    def __track(self) -> pygame.Rect:
        """The 16 px bar the handle rides on."""
        return pygame.Rect(self.__rect.x, self.__rect.centery - 8,
                           self.__rect.w, 16)

    def __value_from_x(self, x: int) -> float:
        """Map a pixel position back onto the value range."""
        track = self.__track()
        ratio = (x - track.x) / max(1, track.w)
        return self.__min + ratio * (self.__max - self.__min)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Click to jump, drag to scrub, release to stop."""
        if not self.__enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.__rect.inflate(0, 12).collidepoint(event.pos):
                self.__dragging = True
                self.set_value(self.__value_from_x(event.pos[0]))
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.__dragging:
                self.__dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.__dragging:
            self.set_value(self.__value_from_x(event.pos[0]))
            return True
        return False

    def render(self, surface: pygame.Surface, label_right: bool = True) -> None:
        """Track, fill, notch, handle, and the live `x1.00` readout."""
        track = self.__track()
        span = max(0.0001, self.__max - self.__min)
        ratio = (self.__value - self.__min) / span
        fill = th.ROW_BLUE if self.__enabled else th.BAR_TRACK
        th.draw_progress(surface, track, ratio, fill)

        if self.__snap_to is not None:
            notch_x = track.x + int(track.w * (self.__snap_to - self.__min)
                                    / span)
            pygame.draw.line(surface, th.BORDER_BROWN, (notch_x, track.y - 4),
                             (notch_x, track.bottom + 4), 2)

        handle = pygame.Rect(0, 0, 16, 16)
        handle.center = (track.x + int(track.w * ratio), track.centery)
        handle.x = max(track.x, min(track.right - 16, handle.x))
        th.draw_panel(surface, handle,
                      th.CARD_TAN if self.__enabled else th.HEADER_TAN,
                      th.BORDER_ROW)

        if label_right:
            font = th.load_font(th.SIZE_LABEL)
            colour = th.STAT_BROWN if not self.__enabled else (
                th.BAR_AMBER if self.__snap_to is not None
                and self.__value != self.__snap_to else th.TEXT_COFFEE)
            th.draw_text(surface, font, f"x{self.__value:.2f}",
                         (track.right + 10, track.y + 3), colour)


# ─────────────────────────────────────────────────────────────
# PALETTE GRID
# ─────────────────────────────────────────────────────────────


class PaletteItem:
    """One selectable cell in a palette section."""

    def __init__(self, key: str, label: str, kind: str) -> None:
        self.__key: str = key
        self.__label: str = label
        self.__kind: str = kind

    def get_key(self) -> str:
        """Registry key, or "eraser" for the tool slot."""
        return self.__key

    def get_label(self) -> str:
        """Name drawn under the cell."""
        return self.__label

    def get_kind(self) -> str:
        """"tile", "prop", "npc" or "eraser"."""
        return self.__kind


class PaletteGrid:
    """
    The 4-column sprite palette shared by the TILES, PROPS and NPCS
    sections (Spec §4). Selection lives OUTSIDE the grid — exactly one
    item may be selected across all three sections at once, so the
    editor owns that state and hands it back in for drawing.
    """

    CELL = 48
    GAP = 6
    LABEL_H = 12
    COLUMNS = 4

    def __init__(self, rect: pygame.Rect) -> None:
        self.__rect: pygame.Rect = rect
        self.__items: List[PaletteItem] = []
        self.__scroll: int = 0

    def set_rect(self, rect: pygame.Rect) -> None:
        """Move/resize the grid."""
        self.__rect = rect
        self.__clamp_scroll()

    def set_items(self, items: Sequence[PaletteItem]) -> None:
        """Replace the palette contents and reset the scroll."""
        self.__items = list(items)
        self.__scroll = 0

    def get_items(self) -> List[PaletteItem]:
        """The palette contents."""
        return list(self.__items)

    def __pitch(self) -> int:
        """Vertical distance between cell rows."""
        return self.CELL + self.LABEL_H + self.GAP + 4

    def __content_height(self) -> int:
        """Total height of every row of cells."""
        rows = (len(self.__items) + self.COLUMNS - 1) // self.COLUMNS
        return rows * self.__pitch()

    def __clamp_scroll(self) -> None:
        """Keep the scroll offset inside the content."""
        limit = max(0, self.__content_height() - self.__rect.h)
        self.__scroll = max(0, min(limit, self.__scroll))

    def get_cell_rect(self, index: int) -> pygame.Rect:
        """Screen rect of the sprite cell at `index` (may be off-view)."""
        col = index % self.COLUMNS
        row = index // self.COLUMNS
        return pygame.Rect(
            self.__rect.x + col * (self.CELL + self.GAP),
            self.__rect.y + row * self.__pitch() - self.__scroll,
            self.CELL, self.CELL)

    def item_at(self, pos: Tuple[int, int]) -> Optional[PaletteItem]:
        """The item under a screen position, or None."""
        if not self.__rect.collidepoint(pos):
            return None
        for index, item in enumerate(self.__items):
            if self.get_cell_rect(index).collidepoint(pos):
                return item
        return None

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Wheel scrolls when the pointer is over the grid."""
        if event.type == pygame.MOUSEWHEEL and \
                self.__rect.collidepoint(pygame.mouse.get_pos()):
            self.__scroll -= event.y * 32
            self.__clamp_scroll()
            return True
        return False

    def render(self, surface: pygame.Surface, selected_key: Optional[str],
               sprite_for: Callable[[PaletteItem, int],
                                    Optional[pygame.Surface]]) -> None:
        """
        Draw every visible cell. `sprite_for(item, size)` returns the
        preview surface, or None — in which case the mandatory
        PLACEHOLDER square is drawn instead (Style Guide §5.2).
        """
        previous_clip = surface.get_clip()
        surface.set_clip(self.__rect)
        font = th.load_font(th.SIZE_LABEL)

        for index, item in enumerate(self.__items):
            cell = self.get_cell_rect(index)
            if cell.bottom < self.__rect.y - 20 or cell.y > self.__rect.bottom:
                continue
            selected = item.get_key() == selected_key
            th.draw_panel(surface, cell, th.ROW_WHITE, 0)

            if item.get_kind() == "eraser":
                self.__draw_eraser_glyph(surface, cell)
            else:
                sprite = sprite_for(item, self.CELL)
                if sprite is not None:
                    surface.blit(sprite, cell.topleft)
                else:
                    th.draw_placeholder(surface, cell)

            pygame.draw.rect(surface,
                             th.ROW_BLUE if selected else th.BORDER_BROWN,
                             cell, 3 if selected else 2)
            label = th.truncate(font, item.get_label(), self.CELL + self.GAP)
            rendered = font.render(label, True,
                                   th.ROW_BLUE if selected else th.STAT_BROWN)
            surface.blit(rendered, (cell.centerx - rendered.get_width() // 2,
                                    cell.bottom + 3))

        surface.set_clip(previous_clip)
        self.__draw_scrollbar(surface)

    def __draw_eraser_glyph(self, surface: pygame.Surface,
                            cell: pygame.Rect) -> None:
        """
        The eraser slot: a placeholder square with an X through it
        (Spec §3.3). [ICON PLACEHOLDER: assets/ui/icon_eraser.png —
        eraser with an X]
        """
        th.draw_placeholder(surface, cell)
        pad = 12
        pygame.draw.line(surface, th.BAR_OVER,
                         (cell.x + pad, cell.y + pad),
                         (cell.right - pad, cell.bottom - pad), 3)
        pygame.draw.line(surface, th.BAR_OVER,
                         (cell.right - pad, cell.y + pad),
                         (cell.x + pad, cell.bottom - pad), 3)

    def __draw_scrollbar(self, surface: pygame.Surface) -> None:
        """Slim 8 px bar, only when the content overflows."""
        content = self.__content_height()
        if content <= self.__rect.h:
            return
        track = pygame.Rect(self.__rect.right - SCROLLBAR_W, self.__rect.y,
                            SCROLLBAR_W, self.__rect.h)
        pygame.draw.rect(surface, th.BAR_TRACK, track)
        height = max(24, int(track.h * self.__rect.h / content))
        offset = int((track.h - height) * self.__scroll /
                     max(1, content - self.__rect.h))
        th.draw_panel(surface,
                      pygame.Rect(track.x, track.y + offset, SCROLLBAR_W,
                                  height), th.BORDER_BROWN, 0)


# ─────────────────────────────────────────────────────────────
# ROW TABLE
# ─────────────────────────────────────────────────────────────


class RowTable:
    """
    The registration-table pattern (Style Guide §4.4) reused for the
    LOAD picker, the dialog chain/line lists and the validation report:
    header bar, white rows, blue selected row, wheel scrolling.
    """

    def __init__(self, rect: pygame.Rect, header: str = "",
                 row_h: int = 30, pitch: int = 34) -> None:
        self.__rect: pygame.Rect = rect
        self.__header: str = header
        self.__row_h: int = row_h
        self.__pitch: int = pitch
        self.__rows: List[str] = []
        self.__colours: List[Optional[tuple]] = []
        self.__selected: int = -1
        self.__scroll: int = 0

    def set_rows(self, rows: Sequence[str],
                 colours: Optional[Sequence[Optional[tuple]]] = None) -> None:
        """Replace the row text, keeping the selection if still valid."""
        self.__rows = list(rows)
        self.__colours = list(colours) if colours else [None] * len(self.__rows)
        if self.__selected >= len(self.__rows):
            self.__selected = len(self.__rows) - 1
        self.__clamp_scroll()

    def get_rows(self) -> List[str]:
        """The row text."""
        return list(self.__rows)

    def get_selected(self) -> int:
        """Selected row index, or -1."""
        return self.__selected

    def set_selected(self, index: int) -> None:
        """Select a row (-1 clears) and scroll it into view."""
        self.__selected = index if 0 <= index < len(self.__rows) else -1
        self.__scroll_into_view()

    def get_rect(self) -> pygame.Rect:
        """The table's rectangle."""
        return self.__rect

    def __body(self) -> pygame.Rect:
        """The scrolling area below the header."""
        top = self.__rect.y + (th.HEADER_H if self.__header else 0)
        return pygame.Rect(self.__rect.x, top, self.__rect.w,
                           self.__rect.bottom - top)

    def __content_height(self) -> int:
        """Total height of all rows."""
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
        """Screen rect of a row (may be scrolled out of view)."""
        body = self.__body()
        return pygame.Rect(body.x, body.y + index * self.__pitch - self.__scroll,
                           body.w, self.__row_h)

    def row_at(self, pos: Tuple[int, int]) -> int:
        """Index of the row under a position, or -1."""
        if not self.__body().collidepoint(pos):
            return -1
        for index in range(len(self.__rows)):
            if self.get_row_rect(index).collidepoint(pos):
                return index
        return -1

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Click selects; wheel scrolls."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self.row_at(event.pos)
            if index >= 0:
                self.__selected = index
                return True
        elif event.type == pygame.MOUSEWHEEL and \
                self.__rect.collidepoint(pygame.mouse.get_pos()):
            self.__scroll -= event.y * self.__pitch
            self.__clamp_scroll()
            return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        """Header bar, then the visible rows, then the scrollbar."""
        font = th.load_font(th.SIZE_SUB)
        if self.__header:
            bar = pygame.Rect(self.__rect.x, self.__rect.y, self.__rect.w,
                              th.HEADER_H)
            th.draw_panel(surface, bar, th.HEADER_TAN, th.BORDER_ROW)
            th.draw_text_vcenter(surface, th.load_font(th.SIZE_LABEL),
                                 self.__header.upper(), bar.x + 10, bar,
                                 th.TEXT_COFFEE)

        body = self.__body()
        previous_clip = surface.get_clip()
        surface.set_clip(body)
        for index, text in enumerate(self.__rows):
            row = self.get_row_rect(index)
            if row.bottom < body.y or row.y > body.bottom:
                continue
            if index == self.__selected:
                fill, colour = th.ROW_BLUE, th.ROW_WHITE
            else:
                fill = self.__colours[index] or th.ROW_WHITE
                colour = th.TEXT_COFFEE
            th.draw_panel(surface, row, fill, th.BORDER_ROW)
            th.draw_text_vcenter(surface, font,
                                 th.truncate(font, text, row.w - 16),
                                 row.x + 8, row, colour)
        surface.set_clip(previous_clip)

        content = self.__content_height()
        if content > body.h:
            track = pygame.Rect(body.right - SCROLLBAR_W, body.y,
                                SCROLLBAR_W, body.h)
            pygame.draw.rect(surface, th.BAR_TRACK, track)
            height = max(24, int(track.h * body.h / content))
            offset = int((track.h - height) * self.__scroll /
                         max(1, content - body.h))
            th.draw_panel(surface, pygame.Rect(track.x, track.y + offset,
                                               SCROLLBAR_W, height),
                          th.BORDER_BROWN, 0)


# ─────────────────────────────────────────────────────────────
# CHIP ROW
# ─────────────────────────────────────────────────────────────


class Cycler:
    """
    A `<  value  >` selector over a fixed list — the editor's stand-in
    for a dropdown (the skill picker, Spec §5.3).

    A pop-open list would need its own overlay, focus handling and
    scroll state inside a modal that already has three tables; for a
    fixed nine-item registry list a cycler is the same number of clicks
    and none of the edge cases.
    """

    def __init__(self, rect: pygame.Rect, options: Sequence[str],
                 value: str = "",
                 labels: Optional[Dict[str, str]] = None) -> None:
        """
        `labels` maps an option to the text drawn for it, for lists
        whose ids are not what a human should be reading —
        "skill_tree" cycles, "Skill Tree" is displayed. Options with
        no entry fall back to the raw id, so callers that never pass
        the map behave exactly as before.
        """
        self.__rect: pygame.Rect = rect
        self.__options: List[str] = list(options)
        self.__labels: Dict[str, str] = dict(labels or {})
        self.__index: int = 0
        self.set_value(value)

    def get_value(self) -> str:
        """The selected option, or "" when the list is empty."""
        if not self.__options:
            return ""
        return self.__options[self.__index]

    def set_value(self, value: str) -> bool:
        """Select by value; unknown values leave the selection alone."""
        if value in self.__options:
            self.__index = self.__options.index(value)
            return True
        return False

    def set_options(self, options: Sequence[str]) -> None:
        """Replace the list, keeping the current value when possible."""
        current = self.get_value()
        self.__options = list(options)
        self.__index = 0
        self.set_value(current)

    def __arrow_rects(self) -> Tuple[pygame.Rect, pygame.Rect]:
        """The `<` and `>` hit boxes."""
        size = self.__rect.h
        return (pygame.Rect(self.__rect.x, self.__rect.y, size, size),
                pygame.Rect(self.__rect.right - size, self.__rect.y, size,
                            size))

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Click an arrow to step, wrapping at both ends."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 \
                and self.__options:
            back, forward = self.__arrow_rects()
            if back.collidepoint(event.pos):
                self.__index = (self.__index - 1) % len(self.__options)
                return True
            if forward.collidepoint(event.pos):
                self.__index = (self.__index + 1) % len(self.__options)
                return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        """Two arrow buttons around a framed value field."""
        back, forward = self.__arrow_rects()
        font = th.load_font(th.SIZE_BODY)
        th.draw_button(surface, back, "<", th.HEADER_TAN, font,
                       len(self.__options) > 1)
        th.draw_button(surface, forward, ">", th.HEADER_TAN, font,
                       len(self.__options) > 1)
        field = pygame.Rect(back.right + 4, self.__rect.y,
                            self.__rect.w - back.w * 2 - 8, self.__rect.h)
        th.draw_panel(surface, field, th.ROW_WHITE, th.BORDER_ROW)
        value = self.get_value()
        text = self.__labels.get(value, value) or "-"
        label = th.fit_font(text, field.w - 8)
        th.draw_text_centered(surface, label, text, field, th.TEXT_COFFEE)


class ChipRow:
    """
    A row of mutually-exclusive toggle chips — facing, ambient preset,
    interaction kind, on-complete mode. Exactly one is always active.
    """

    def __init__(self, rect: pygame.Rect, options: Sequence[str],
                 value: str, gap: int = 6) -> None:
        self.__rect: pygame.Rect = rect
        self.__options: List[str] = list(options)
        self.__value: str = value if value in options else (
            self.__options[0] if self.__options else "")
        self.__gap: int = gap

    def get_value(self) -> str:
        """The active option."""
        return self.__value

    def set_value(self, value: str) -> bool:
        """Activate an option; unknown options are ignored."""
        if value not in self.__options:
            return False
        self.__value = value
        return True

    def get_options(self) -> List[str]:
        """Every option, in draw order."""
        return list(self.__options)

    def get_chip_rect(self, index: int) -> pygame.Rect:
        """Hit box of one chip."""
        count = max(1, len(self.__options))
        width = (self.__rect.w - self.__gap * (count - 1)) // count
        return pygame.Rect(self.__rect.x + index * (width + self.__gap),
                           self.__rect.y, width, self.__rect.h)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Click a chip to activate it."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, option in enumerate(self.__options):
                if self.get_chip_rect(index).collidepoint(event.pos):
                    self.__value = option
                    return True
        return False

    def render(self, surface: pygame.Surface,
               active_fill: tuple = th.ROW_BLUE) -> None:
        """Draw every chip, the active one in the accent fill."""
        for index, option in enumerate(self.__options):
            th.draw_chip(surface, self.get_chip_rect(index),
                         option.replace("_", " "), option == self.__value,
                         active_fill=active_fill)

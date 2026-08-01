"""
tools/editor_popups.py
CSE Life: Compile & Conquer — Level editor, phases E2 + E3
─────────────────────────────────────────────────────────────
Every modal the editor opens, all built on the Style Guide §4.7
popup pattern: dim the screen, centre a CARD_TAN box with a 4 px
border in the severity colour, ALL-CAPS title, body, buttons.
While a modal is open it consumes ALL input.

Contract shared by every popup:

    handle_event(event)     feed it input
    update(dt)              caret blink / typewriter
    render(surface)         draw on top of the dimmed screen
    get_result()            None while open, else a payload
                            ("cancel" when dismissed)

Popups never touch the level document. They return a value and
the editor applies it as exactly one undo step.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pygame

from content.level_registry import (
    EXP_MAX,
    EXP_MIN,
    EXP_STEP,
    FACINGS,
    GATE_CREDITS_MAX,
    GATE_CREDITS_MIN,
    GATE_CREDITS_STEP,
    GATE_DAYS_MAX,
    GATE_DAYS_MIN,
    GATE_LOCKED_LINES_MAX,
    GATE_LOCKED_TITLE_DEFAULT,
    GATE_MONEY_COST_MAX,
    GATE_MONEY_COST_MIN,
    GATE_SEMESTER_MAX,
    GATE_SEMESTER_MIN,
    GATE_SKILL_LEVEL_MAX,
    GATE_SKILL_LEVEL_MIN,
    GATE_WALLET_MAX,
    GATE_WALLET_MIN,
    GATE_WALLET_STEP,
    GRID_MAX,
    GRID_MIN,
    INTERACTION_KINDS,
    MONEY_MAX,
    MONEY_MIN,
    MONEY_STEP,
    ON_COMPLETE_MODES,
    SKILL_IDS,
    SPEED_MODIFIER_BASE,
    SPEED_MODIFIER_MAX,
    SPEED_MODIFIER_MIN,
    SPEED_MODIFIER_STEP,
    TRIGGERS_MAX,
    TRIGGERS_MIN,
    get_npc_display_name,
    get_npc_emotions,
    get_prop_def,
)
from content.level_schema import (
    GateData,
    NpcData,
    PropData,
    ValidationReport,
)
from tools import editor_theme as th
from tools.editor_widgets import (
    ChipRow,
    Cycler,
    RowTable,
    Slider,
    Stepper,
    TextInput,
)
from ui.dialog_box import TYPEWRITER_CPS, DialogBox

CANCEL = "cancel"

_SLUG_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789_"


def slugify(text: str) -> str:
    """Turn a level name into a legal `[a-z0-9_]+` id."""
    out = "".join(c if c in _SLUG_CHARS else "_"
                  for c in text.strip().lower())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_") or "level"


class Modal:
    """
    Base modal: dim overlay, framed card, title, and a button strip.

    OOP: Inheritance — every popup below extends this and only adds
    its own body drawing and its own result payload.
    """

    def __init__(self, size: Tuple[int, int], title: str,
                 accent: tuple = th.BORDER_BROWN,
                 buttons: Sequence[Tuple[str, str, tuple]] = ()) -> None:
        self.__rect: pygame.Rect = pygame.Rect(0, 0, *size)
        self.__rect.center = (th.SCREEN_W // 2, th.SCREEN_H // 2)
        self.__title: str = title
        self.__accent: tuple = accent
        # (result value, label, fill) — laid out right-to-left
        self.__buttons: List[Tuple[str, str, tuple]] = list(buttons)
        self.__result: Optional[Any] = None

    # ── frame ─────────────────────────────────────────────────

    def get_rect(self) -> pygame.Rect:
        """The popup card."""
        return self.__rect

    def get_accent(self) -> tuple:
        """Severity colour driving the border and title."""
        return self.__accent

    def get_body_rect(self) -> pygame.Rect:
        """The area below the title, above the buttons."""
        return pygame.Rect(self.__rect.x + 26, self.__rect.y + 74,
                           self.__rect.w - 52, self.__rect.h - 74 - 74)

    def get_button_rects(self) -> List[pygame.Rect]:
        """Button hit boxes, in declaration order (packed from the right)."""
        rects: List[pygame.Rect] = []
        x = self.__rect.right - 26
        for _ in self.__buttons:
            x -= 150
            rects.append(pygame.Rect(x, self.__rect.bottom - 62, 150,
                                     th.BTN_H))
            x -= 12
        return rects

    # ── result ────────────────────────────────────────────────

    def get_result(self) -> Optional[Any]:
        """None while the popup is open, else its payload."""
        return self.__result

    def set_result(self, value: Any) -> None:
        """Close the popup with a payload."""
        self.__result = value

    def is_open(self) -> bool:
        """True until a result is set."""
        return self.__result is None

    # ── input ─────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route ESC and the button strip; subclasses extend this."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.set_result(CANCEL)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = th.hit(self.get_button_rects(), event.pos)
            if index >= 0:
                self.on_button(self.__buttons[index][0])

    def on_button(self, value: str) -> None:
        """Default: a button's value IS the result. Override to validate."""
        self.set_result(value)

    def update(self, dt: float) -> None:
        """Per-frame tick for animated popups. Default: nothing."""

    # ── drawing ───────────────────────────────────────────────

    def render(self, surface: pygame.Surface) -> None:
        """Dim, card, title, body, buttons."""
        th.draw_dim_overlay(surface)
        th.draw_panel(surface, self.__rect, th.CARD_TAN, 4, self.__accent)
        title_font = th.load_font(th.SIZE_POPUP_TITLE)
        rendered = title_font.render(
            th.truncate(title_font, self.__title.upper(), self.__rect.w - 52),
            True, self.__accent)
        surface.blit(rendered, (self.__rect.centerx - rendered.get_width() // 2,
                                self.__rect.y + 26))
        th.draw_rule(surface, self.__rect.y + 58, self.__rect.x + 26,
                     self.__rect.right - 26, self.__accent)
        self.render_body(surface)
        for rect, (_, label, fill) in zip(self.get_button_rects(),
                                          self.__buttons):
            th.draw_button(surface, rect, label, fill)

    def render_body(self, surface: pygame.Surface) -> None:
        """Subclass hook — draw the popup's contents."""


# ─────────────────────────────────────────────────────────────
# MESSAGE + CONFIRM
# ─────────────────────────────────────────────────────────────


class MessagePopup(Modal):
    """One-button notice — the `TOO MANY CREDITS` pattern (§4.7)."""

    def __init__(self, title: str, lines: Sequence[str],
                 accent: tuple = th.BAR_OVER) -> None:
        super().__init__((600, 244), title, accent,
                         [("ok", "OK", th.BTN_CANCEL)])
        self.__lines: List[str] = list(lines)

    def render_body(self, surface: pygame.Surface) -> None:
        """Centred body lines at a fixed pitch — no wrapping (§3)."""
        font = th.load_font(th.SIZE_SUB)
        body = self.get_body_rect()
        for index, line in enumerate(self.__lines[:3]):
            rendered = font.render(th.truncate(font, line, body.w), True,
                                   th.TEXT_COFFEE)
            surface.blit(rendered,
                         (body.centerx - rendered.get_width() // 2,
                          body.y + 10 + index * 26))


class ConfirmPopup(Modal):
    """Two-button question. Result is True (OK) or CANCEL."""

    def __init__(self, title: str, lines: Sequence[str],
                 accent: tuple = th.BAR_OVER,
                 ok_label: str = "OK") -> None:
        super().__init__((600, 244), title, accent,
                         [(CANCEL, "CANCEL", th.BTN_CANCEL),
                          ("ok", ok_label, th.BTN_CONFIRM)])
        self.__lines: List[str] = list(lines)

    def on_button(self, value: str) -> None:
        """Map the OK button onto a True payload."""
        self.set_result(True if value == "ok" else CANCEL)

    def render_body(self, surface: pygame.Surface) -> None:
        """Centred body lines."""
        font = th.load_font(th.SIZE_SUB)
        body = self.get_body_rect()
        for index, line in enumerate(self.__lines[:3]):
            rendered = font.render(th.truncate(font, line, body.w), True,
                                   th.TEXT_COFFEE)
            surface.blit(rendered,
                         (body.centerx - rendered.get_width() // 2,
                          body.y + 10 + index * 26))


# ─────────────────────────────────────────────────────────────
# LOAD PICKER
# ─────────────────────────────────────────────────────────────


class FilePickerPopup(Modal):
    """
    The LOAD dialog (Spec §3.2): every `levels/*.json` as a table row,
    blue on select, CONFIRM/CANCEL. Double-clicking a row confirms.
    """

    def __init__(self, paths: Sequence[str]) -> None:
        super().__init__((640, 460), "LOAD LEVEL", th.BORDER_BROWN,
                         [(CANCEL, "CANCEL", th.BTN_CANCEL),
                          ("ok", "LOAD", th.BTN_CONFIRM)])
        self.__paths: List[str] = list(paths)
        body = self.get_body_rect()
        self.__table: RowTable = RowTable(
            pygame.Rect(body.x, body.y, body.w, body.h - 6), "LEVEL FILE")
        self.__table.set_rows([os.path.basename(p) for p in self.__paths])
        if self.__paths:
            self.__table.set_selected(0)
        self.__last_click: Tuple[int, int] = (-1, 0)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Table first, then the frame's buttons."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self.__table.row_at(event.pos)
            now = pygame.time.get_ticks()
            if index >= 0 and index == self.__last_click[0] and \
                    now - self.__last_click[1] < 400:
                self.__table.set_selected(index)
                self.on_button("ok")
                return
            if index >= 0:
                self.__last_click = (index, now)
        if self.__table.handle_event(event):
            return
        super().handle_event(event)

    def on_button(self, value: str) -> None:
        """LOAD returns the chosen path; CANCEL returns CANCEL."""
        if value != "ok":
            self.set_result(CANCEL)
            return
        index = self.__table.get_selected()
        if 0 <= index < len(self.__paths):
            self.set_result(self.__paths[index])

    def render_body(self, surface: pygame.Surface) -> None:
        """The file table, or an empty-state line."""
        if not self.__paths:
            body = self.get_body_rect()
            th.draw_text(surface, th.load_font(th.SIZE_SUB),
                         "No level files in levels/ yet.",
                         (body.x, body.y + 10), th.STAT_BROWN)
            return
        self.__table.render(surface)


# ─────────────────────────────────────────────────────────────
# NEW LEVEL
# ─────────────────────────────────────────────────────────────


class NewLevelPopup(Modal):
    """
    NEW prompts for a name and a grid size (Spec §3.2). The id is
    slugged from the name as you type until you edit it by hand.
    """

    def __init__(self, default_width: int = 40,
                 default_height: int = 24) -> None:
        super().__init__((640, 400), "NEW LEVEL", th.BORDER_BROWN,
                         [(CANCEL, "CANCEL", th.BTN_CANCEL),
                          ("ok", "CREATE", th.BTN_CONFIRM)])
        body = self.get_body_rect()
        self.__name: TextInput = TextInput(
            pygame.Rect(body.x, body.y + 22, body.w, 34), "New Level")
        self.__slug: TextInput = TextInput(
            pygame.Rect(body.x, body.y + 92, body.w, 34), "new_level", 48,
            lambda c: c in _SLUG_CHARS)
        self.__slug_is_manual: bool = False
        self.__width: Stepper = Stepper(
            pygame.Rect(body.x, body.y + 162, 190, 34), default_width,
            GRID_MIN, GRID_MAX, 1)
        self.__height: Stepper = Stepper(
            pygame.Rect(body.x + 210, body.y + 162, 190, 34), default_height,
            GRID_MIN, GRID_MAX, 1)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Fields first, then steppers, then the frame."""
        if self.__name.handle_event(event):
            if self.__name.take_changed() and not self.__slug_is_manual:
                self.__slug.set_text(slugify(self.__name.get_text()))
            return
        if self.__slug.handle_event(event):
            if self.__slug.take_changed():
                self.__slug_is_manual = True
            return
        if self.__width.handle_event(event) or self.__height.handle_event(event):
            return
        super().handle_event(event)

    def update(self, dt: float) -> None:
        """Blink both carets."""
        self.__name.update(dt)
        self.__slug.update(dt)

    def on_button(self, value: str) -> None:
        """CREATE returns the settings; a bad slug is repaired first."""
        if value != "ok":
            self.set_result(CANCEL)
            return
        slug = slugify(self.__slug.get_text())
        self.set_result({
            "name": self.__name.get_text().strip() or "New Level",
            "level_id": slug,
            "width": int(self.__width.get_value()),
            "height": int(self.__height.get_value()),
        })

    def render_body(self, surface: pygame.Surface) -> None:
        """Labelled fields at the registration right-panel pitch."""
        body = self.get_body_rect()
        label = th.load_font(th.SIZE_LABEL)
        th.draw_text(surface, label, "LEVEL NAME", (body.x, body.y + 6),
                     th.CREDIT_HL)
        self.__name.render(surface)
        th.draw_text(surface, label, "LEVEL ID", (body.x, body.y + 76),
                     th.CREDIT_HL)
        self.__slug.render(surface, "new_level")
        th.draw_text(surface, label, "GRID WIDTH", (body.x, body.y + 146),
                     th.CREDIT_HL)
        th.draw_text(surface, label, "GRID HEIGHT",
                     (body.x + 210, body.y + 146), th.CREDIT_HL)
        self.__width.render(surface)
        self.__height.render(surface)


# ─────────────────────────────────────────────────────────────
# VALIDATION RESULTS
# ─────────────────────────────────────────────────────────────


class ValidationPopup(Modal):
    """
    The §7 report as a table: blockers in red, warnings in amber.
    Double-clicking a row asks the editor to pan to the offending cell.
    """

    def __init__(self, report: ValidationReport,
                 title: str = "VALIDATION") -> None:
        blockers = report.get_blockers()
        accent = th.BAR_OVER if blockers else (
            th.BAR_AMBER if report.get_warnings() else th.BTN_CONFIRM)
        super().__init__((760, 500), title, accent,
                         [("ok", "CLOSE", th.BTN_CONFIRM)])
        self.__issues = report.get_issues()
        self.__summary: str = (
            f"{len(blockers)} blocker(s), "
            f"{len(report.get_warnings())} warning(s)")
        body = self.get_body_rect()
        self.__table: RowTable = RowTable(
            pygame.Rect(body.x, body.y + 24, body.w, body.h - 30),
            "ISSUE")
        self.__table.set_rows(
            [f"{'!' if i.is_blocker() else '?'} {i.get_message()}"
             for i in self.__issues],
            [th.BAR_RED if i.is_blocker() else th.BAR_AMBER
             for i in self.__issues])
        self.__focus_cell: Optional[Tuple[int, int]] = None
        self.__last_click: Tuple[int, int] = (-1, 0)

    def take_focus_cell(self) -> Optional[Tuple[int, int]]:
        """The cell a double-clicked row pointed at — read once."""
        cell, self.__focus_cell = self.__focus_cell, None
        return cell

    def handle_event(self, event: pygame.event.Event) -> None:
        """Detect the double-click, then defer to the table and frame."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self.__table.row_at(event.pos)
            now = pygame.time.get_ticks()
            if index >= 0:
                if index == self.__last_click[0] and \
                        now - self.__last_click[1] < 400:
                    self.__focus_cell = self.__issues[index].get_cell()
                self.__last_click = (index, now)
        if self.__table.handle_event(event):
            return
        super().handle_event(event)

    def render_body(self, surface: pygame.Surface) -> None:
        """Summary line, then the issue table."""
        body = self.get_body_rect()
        th.draw_text(surface, th.load_font(th.SIZE_LABEL),
                     self.__summary.upper(), (body.x, body.y),
                     self.get_accent())
        if not self.__issues:
            th.draw_text(surface, th.load_font(th.SIZE_SUB),
                         "Nothing to report — this level is clean.",
                         (body.x, body.y + 34), th.STAT_BROWN)
            return
        th.draw_text(surface, th.load_font(th.SIZE_LABEL),
                     "DOUBLE-CLICK A ROW TO JUMP TO IT",
                     (body.right - 250, body.y), th.STAT_BROWN)
        self.__table.render(surface)


# ─────────────────────────────────────────────────────────────
# PROP SETTINGS  (Spec §5.3)
# ─────────────────────────────────────────────────────────────


class PropSettingsPopup(Modal):
    """
    Right-click settings for one placed prop.

    Edits a DETACHED copy of the prop, so CANCEL genuinely changes
    nothing and OK is exactly one undo step. The result payload is the
    edited prop's dict, applied by `LevelData.replace_prop()`.

    Portal props swap the reward controls for travel controls: a portal
    grants nothing, it moves the player between campus locations
    (Spec §9).
    """

    def __init__(self, prop: PropData) -> None:
        definition = get_prop_def(prop.get_type_id()) or {}
        name = definition.get("name", prop.get_type_id())
        super().__init__((660, 486),
                         f"PROP SETTINGS - {name} ({prop.get_uid()})",
                         th.BORDER_BROWN,
                         [(CANCEL, "CANCEL", th.BTN_CANCEL),
                          ("ok", "OK", th.BTN_CONFIRM)])
        self.__prop: PropData = PropData.from_dict(prop.to_dict())
        self.__is_portal: bool = prop.is_portal()

        body = self.get_body_rect()
        self.__solid: ChipRow = ChipRow(
            pygame.Rect(body.x, body.y + 16, 300, 26),
            ["blocking", "passthrough"],
            "passthrough" if prop.get_passthrough() else "blocking")
        self.__speed: Slider = Slider(
            pygame.Rect(body.x, body.y + 66, 300, 20),
            prop.get_speed_modifier(), SPEED_MODIFIER_MIN,
            SPEED_MODIFIER_MAX, SPEED_MODIFIER_STEP, SPEED_MODIFIER_BASE)
        self.__speed.set_enabled(prop.get_passthrough())
        self.__interactable: ChipRow = ChipRow(
            pygame.Rect(body.x, body.y + 122, 180, 26), ["yes", "no"],
            "yes" if prop.get_interactable() else "no")

        inner_x = body.x + 12
        self.__kind: ChipRow = ChipRow(
            pygame.Rect(inner_x, body.y + 184, 330, 26),
            list(INTERACTION_KINDS), prop.get_interaction_kind())
        self.__amount: Stepper = Stepper(
            pygame.Rect(inner_x, body.y + 232, 210, 30), prop.get_amount(),
            MONEY_MIN, MONEY_MAX, MONEY_STEP)
        self.__triggers: Stepper = Stepper(
            pygame.Rect(inner_x + 240, body.y + 232, 210, 30),
            prop.get_triggers_per_semester(), TRIGGERS_MIN, TRIGGERS_MAX, 1)
        self.__skill: Cycler = Cycler(
            pygame.Rect(inner_x, body.y + 292, 450, 30), list(SKILL_IDS),
            prop.get_skill_id() or SKILL_IDS[0])
        self.__retune_amount()

        self.__target: TextInput = TextInput(
            pygame.Rect(inner_x, body.y + 184, 450, 30),
            prop.get_target_level_id(), 48, lambda c: c in _SLUG_CHARS)
        spawn = prop.get_target_spawn() or (0, 0)
        self.__spawn_x: Stepper = Stepper(
            pygame.Rect(inner_x, body.y + 244, 210, 30), spawn[0], 0,
            GRID_MAX - 1, 1)
        self.__spawn_y: Stepper = Stepper(
            pygame.Rect(inner_x + 240, body.y + 244, 210, 30), spawn[1], 0,
            GRID_MAX - 1, 1)

    # ── helpers ───────────────────────────────────────────────

    def __retune_amount(self) -> None:
        """Point the amount stepper at the active reward's range."""
        if self.__kind.get_value() == "money":
            self.__amount.set_range(MONEY_MIN, MONEY_MAX, MONEY_STEP, 0,
                                    " BDT")
        else:
            self.__amount.set_range(float(EXP_MIN), float(EXP_MAX),
                                    float(EXP_STEP), 0, " EXP")

    def __is_interactable(self) -> bool:
        """Whether the interaction sub-box should be live."""
        return self.__interactable.get_value() == "yes"

    # ── input ─────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        """Widgets first (in draw order), then the frame."""
        passthrough = self.__solid.get_value() == "passthrough"
        if self.__solid.handle_event(event):
            self.__speed.set_enabled(
                self.__solid.get_value() == "passthrough")
            return
        if passthrough and self.__speed.handle_event(event):
            return
        if self.__interactable.handle_event(event):
            return
        if self.__is_interactable():
            if self.__is_portal:
                if self.__target.handle_event(event):
                    return
                if self.__spawn_x.handle_event(event) or \
                        self.__spawn_y.handle_event(event):
                    return
            else:
                if self.__kind.handle_event(event):
                    self.__retune_amount()
                    return
                if self.__kind.get_value() != "none":
                    if self.__amount.handle_event(event):
                        return
                    if self.__triggers.handle_event(event):
                        return
                if self.__kind.get_value() == "skill" and \
                        self.__skill.handle_event(event):
                    return
        super().handle_event(event)

    def update(self, dt: float) -> None:
        """Blink the portal target caret."""
        self.__target.update(dt)

    def on_button(self, value: str) -> None:
        """OK folds every widget back onto the detached prop."""
        if value != "ok":
            self.set_result(CANCEL)
            return
        prop = self.__prop
        prop.set_passthrough(self.__solid.get_value() == "passthrough")
        prop.set_speed_modifier(self.__speed.get_value())
        prop.set_interactable(self.__is_interactable())
        if self.__is_portal:
            prop.set_interaction_kind("none")
            prop.set_target_level_id(self.__target.get_text())
            prop.set_target_spawn((int(self.__spawn_x.get_value()),
                                   int(self.__spawn_y.get_value())))
        else:
            prop.set_interaction_kind(self.__kind.get_value())
            if self.__kind.get_value() == "skill":
                prop.set_skill_id(self.__skill.get_value())
            if self.__kind.get_value() != "none":
                prop.set_amount(self.__amount.get_value())
                prop.set_triggers_per_semester(
                    int(self.__triggers.get_value()))
        self.set_result(prop.to_dict())

    # ── drawing ───────────────────────────────────────────────

    def render_body(self, surface: pygame.Surface) -> None:
        """Collision controls, then the interaction sub-box."""
        body = self.get_body_rect()
        label = th.load_font(th.SIZE_LABEL)
        passthrough = self.__solid.get_value() == "passthrough"

        th.draw_text(surface, label, "COLLISION", (body.x, body.y),
                     th.CREDIT_HL)
        self.__solid.render(surface)

        speed_colour = th.CREDIT_HL if passthrough else th.STAT_BROWN
        th.draw_text(surface, label, "SPEED MODIFIER",
                     (body.x, body.y + 50), speed_colour)
        self.__speed.render(surface)
        if not passthrough:
            th.draw_text(surface, label, "(BLOCKING - NOT WALKABLE)",
                         (body.x + 380, body.y + 70), th.STAT_BROWN)

        th.draw_text(surface, label, "INTERACTABLE", (body.x, body.y + 106),
                     th.CREDIT_HL)
        self.__interactable.render(surface)

        box = pygame.Rect(body.x, body.y + 158, body.w, body.h - 158)
        th.draw_panel(surface, box, th.HEADER_TAN, th.BORDER_ROW)
        if not self.__is_interactable():
            th.draw_text_centered(surface, th.load_font(th.SIZE_SUB),
                                  "Not interactable — no reward.", box,
                                  th.STAT_BROWN)
            return
        if self.__is_portal:
            self.__render_portal_fields(surface, label)
        else:
            self.__render_reward_fields(surface, label)

    def __render_portal_fields(self, surface: pygame.Surface,
                               label: pygame.font.Font) -> None:
        """Portals travel; they never pay out."""
        body = self.get_body_rect()
        x = body.x + 12
        th.draw_text(surface, label, "TARGET LEVEL ID", (x, body.y + 168),
                     th.CREDIT_HL)
        self.__target.render(surface, "campus_lab")
        th.draw_text(surface, label, "TARGET SPAWN X", (x, body.y + 228),
                     th.CREDIT_HL)
        th.draw_text(surface, label, "TARGET SPAWN Y", (x + 240, body.y + 228),
                     th.CREDIT_HL)
        self.__spawn_x.render(surface)
        self.__spawn_y.render(surface)
        th.draw_text(surface, label,
                     "PORTALS MOVE THE PLAYER — THEY GRANT NOTHING",
                     (x, body.y + 288), th.STAT_BROWN)

    def __render_reward_fields(self, surface: pygame.Surface,
                               label: pygame.font.Font) -> None:
        """Reward kind, amount, triggers and (for skills) the node."""
        body = self.get_body_rect()
        x = body.x + 12
        th.draw_text(surface, label, "REWARD KIND", (x, body.y + 168),
                     th.CREDIT_HL)
        self.__kind.render(surface)
        kind = self.__kind.get_value()
        if kind == "none":
            th.draw_text(surface, th.load_font(th.SIZE_SUB),
                         "Shows a flavour line only.", (x, body.y + 236),
                         th.STAT_BROWN)
            return

        th.draw_text(surface, label, "AMOUNT", (x, body.y + 216),
                     th.CREDIT_HL)
        th.draw_text(surface, label, "TRIGGERS / SEMESTER",
                     (x + 240, body.y + 216), th.CREDIT_HL)
        self.__amount.render(surface)
        self.__triggers.render(surface)

        if kind == "skill":
            th.draw_text(surface, label, "SKILL NODE", (x, body.y + 276),
                         th.CREDIT_HL)
            self.__skill.render(surface)
            th.draw_text(surface, label,
                         f"EXP IS CAPPED AT {EXP_MAX} — A PROP NEVER BEATS "
                         f"A SIDEQUEST", (x, body.y + 330), th.STAT_BROWN)
        else:
            total = self.__amount.get_value() * self.__triggers.get_value()
            th.draw_text(surface, label,
                         f"UP TO {int(total):,} BDT PER SEMESTER FROM THIS "
                         f"PROP", (x, body.y + 276), th.STAT_BROWN)


# ─────────────────────────────────────────────────────────────
# NPC DIALOG EDITOR  (Spec §6.3)
# ─────────────────────────────────────────────────────────────


class NpcDialogPopup(Modal):
    """
    Right-click editor for one placed NPC: facing, interactivity, the
    ordered chain list, the lines inside the selected chain, the
    emotion its portrait wears, the on-complete mode, and a live
    preview that plays the chain in the real in-game dialog box.

    Like the prop popup, it edits a DETACHED copy and returns a dict.

    There is deliberately no availability control: the 0.75-1.00
    time-pool window is a game rule, not level data (Spec §6.1).
    """

    def __init__(self, npc: NpcData, assets: Any) -> None:
        super().__init__(
            (1080, 604),
            f"NPC DIALOG - {get_npc_display_name(npc.get_type_id())} "
            f"({npc.get_uid()})", th.BORDER_BROWN,
            [(CANCEL, "CANCEL", th.BTN_CANCEL),
             ("ok", "OK", th.BTN_CONFIRM),
             ("preview", "> PREVIEW", th.BAR_AMBER)])
        self.__npc: NpcData = NpcData.from_dict(npc.to_dict())
        self.__type_id: str = npc.get_type_id()
        self.__assets: Any = assets
        self.__emotions: List[str] = get_npc_emotions(self.__type_id)

        body = self.get_body_rect()
        left_w, right_x = 300, body.x + 320
        right_w = body.right - right_x

        self.__facing: ChipRow = ChipRow(
            pygame.Rect(body.x, body.y + 16, left_w, 26), list(FACINGS),
            npc.get_facing())
        self.__interactable: ChipRow = ChipRow(
            pygame.Rect(right_x, body.y + 16, 180, 26), ["yes", "no"],
            "yes" if npc.get_interactable() else "no")
        self.__on_complete: ChipRow = ChipRow(
            pygame.Rect(right_x + 200, body.y + 16, right_w - 200, 26),
            list(ON_COMPLETE_MODES), npc.get_on_complete())

        self.__chains: RowTable = RowTable(
            pygame.Rect(body.x, body.y + 56, left_w, 200), "CHAINS")
        self.__lines: RowTable = RowTable(
            pygame.Rect(right_x, body.y + 56, right_w, 200), "LINES")

        self.__chain_id: TextInput = TextInput(
            pygame.Rect(body.x, body.y + 312, left_w, 30), "", 32)
        self.__line_text: TextInput = TextInput(
            pygame.Rect(right_x, body.y + 312, right_w, 30), "", 60)
        self.__emotion: ChipRow = ChipRow(
            pygame.Rect(body.x, body.y + 364, left_w, 26),
            self.__emotions or ["neutral"],
            self.__emotions[0] if self.__emotions else "neutral")

        self.__chain_buttons: List[pygame.Rect] = self.__button_row(
            body.x, body.y + 262, left_w)
        self.__line_buttons: List[pygame.Rect] = self.__button_row(
            right_x, body.y + 262, 298)

        # preview state — the typewriter clock lives here, not in DialogBox
        self.__preview: bool = False
        self.__preview_line: int = 0
        self.__preview_elapsed: float = 0.0
        self.__pulse: float = 0.0
        self.__dialog: DialogBox = DialogBox(th.SCREEN_W, th.SCREEN_H)

        if self.__npc.get_chain_count() == 0:
            self.__npc.add_chain("intro")
        self.__refresh()

    # ── layout helper ─────────────────────────────────────────

    @staticmethod
    def __button_row(x: int, y: int, width: int) -> List[pygame.Rect]:
        """Four equal buttons: add, remove, up, down."""
        gap = 6
        each = (width - gap * 3) // 4
        return [pygame.Rect(x + i * (each + gap), y, each, 28)
                for i in range(4)]

    # ── state ─────────────────────────────────────────────────

    def __selected_chain(self):
        """The chain the tables are showing, or None."""
        return self.__npc.get_chain(self.__chains.get_selected())

    def __refresh(self) -> None:
        """
        Re-read the tables and fields from the working NPC copy. Rows are
        filled BEFORE any selection is applied, because a table refuses a
        selection index it has no row for yet.
        """
        self.__chains.set_rows(
            [f"{c.get_chain_id()}  ({c.get_line_count()} lines)"
             for c in self.__npc.get_chains()])
        if self.__chains.get_selected() < 0 and self.__npc.get_chain_count():
            self.__chains.set_selected(0)

        chain = self.__selected_chain()
        if chain is None:
            self.__lines.set_rows([])
            self.__chain_id.set_text("")
            self.__line_text.set_text("")
            return

        self.__chain_id.set_text(chain.get_chain_id())
        lines = chain.get_lines()
        self.__lines.set_rows(lines)
        if self.__lines.get_selected() < 0 and lines:
            self.__lines.set_selected(0)
        if self.__emotions:
            self.__emotion.set_value(chain.get_emotion()
                                     or self.__emotions[0])
        index = self.__lines.get_selected()
        self.__line_text.set_text(lines[index] if 0 <= index < len(lines)
                                  else "")

    def __commit_fields(self) -> None:
        """Push the two text fields back into the working copy."""
        chain = self.__selected_chain()
        if chain is None:
            return
        if self.__chain_id.get_text().strip():
            chain.set_chain_id(self.__chain_id.get_text())
        index = self.__lines.get_selected()
        if index >= 0:
            chain.set_line(index, self.__line_text.get_text())
        chain.set_emotion(self.__emotion.get_value())

    # ── input ─────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        """Preview swallows everything while it plays."""
        if self.__preview:
            self.__handle_preview_event(event)
            return

        if self.__facing.handle_event(event) or \
                self.__interactable.handle_event(event) or \
                self.__on_complete.handle_event(event):
            return
        if self.__emotion.handle_event(event):
            self.__commit_fields()
            self.__refresh()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = th.hit(self.__chain_buttons, event.pos)
            if index >= 0:
                self.__chain_action(index)
                return
            index = th.hit(self.__line_buttons, event.pos)
            if index >= 0:
                self.__line_action(index)
                return

        previous_chain = self.__chains.get_selected()
        if self.__chains.handle_event(event):
            if self.__chains.get_selected() != previous_chain:
                self.__lines.set_selected(-1)
            self.__refresh()
            return
        if self.__lines.handle_event(event):
            self.__refresh()
            return
        if self.__chain_id.handle_event(event):
            self.__commit_fields()
            self.__chains.set_rows(
                [f"{c.get_chain_id()}  ({c.get_line_count()} lines)"
                 for c in self.__npc.get_chains()])
            return
        if self.__line_text.handle_event(event):
            self.__commit_fields()
            chain = self.__selected_chain()
            if chain is not None:
                self.__lines.set_rows(chain.get_lines())
            return
        super().handle_event(event)

    def __chain_action(self, index: int) -> None:
        """+ CHAIN / - CHAIN / move up / move down."""
        self.__commit_fields()
        selected = self.__chains.get_selected()
        if index == 0:
            self.__npc.add_chain()
            self.__chains.set_selected(self.__npc.get_chain_count() - 1)
        elif index == 1 and self.__npc.get_chain_count() > 1:
            if self.__npc.remove_chain(selected):
                self.__chains.set_selected(min(selected,
                                               self.__npc.get_chain_count() - 1))
        elif index in (2, 3):
            delta = -1 if index == 2 else 1
            if self.__npc.move_chain(selected, delta):
                self.__chains.set_selected(selected + delta)
        self.__lines.set_selected(-1)
        self.__refresh()

    def __line_action(self, index: int) -> None:
        """+ LINE / - LINE / move up / move down."""
        self.__commit_fields()
        chain = self.__selected_chain()
        if chain is None:
            return
        selected = self.__lines.get_selected()
        if index == 0:
            chain.add_line("New line.")
            self.__lines.set_selected(chain.get_line_count() - 1)
        elif index == 1 and selected >= 0:
            if chain.remove_line(selected):
                self.__lines.set_selected(min(selected,
                                              chain.get_line_count() - 1))
        elif index in (2, 3) and selected >= 0:
            delta = -1 if index == 2 else 1
            if chain.move_line(selected, delta):
                self.__lines.set_selected(selected + delta)
        self.__refresh()

    def __handle_preview_event(self, event: pygame.event.Event) -> None:
        """
        Advance the preview: the first press finishes the line instantly,
        the next moves on, and the press after the last line closes it
        (Spec §6.4).
        """
        advance = (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) \
            or (event.type == pygame.KEYDOWN
                and event.key in (pygame.K_SPACE, pygame.K_RETURN))
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.__preview = False
            return
        if not advance:
            return
        chain = self.__selected_chain()
        lines = chain.get_lines() if chain else []
        if self.__preview_line >= len(lines):
            self.__preview = False
            return
        full = lines[self.__preview_line]
        if DialogBox.visible_length(self.__preview_elapsed) < len(full):
            self.__preview_elapsed = len(full) / TYPEWRITER_CPS
            return
        self.__preview_line += 1
        self.__preview_elapsed = 0.0
        if self.__preview_line >= len(lines):
            self.__preview = False

    def on_button(self, value: str) -> None:
        """PREVIEW starts playback; OK returns the edited NPC dict."""
        if value == "preview":
            self.__commit_fields()
            self.__refresh()
            chain = self.__selected_chain()
            if chain is None or chain.get_line_count() == 0:
                return
            self.__preview = True
            self.__preview_line = 0
            self.__preview_elapsed = 0.0
            return
        if value != "ok":
            self.set_result(CANCEL)
            return
        self.__commit_fields()
        self.__npc.set_facing(self.__facing.get_value())
        self.__npc.set_interactable(self.__interactable.get_value() == "yes")
        self.__npc.set_on_complete(self.__on_complete.get_value())
        self.set_result(self.__npc.to_dict())

    def update(self, dt: float) -> None:
        """Carets, the preview typewriter and the arrow pulse."""
        self.__chain_id.update(dt)
        self.__line_text.update(dt)
        self.__pulse += dt
        if self.__preview:
            self.__preview_elapsed += dt

    # ── drawing ───────────────────────────────────────────────

    def render_body(self, surface: pygame.Surface) -> None:
        """Chips, both tables, both editors, then the preview overlay."""
        body = self.get_body_rect()
        label = th.load_font(th.SIZE_LABEL)
        right_x = self.__lines.get_rect().x

        th.draw_text(surface, label, "FACING", (body.x, body.y), th.CREDIT_HL)
        th.draw_text(surface, label, "INTERACTABLE", (right_x, body.y),
                     th.CREDIT_HL)
        th.draw_text(surface, label, "WHEN ALL CHAINS HAVE PLAYED",
                     (right_x + 200, body.y), th.CREDIT_HL)
        self.__facing.render(surface)
        self.__interactable.render(surface)
        self.__on_complete.render(surface, th.BAR_AMBER)

        self.__chains.render(surface)
        self.__lines.render(surface)

        for rect, text in zip(self.__chain_buttons,
                              ("+ CHAIN", "- CHAIN", "UP", "DOWN")):
            th.draw_button(surface, rect, text, th.HEADER_TAN,
                           th.fit_font(text, rect.w - 6))
        for rect, text in zip(self.__line_buttons,
                              ("+ LINE", "- LINE", "UP", "DOWN")):
            th.draw_button(surface, rect, text, th.HEADER_TAN,
                           th.fit_font(text, rect.w - 6))

        th.draw_text(surface, label, "CHAIN ID", (body.x, body.y + 298),
                     th.CREDIT_HL)
        self.__chain_id.render(surface, "intro")
        th.draw_text(surface, label, "LINE TEXT", (right_x, body.y + 298),
                     th.CREDIT_HL)
        self.__line_text.render(surface, "select a line to edit it")

        th.draw_text(surface, label, "PORTRAIT EMOTION",
                     (body.x, body.y + 350), th.CREDIT_HL)
        self.__emotion.render(surface)

        th.draw_text(surface, label,
                     "CHAINS PLAY IN ORDER, ONE PER INTERACTION.",
                     (right_x, body.y + 356), th.STAT_BROWN)
        th.draw_text(surface, label,
                     "LINES ARE PRE-SPLIT — KEEP THEM SHORT.",
                     (right_x, body.y + 372), th.STAT_BROWN)

        if self.__preview:
            self.__render_preview(surface)

    def __render_preview(self, surface: pygame.Surface) -> None:
        """
        Play the selected chain in the REAL in-game dialog box, typewriter
        and portrait included, inside the popup card.
        """
        card = self.get_rect()
        shade = pygame.Surface(card.size, pygame.SRCALPHA)
        shade.fill(th.OVERLAY_DIM)
        surface.blit(shade, card.topleft)

        chain = self.__selected_chain()
        lines = chain.get_lines() if chain else []
        if not lines:
            return
        index = min(self.__preview_line, len(lines) - 1)
        full = lines[index]
        shown = full[:DialogBox.visible_length(self.__preview_elapsed)]
        emotion = self.__emotion.get_value()
        portrait = self.__assets.get_npc_portrait(self.__type_id, emotion, 96) \
            if self.__assets is not None else None

        box = pygame.Rect(card.x + 40, card.bottom - 240, card.w - 80, 168)

        # The dimmed form still shows through, so the hint gets its own
        # opaque strip rather than fighting the buttons underneath it.
        strip = pygame.Rect(box.x, box.y - 30, box.w, 24)
        th.draw_panel(surface, strip, th.TITLE_SLATE, 2, th.BAR_AMBER)
        th.draw_text_vcenter(
            surface, th.load_font(th.SIZE_LABEL),
            f"PREVIEW {index + 1}/{len(lines)}   EMOTION: {emotion.upper()}"
            f"   SPACE ADVANCE   ESC CLOSE",
            strip.x + 8, strip, th.BAR_AMBER)

        self.__dialog.render(surface, get_npc_display_name(self.__type_id),
                             shown, portrait, len(shown) >= len(full),
                             self.__pulse, box)


# ─────────────────────────────────────────────────────────────
# GATE FORM  (Feature 6, phase F6)
# ─────────────────────────────────────────────────────────────


def gate_requirement_labels(gate: GateData) -> List[str]:
    """
    The requirement side of the locked notice, ALL-CAPS (Style Guide §7).

    ui/gate_notice.py (F8) draws the same strings with a "YOU HAVE"
    column beside them; the editor has no player, so it shows the
    requirement column alone. Keeping the wording here means the author
    reads exactly what the player will read.
    """
    lines: List[str] = []
    if gate.get_min_semester():
        lines.append(f"SEMESTER {gate.get_min_semester()}")
    if gate.get_min_credits():
        lines.append(f"CREDITS {gate.get_min_credits()}")
    if gate.get_min_days_remaining():
        lines.append(f"{gate.get_min_days_remaining()} DAYS LEFT")
    if gate.get_min_wallet():
        lines.append(f"{gate.get_min_wallet():,.0f} BDT")
    skill = gate.get_required_skill_id()
    if skill and gate.get_required_skill_level():
        lines.append(f"{skill.upper().replace('_', ' ')} "
                     f"LEVEL {gate.get_required_skill_level()}")
    for code in gate.get_required_course_codes():
        lines.append(f"PASSED {code}")
    if gate.get_requires_graduated():
        lines.append("GRADUATED")
    return lines


def gate_cost_labels(gate: GateData) -> List[str]:
    """What entering charges, ALL-CAPS, or [] when entry is free."""
    lines: List[str] = []
    if gate.get_cost_days():
        lines.append(f"-{gate.get_cost_days()} DAYS")
    if gate.get_cost_money():
        lines.append(f"-{gate.get_cost_money():,.0f} BDT")
    return lines


class GatePopup(Modal):
    """
    The gate form: one editable GateData for a prop, an NPC or a zone.

    Edits a DETACHED copy, so CANCEL genuinely changes nothing and OK is
    exactly one undo step — the same contract PropSettingsPopup uses.
    The result payload is the gate's dict, which the caller folds into
    the entity it came from.

    CLEAR GATE resets every field without closing, so an author can undo
    a half-built gate without cancelling the whole popup.
    """

    SIZE = (940, 640)

    NONE_SKILL = "NONE"

    def __init__(self, gate: GateData, owner_label: str = "",
                 default_min_semester: int = 0) -> None:
        """
        Build the form over a copy of `gate`.

        `default_min_semester` seeds an EMPTY gate only. It is how an
        NPC's roster semester reaches the form (PHASELOG_F5 §4.6): the
        editor passes npc.make_default_gate().get_min_semester(), so
        opening the form on Prof. Hoque starts at semester 5 while a
        gate the author already saved is never silently overwritten.
        """
        title = "GATE" if not owner_label else f"GATE - {owner_label}"
        super().__init__(self.SIZE, title, th.BORDER_BROWN,
                         [(CANCEL, "CANCEL", th.BTN_CANCEL),
                          ("clear", "CLEAR GATE", th.HEADER_TAN),
                          ("ok", "OK", th.BTN_CONFIRM)])
        self.__gate: GateData = gate.clone()
        if self.__gate.is_default() and default_min_semester:
            self.__gate.set_min_semester(default_min_semester)

        body = self.get_body_rect()
        left = body.x
        right = body.x + 452
        gate_now = self.__gate

        # ── left column: who may pass ─────────────────────────
        self.__semester: Stepper = Stepper(
            pygame.Rect(left, body.y + 16, 210, 30),
            gate_now.get_min_semester(), GATE_SEMESTER_MIN,
            GATE_SEMESTER_MAX, 1)
        self.__credits: Stepper = Stepper(
            pygame.Rect(left, body.y + 72, 210, 30),
            gate_now.get_min_credits(), GATE_CREDITS_MIN, GATE_CREDITS_MAX,
            GATE_CREDITS_STEP)
        self.__days: Stepper = Stepper(
            pygame.Rect(left, body.y + 128, 210, 30),
            gate_now.get_min_days_remaining(), GATE_DAYS_MIN, GATE_DAYS_MAX,
            1)
        self.__wallet: Stepper = Stepper(
            pygame.Rect(left, body.y + 184, 300, 30),
            gate_now.get_min_wallet(), GATE_WALLET_MIN, GATE_WALLET_MAX,
            GATE_WALLET_STEP, 0, " BDT")
        self.__skill: Cycler = Cycler(
            pygame.Rect(left, body.y + 240, 420, 30),
            [self.NONE_SKILL] + list(SKILL_IDS),
            gate_now.get_required_skill_id() or self.NONE_SKILL)
        self.__skill_level: Stepper = Stepper(
            pygame.Rect(left, body.y + 296, 210, 30),
            gate_now.get_required_skill_level(), GATE_SKILL_LEVEL_MIN,
            GATE_SKILL_LEVEL_MAX, 1)
        self.__graduated: ChipRow = ChipRow(
            pygame.Rect(left, body.y + 352, 180, 26), ["no", "yes"],
            "yes" if gate_now.get_requires_graduated() else "no")

        # ── right column: what it costs, and what it says ─────
        self.__cost_days: Stepper = Stepper(
            pygame.Rect(right, body.y + 16, 210, 30),
            gate_now.get_cost_days(), GATE_DAYS_MIN, GATE_DAYS_MAX, 1)
        self.__cost_money: Stepper = Stepper(
            pygame.Rect(right, body.y + 72, 300, 30),
            gate_now.get_cost_money(), GATE_MONEY_COST_MIN,
            GATE_MONEY_COST_MAX, GATE_WALLET_STEP, 0, " BDT")
        self.__courses: TextInput = TextInput(
            pygame.Rect(right, body.y + 128, 420, 30),
            ", ".join(gate_now.get_required_course_codes()), 96)
        self.__locked_title: TextInput = TextInput(
            pygame.Rect(right, body.y + 184, 420, 30),
            gate_now.get_locked_title(), 32)

        existing = gate_now.get_locked_lines()
        self.__lines: List[TextInput] = [
            TextInput(pygame.Rect(right, body.y + 240 + i * 36, 420, 30),
                      existing[i] if i < len(existing) else "", 64)
            for i in range(GATE_LOCKED_LINES_MAX)]

        self.__inputs: List[TextInput] = [self.__courses,
                                          self.__locked_title] + self.__lines

    # ── helpers ───────────────────────────────────────────────

    def get_gate(self) -> GateData:
        """
        The detached gate being edited.

        Mutating it directly does NOT change the form -- OK reads the
        widgets, not this object. Use load() to push a gate INTO the
        controls; this getter is for inspecting the current state.
        """
        return self.__gate

    def load(self, gate: GateData) -> None:
        """
        Push a GateData into every control -- the mirror of the commit.

        Exists because the widgets are the source of truth once the form
        is open: without this, setting a field on the object returned by
        get_gate() would be silently discarded on OK.
        """
        self.__gate = gate.clone()
        self.__semester.set_value(self.__gate.get_min_semester())
        self.__credits.set_value(self.__gate.get_min_credits())
        self.__days.set_value(self.__gate.get_min_days_remaining())
        self.__wallet.set_value(self.__gate.get_min_wallet())
        self.__skill.set_value(self.__gate.get_required_skill_id()
                               or self.NONE_SKILL)
        self.__skill_level.set_value(self.__gate.get_required_skill_level())
        self.__graduated.set_value(
            "yes" if self.__gate.get_requires_graduated() else "no")
        self.__cost_days.set_value(self.__gate.get_cost_days())
        self.__cost_money.set_value(self.__gate.get_cost_money())
        self.__courses.set_text(
            ", ".join(self.__gate.get_required_course_codes()))
        self.__locked_title.set_text(self.__gate.get_locked_title())
        lines = self.__gate.get_locked_lines()
        for index, field in enumerate(self.__lines):
            field.set_text(lines[index] if index < len(lines) else "")

    def __harvest(self) -> GateData:
        """Fold every widget back onto the detached gate."""
        gate = self.__gate
        gate.set_min_semester(int(self.__semester.get_value()))
        gate.set_min_credits(int(self.__credits.get_value()))
        gate.set_min_days_remaining(int(self.__days.get_value()))
        gate.set_min_wallet(self.__wallet.get_value())
        skill = self.__skill.get_value()
        gate.set_required_skill_id(None if skill == self.NONE_SKILL
                                   else skill)
        gate.set_required_skill_level(int(self.__skill_level.get_value()))
        gate.set_requires_graduated(self.__graduated.get_value() == "yes")
        gate.set_cost_days(int(self.__cost_days.get_value()))
        gate.set_cost_money(self.__cost_money.get_value())
        # GateData upper-cases and de-duplicates; the field is free text.
        gate.set_required_course_codes(self.__courses.get_text())
        gate.set_locked_title(self.__locked_title.get_text())
        gate.set_locked_lines([field.get_text() for field in self.__lines])
        return gate

    def __reset_widgets(self) -> None:
        """Put every control back to the default gate -- CLEAR GATE."""
        self.load(GateData())

    # ── input ─────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        """Widgets first (in draw order), then the frame."""
        for widget in (self.__semester, self.__credits, self.__days,
                       self.__wallet, self.__skill, self.__skill_level,
                       self.__graduated, self.__cost_days,
                       self.__cost_money):
            if widget.handle_event(event):
                return
        for field in self.__inputs:
            if field.handle_event(event):
                return
        super().handle_event(event)

    def update(self, dt: float) -> None:
        """Blink the caret in whichever field has focus."""
        for field in self.__inputs:
            field.update(dt)

    def on_button(self, value: str) -> None:
        """OK commits; CLEAR resets in place; anything else cancels."""
        if value == "clear":
            self.__reset_widgets()
            return
        if value != "ok":
            self.set_result(CANCEL)
            return
        self.set_result(self.__harvest().to_dict())

    # ── drawing ───────────────────────────────────────────────

    def render_body(self, surface: pygame.Surface) -> None:
        """Two columns of controls, then the live requirement strip."""
        body = self.get_body_rect()
        label = th.load_font(th.SIZE_LABEL)
        left = body.x
        right = body.x + 452

        for text, y in (("MIN SEMESTER", 0), ("MIN CREDITS", 56),
                        ("MIN DAYS LEFT", 112), ("MIN WALLET", 168),
                        ("REQUIRED SKILL", 224),
                        ("REQUIRED SKILL LEVEL", 280),
                        ("REQUIRES GRADUATED", 336)):
            th.draw_text(surface, label, text, (left, body.y + y),
                         th.CREDIT_HL)
        for text, y in (("COST DAYS", 0), ("COST MONEY", 56),
                        ("REQUIRED COURSES (COMMA SEPARATED)", 112),
                        ("LOCKED TITLE", 168), ("LOCKED MESSAGE", 224)):
            th.draw_text(surface, label, text, (right, body.y + y),
                         th.CREDIT_HL)

        for widget in (self.__semester, self.__credits, self.__days,
                       self.__wallet, self.__skill, self.__skill_level,
                       self.__cost_days, self.__cost_money):
            widget.render(surface)
        self.__graduated.render(surface)
        self.__courses.render(surface, "CSE101, MAT120")
        self.__locked_title.render(surface, GATE_LOCKED_TITLE_DEFAULT)
        for field in self.__lines:
            field.render(surface)

        # The skill level stepper only means anything with a skill set.
        if self.__skill.get_value() == self.NONE_SKILL:
            th.draw_text(surface, label, "(NO SKILL SELECTED)",
                         (left + 224, body.y + 304), th.STAT_BROWN)

        self.__render_summary(surface)

    def __render_summary(self, surface: pygame.Surface) -> None:
        """
        The live preview strip: what the player will be told.

        Drawn in the same words ui/gate_notice.py (F8) will use, so the
        author is looking at the player's view while editing rather than
        guessing what their steppers add up to.
        """
        body = self.get_body_rect()
        strip = pygame.Rect(body.x, body.y + 396, body.w, 96)
        th.draw_panel(surface, strip, th.HEADER_TAN, th.BORDER_ROW)

        gate = self.__harvest()
        label = th.load_font(th.SIZE_LABEL)
        sub = th.load_font(th.SIZE_SUB)

        th.draw_text(surface, label, "PLAYER SEES", (strip.x + 10,
                                                     strip.y + 8),
                     th.CREDIT_HL)
        if gate.is_default():
            th.draw_text(surface, sub, "No gate - anyone may pass.",
                         (strip.x + 10, strip.y + 30), th.STAT_BROWN)
            return

        th.draw_text(surface, sub, gate.get_locked_title(),
                     (strip.x + 10, strip.y + 28), th.BAR_OVER)

        requirements = gate_requirement_labels(gate)
        if requirements:
            th.draw_text(surface, sub,
                         th.truncate(sub, "  |  ".join(requirements),
                                     strip.w - 20),
                         (strip.x + 10, strip.y + 50), th.TEXT_COFFEE)
        else:
            th.draw_text(surface, sub, "No requirements set.",
                         (strip.x + 10, strip.y + 50), th.STAT_BROWN)

        costs = gate_cost_labels(gate)
        if costs:
            th.draw_text(surface, sub, "ENTRY COSTS  " + "  ".join(costs),
                         (strip.x + 10, strip.y + 70), th.BAR_AMBER)


# ─────────────────────────────────────────────────────────────
# NEW ZONE  (Feature 6, phase F6)
# ─────────────────────────────────────────────────────────────


class NewZonePopup(Modal):
    """
    Names a freshly-dragged zone rectangle, then chains into GatePopup.

    Two fields only. The gate is the interesting part, and asking for it
    in the same popup would make a form nobody reads; naming first and
    gating second matches how an author actually thinks -- "this is the
    lab block" then "and this is who gets in".
    """

    SIZE = (620, 320)

    def __init__(self, rect: Tuple[int, int, int, int],
                 suggested_id: str = "zone") -> None:
        """Build the form for a zone covering `rect` (x, y, w, h)."""
        super().__init__(self.SIZE, "NEW ZONE", th.BORDER_BROWN,
                         [(CANCEL, "CANCEL", th.BTN_CANCEL),
                          ("ok", "OK", th.BTN_CONFIRM)])
        self.__rect: Tuple[int, int, int, int] = rect
        body = self.get_body_rect()
        self.__zone_id: TextInput = TextInput(
            pygame.Rect(body.x, body.y + 22, body.w, 30),
            slugify(suggested_id), 40, lambda c: c in _SLUG_CHARS)
        self.__display: TextInput = TextInput(
            pygame.Rect(body.x, body.y + 92, body.w, 30), "", 40)

    def get_rect_cells(self) -> Tuple[int, int, int, int]:
        """The (x, y, w, h) the drag produced."""
        return self.__rect

    def handle_event(self, event: pygame.event.Event) -> None:
        """Both fields first, then the frame."""
        if self.__zone_id.handle_event(event):
            return
        if self.__display.handle_event(event):
            return
        super().handle_event(event)

    def update(self, dt: float) -> None:
        """Blink whichever caret has focus."""
        self.__zone_id.update(dt)
        self.__display.update(dt)

    def on_button(self, value: str) -> None:
        """OK returns the two names; a blank id falls back to the slug."""
        if value != "ok":
            self.set_result(CANCEL)
            return
        zone_id = slugify(self.__zone_id.get_text()) or "zone"
        self.set_result({"zone_id": zone_id,
                         "display_name": self.__display.get_text().strip()})

    def render_body(self, surface: pygame.Surface) -> None:
        """Two labelled fields and the cell count the drag covered."""
        body = self.get_body_rect()
        label = th.load_font(th.SIZE_LABEL)
        x, y, w, h = self.__rect

        th.draw_text(surface, label, "ZONE ID", (body.x, body.y + 6),
                     th.CREDIT_HL)
        self.__zone_id.render(surface, "lab_block")
        th.draw_text(surface, label, "DISPLAY NAME", (body.x, body.y + 76),
                     th.CREDIT_HL)
        self.__display.render(surface, "Lab Block")
        th.draw_text(surface, th.load_font(th.SIZE_SUB),
                     f"Covers {w}x{h} cells from ({x},{y}) - {w * h} total.",
                     (body.x, body.y + 140), th.STAT_BROWN)

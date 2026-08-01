"""
ui/skill_tree_screen.py
CSE Life: Compile & Conquer — phase F10  (Feature 7, the skill tree)
─────────────────────────────────────────────────────────────
The skill tree: a node graph on the left, a detail panel on the
right. Each node shows what it is, what level it has reached, and
which of four states it is in — locked, available, unlocked or
mastered.

This file has NO skill logic. It never decides whether a node can
be unlocked, never reads a SkillTree, and NEVER calls a SkillTree
mutator. It draws the states it is handed by
content/skill_tree_layout.py::build_view_model(), which is the one
adapter between Saif's store and this screen (§6.1).

Connectors between a node and its prerequisites are ORTHOGONAL
only — across, down, across — never a diagonal or a curve, matching
the flat rectangular look the style guide fixes (§7).

Self-contained by owner ruling (Build Plan §0.5): the palette and
layout constants below are copied verbatim from UI_STYLE_GUIDE.md
§2-§4 rather than imported from another screen.

Layout, connectors + test by Nangiba Tasnim (Dev 3).
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pygame

# -------------------------------------------------------------
# PATHS
# -------------------------------------------------------------
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")
SKILL_ICON_PATH: str = os.path.join(PROJECT_ROOT, "assets", "ui",
                                    "icon_skill.png")

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues (§0.5).
PANEL_TAN     = (231, 214, 189)   # screen background behind the card
CARD_TAN      = (240, 228, 208)   # the card fill
HEADER_TAN    = (214, 196, 168)   # panel fill, disabled button
BORDER_BROWN  = (169, 130, 94)    # every outline, connector and corner mark
TEXT_COFFEE   = (74, 53, 39)      # primary text
CREDIT_HL     = (155, 110, 70)    # emphasised labels
STAT_BROWN    = (140, 110, 85)    # secondary / muted text
BAR_TRACK     = (222, 208, 186)   # empty part of a level bar (in-card)

ROW_WHITE     = (247, 243, 236)   # an AVAILABLE node
ROW_BLUE      = (120, 150, 190)   # an UNLOCKED node, level-bar fill
ROW_GREEN     = (150, 180, 125)   # a MASTERED node

BAR_AMBER     = (217, 169, 106)   # the selection frame
BAR_RED       = (199, 123, 107)   # unmet prerequisites
BTN_CONFIRM   = (150, 180, 125)   # INVEST, when affordable
PLACEHOLDER   = (196, 178, 150)   # a LOCKED node, and missing icon art
HINT_BROWN    = (150, 125, 100)   # stub-test hint line only

# State -> node fill. Keyed by the strings content/skill_tree_layout.py
# produces, so a new state there fails loudly here rather than silently
# drawing the wrong colour.
STATE_FILLS: Dict[str, Tuple[int, int, int]] = {
    "locked": PLACEHOLDER,
    "available": ROW_WHITE,
    "unlocked": ROW_BLUE,
    "mastered": ROW_GREEN,
}

# -------------------------------------------------------------
# LAYOUT  (UI_STYLE_GUIDE §4 — fixed pixel constants)
# -------------------------------------------------------------
SCREEN_W       = 1280
SCREEN_H       = 720

CARD_MARGIN    = 24         # dense-screen card inset (§4.2)
CARD_PAD       = 14         # gap between card and inner border
CORNER_LEN     = 22         # card corner bracket arm length
BORDER_CARD    = 3
BORDER_NODE    = 3          # node outline weight
BORDER_ROW     = 2          # bars, panel outline, separators

TITLE_Y        = 40         # screen title, from the card top
GRAPH_LEFT     = 70         # first column, from the card left
GRAPH_TOP      = 116        # first row, from the card top
COL_PITCH      = 230        # horizontal gap between node columns
ROW_PITCH      = 108        # vertical gap between node rows

NODE_SIZE      = 64         # every node box is 64x64
ICON_SIZE      = 24         # the skill icon inside a node
NODE_CORNER    = 12         # selection bracket arm length, at node scale

LEVEL_BAR_W    = 56         # per-node level bar (§4.5)
LEVEL_BAR_H    = 8
LEVEL_BAR_GAP  = 6          # gap below the node box
NODE_LABEL_GAP = 6          # gap below the level bar

PANEL_W        = 300        # the detail panel
PANEL_TOP      = 100        # from the card top
PANEL_GAP      = 24         # from the card right edge

PANEL_PAD      = 16         # inset inside the panel
PANEL_BAR_H    = 16         # the panel's full-width level bar
DESC_PITCH     = 20         # gap between description lines
REQ_PITCH      = 20         # gap between unmet-prerequisite lines

BTN_W          = 268        # INVEST / BACK, inside the panel
BTN_H          = 44         # every button is 44 px tall (§4.6)
BTN_GAP        = 12
BORDER_BTN     = 3

SIZE_TITLE     = 16         # screen title
SIZE_PANEL     = 13         # the selected node's name
SIZE_BODY      = 11         # panel body, buttons, points readout
SIZE_LABEL     = 10         # node labels and descriptions

_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def load_font(size: int) -> pygame.font.Font:
    """
    Return the pixel font at `size`, cached across the module.

    Falls back to the mandatory Courier substitute so a missing TTF can
    never crash the screen (UI_STYLE_GUIDE §3).
    """
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            _FONT_CACHE[size] = pygame.font.SysFont("Courier", size + 3,
                                                    bold=True)
    return _FONT_CACHE[size]


class SkillTreeScreen:
    """
    Draws the skill graph and the detail panel for the selected node.

    Holds no skill state: render() is handed the view model that
    content/skill_tree_layout.py built, and the caller reads
    get_node_rects() / get_invest_rect() / get_back_rect() to interpret
    clicks. The screen returns no decisions (§6.2) and calls no mutator.
    """

    def __init__(self) -> None:
        """Build the card, panel and button geometry once."""
        self.__card: pygame.Rect = pygame.Rect(
            CARD_MARGIN, CARD_MARGIN,
            SCREEN_W - CARD_MARGIN * 2, SCREEN_H - CARD_MARGIN * 2)
        self.__panel: pygame.Rect = pygame.Rect(
            self.__card.right - PANEL_GAP - PANEL_W,
            self.__card.y + PANEL_TOP, PANEL_W,
            self.__card.bottom - (self.__card.y + PANEL_TOP) - PANEL_GAP)
        self.__back: pygame.Rect = pygame.Rect(
            self.__panel.x + PANEL_PAD,
            self.__panel.bottom - PANEL_PAD - BTN_H, BTN_W, BTN_H)
        self.__invest: pygame.Rect = pygame.Rect(
            self.__panel.x + PANEL_PAD,
            self.__back.y - BTN_GAP - BTN_H, BTN_W, BTN_H)
        self.__icon: Optional[pygame.Surface] = None
        self.__icon_loaded: bool = False

    # -- geometry getters -------------------------------------
    def get_card_rect(self) -> pygame.Rect:
        """The framed card rectangle."""
        return self.__card

    def get_panel_rect(self) -> pygame.Rect:
        """The right-hand detail panel rectangle."""
        return self.__panel

    def get_node_rects(self, nodes: Sequence[Dict[str, Any]]
                       ) -> Dict[str, pygame.Rect]:
        """
        The 64x64 rectangle for each node, keyed by skill_id.

        Keyed rather than indexed so a caller hit-tests a click straight
        to a skill id without tracking list order.
        """
        rects: Dict[str, pygame.Rect] = {}
        for node in nodes or ():
            rects[str(node.get("skill_id", ""))] = self.__node_rect(node)
        return rects

    def get_invest_rect(self) -> pygame.Rect:
        """The INVEST button rectangle."""
        return self.__invest

    def get_back_rect(self) -> pygame.Rect:
        """The BACK button rectangle."""
        return self.__back

    def __node_rect(self, node: Dict[str, Any]) -> pygame.Rect:
        """Where one node sits, from its column and row."""
        return pygame.Rect(
            self.__card.x + GRAPH_LEFT + int(node.get("column", 0)) * COL_PITCH,
            self.__card.y + GRAPH_TOP + int(node.get("row", 0)) * ROW_PITCH,
            NODE_SIZE, NODE_SIZE)

    # -- drawing ----------------------------------------------
    def render(self, screen: pygame.Surface,
               nodes: Sequence[Dict[str, Any]] = (),
               selected_skill_id: str = "",
               available_points: int = 0) -> None:
        """
        Draw the whole skill tree from the handed-in view model (§6.1).

        `nodes` is exactly what build_view_model() returns; the screen
        reads its keys and draws them, and interprets nothing else.
        """
        screen.fill(PANEL_TAN)
        self.__draw_card(screen)
        self.__draw_title(screen, available_points)

        entries = list(nodes or ())
        rects = self.get_node_rects(entries)
        # Connectors first, so the node boxes sit on top of the lines
        # rather than being crossed by them.
        self.__draw_connectors(screen, entries, rects)
        for node in entries:
            self.__draw_node(screen, node, rects, selected_skill_id)
        self.__draw_panel(screen, entries, selected_skill_id,
                          available_points)

    def __draw_card(self, screen: pygame.Surface) -> None:
        """Framed card with an inner border and corner brackets (§4.2)."""
        pygame.draw.rect(screen, CARD_TAN, self.__card)
        pygame.draw.rect(screen, BORDER_BROWN, self.__card, BORDER_CARD)
        inner = self.__card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
        pygame.draw.rect(screen, BORDER_BROWN, inner, 1)
        n = CORNER_LEN
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((inner.left, inner.top), (n, 0), (0, n)),
                ((inner.right, inner.top), (-n, 0), (0, n)),
                ((inner.left, inner.bottom), (n, 0), (0, -n)),
                ((inner.right, inner.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, BORDER_BROWN, (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_title(self, screen: pygame.Surface,
                     available_points: int) -> None:
        """The screen title and the unspent-points readout."""
        y = self.__card.y + TITLE_Y
        screen.blit(load_font(SIZE_TITLE).render("SKILL TREE", True,
                                                 TEXT_COFFEE),
                    (self.__card.x + GRAPH_LEFT, y))
        points = load_font(SIZE_BODY).render(
            f"POINTS {int(available_points)}", True, CREDIT_HL)
        screen.blit(points, (self.__panel.right - points.get_width(), y + 4))

    def __draw_connectors(self, screen: pygame.Surface,
                          nodes: Sequence[Dict[str, Any]],
                          rects: Dict[str, pygame.Rect]) -> None:
        """
        Orthogonal lines from each node back to its prerequisites.

        Three segments — out of the parent's right edge, across to the
        midpoint, vertically to the child's row, then into the child's
        left edge. Never a diagonal: the whole look is rectangular (§7).
        """
        for node in nodes:
            child = rects.get(str(node.get("skill_id", "")))
            if child is None:
                continue
            for required in node.get("requires", ()):
                parent = rects.get(str(required))
                if parent is None:
                    continue
                mid_x = (parent.right + child.left) // 2
                pygame.draw.line(screen, BORDER_BROWN,
                                 (parent.right, parent.centery),
                                 (mid_x, parent.centery), BORDER_ROW)
                pygame.draw.line(screen, BORDER_BROWN,
                                 (mid_x, parent.centery),
                                 (mid_x, child.centery), BORDER_ROW)
                pygame.draw.line(screen, BORDER_BROWN,
                                 (mid_x, child.centery),
                                 (child.left, child.centery), BORDER_ROW)

    def __draw_node(self, screen: pygame.Surface, node: Dict[str, Any],
                    rects: Dict[str, pygame.Rect],
                    selected_skill_id: str) -> None:
        """One node: state fill, icon, level bar and label."""
        skill_id = str(node.get("skill_id", ""))
        rect = rects.get(skill_id)
        if rect is None:
            return
        state = str(node.get("state", "locked"))
        pygame.draw.rect(screen, STATE_FILLS.get(state, PLACEHOLDER), rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_NODE)

        icon = self.__get_icon()
        icon_pos = (rect.centerx - ICON_SIZE // 2,
                    rect.centery - ICON_SIZE // 2)
        if icon is not None:
            screen.blit(icon, icon_pos)
        else:
            pygame.draw.rect(screen, PLACEHOLDER,
                             (*icon_pos, ICON_SIZE, ICON_SIZE))
            pygame.draw.rect(screen, BORDER_BROWN,
                             (*icon_pos, ICON_SIZE, ICON_SIZE), 2)

        if skill_id and skill_id == selected_skill_id:
            self.__draw_selection(screen, rect)

        self.__draw_level_bar(screen, rect, int(node.get("level", 0)),
                              int(node.get("max_level", 1)))

        label = load_font(SIZE_LABEL).render(
            str(node.get("display_name", "")).upper(), True, TEXT_COFFEE)
        screen.blit(label, (rect.centerx - label.get_width() // 2,
                            rect.bottom + LEVEL_BAR_GAP + LEVEL_BAR_H
                            + NODE_LABEL_GAP))

    def __draw_selection(self, screen: pygame.Surface,
                         rect: pygame.Rect) -> None:
        """The amber frame plus corner brackets — the signature at node scale."""
        frame = rect.inflate(10, 10)
        pygame.draw.rect(screen, BAR_AMBER, frame, BORDER_NODE)
        n = NODE_CORNER
        for (px, py), (dx1, dy1), (dx2, dy2) in (
                ((frame.left, frame.top), (n, 0), (0, n)),
                ((frame.right, frame.top), (-n, 0), (0, n)),
                ((frame.left, frame.bottom), (n, 0), (0, -n)),
                ((frame.right, frame.bottom), (-n, 0), (0, -n))):
            pygame.draw.line(screen, BAR_AMBER, (px, py),
                             (px + dx1, py + dy1), 3)
            pygame.draw.line(screen, BAR_AMBER, (px, py),
                             (px + dx2, py + dy2), 3)

    def __draw_level_bar(self, screen: pygame.Surface, node_rect: pygame.Rect,
                         level: int, max_level: int) -> None:
        """The 56x8 level bar under a node (§4.5)."""
        track = pygame.Rect(node_rect.centerx - LEVEL_BAR_W // 2,
                            node_rect.bottom + LEVEL_BAR_GAP,
                            LEVEL_BAR_W, LEVEL_BAR_H)
        self.__draw_bar(screen, track, level, max_level)

    def __draw_bar(self, screen: pygame.Surface, track: pygame.Rect,
                   level: int, max_level: int) -> None:
        """A track, a proportional fill and a 2 px outline."""
        pygame.draw.rect(screen, BAR_TRACK, track)
        ceiling = max(1, int(max_level))
        ratio = max(0.0, min(1.0, float(level) / ceiling))
        if ratio > 0:
            fill = ROW_GREEN if level >= ceiling else ROW_BLUE
            pygame.draw.rect(screen, fill,
                             (track.x, track.y, int(track.w * ratio),
                              track.h))
        pygame.draw.rect(screen, BORDER_BROWN, track, BORDER_ROW)

    def __draw_panel(self, screen: pygame.Surface,
                     nodes: Sequence[Dict[str, Any]],
                     selected_skill_id: str, available_points: int) -> None:
        """The right-hand detail panel for whichever node is selected."""
        pygame.draw.rect(screen, HEADER_TAN, self.__panel)
        pygame.draw.rect(screen, BORDER_BROWN, self.__panel, BORDER_ROW)

        selected = self.__find(nodes, selected_skill_id)
        left = self.__panel.x + PANEL_PAD
        width = self.__panel.w - PANEL_PAD * 2
        y = self.__panel.y + PANEL_PAD

        if selected is None:
            screen.blit(load_font(SIZE_BODY).render("SELECT A SKILL", True,
                                                    STAT_BROWN), (left, y))
            self.__draw_button(screen, self.__invest, "INVEST", HEADER_TAN)
            self.__draw_button(screen, self.__back, "BACK", HEADER_TAN)
            return

        screen.blit(load_font(SIZE_PANEL).render(
            str(selected.get("display_name", "")).upper(), True,
            TEXT_COFFEE), (left, y))
        y += 28

        level = int(selected.get("level", 0))
        max_level = int(selected.get("max_level", 1))
        screen.blit(load_font(SIZE_BODY).render(
            f"LEVEL {level} / {max_level}", True, CREDIT_HL), (left, y))
        y += 22
        self.__draw_bar(screen, pygame.Rect(left, y, width, PANEL_BAR_H),
                        level, max_level)
        y += PANEL_BAR_H + 16

        screen.blit(load_font(SIZE_LABEL).render(
            str(selected.get("state", "")).upper(), True, STAT_BROWN),
            (left, y))
        y += 24

        # Description lines are authored to fit (content/skill_tree_layout.py
        # keeps them inside this width), but they are truncated defensively
        # too: a future edit there must never push text past the panel edge.
        body_font = load_font(SIZE_LABEL)
        for line in selected.get("description", ()):
            screen.blit(body_font.render(
                self.__truncate(str(line), body_font, width), True,
                TEXT_COFFEE), (left, y))
            y += DESC_PITCH

        unmet = self.__unmet_names(nodes, selected)
        if unmet:
            y += 10
            screen.blit(body_font.render("REQUIRES", True, BAR_RED),
                        (left, y))
            y += REQ_PITCH
            for name in unmet:
                screen.blit(body_font.render(
                    self.__truncate(f"- {name}", body_font, width), True,
                    BAR_RED), (left, y))
                y += REQ_PITCH

        can_invest = bool(selected.get("can_invest", False))
        self.__draw_button(screen, self.__invest, "INVEST",
                           BTN_CONFIRM if can_invest else HEADER_TAN,
                           TEXT_COFFEE if can_invest else STAT_BROWN)
        self.__draw_button(screen, self.__back, "BACK", HEADER_TAN)

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, fill: Tuple[int, int, int],
                      ink: Tuple[int, int, int] = TEXT_COFFEE) -> None:
        """One flat button: fill, 3 px border, ALL-CAPS label (§4.6)."""
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, BORDER_BTN)
        rendered = load_font(SIZE_BODY).render(label.upper(), True, ink)
        screen.blit(rendered, (rect.centerx - rendered.get_width() // 2,
                               rect.centery - rendered.get_height() // 2))

    # -- helpers ----------------------------------------------
    @staticmethod
    def __truncate(text: str, font: pygame.font.Font, max_px: int) -> str:
        """Shorten `text` with an ellipsis until it fits `max_px`."""
        if max_px <= 0 or font.size(text)[0] <= max_px:
            return text
        cut = len(text)
        while cut > 0 and font.size(text[:cut] + "...")[0] > max_px:
            cut -= 1
        return text[:cut] + "..." if cut > 0 else ""

    @staticmethod
    def __find(nodes: Sequence[Dict[str, Any]],
               skill_id: str) -> Optional[Dict[str, Any]]:
        """The view-model entry for a skill id, or None."""
        for node in nodes or ():
            if str(node.get("skill_id", "")) == str(skill_id):
                return node
        return None

    def __unmet_names(self, nodes: Sequence[Dict[str, Any]],
                      selected: Dict[str, Any]) -> List[str]:
        """
        Display names of the selected node's not-yet-unlocked prerequisites.

        Derived from the view model already on screen rather than by
        reading a SkillTree, so this file still touches no game state.
        """
        names: List[str] = []
        for required in selected.get("requires", ()):
            entry = self.__find(nodes, required)
            if entry is None:
                continue
            if int(entry.get("level", 0)) < 1:
                names.append(str(entry.get("display_name", required)))
        return names

    def __get_icon(self) -> Optional[pygame.Surface]:
        """
        The 24×24 skill icon, loaded once, or None while the PNG is missing.

        # [ICON PLACEHOLDER: assets/ui/icon_skill.png — skill tree node,
        #  readable at 24×24] (§5.2/§5.3)
        """
        if self.__icon_loaded:
            return self.__icon
        self.__icon_loaded = True
        try:
            surface = pygame.image.load(SKILL_ICON_PATH).convert_alpha()
            self.__icon = pygame.transform.scale(surface,
                                                 (ICON_SIZE, ICON_SIZE))
        except (FileNotFoundError, OSError, pygame.error):
            self.__icon = None
        return self.__icon

    def get_missing_paths(self) -> List[str]:
        """Asset paths that failed to load — the §5.2 step-4 work queue."""
        if self.__icon_loaded and self.__icon is None:
            return [SKILL_ICON_PATH]
        return []


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   arrows / click -> select a node
#   ENTER / I      -> invest a point in the selected node (REAL SkillTree)
#   P              -> grant 5 more points
#   R              -> reset the tree to empty
#   F11            -> toggle windowed / fullscreen
#   ESC            -> quit
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, PROJECT_ROOT)

    from content.skill_tree_layout import NODE_ORDER, build_view_model
    from core.skill_tree import SkillTree

    pygame.init()

    SIZE = (SCREEN_W, SCREEN_H)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Skill tree test")
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    ui = SkillTreeScreen()

    def _fresh_tree() -> SkillTree:
        """A REAL SkillTree stocked through increment_skill() only."""
        tree = SkillTree()
        tree.increment_skill("programming_language", 10)   # mastered
        tree.increment_skill("dsa", 3)                     # unlocked
        tree.increment_skill("oop", 1)                     # unlocked
        tree.increment_skill("git", 2)                     # unlocked
        return tree

    skills = _fresh_tree()
    points = 3
    selected = NODE_ORDER[0]

    running = True
    while running:
        model = build_view_model(skills, points)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    window = pygame.display.set_mode(
                        SIZE,
                        FULLSCREEN_FLAGS if is_fullscreen else WINDOWED_FLAGS)
                elif event.key in (pygame.K_DOWN, pygame.K_UP):
                    step = 1 if event.key == pygame.K_DOWN else -1
                    index = NODE_ORDER.index(selected)
                    selected = NODE_ORDER[(index + step) % len(NODE_ORDER)]
                elif event.key in (pygame.K_RIGHT, pygame.K_LEFT):
                    step = 4 if event.key == pygame.K_RIGHT else -4
                    index = NODE_ORDER.index(selected)
                    selected = NODE_ORDER[(index + step) % len(NODE_ORDER)]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                   pygame.K_i):
                    # The RUNNER decides and mutates -- never the screen.
                    entry = next((n for n in model
                                  if n["skill_id"] == selected), None)
                    if entry and entry["can_invest"]:
                        skills.increment_skill(selected, 1)
                        points -= 1
                elif event.key == pygame.K_p:
                    points += 5
                elif event.key == pygame.K_r:
                    skills, points = _fresh_tree(), 3
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for skill_id, rect in ui.get_node_rects(model).items():
                    if rect.collidepoint(event.pos):
                        selected = skill_id
                entry = next((n for n in model
                              if n["skill_id"] == selected), None)
                if ui.get_invest_rect().collidepoint(event.pos):
                    if entry and entry["can_invest"]:
                        skills.increment_skill(selected, 1)
                        points -= 1

        ui.render(window, build_view_model(skills, points), selected, points)

        hint = hint_font.render(
            "arrows/click select  |  ENTER invest  |  P +5 points"
            "  |  R reset  |  F11  |  ESC", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

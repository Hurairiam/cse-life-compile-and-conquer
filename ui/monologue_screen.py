"""
CSE Life: Compile & Conquer
ui/monologue_screen.py

The ceremonial card the player reads between semesters, and the one
that opens the game. Centred single column: title, subtitle, a
horizontal rule with its diamond, the monologue lines revealed letter
by letter, then a hint and a bobbing arrow once the block is complete.

This file has NO game logic. render() only DRAWS what it is handed:
a title, a subtitle, the lines, and how many characters of the block
are currently visible. It does not know which semester it is, does not
read the clock, and does not decide when the beat ends.

NO PROSE LIVES HERE EITHER. Every line comes from
content/dialogues.py::SEMESTER_INTROS, bound by the two module-level
helpers near the bottom of this file (build_opening_beat,
build_semester_beat). They sit OUTSIDE the class on purpose, so the
class itself never fetches its own data (Style Guide §6.1). The owner's
ruling for this phase was explicit: bind the existing text, write none.

Style: Nangiba Tasnim's ceremonial card, ported from the quarry's
main_menu_system/monologue_screen.py.
Abu Huraira removes the stub test block when he plugs in the real game.
"""
from __future__ import annotations

import os
from typing import List, Sequence, Tuple

import pygame

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues, and no
# colours imported from another screen (Build Plan §0.5).
PANEL_TAN = (231, 214, 189)     # screen background behind the card
CARD_TAN = (240, 228, 208)      # the ceremonial card
BORDER_BROWN = (169, 130, 94)   # frame, corner marks, the rule
TEXT_COFFEE = (74, 53, 39)      # the monologue lines
TITLE_SLATE = (45, 58, 71)      # the title
CREDIT_HL = (155, 110, 70)      # the subtitle
STAT_BROWN = (140, 110, 85)     # the continue hint
BAR_AMBER = (217, 169, 106)     # the bobbing arrow
HINT_BROWN = (150, 125, 100)    # stub-test hint line only

# Anchored to the project, not to the working directory, so the font
# loads the same whether the game was started from the project root,
# from an IDE, or from a shortcut.
FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "ui", "PressStart2P.ttf")

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
CARD_MARGIN = 46        # ceremonial inset (§4.2), not the dense 24
CARD_PAD = 18           # gap between the card and its inner border
CORNER_LEN = 26         # length of each corner mark arm

TITLE_Y = 120
SUBTITLE_Y = 166
RULE_Y = 200
RULE_HALF = 300         # half-width of the horizontal rule
RULE_GAP = 14           # the gap in the middle of the rule (§4.8)
RULE_DIAMOND = 7        # half-width of the diamond in that gap (§4.8)

FIRST_LINE_Y = 268
LINE_PITCH = 32

HINT_Y = 570
ARROW_Y = 606
ARROW_HALF_W = 8
ARROW_H = 9
ARROW_BOB = 3           # pixels the arrow rides up and down
ARROW_PERIOD_MS = 420   # milliseconds per bob step

TITLE_SIZE = 26
SUB_SIZE = 11
BODY_SIZE = 13
LABEL_SIZE = 10

HINT_TEXT = "PRESS ANY KEY TO CONTINUE"

# Letters per second, matching ui/dialog_box.py so the intro and the
# NPC who speaks right after it reveal at the same speed.
TYPEWRITER_CPS = 30

# skip_to_end() pushes the counter past any plausible block length
# rather than needing to be told how long the block is.
REVEAL_SENTINEL = 1_000_000


class MonologueScreen:
    """
    Draws one ceremonial monologue card.

    The screen keeps a convenience reveal clock so a caller can drive it
    with update(dt) and skip_to_end(), but render() still takes the
    revealed count as a parameter -- a caller that owns its own clock
    passes its own number and ignores the rest (§6.1).
    """

    def __init__(self, screen_w: int = 1280, screen_h: int = 720,
                 audio=None) -> None:
        """
        Load the fonts and fix the continue-hint rect.

        `audio` is optional and defaults to None, following the F1
        call-site convention: a screen with no audio manager injected
        behaves identically.
        """
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h
        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_sub: pygame.font.Font = self.__load_font(SUB_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)
        self.__audio = audio
        self.__revealed: float = 0.0

    # -- loading helpers --------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    # -- the convenience reveal clock -------------------------
    def update(self, dt: float) -> None:
        """
        Advance the typewriter by `dt` seconds.

        Optional: a caller that tracks its own reveal count never calls
        this. A bad dt is ignored rather than corrupting the clock.
        """
        try:
            step = float(dt)
        except (TypeError, ValueError):
            return
        if step > 0.0:
            self.__revealed += TYPEWRITER_CPS * step

    def get_revealed_chars(self) -> int:
        """How many characters of the block are currently revealed."""
        return int(self.__revealed)

    def skip_to_end(self) -> bool:
        """
        Reveal the whole block at once.

        Returns False when it was already fully revealed, so one key can
        mean "finish the text, then move on" -- which is what the brief
        asks for: a second keypress skips to the full line rather than
        advancing past it.
        """
        if self.__revealed >= REVEAL_SENTINEL:
            return False
        self.__revealed = float(REVEAL_SENTINEL)
        return True

    def reset(self) -> None:
        """Rewind the reveal for a new beat."""
        self.__revealed = 0.0

    def is_fully_revealed(self, lines: Sequence[str]) -> bool:
        """True once every character of `lines` is showing."""
        return self.get_revealed_chars() >= sum(len(line) for line in lines)

    # -- rectangle getters (for click detection outside this file) ---
    def get_continue_rect(self) -> pygame.Rect:
        """
        The hint-and-arrow strip. A click anywhere inside means
        "continue", so mouse players are not forced onto the keyboard.
        """
        return pygame.Rect(self.__screen_w // 2 - RULE_HALF, HINT_Y - 8,
                           RULE_HALF * 2, ARROW_Y + ARROW_H + 16 - HINT_Y)

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, title: str, subtitle: str,
               lines: Sequence[str], revealed_chars: int) -> None:
        """
        Draw the ceremonial card from the state handed in.

        title          : ALL-CAPS, size 26, in TITLE_SLATE
        subtitle       : ALL-CAPS, size 11, in CREDIT_HL
        lines          : the monologue, pre-split, sentence case
        revealed_chars : characters revealed across the WHOLE block --
                         one counter for the caller, sliced per line here
        """
        screen.fill(PANEL_TAN)
        self.__draw_card(screen)

        cx = screen.get_width() // 2
        self.__blit_centred(screen, self.__font_title, title.upper(),
                            TITLE_SLATE, cx, TITLE_Y)
        self.__blit_centred(screen, self.__font_sub, subtitle.upper(),
                            CREDIT_HL, cx, SUBTITLE_Y)
        self.__draw_rule(screen, cx, RULE_Y)

        for index, line in enumerate(self.__slice_lines(lines,
                                                        revealed_chars)):
            self.__blit_centred(screen, self.__font_body, line, TEXT_COFFEE,
                                cx, FIRST_LINE_Y + index * LINE_PITCH)

        if revealed_chars >= sum(len(line) for line in lines):
            self.__blit_centred(screen, self.__font_label, HINT_TEXT,
                                STAT_BROWN, cx, HINT_Y)
            self.__draw_continue_arrow(screen, cx)

    # -- piece-by-piece drawing -------------------------------
    def __slice_lines(self, lines: Sequence[str],
                      revealed_chars: int) -> List[str]:
        """
        Turn one whole-block character count into per-line slices.

        The caller keeps a single counter and the screen does the
        bookkeeping, which stops every caller reimplementing the same
        loop. Lines not reached yet are dropped rather than drawn empty,
        so the block grows downward as it reveals.
        """
        remaining = max(0, int(revealed_chars))
        shown: List[str] = []
        for line in lines:
            if remaining <= 0:
                break
            shown.append(line[:remaining])
            remaining -= len(line)
        return shown

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

    def __draw_rule(self, screen: pygame.Surface, cx: int, y: int) -> None:
        """
        The ceremonial horizontal rule (§4.8): two 2 px segments with a
        14 px gap in the middle holding a 7 px half-width diamond.
        """
        pygame.draw.line(screen, BORDER_BROWN,
                         (cx - RULE_HALF, y), (cx - RULE_GAP, y), 2)
        pygame.draw.line(screen, BORDER_BROWN,
                         (cx + RULE_GAP, y), (cx + RULE_HALF, y), 2)
        pygame.draw.polygon(screen, BORDER_BROWN,
                            [(cx, y - 6), (cx + RULE_DIAMOND, y),
                             (cx, y + 6), (cx - RULE_DIAMOND, y)])

    def __draw_continue_arrow(self, screen: pygame.Surface, cx: int) -> None:
        """
        The bobbing "press to continue" arrow. It steps between two
        positions rather than easing, which keeps it readable on a flat
        fill and stays inside §7's ban on animated decoration.
        """
        step = (pygame.time.get_ticks() // ARROW_PERIOD_MS) % 2
        y = ARROW_Y + (ARROW_BOB if step else 0)
        pygame.draw.polygon(screen, BAR_AMBER,
                            [(cx - ARROW_HALF_W, y),
                             (cx + ARROW_HALF_W, y),
                             (cx, y + ARROW_H)])

    def __blit_centred(self, screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: tuple, centre_x: int,
                       y: int) -> None:
        """Draw text horizontally centred on `centre_x` at `y`."""
        surface = font.render(text, True, colour)
        screen.blit(surface, (centre_x - surface.get_width() // 2, y))


# -------------------------------------------------------------
# CONTENT BINDING
# -------------------------------------------------------------
# Module-level, deliberately OUTSIDE the class: MonologueScreen must
# never fetch its own data (§6.1). These two helpers are the whole of
# the binding job -- every string they return already exists in
# content/dialogues.py, and no new prose was written for this phase.
# -------------------------------------------------------------

OPENING_TITLE = "CSE LIFE"
OPENING_SUBTITLE = "COMPILE & CONQUER"
SEMESTER_SUBTITLE = "A NEW TERM BEGINS — 80 DAYS"


def build_semester_beat(semester: int) -> Tuple[str, str, List[str]]:
    """
    (title, subtitle, lines) for a semester's opening monologue.

    Falls back to DEFAULT_SEMESTER_INTRO for any term without its own
    entry, so a 13th semester would still render rather than crash.
    Returns an empty line list if the content module is unavailable,
    which keeps this screen importable on its own.
    """
    try:
        from content.dialogues import (DEFAULT_SEMESTER_INTRO,
                                       SEMESTER_INTROS)
    except ImportError:
        return (f"SEMESTER {semester}", SEMESTER_SUBTITLE, [])
    lines = SEMESTER_INTROS.get(semester, DEFAULT_SEMESTER_INTRO)
    return (f"SEMESTER {semester}", SEMESTER_SUBTITLE, list(lines))


def build_opening_beat() -> Tuple[str, str, List[str]]:
    """
    (title, subtitle, lines) for the game's introductory monologue.

    Per the owner's ruling this is SEMESTER_INTROS[1] under the game's
    own title -- there is no separate prologue, and none was written.
    """
    _, _, lines = build_semester_beat(1)
    return (OPENING_TITLE, OPENING_SUBTITLE, lines)


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   SPACE / ENTER / click -> reveal the rest, then continue
#   S            -> skip the reveal outright
#   LEFT / RIGHT -> step through all 12 semesters' monologues
#   R            -> replay the opening beat (title card -> Purnno)
#   F11          -> toggle windowed / fullscreen
#   ESC          -> quit
#
# It opens on semester 1's full sequence: the CSE LIFE title card,
# then Purnno's real greeting through ui/dialog_box.py driven by
# engine/dialogue_manager.load_npc_dialogue(). Purnno has no portrait
# art yet, so that beat also proves the §5.2 placeholder path.
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    from engine.dialogue_manager import DialogueManager

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Monologue screen test")
    scene = MonologueScreen(*SIZE)
    dialogue = DialogueManager(*SIZE)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    GREETER = "warm_classmate_purnno"   # available from semester 1

    semester = 1
    opening = True          # True = the CSE LIFE title card
    phase = "monologue"     # "monologue" -> "greeting"
    title, subtitle, lines = build_opening_beat()

    def start_beat(term: int, as_opening: bool) -> None:
        """Load a beat and rewind the reveal."""
        global title, subtitle, lines, phase, opening, semester
        semester = term
        opening = as_opening
        phase = "monologue"
        if as_opening:
            title, subtitle, lines = build_opening_beat()
        else:
            title, subtitle, lines = build_semester_beat(term)
        scene.reset()

    def advance() -> None:
        """Finish the reveal first, then move to the greeting beat."""
        global phase
        if phase != "monologue":
            return
        if not scene.is_fully_revealed(lines):
            scene.skip_to_end()
            return
        # The NPC greeting only follows the opening beat; stepping
        # through the other eleven semesters just shows the monologues.
        if opening and dialogue.load_npc_dialogue(GREETER, "greeting"):
            phase = "greeting"

    def continue_dialogue() -> None:
        """Finish the spoken line, else advance, else restart the beat."""
        if not dialogue.skip_reveal() and not dialogue.advance():
            start_beat(semester, opening)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        if phase == "monologue":
            scene.update(dt)
        else:
            dialogue.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    window = pygame.display.set_mode(
                        SIZE, FULLSCREEN_FLAGS if is_fullscreen
                        else WINDOWED_FLAGS)
                elif event.key == pygame.K_s:
                    if phase == "monologue":
                        scene.skip_to_end()
                    else:
                        dialogue.skip_reveal()
                elif event.key == pygame.K_r:
                    start_beat(1, True)
                elif event.key == pygame.K_LEFT:
                    start_beat(semester - 1 if semester > 1 else 12, False)
                elif event.key == pygame.K_RIGHT:
                    start_beat(semester % 12 + 1, False)
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if phase == "monologue":
                        advance()
                    else:
                        continue_dialogue()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if phase == "monologue":
                    advance()
                else:
                    continue_dialogue()

        scene.render(window, title, subtitle, lines,
                     scene.get_revealed_chars())
        if phase == "greeting":
            # The monologue card stays behind the conversation, so the
            # dock alignment is validated against a real backdrop.
            dialogue.render(window)

        state = hint_font.render(
            f"semester {semester}  |  beat: "
            f"{'opening' if opening else 'term'}  |  phase: {phase}",
            True, STAT_BROWN)
        window.blit(state, (CARD_MARGIN + CARD_PAD + 10, CARD_MARGIN + 26))

        hint = hint_font.render(
            "SPACE advance  |  S skip  |  LEFT/RIGHT semester  |  R replay"
            "  |  F11 fullscreen  |  ESC quit", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        pygame.display.flip()

    pygame.quit()

"""
CSE Life: Compile & Conquer
ui/dialog_box.py

The dialog box the player reads when they talk to an NPC or poke
an interactable prop. A framed card anchored to the bottom of the
screen: the speaker's emotion portrait on the left, the speaker's
name above the text, and the line itself revealed letter by letter.

Which portrait appears is decided by the CHAIN being played --
each dialog chain in a level file names an emotion, and the level
registry maps that emotion to the NPC's face art (Hoque:
neutral / approving / strict, Roya: neutral / happy / serious).

This file has NO game logic. render() only DRAWS what it is handed:
the speaker name, the portrait, however much of the line is
currently visible, and whether the "press to continue" arrow should
show. The typewriter clock and the chain pointer live in the state
manager -- this class does not know what a semester is.

Style: Nangiba Tasnim's tan card pattern, corner brackets and all.
Abu Huraira removes the stub test block when he plugs in the real game.

─────────────────────────────────────────────────────────────
REVISION — phase F2 (branch nangiba-temp-01).
Ported to ui/ unchanged in behaviour and API. Three ADDITIVE
changes, none of which touch an existing signature:

  * a private __wrap_line() so a long line wraps inside the card
    instead of running off the right edge. Width is derived from
    the rect PASSED IN, so the level editor's narrower preview
    box wraps correctly too.
  * an optional `audio` constructor argument (dialogue blip while
    revealing, page turn on advance). Omit it and nothing changes.
  * LINE_PITCH / MAX_LINES / TEXT_RIGHT_PAD / BLIP_EVERY_CHARS.

The five load-bearing names tools/editor_popups.py depends on --
DialogBox(screen_w, screen_h), render(..., rect=), get_box_rect(),
get_portrait_rect(rect=), the STATIC visible_length(elapsed), and
the module-level TYPEWRITER_CPS -- are unchanged.
─────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import math
import os
from typing import List, Optional

import pygame

# -- palette --------------------------------------------------
CARD_TAN = (240, 228, 208)      # the box itself
BORDER_BROWN = (169, 130, 94)   # frame, corner marks, portrait frame
TEXT_COFFEE = (74, 53, 39)      # the spoken line
CREDIT_HL = (155, 110, 70)      # the speaker's name label
STAT_BROWN = (140, 110, 85)     # the hint line
BAR_AMBER = (217, 169, 106)     # the continue arrow

PORTRAIT_BG = (255, 255, 255)   # white backdrop behind the face
PORTRAIT_FILL = (190, 165, 135)  # placeholder when the art is missing
PORTRAIT_LABEL = (120, 95, 75)  # faded text inside the placeholder

# Anchored to the project, not to the working directory, so the font
# loads the same whether the game was started from the project root,
# from an IDE, or from a shortcut.
FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "ui", "PressStart2P.ttf")

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
SIDE_MARGIN = 46        # gap from the screen edge to the card
BOTTOM_MARGIN = 28      # gap from the bottom of the screen
BOX_H = 168             # card height

CARD_PAD = 14           # gap between the card and its inner border
CORNER_LEN = 22         # length of each corner mark arm
BORDER_W = 3

PORTRAIT_SIZE = 112     # the square face box
PORTRAIT_PAD = 26       # gap from the card edge to the portrait
TEXT_GAP = 22           # gap between the portrait and the text column

NAME_Y = 30             # speaker name, measured from the card top
LINE_Y = 66             # the spoken line, measured from the card top

LINE_PITCH = 26         # gap between wrapped lines (F2 addition)
MAX_LINES = 3           # lines that fit above the card's bottom edge
TEXT_RIGHT_PAD = 52     # keeps wrapped text clear of the continue arrow

BODY_SIZE = 13
LABEL_SIZE = 10

# Letters per second (Spec §6.4). One global speed for every NPC --
# a per-NPC speed would make some characters feel broken, not
# characterful.
TYPEWRITER_CPS = 30

ARROW_PERIOD = 0.9      # seconds per pulse of the continue arrow

BLIP_EVERY_CHARS = 3    # one dialogue blip per this many revealed chars


class DialogBox:
    """
    Draws one dialog line. It never fetches its own data -- render()
    is handed the speaker, the portrait, the visible slice of text and
    whether the line has finished, so the visuals stay fully separate
    from the dialog state machine (separation of concerns).

    The card rect is exposed through a getter so click-to-advance can
    live outside this class.
    """

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        """
        Store the screen size, load the fonts, fix the card rect.

        `audio` is optional and defaults to None (F2 addition). With no
        audio manager injected the box behaves exactly as before.
        """
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)
        self.__rect: pygame.Rect = pygame.Rect(
            SIDE_MARGIN, screen_h - BOTTOM_MARGIN - BOX_H,
            screen_w - SIDE_MARGIN * 2, BOX_H)
        self.__audio = audio
        self.__last_visible: int = 0

    # -- loading helpers --------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    # -- rectangle getters (for click detection outside this file) ---
    def get_box_rect(self) -> pygame.Rect:
        """The card rectangle -- a click anywhere inside advances."""
        return self.__rect

    def get_portrait_rect(self, rect: Optional[pygame.Rect] = None) -> \
            pygame.Rect:
        """The square the speaker's face is drawn in."""
        box = rect or self.__rect
        return pygame.Rect(box.x + PORTRAIT_PAD,
                           box.centery - PORTRAIT_SIZE // 2,
                           PORTRAIT_SIZE, PORTRAIT_SIZE)

    # -- helpers the state manager needs ----------------------
    @staticmethod
    def visible_length(elapsed: float) -> int:
        """
        How many characters of a line should be showing after `elapsed`
        seconds. Kept here so the reveal speed is defined in exactly one
        place, next to the constant it uses.
        """
        return max(0, int(elapsed * TYPEWRITER_CPS))

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, speaker: str, text: str,
               portrait: Optional[pygame.Surface] = None,
               show_indicator: bool = False, pulse: float = 0.0,
               rect: Optional[pygame.Rect] = None) -> None:
        """
        Draw the dialog box from the state handed in.

        speaker        : name label, drawn ALL CAPS
        text           : the visible slice of the line (already cut by
                         the caller's typewriter clock)
        portrait       : the emotion face, or None for a placeholder
        show_indicator : True once the line is fully revealed
        pulse          : a seconds counter driving the arrow's blink
        rect           : optional override, so the level editor can draw
                         this same box inside its preview popup
        """
        box = rect or self.__rect
        self.__draw_card(screen, box)
        self.__draw_portrait(screen, box, speaker, portrait)

        text_x = self.get_portrait_rect(box).right + TEXT_GAP
        screen.blit(self.__font_label.render(speaker.upper(), True, CREDIT_HL),
                    (text_x, box.y + NAME_Y))

        # F2 addition: wrap instead of overflowing the card. The width
        # comes from the box actually being drawn, so the editor's
        # narrower preview wraps at its own edge, not the screen's.
        max_px = box.right - TEXT_RIGHT_PAD - text_x
        for index, line in enumerate(
                self.__wrap_line(text, self.__font_body, max_px)):
            screen.blit(self.__font_body.render(line, True, TEXT_COFFEE),
                        (text_x, box.y + LINE_Y + index * LINE_PITCH))

        self.__play_reveal_audio(text)

        if show_indicator:
            self.__draw_indicator(screen, box, pulse)

    # -- piece-by-piece drawing -------------------------------
    def __wrap_line(self, text: str, font: pygame.font.Font,
                    max_px: int) -> List[str]:
        """
        Greedy word-wrap `text` to `max_px`, hard-splitting any single
        word too wide to fit on a line of its own.

        Returns at most MAX_LINES lines -- the card has a fixed height,
        so anything past the third line is dropped rather than drawn
        over the frame. Callers with long speeches split them into
        separate dialog lines, which is what the content files already do.
        """
        if max_px <= 0 or not text:
            return [text] if text else []

        lines: List[str] = []
        current = ""
        for word in text.split(" "):
            candidate = f"{current} {word}" if current else word
            if font.size(candidate)[0] <= max_px:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            # A single word wider than the box: split it by character
            # rather than let it run off the edge.
            while font.size(word)[0] > max_px and len(word) > 1:
                cut = len(word)
                while cut > 1 and font.size(word[:cut])[0] > max_px:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            current = word
        if current:
            lines.append(current)
        return lines[:MAX_LINES]

    def __play_reveal_audio(self, text: str) -> None:
        """
        Fire the typing blip while characters appear, and a page turn
        when the caller moves to a new line.

        Driven entirely off the length of the slice handed in, so no new
        public method is needed and a caller with no audio manager is
        completely unaffected.
        """
        length = len(text)
        if self.__audio is None:
            self.__last_visible = length
            return
        if length < self.__last_visible:
            self.__audio.play_sfx("page_turn")      # a new line started
        elif length > self.__last_visible and \
                length // BLIP_EVERY_CHARS != \
                self.__last_visible // BLIP_EVERY_CHARS:
            self.__audio.play_sfx("dialogue_blip")
        self.__last_visible = length

    def __draw_card(self, screen: pygame.Surface, box: pygame.Rect) -> None:
        """Draw the framed card, inner border, and corner marks."""
        pygame.draw.rect(screen, CARD_TAN, box)
        pygame.draw.rect(screen, BORDER_BROWN, box, BORDER_W)
        inner = box.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
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

    def __draw_portrait(self, screen: pygame.Surface, box: pygame.Rect,
                        speaker: str,
                        portrait: Optional[pygame.Surface]) -> None:
        """
        Draw the speaker's emotion face on a white backdrop. A missing
        image falls back to a filled block with a faded label, exactly
        like the ID photo on the registration screen.
        """
        frame = self.get_portrait_rect(box)
        if portrait is not None:
            pygame.draw.rect(screen, PORTRAIT_BG, frame)
            scaled = pygame.transform.scale(portrait, (frame.w, frame.h))
            screen.blit(scaled, frame.topleft)
        else:
            # [IMAGE PLACEHOLDER: assets/npcs/npc_<name>_<emotion>.png --
            #  96x96 emotion portrait. Missing art draws the PORTRAIT_FILL
            #  block with a faded label, never a crash (Style Guide §5.2).]
            pygame.draw.rect(screen, PORTRAIT_FILL, frame)
            label = self.__font_label.render(
                (speaker[:6] or "FACE").upper(), True, PORTRAIT_LABEL)
            screen.blit(label, (frame.centerx - label.get_width() // 2,
                                frame.centery - label.get_height() // 2))
        pygame.draw.rect(screen, BORDER_BROWN, frame, BORDER_W)

    def __draw_indicator(self, screen: pygame.Surface, box: pygame.Rect,
                         pulse: float) -> None:
        """
        The small pulsing arrow that means "press to continue". It rides
        up and down a couple of pixels instead of fading, so it stays
        readable on a flat fill.
        """
        bob = int(2 * math.sin(pulse * 2 * math.pi / ARROW_PERIOD))
        x = box.right - 40
        y = box.bottom - 34 + bob
        pygame.draw.polygon(screen, BAR_AMBER,
                            [(x - 8, y - 5), (x + 8, y - 5), (x, y + 6)])


# -------------------------------------------------------------
# STUB TEST -- lets me run this file on its own to see the box.
# Abu Huraira removes this block when he plugs in the real game.
#   SPACE / ENTER / click -> finish the line, then the next line
#   TAB   -> cycle emotion (and, every full cycle, the speaker)
#   N     -> jump to the next NPC in the roster
#   S     -> cycle the dialogue section (greeting/offer/farewell/...)
#   F11   -> toggle windowed / fullscreen
#   ESC   -> quit
#
# Lines come from content/dialogues.py and portraits from
# content/npc_roster.py -- real data, no invented prose. Purnno,
# Rafi, Zayan, Kabir and Rahman have no portrait art yet, so they
# prove the PORTRAIT_FILL placeholder path on the same screen.
#
# The typewriter clock and the chain pointer live HERE, not in the
# class -- in the real game the state manager owns them.
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    from content.dialogues import NPC_DIALOGUES
    from content.npc_roster import NPC_IDS, NPC_ROSTER

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Dialog box test")
    dialog = DialogBox(*SIZE)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    SECTIONS = ("greeting", "offer", "farewell", "unavailable")

    # Hoque and Roya are the two NPCs whose art exists today; the demo
    # opens on them so the real 96x96 portraits are visible immediately.
    speakers = ["professor_hoque", "career_advisor_roya"] + [
        npc_id for npc_id in NPC_IDS
        if npc_id not in ("professor_hoque", "career_advisor_roya")]
    speaker_index = 0
    emotion_index = 0
    section_index = 0
    line_index = 0
    elapsed = 0.0
    pulse = 0.0

    def current_npc() -> str:
        """The roster id currently speaking."""
        return speakers[speaker_index]

    def current_emotion() -> str:
        """The emotion variant currently selected for this speaker."""
        variants = NPC_ROSTER[current_npc()]["portrait_variants"]
        return variants[emotion_index % len(variants)]

    def current_script() -> list:
        """The real dialogue lines for this speaker and section."""
        section = SECTIONS[section_index]
        return NPC_DIALOGUES[current_npc()][section]

    def portrait_surface() -> pygame.Surface | None:
        """
        Load the speaker's emotion face.

        The roster declares assets/portraits/npc_<name>_{emotion}.png,
        which does not exist for anybody yet; the real art shipped to
        assets/npcs/ for Hoque and Roya only. Try the declared path
        first, then the real one, then give up and let the box draw its
        placeholder block (Style Guide §5.2).
        """
        npc_id = current_npc()
        emotion = current_emotion()
        short = npc_id.rsplit("_", 1)[-1]
        candidates = [
            NPC_ROSTER[npc_id]["portrait_file"].format(emotion=emotion),
            f"assets/npcs/npc_{short}_{emotion}.png",
        ]
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for relative in candidates:
            try:
                return pygame.image.load(
                    os.path.join(root, relative)).convert_alpha()
            except (FileNotFoundError, OSError, pygame.error, TypeError):
                continue
        # [IMAGE PLACEHOLDER: assets/npcs/npc_{purnno,rafi,zayan,kabir,
        #  rahman}_<emotion>.png -- 96x96 emotion portraits, still to be
        #  drawn. Until then these five speakers show the placeholder.]
        return None

    def advance() -> None:
        """First press finishes the line; the next press moves on."""
        global line_index, elapsed
        script = current_script()
        full = script[line_index % len(script)]
        if dialog.visible_length(elapsed) < len(full):
            elapsed = len(full) / TYPEWRITER_CPS
        else:
            line_index = (line_index + 1) % len(script)
            elapsed = 0.0

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        elapsed += dt
        pulse += dt

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
                elif event.key == pygame.K_TAB:
                    emotion_index += 1
                    if emotion_index % 3 == 0:
                        speaker_index = (speaker_index + 1) % len(speakers)
                        line_index, elapsed = 0, 0.0
                elif event.key == pygame.K_n:
                    speaker_index = (speaker_index + 1) % len(speakers)
                    emotion_index, line_index, elapsed = 0, 0, 0.0
                elif event.key == pygame.K_s:
                    section_index = (section_index + 1) % len(SECTIONS)
                    line_index, elapsed = 0, 0.0
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    advance()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                advance()

        window.fill((231, 214, 189))

        script = current_script()
        line = script[line_index % len(script)]
        shown = line[:dialog.visible_length(elapsed)]
        done = len(shown) >= len(line)
        dialog.render(window, NPC_ROSTER[current_npc()]["display_name"],
                      shown, portrait_surface(), done, pulse)

        header = hint_font.render(
            f"{NPC_ROSTER[current_npc()]['display_name']}  |  "
            f"section: {SECTIONS[section_index]}  |  "
            f"emotion: {current_emotion()}  |  "
            f"line {line_index + 1}/{len(script)}", True, (140, 110, 85))
        window.blit(header, (SIDE_MARGIN, 40))

        hint = hint_font.render(
            "SPACE advance  |  TAB emotion  |  N next NPC  |  S section"
            "  |  F11 fullscreen  |  ESC quit", True, (150, 125, 100))
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 8))

        pygame.display.flip()

    pygame.quit()

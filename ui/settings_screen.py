"""
CSE Life: Compile & Conquer
ui/settings_screen.py

The settings form: two volume sliders, a display-mode chip pair, a
text-speed chip trio, and APPLY / BACK.

This file has NO game logic. render() only DRAWS what it is handed:
the two volume numbers, whether the game is fullscreen, and which
text speed is selected. It does not own those values, does not talk
to the mixer, and does not resize the window. The caller reads the
rects, updates its own state, and calls AudioManager (§6.1, §6.2).

Style: Nangiba Tasnim's dense card, ported from the quarry's
main_menu_system/settings_screen.py and completed with the TEXT
SPEED row the quarry did not have.
Abu Huraira removes the stub test block when he plugs in the real game.
"""
from __future__ import annotations

import os
from typing import Dict, List

import pygame

# -- palette --------------------------------------------------
# Copied verbatim from UI_STYLE_GUIDE.md §2. No new hues, and no
# colours imported from another screen (Build Plan §0.5).
PANEL_TAN = (231, 214, 189)     # screen background behind the card
CARD_TAN = (240, 228, 208)      # the dense card
BORDER_BROWN = (169, 130, 94)   # frame, corner marks, outlines
TEXT_COFFEE = (74, 53, 39)      # values and button labels
TITLE_SLATE = (45, 58, 71)      # the screen title
CREDIT_HL = (155, 110, 70)      # row labels
STAT_BROWN = (140, 110, 85)     # muted helper text
BAR_TRACK = (222, 208, 186)     # empty part of a slider track
ROW_BLUE = (120, 150, 190)      # slider fill, selected chip
ROW_WHITE = (247, 243, 236)     # slider handle, unselected chip
BAR_AMBER = (217, 169, 106)     # a volume sitting at zero
BTN_CONFIRM = (150, 180, 125)   # APPLY
BTN_CANCEL = (199, 123, 107)    # BACK
HINT_BROWN = (150, 125, 100)    # stub-test hint line only

# Volume range, matching engine/audio_manager.py's 0-100 integers
# exactly so the slider and the mixer never disagree about units.
VOLUME_MIN = 0
VOLUME_MAX = 100
VOLUME_STEP = 5

# Text speed in characters per second, feeding ui/dialog_box.py's
# TYPEWRITER_CPS. NORMAL is 30, which is the shipped default.
TEXT_SPEED_LABELS: tuple = ("SLOW", "NORMAL", "FAST")
TEXT_SPEED_CPS: Dict[str, int] = {"SLOW": 15, "NORMAL": 30, "FAST": 60}
DEFAULT_TEXT_SPEED = "NORMAL"

# Anchored to the project, not to the working directory.
FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "ui", "PressStart2P.ttf")

TITLE_TEXT = "SETTINGS"

# -------------------------------------------------------------
# LAYOUT  (positions and sizes, all in pixels)
# -------------------------------------------------------------
CARD_MARGIN = 24        # dense inset (§4.2)
CARD_PAD = 14
CORNER_LEN = 22

TITLE_Y = 50

FORM_W = 520
FIRST_LABEL_Y = 180
# 72, not the quarry's 64: the quarry had three rows and the last one
# was a chip pair. A fourth row of 36 px chips at a 64 px pitch puts the
# TEXT SPEED label flush against the bottom edge of the DISPLAY MODE
# chips, with no gap at all.
ROW_PITCH = 72
LABEL_TO_CONTROL = 28

TRACK_W = 420           # §4.5 progress bar width
TRACK_H = 16
HANDLE_SIZE = 16        # square handle, exactly the track height
VALUE_GAP = 16

CHIP_W = 200
CHIP_H = 36
CHIP_GAP = 20
SPEED_CHIP_W = 160      # three chips fit where two 200 px ones do
SPEED_CHIP_GAP = 20

BTN_W = 160
BTN_H = 44
BTN_GAP = 22
BTN_Y = 500

TITLE_SIZE = 28
BODY_SIZE = 12
LABEL_SIZE = 10

ROW_LABELS: tuple = ("MUSIC VOLUME", "SFX VOLUME", "DISPLAY MODE",
                     "TEXT SPEED")


def value_from_x(track_rect: pygame.Rect, mouse_x: int) -> int:
    """
    Map a mouse x position onto a clamped, stepped volume.

    Module-level rather than a method because the caller owns the volume
    values and needs this maths without holding a screen instance. The
    handle is HANDLE_SIZE wide, so the usable travel is the track minus
    the handle -- otherwise the value would hit 100 before the handle
    reached the right edge.
    """
    travel = track_rect.w - HANDLE_SIZE
    if travel <= 0:
        return VOLUME_MIN
    offset = mouse_x - (track_rect.x + HANDLE_SIZE // 2)
    ratio = min(max(offset / travel, 0.0), 1.0)
    return int(round(ratio * VOLUME_MAX / VOLUME_STEP) * VOLUME_STEP)


def cps_for_speed(label: str) -> int:
    """Characters per second for a text-speed label; NORMAL if unknown."""
    return TEXT_SPEED_CPS.get(str(label).upper(),
                              TEXT_SPEED_CPS[DEFAULT_TEXT_SPEED])


class SettingsScreen:
    """
    Draws the settings form and exposes a rect for every control.

    It holds no settings of its own. The caller keeps the values, hands
    them to render() each frame, and applies them to the AudioManager
    and the display -- which is why APPLY is a rect here and an action
    somewhere else.
    """

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        """Load fonts and fix every control rect."""
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h
        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)
        self.__audio = audio

        form_x = (screen_w - FORM_W) // 2
        self.__form_x: int = form_x
        self.__title_pos: tuple = (form_x, TITLE_Y)

        self.__label_ys: List[int] = [
            FIRST_LABEL_Y + i * ROW_PITCH for i in range(len(ROW_LABELS))]
        control_ys = [y + LABEL_TO_CONTROL for y in self.__label_ys]

        self.__music_track: pygame.Rect = pygame.Rect(
            form_x, control_ys[0], TRACK_W, TRACK_H)
        self.__sfx_track: pygame.Rect = pygame.Rect(
            form_x, control_ys[1], TRACK_W, TRACK_H)
        self.__windowed_chip: pygame.Rect = pygame.Rect(
            form_x, control_ys[2], CHIP_W, CHIP_H)
        self.__fullscreen_chip: pygame.Rect = pygame.Rect(
            form_x + CHIP_W + CHIP_GAP, control_ys[2], CHIP_W, CHIP_H)
        self.__speed_chips: List[pygame.Rect] = [
            pygame.Rect(form_x + i * (SPEED_CHIP_W + SPEED_CHIP_GAP),
                        control_ys[3], SPEED_CHIP_W, CHIP_H)
            for i in range(len(TEXT_SPEED_LABELS))]

        self.__apply_rect: pygame.Rect = pygame.Rect(
            form_x, BTN_Y, BTN_W, BTN_H)
        self.__back_rect: pygame.Rect = pygame.Rect(
            form_x + BTN_W + BTN_GAP, BTN_Y, BTN_W, BTN_H)

    # -- loading helpers --------------------------------------
    def __load_font(self, size: int) -> pygame.font.Font:
        """Load the pixel font, or fall back to a built-in font if missing."""
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    # -- rectangle getters (for click detection outside this file) ---
    def get_music_track_rect(self) -> pygame.Rect:
        """The music volume slider track."""
        return self.__music_track

    def get_sfx_track_rect(self) -> pygame.Rect:
        """The effects volume slider track."""
        return self.__sfx_track

    def get_windowed_chip_rect(self) -> pygame.Rect:
        """The WINDOWED display-mode chip."""
        return self.__windowed_chip

    def get_fullscreen_chip_rect(self) -> pygame.Rect:
        """The FULLSCREEN display-mode chip."""
        return self.__fullscreen_chip

    def get_text_speed_chip_rects(self) -> List[pygame.Rect]:
        """One rect per text-speed chip, in TEXT_SPEED_LABELS order."""
        return list(self.__speed_chips)

    def get_text_speed_at(self, pos: tuple) -> str:
        """The speed label under a screen position, or "" if none."""
        for index, rect in enumerate(self.__speed_chips):
            if rect.collidepoint(pos):
                return TEXT_SPEED_LABELS[index]
        return ""

    def get_apply_rect(self) -> pygame.Rect:
        """The APPLY button."""
        return self.__apply_rect

    def get_back_rect(self) -> pygame.Rect:
        """The BACK button."""
        return self.__back_rect

    # -- audio hooks (optional, F1 convention) ----------------
    def notify_clicked(self) -> None:
        """Play the click cue. The caller decides what was clicked."""
        if self.__audio:
            self.__audio.play_sfx("click")

    # -- main drawing -----------------------------------------
    def render(self, screen: pygame.Surface, music_volume: int,
               sfx_volume: int, is_fullscreen: bool,
               text_speed: str = DEFAULT_TEXT_SPEED) -> None:
        """
        Draw the settings form from the state handed in.

        music_volume / sfx_volume : 0-100 integers, as AudioManager uses
        is_fullscreen             : which display chip is active
        text_speed                : one of TEXT_SPEED_LABELS
        """
        screen.fill(PANEL_TAN)
        self.__draw_card(screen)

        screen.blit(self.__font_title.render(TITLE_TEXT, True, TITLE_SLATE),
                    self.__title_pos)

        self.__draw_label(screen, ROW_LABELS[0], self.__label_ys[0])
        self.__draw_slider(screen, self.__music_track, music_volume)

        self.__draw_label(screen, ROW_LABELS[1], self.__label_ys[1])
        self.__draw_slider(screen, self.__sfx_track, sfx_volume)

        self.__draw_label(screen, ROW_LABELS[2], self.__label_ys[2])
        self.__draw_chip(screen, self.__windowed_chip, "WINDOWED",
                         not is_fullscreen)
        self.__draw_chip(screen, self.__fullscreen_chip, "FULLSCREEN",
                         is_fullscreen)

        self.__draw_label(screen, ROW_LABELS[3], self.__label_ys[3])
        active = str(text_speed).upper()
        for index, label in enumerate(TEXT_SPEED_LABELS):
            self.__draw_chip(screen, self.__speed_chips[index], label,
                             label == active)
        self.__draw_speed_note(screen, active)

        self.__draw_button(screen, self.__apply_rect, "APPLY", BTN_CONFIRM)
        self.__draw_button(screen, self.__back_rect, "BACK", BTN_CANCEL)

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

    def __draw_label(self, screen: pygame.Surface, text: str, y: int) -> None:
        """Draw one ALL-CAPS row label in the emphasis brown."""
        screen.blit(self.__font_label.render(text, True, CREDIT_HL),
                    (self.__form_x, y))

    def __draw_slider(self, screen: pygame.Surface, track: pygame.Rect,
                      value: int) -> None:
        """
        Draw a volume slider: track, fill, square handle, numeric value.

        The fill stops under the handle rather than at the raw ratio, so
        the two agree at every value instead of drifting apart by half a
        handle at the ends.
        """
        clamped = max(VOLUME_MIN, min(VOLUME_MAX, int(value)))
        pygame.draw.rect(screen, BAR_TRACK, track)

        travel = track.w - HANDLE_SIZE
        ratio = clamped / VOLUME_MAX if VOLUME_MAX else 0.0
        filled = int(travel * ratio) + HANDLE_SIZE // 2
        if filled > 0:
            pygame.draw.rect(screen, ROW_BLUE,
                             pygame.Rect(track.x, track.y, filled, track.h))
        pygame.draw.rect(screen, BORDER_BROWN, track, 2)

        handle = pygame.Rect(track.x + int(travel * ratio),
                             track.y + (track.h - HANDLE_SIZE) // 2,
                             HANDLE_SIZE, HANDLE_SIZE)
        pygame.draw.rect(screen, ROW_WHITE, handle)
        pygame.draw.rect(screen, BORDER_BROWN, handle, 2)

        # Amber at zero: silence is a state worth noticing, and it is the
        # same warning colour the HUD uses for "at the limit" (§2.2).
        colour = BAR_AMBER if clamped <= VOLUME_MIN else TEXT_COFFEE
        number = self.__font_body.render(f"{clamped}%", True, colour)
        screen.blit(number, (track.right + VALUE_GAP,
                             track.centery - number.get_height() // 2))

    def __draw_chip(self, screen: pygame.Surface, rect: pygame.Rect,
                    label: str, active: bool) -> None:
        """Draw a two-state chip: blue when active, white when not."""
        pygame.draw.rect(screen, ROW_BLUE if active else ROW_WHITE, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, 2)
        surface = self.__font_body.render(label, True,
                                          ROW_WHITE if active
                                          else TEXT_COFFEE)
        screen.blit(surface, (rect.centerx - surface.get_width() // 2,
                              rect.centery - surface.get_height() // 2))

    def __draw_speed_note(self, screen: pygame.Surface,
                          active: str) -> None:
        """Spell out what the selected text speed means, in cps."""
        note = self.__font_label.render(f"{cps_for_speed(active)} CPS", True,
                                        STAT_BROWN)
        last = self.__speed_chips[-1]
        screen.blit(note, (last.right + VALUE_GAP,
                           last.centery - note.get_height() // 2))

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, colour: tuple) -> None:
        """Draw a labelled button: fill, 3 px border, ALL-CAPS label."""
        pygame.draw.rect(screen, colour, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, 3)
        surface = self.__font_body.render(label, True, TEXT_COFFEE)
        screen.blit(surface, (rect.centerx - surface.get_width() // 2,
                              rect.centery - surface.get_height() // 2))


# -------------------------------------------------------------
# STUB TEST -- run this file on its own to see/exercise the feature.
# Abu Huraira removes this block when he plugs in the real game.
#   drag either slider  -> volume follows the mouse, in steps of 5
#   click a chip        -> display mode / text speed
#   APPLY               -> prints the settings and pushes them at audio
#   BACK                -> prints BACK
#   F11                 -> toggle windowed / fullscreen
#   ESC                 -> quit
#
# The sliders are LIVE-WIRED to engine/audio_manager.py, which is the
# F1 hookup contract being proved: two setters, no conversion, no
# try/except at the call site. With no audio device or no files in
# assets/audio/ the manager reports unavailable and nothing breaks.
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    from engine.audio_manager import AudioManager

    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Settings screen test")

    audio = AudioManager()
    settings = SettingsScreen(*SIZE, audio=audio)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    music = audio.get_music_volume()
    sfx = audio.get_sfx_volume()
    speed = DEFAULT_TEXT_SPEED
    dragging = None
    last_action = "-"

    def apply_display(flag: bool) -> None:
        """Switch the real window between windowed and fullscreen."""
        global fullscreen, window
        fullscreen = flag
        window = pygame.display.set_mode(
            SIZE, FULLSCREEN_FLAGS if fullscreen else WINDOWED_FLAGS)

    def push_audio() -> None:
        """The entire F1 settings hookup contract: two setters."""
        audio.set_music_volume(music)
        audio.set_sfx_volume(sfx)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    apply_display(not fullscreen)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                music_track = settings.get_music_track_rect()
                sfx_track = settings.get_sfx_track_rect()
                speed_label = settings.get_text_speed_at(pos)

                if music_track.inflate(0, 16).collidepoint(pos):
                    dragging = "music"
                    music = value_from_x(music_track, pos[0])
                    push_audio()
                elif sfx_track.inflate(0, 16).collidepoint(pos):
                    dragging = "sfx"
                    sfx = value_from_x(sfx_track, pos[0])
                    push_audio()
                    audio.play_sfx("click")     # hear the level you set
                elif settings.get_windowed_chip_rect().collidepoint(pos):
                    apply_display(False)
                elif settings.get_fullscreen_chip_rect().collidepoint(pos):
                    apply_display(True)
                elif speed_label:
                    speed = speed_label
                    last_action = f"TEXT SPEED -> {speed} " \
                                  f"({cps_for_speed(speed)} cps)"
                    print(last_action)
                elif settings.get_apply_rect().collidepoint(pos):
                    push_audio()
                    last_action = (f"APPLY -> music={music} sfx={sfx} "
                                   f"fullscreen={fullscreen} speed={speed}")
                    print(last_action)
                elif settings.get_back_rect().collidepoint(pos):
                    last_action = "BACK"
                    print(last_action)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = None

            elif event.type == pygame.MOUSEMOTION and dragging is not None:
                if dragging == "music":
                    music = value_from_x(settings.get_music_track_rect(),
                                         event.pos[0])
                else:
                    sfx = value_from_x(settings.get_sfx_track_rect(),
                                       event.pos[0])
                push_audio()

        settings.render(window, music, sfx, fullscreen, speed)

        window.blit(hint_font.render(
            f"mixer: {'ready' if audio.is_available() else 'unavailable'}"
            f"   |   audio volumes: music={audio.get_music_volume()} "
            f"sfx={audio.get_sfx_volume()}   |   last: {last_action}",
            True, STAT_BROWN), ((SIZE[0] - FORM_W) // 2, 110))

        hint = hint_font.render(
            "drag the sliders  |  click a chip  |  APPLY / BACK"
            "  |  F11 fullscreen  |  ESC quit", True, HINT_BROWN)
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        pygame.display.flip()
        clock.tick(60)

    audio.shutdown()
    pygame.quit()

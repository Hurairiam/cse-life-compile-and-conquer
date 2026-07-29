from __future__ import annotations

import os

import pygame

CARD_TAN = (240, 228, 208)
HEADER_TAN = (214, 196, 168)
BORDER_BROWN = (169, 130, 94)
TEXT_COFFEE = (74, 53, 39)
BAR_OVER = (186, 74, 62)
BTN_CONFIRM = (150, 180, 125)
BTN_CANCEL = (199, 123, 107)

OVERLAY_RGBA = (25, 18, 12, 160)

FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "ui", "PressStart2P.ttf")

BOX_W = 600
BOX_H = 224
BORDER_W = 4

TITLE_Y = 30
FIRST_LINE_Y = 78
LINE_PITCH = 26

BTN_W = 160
BTN_H = 44
BTN_GAP = 22
BTN_BOTTOM_GAP = 24

TITLE_SIZE = 16
BODY_SIZE = 11


class ConfirmPopup:

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)

        self.__box_rect: pygame.Rect = pygame.Rect(
            (screen_w - BOX_W) // 2, (screen_h - BOX_H) // 2, BOX_W, BOX_H)

        buttons_y = self.__box_rect.bottom - BTN_BOTTOM_GAP - BTN_H
        centre_x = self.__box_rect.centerx
        self.__confirm_rect: pygame.Rect = pygame.Rect(
            centre_x - BTN_GAP // 2 - BTN_W, buttons_y, BTN_W, BTN_H)
        self.__cancel_rect: pygame.Rect = pygame.Rect(
            centre_x + BTN_GAP // 2, buttons_y, BTN_W, BTN_H)
        self.__ok_rect: pygame.Rect = pygame.Rect(
            centre_x - BTN_W // 2, buttons_y, BTN_W, BTN_H)

    def __load_font(self, size: int) -> pygame.font.Font:
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    def get_box_rect(self) -> pygame.Rect:
        return self.__box_rect

    def get_confirm_rect(self) -> pygame.Rect:
        return self.__confirm_rect

    def get_cancel_rect(self) -> pygame.Rect:
        return self.__cancel_rect

    def get_ok_rect(self) -> pygame.Rect:
        return self.__ok_rect

    def render(self, screen: pygame.Surface, title: str, lines: list[str],
               confirm_label: str, cancel_label: str | None = None,
               accent: tuple = BAR_OVER,
               confirm_colour: tuple = BTN_CANCEL,
               cancel_colour: tuple = HEADER_TAN) -> None:
        self.__draw_overlay(screen)

        pygame.draw.rect(screen, CARD_TAN, self.__box_rect)
        pygame.draw.rect(screen, accent, self.__box_rect, BORDER_W)

        self.__blit_centred(screen, self.__font_title, title, accent,
                            self.__box_rect.centerx,
                            self.__box_rect.y + TITLE_Y)

        for i, line in enumerate(lines):
            self.__blit_centred(screen, self.__font_body, line, TEXT_COFFEE,
                                self.__box_rect.centerx,
                                self.__box_rect.y + FIRST_LINE_Y
                                + i * LINE_PITCH)

        if cancel_label is None:
            self.__draw_button(screen, self.__ok_rect, confirm_label,
                               confirm_colour)
        else:
            self.__draw_button(screen, self.__confirm_rect, confirm_label,
                               confirm_colour)
            self.__draw_button(screen, self.__cancel_rect, cancel_label,
                               cancel_colour)

    def __draw_overlay(self, screen: pygame.Surface) -> None:
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill(OVERLAY_RGBA)
        screen.blit(shade, (0, 0))

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, colour: tuple) -> None:
        pygame.draw.rect(screen, colour, rect)
        pygame.draw.rect(screen, BORDER_BROWN, rect, 3)
        surface = self.__font_body.render(label, True, TEXT_COFFEE)
        screen.blit(surface,
                    (rect.centerx - surface.get_width() // 2,
                     rect.centery - surface.get_height() // 2))

    def __blit_centred(self, screen: pygame.Surface, font: pygame.font.Font,
                       text: str, colour: tuple, centre_x: int,
                       y: int) -> None:
        surface = font.render(text, True, colour)
        screen.blit(surface, (centre_x - surface.get_width() // 2, y))


if __name__ == "__main__":
    pygame.init()

    SIZE = (1280, 720)
    WINDOWED_FLAGS = pygame.SCALED
    FULLSCREEN_FLAGS = pygame.SCALED | pygame.FULLSCREEN

    is_fullscreen = False
    window = pygame.display.set_mode(SIZE, WINDOWED_FLAGS)
    pygame.display.set_caption("Confirm popup test")
    popup = ConfirmPopup(*SIZE)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    cases = [
        ("EXIT GAME?",
         ["Any unsaved progress will be lost."],
         "EXIT", "STAY", BAR_OVER, BTN_CANCEL),
        ("RETURN TO MAIN MENU?",
         ["Progress cannot be saved yet."],
         "RETURN", "STAY", BAR_OVER, BTN_CANCEL),
        ("UNSAVED CHANGES",
         ["Your settings have not been applied.", "Discard them?"],
         "DISCARD", "STAY", (217, 169, 106), BTN_CANCEL),
        ("TOO MANY CREDITS",
         ["You can register a maximum of", "15 credits per semester.",
          "Deselect a course and try again."],
         "OK", None, BAR_OVER, BTN_CANCEL),
    ]
    index = 0

    running = True
    while running:
        title, lines, confirm, cancel, accent, confirm_col = cases[index]

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
                elif event.key == pygame.K_SPACE:
                    index = (index + 1) % len(cases)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if cancel is None:
                    if popup.get_ok_rect().collidepoint(event.pos):
                        print("OK")
                elif popup.get_confirm_rect().collidepoint(event.pos):
                    print(f"{confirm} pressed")
                elif popup.get_cancel_rect().collidepoint(event.pos):
                    print(f"{cancel} pressed")

        window.fill((231, 214, 189))
        popup.render(window, title, lines, confirm, cancel, accent,
                     confirm_col)

        hint = hint_font.render(
            "SPACE = next popup  |  click a button  |  F11 fullscreen"
            "  |  ESC quit", True, (150, 125, 100))
        window.blit(hint, (window.get_width() - hint.get_width() - 24,
                           window.get_height() - hint.get_height() - 14))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

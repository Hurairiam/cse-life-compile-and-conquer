from __future__ import annotations

import os

import pygame

PANEL_TAN = (231, 214, 189)
CARD_TAN = (240, 228, 208)
HEADER_TAN = (214, 196, 168)
BORDER_BROWN = (169, 130, 94)
TEXT_COFFEE = (74, 53, 39)
TITLE_SLATE = (45, 58, 71)
CREDIT_HL = (155, 110, 70)
STAT_BROWN = (140, 110, 85)

BAR_AMBER = (217, 169, 106)
BTN_CONFIRM = (150, 180, 125)
BTN_CANCEL = (199, 123, 107)

BACKDROP_ALPHA = 90

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(_PROJECT_ROOT, "assets", "ui", "PressStart2P.ttf")
# [IMAGE PLACEHOLDER: assets/ui/logo_title.png -- "CSE LIFE" wordmark ~640x96]
LOGO_PATH = os.path.join(_PROJECT_ROOT, "assets", "ui", "logo_title.png")
# [IMAGE PLACEHOLDER: assets/ui/menu_backdrop.png -- muted campus scene]
BACKDROP_PATH = os.path.join(_PROJECT_ROOT, "assets", "ui",
                             "menu_backdrop.png")

START_GAME = 0
EXIT = 1

MENU_LABELS: tuple[str, ...] = ("START GAME", "EXIT")
MENU_FILLS: tuple[tuple, ...] = (BTN_CONFIRM, BTN_CANCEL)

TITLE_TEXT = "COMPILE & CONQUER"
SUBTITLE_TEXT = "CSE LIFE"

CARD_MARGIN = 46
CARD_PAD = 18
CORNER_LEN = 26

LOGO_W = 640
LOGO_H = 96
LOGO_Y = 96

TITLE_Y = 110
SUBTITLE_Y = 168
RULE_Y = 200
RULE_HALF = 300

FIRST_BTN_Y = 260
BTN_W = 320
BTN_H = 44
BTN_PITCH = 60

MARKER_GAP = 12
CHROME_PAD = 14

TITLE_SIZE = 28
SUB_SIZE = 11
BODY_SIZE = 12
LABEL_SIZE = 10


class MainMenuScreen:

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.__screen_w: int = screen_w
        self.__screen_h: int = screen_h

        self.__font_title: pygame.font.Font = self.__load_font(TITLE_SIZE)
        self.__font_sub: pygame.font.Font = self.__load_font(SUB_SIZE)
        self.__font_body: pygame.font.Font = self.__load_font(BODY_SIZE)
        self.__font_label: pygame.font.Font = self.__load_font(LABEL_SIZE)

        self.__logo: pygame.Surface | None = self.__load_logo()
        self.__backdrop: pygame.Surface | None = self.__load_backdrop()

        centre_x = screen_w // 2
        self.__button_rects: list[pygame.Rect] = [
            pygame.Rect(centre_x - BTN_W // 2, FIRST_BTN_Y + i * BTN_PITCH,
                        BTN_W, BTN_H)
            for i in range(len(MENU_LABELS))
        ]

    def __load_font(self, size: int) -> pygame.font.Font:
        try:
            return pygame.font.Font(FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", size + 3, bold=True)

    def __load_logo(self) -> pygame.Surface | None:
        try:
            image = pygame.image.load(LOGO_PATH).convert_alpha()
            return pygame.transform.scale(image, (LOGO_W, LOGO_H))
        except (FileNotFoundError, OSError, pygame.error):
            return None

    def __load_backdrop(self) -> pygame.Surface | None:
        try:
            image = pygame.image.load(BACKDROP_PATH).convert()
            scaled = pygame.transform.scale(
                image, (self.__screen_w, self.__screen_h))
            scaled.set_alpha(BACKDROP_ALPHA)
            return scaled
        except (FileNotFoundError, OSError, pygame.error):
            return None

    def get_button_rects(self) -> list[pygame.Rect]:
        return list(self.__button_rects)

    def render(self, screen: pygame.Surface, focused_index: int,
               version: str) -> None:
        screen.fill(PANEL_TAN)
        if self.__backdrop is not None:
            screen.blit(self.__backdrop, (0, 0))

        inner = self.__draw_card(screen)
        self.__draw_masthead(screen)
        self.__draw_rule(screen, screen.get_width() // 2, RULE_Y)

        for i, rect in enumerate(self.__button_rects):
            self.__draw_button(screen, rect, MENU_LABELS[i], MENU_FILLS[i],
                               focused=(i == focused_index), disabled=False)

        self.__draw_version(screen, inner, version)

    def __draw_card(self, screen: pygame.Surface) -> pygame.Rect:
        card = pygame.Rect(CARD_MARGIN, CARD_MARGIN,
                           screen.get_width() - CARD_MARGIN * 2,
                           screen.get_height() - CARD_MARGIN * 2)
        pygame.draw.rect(screen, CARD_TAN, card)
        pygame.draw.rect(screen, BORDER_BROWN, card, 3)

        inner = card.inflate(-CARD_PAD * 2, -CARD_PAD * 2)
        pygame.draw.rect(screen, BORDER_BROWN, inner, 1)
        self.__draw_corners(screen, inner)
        return inner

    def __draw_corners(self, screen: pygame.Surface,
                       rect: pygame.Rect) -> None:
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

    def __draw_masthead(self, screen: pygame.Surface) -> None:
        centre_x = screen.get_width() // 2
        if self.__logo is not None:
            screen.blit(self.__logo, (centre_x - LOGO_W // 2, LOGO_Y))
            return

        self.__blit_centred(screen, self.__font_title, TITLE_TEXT,
                            TITLE_SLATE, centre_x, TITLE_Y)
        self.__blit_centred(screen, self.__font_sub, SUBTITLE_TEXT,
                            CREDIT_HL, centre_x, SUBTITLE_Y)

    def __draw_rule(self, screen: pygame.Surface, cx: int, y: int) -> None:
        pygame.draw.line(screen, BORDER_BROWN,
                         (cx - RULE_HALF, y), (cx - 14, y), 2)
        pygame.draw.line(screen, BORDER_BROWN,
                         (cx + 14, y), (cx + RULE_HALF, y), 2)
        pygame.draw.polygon(screen, BORDER_BROWN,
                            [(cx, y - 6), (cx + 7, y), (cx, y + 6),
                             (cx - 7, y)])

    def __draw_button(self, screen: pygame.Surface, rect: pygame.Rect,
                      label: str, fill: tuple, focused: bool,
                      disabled: bool) -> None:
        if disabled:
            fill_colour = HEADER_TAN
            border_colour = STAT_BROWN
            text_colour = STAT_BROWN
        elif focused:
            fill_colour = BAR_AMBER
            border_colour = BORDER_BROWN
            text_colour = TEXT_COFFEE
        else:
            fill_colour = fill
            border_colour = BORDER_BROWN
            text_colour = TEXT_COFFEE

        pygame.draw.rect(screen, fill_colour, rect)
        pygame.draw.rect(screen, border_colour, rect, 3)

        text = self.__font_body.render(label, True, text_colour)
        text_x = rect.centerx - text.get_width() // 2
        screen.blit(text, (text_x, rect.centery - text.get_height() // 2))

        if focused and not disabled:
            marker = self.__font_label.render("»", True, TEXT_COFFEE)
            screen.blit(marker,
                        (text_x - MARKER_GAP - marker.get_width(),
                         rect.centery - marker.get_height() // 2))

    def __draw_version(self, screen: pygame.Surface, inner: pygame.Rect,
                       version: str) -> None:
        surface = self.__font_label.render(version, True, STAT_BROWN)
        screen.blit(surface,
                    (inner.right - CHROME_PAD - surface.get_width(),
                     inner.bottom - CHROME_PAD - surface.get_height()))

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
    pygame.display.set_caption("Main menu test")
    menu = MainMenuScreen(*SIZE)
    clock = pygame.time.Clock()
    hint_font = pygame.font.SysFont("Courier", 13)

    focused = START_GAME

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if focused == EXIT:
                        running = False
                    else:
                        focused = EXIT
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    flags = (FULLSCREEN_FLAGS if is_fullscreen
                             else WINDOWED_FLAGS)
                    window = pygame.display.set_mode(SIZE, flags)
                elif event.key == pygame.K_UP:
                    focused = (focused - 1) % len(MENU_LABELS)
                elif event.key == pygame.K_DOWN:
                    focused = (focused + 1) % len(MENU_LABELS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    print(f"activated: {MENU_LABELS[focused]}")

            elif event.type == pygame.MOUSEMOTION:
                for i, r in enumerate(menu.get_button_rects()):
                    if r.collidepoint(event.pos):
                        focused = i
                        break

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(menu.get_button_rects()):
                    if r.collidepoint(event.pos):
                        print(f"clicked: {MENU_LABELS[i]}")
                        break

        menu.render(window, focused, "v0.2 — short scope")

        hint = hint_font.render(
            "arrows / hover = focus  |  F11 fullscreen  |  ESC quit",
            True, (150, 125, 100))
        window.blit(hint, (window.get_width() - hint.get_width() - 62,
                           window.get_height() - hint.get_height() - 52))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

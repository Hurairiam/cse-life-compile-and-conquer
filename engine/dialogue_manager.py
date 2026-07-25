"""
engine/dialogue_manager.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation + Separation of Concerns
DialogueManager handles ALL in-game text box rendering.
It is the only file in Ayesha's layer that imports Pygame.
It does not contain any game logic -- only rendering.
Abu Huraira's main loop calls render() every frame and
advance() when the player presses SPACE.
─────────────────────────────────────────────────────────────
Sprint 2 — Created by Ayesha Saheba Mostofa (dev4-aysha-narrative)
"""
from __future__ import annotations
import pygame


class DialogueManager:
    """
    Manages and renders dialogue sequences.
    load_dialogue() must be called before render() will show anything.
    advance() returns False when the dialogue sequence is finished.
    """

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.__dialogue_queue: list[str] = []
        self.__current_index: int = 0
        self.__is_active: bool = False
        self.__current_portrait: pygame.Surface | None = None
        self.__font: pygame.font.Font = pygame.font.SysFont("Arial", 18)
        self.__font_hint: pygame.font.Font = pygame.font.SysFont("Arial", 13)
        self.__box_rect: pygame.Rect = pygame.Rect(
            40, screen_height - 155, screen_width - 80, 125
        )

    def load_dialogue(self, lines: list[str],
                      portrait_path: str | None = None) -> None:
        """
        Loads a new dialogue sequence and optionally a portrait image.
        portrait_path should match a value from npc_roster.py with
        the emotion placeholder replaced by the actual emotion name.
        Example: assets/portraits/npc_purnno_neutral.png
        """
        self.__dialogue_queue = lines
        self.__current_index = 0
        self.__is_active = True
        self.__current_portrait = None
        if portrait_path:
            try:
                raw = pygame.image.load(portrait_path).convert_alpha()
                self.__current_portrait = pygame.transform.scale(raw, (96, 96))
            except FileNotFoundError:
                self.__current_portrait = None

    def advance(self) -> bool:
        """
        Advances to the next dialogue line.
        Returns True if there are more lines remaining.
        Returns False when the sequence is complete -- caller should
        deactivate the dialogue state in the screen manager.
        """
        self.__current_index += 1
        if self.__current_index >= len(self.__dialogue_queue):
            self.__is_active = False
            return False
        return True

    def is_active(self) -> bool:
        """Returns True if a dialogue sequence is currently running."""
        return self.__is_active

    def get_current_line(self) -> str:
        """Returns the current dialogue line, or empty string if inactive."""
        if not self.__is_active:
            return ""
        return self.__dialogue_queue[self.__current_index]

    def render(self, screen: pygame.Surface) -> None:
        """
        Renders the dialogue box, current text line, portrait, and
        the SPACE key hint. Called every frame by the main loop.
        Does nothing if is_active() is False.
        """
        if not self.__is_active:
            return

        # Draw box background
        pygame.draw.rect(screen, (18, 18, 30), self.__box_rect)
        pygame.draw.rect(screen, (80, 130, 200), self.__box_rect, 2)

        # Draw portrait if available
        if self.__current_portrait:
            portrait_rect = pygame.Rect(
                self.__box_rect.x + 10,
                self.__box_rect.y + 12,
                96, 96
            )
            screen.blit(self.__current_portrait, portrait_rect)
            text_x: int = self.__box_rect.x + 116
        else:
            text_x = self.__box_rect.x + 14

        # Draw current dialogue line
        line: str = self.__dialogue_queue[self.__current_index]
        text_surface = self.__font.render(line, True, (240, 240, 240))
        screen.blit(text_surface, (text_x, self.__box_rect.y + 22))

        # Draw SPACE hint at bottom of box
        hint = self.__font_hint.render(
            "[ SPACE ]  Continue", True, (120, 120, 140)
        )
        screen.blit(hint, (self.__box_rect.x + 14, self.__box_rect.bottom - 22))
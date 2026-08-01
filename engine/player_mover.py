"""
engine/player_mover.py
Smooth pixel movement across a Level's collision grid.

Not grid-stepping: the position is a pair of floats, so the sprite rides
between cells and stops flush against a wall instead of snapping to it.
Three rules make it feel right:
  * the two axes move SEPARATELY, so walking into a wall at an angle
    slides along it rather than stopping dead
  * the destination is tested BEFORE it is committed, using four corners
    of a 30 px hitbox, so the player can never end up inside a rock
  * the per-cell speed modifier is EASED toward its target, so stepping
    onto mud slows you over about a third of a second

Pure Python except for the Level it queries. No pygame.
"""
from __future__ import annotations

import math
from typing import Tuple

from content.level_registry import (
    BASE_PLAYER_SPEED_PX_S, FACINGS, SPEED_MODIFIER_BASE, SPEED_SMOOTH_RATE,
    TILE_SIZE_PX,
)

CELL: int = TILE_SIZE_PX
HITBOX_PX: int = 30
WALK_FPS: float = 8.0
WALK_FRAMES: int = 4

STEP = {"down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0)}


class PlayerMover:

    def __init__(self, cell: Tuple[int, int]) -> None:
        self.__x: float = cell[0] * CELL + CELL / 2.0
        self.__y: float = cell[1] * CELL + CELL / 2.0
        self.__facing: str = FACINGS[0]
        self.__factor: float = SPEED_MODIFIER_BASE
        self.__anim_time: float = 0.0
        self.__frame: int = 0
        self.__is_moving: bool = False

    # -- getters ------------------------------------------------
    def get_position(self) -> Tuple[float, float]:
        return (self.__x, self.__y)

    def get_cell(self) -> Tuple[int, int]:
        return (int(self.__x // CELL), int(self.__y // CELL))

    def get_facing(self) -> str:
        return self.__facing

    def get_frame(self) -> int:
        return self.__frame

    def get_speed_factor(self) -> float:
        return self.__factor

    def is_moving(self) -> bool:
        return self.__is_moving

    def get_facing_cell(self) -> Tuple[int, int]:
        """The cell in front of the player — what E acts on."""
        x, y = self.get_cell()
        step = STEP[self.__facing]
        return (x + step[0], y + step[1])

    # -- mutators -----------------------------------------------
    def place(self, cell: Tuple[int, int]) -> None:
        """Teleport — used on spawn and on portal arrival."""
        self.__x = cell[0] * CELL + CELL / 2.0
        self.__y = cell[1] * CELL + CELL / 2.0
        self.__factor = SPEED_MODIFIER_BASE
        self.__anim_time = 0.0
        self.__frame = 0
        self.__is_moving = False

    def update(self, dt: float, dx: float, dy: float, level) -> None:
        """dt seconds; dx/dy are -1 / 0 / +1 input."""
        if dt <= 0.0:
            return
        length = math.hypot(dx, dy)
        if length > 0.0:
            dx, dy = dx / length, dy / length      # no diagonal speed bonus
            self.__facing = self.__facing_for(dx, dy)

        target = level.get_speed_modifier_at(*self.get_cell())
        self.__factor += (target - self.__factor) * \
            min(1.0, SPEED_SMOOTH_RATE * dt)

        speed = BASE_PLAYER_SPEED_PX_S * self.__factor * dt
        before = (self.__x, self.__y)
        if dx:
            step_x = self.__x + dx * speed
            if self.__can_stand(level, step_x, self.__y):
                self.__x = step_x
        if dy:
            step_y = self.__y + dy * speed
            if self.__can_stand(level, self.__x, step_y):
                self.__y = step_y

        self.__is_moving = (self.__x, self.__y) != before
        if self.__is_moving:
            self.__anim_time += dt
            self.__frame = int(self.__anim_time * WALK_FPS) % WALK_FRAMES
        else:
            self.__anim_time = 0.0
            self.__frame = 0

    # -- private ------------------------------------------------
    @staticmethod
    def __facing_for(dx: float, dy: float) -> str:
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        return "down" if dy > 0 else "up"

    @staticmethod
    def __can_stand(level, cx: float, cy: float) -> bool:
        half = HITBOX_PX / 2.0
        for px, py in ((cx - half, cy - half), (cx + half, cy - half),
                       (cx - half, cy + half), (cx + half, cy + half)):
            if not level.is_walkable(int(px // CELL), int(py // CELL)):
                return False
        return True

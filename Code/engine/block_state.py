"""Shared orientation and multipart state for non-cubic blocks.

The enums deliberately use stable names because build files serialize those
names.  Keeping this state independent from the application module lets the
world, renderer, persistence layer, and tests share one definition.
"""

from dataclasses import dataclass
from enum import Enum


class Facing(Enum):
    """Cardinal block direction in world coordinates."""

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    def opposite(self) -> "Facing":
        return Facing((self.value + 2) % 4)

    def clockwise(self) -> "Facing":
        return Facing((self.value + 1) % 4)

    def counterclockwise(self) -> "Facing":
        return Facing((self.value - 1) % 4)

    @property
    def offset(self) -> tuple[int, int]:
        return {
            Facing.NORTH: (0, -1),
            Facing.EAST: (1, 0),
            Facing.SOUTH: (0, 1),
            Facing.WEST: (-1, 0),
        }[self]


class SlabPosition(Enum):
    """Vertical half occupied by a slab or stair."""

    BOTTOM = 0
    TOP = 1


class StairShape(Enum):
    """Vanilla stair topology derived from neighboring stairs."""

    STRAIGHT = "straight"
    INNER_LEFT = "inner_left"
    INNER_RIGHT = "inner_right"
    OUTER_LEFT = "outer_left"
    OUTER_RIGHT = "outer_right"


class DoorHalf(Enum):
    """Which vertical cell of a two-block door this state belongs to."""

    LOWER = "lower"
    UPPER = "upper"


class DoorHinge(Enum):
    """Hinge side when looking in the door's facing direction."""

    LEFT = "left"
    RIGHT = "right"


@dataclass
class BlockProperties:
    """Serializable state shared by doors, slabs, and stairs."""

    facing: Facing = Facing.SOUTH
    isOpen: bool = False
    slabPosition: SlabPosition = SlabPosition.BOTTOM
    stairShape: StairShape = StairShape.STRAIGHT
    doorHalf: DoorHalf = DoorHalf.LOWER
    doorHinge: DoorHinge = DoorHinge.LEFT

    def copy(self) -> "BlockProperties":
        """Return an independent state value for undo and transactions."""

        return BlockProperties(
            facing=self.facing,
            isOpen=self.isOpen,
            slabPosition=self.slabPosition,
            stairShape=self.stairShape,
            doorHalf=self.doorHalf,
            doorHinge=self.doorHinge,
        )

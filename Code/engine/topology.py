"""Vanilla-style neighbor topology for stairs and multipart doors."""

from typing import Callable, Optional, Tuple

from engine.block_state import BlockProperties, Facing, SlabPosition, StairShape


Position = Tuple[int, int, int]


def _neighbor(position: Position, facing: Facing) -> Position:
    x, y, z = position
    dx, dy = facing.offset
    return x + dx, y + dy, z


def _stair_state(world, position: Position, is_stair: Callable[[object], bool]) -> Optional[BlockProperties]:
    block = world.getBlock(*position)
    if not is_stair(block):
        return None
    return world.getBlockProperties(*position) or BlockProperties()


def _different_stair(world, position: Position, direction: Facing, state: BlockProperties, is_stair) -> bool:
    neighbor = _stair_state(world, _neighbor(position, direction), is_stair)
    return (
        neighbor is None
        or neighbor.facing != state.facing
        or neighbor.slabPosition != state.slabPosition
    )


def stair_shape(world, position: Position, is_stair: Callable[[object], bool]) -> StairShape:
    """Derive the 1.16.1 stair shape from front and rear neighbors."""

    state = _stair_state(world, position, is_stair)
    if state is None:
        return StairShape.STRAIGHT

    front = _stair_state(world, _neighbor(position, state.facing), is_stair)
    if (
        front
        and front.slabPosition == state.slabPosition
        and front.facing.value % 2 != state.facing.value % 2
        and _different_stair(world, position, front.facing.opposite(), state, is_stair)
    ):
        return (
            StairShape.OUTER_LEFT
            if front.facing == state.facing.counterclockwise()
            else StairShape.OUTER_RIGHT
        )

    rear = _stair_state(world, _neighbor(position, state.facing.opposite()), is_stair)
    if (
        rear
        and rear.slabPosition == state.slabPosition
        and rear.facing.value % 2 != state.facing.value % 2
        and _different_stair(world, position, rear.facing, state, is_stair)
    ):
        return (
            StairShape.INNER_LEFT
            if rear.facing == state.facing.counterclockwise()
            else StairShape.INNER_RIGHT
        )

    return StairShape.STRAIGHT

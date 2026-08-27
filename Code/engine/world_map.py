"""Source-backed dimension hubs and focused builder objectives for World Map."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import gzip
import json
import math
import os
from typing import Mapping, Sequence

from domain.blocks import (
    BlockProperties,
    BlockType,
    DoorHalf,
    DoorHinge,
    Facing,
    SlabPosition,
    StairShape,
)
from runtime_paths import BUNDLED_DATA_DIR


DIMENSION_ORDER = ("overworld", "nether", "end", "ocean")
TEMPLATE_PATH = os.path.join(BUNDLED_DATA_DIR, "world_map_templates.json.gz")


@dataclass(frozen=True)
class MapScene:
    dimension: str
    title: str
    subtitle: str
    playable_anchors: tuple[tuple[int, int, int], ...]
    locked_anchors: tuple[tuple[int, int, int], ...]
    route_labels: tuple[str, ...]
    framing_bounds: tuple[tuple[int, int, int], tuple[int, int, int]]
    source_templates: tuple[str, ...]
    ambient_routes: tuple[tuple[tuple[float, float, float], ...], ...] = ()

    @property
    def runtime_dimension(self) -> str:
        return "overworld" if self.dimension == "ocean" else self.dimension


@dataclass(frozen=True)
class ObjectiveSpec:
    dimension: str
    title: str
    instructions: tuple[str, ...]
    targets: Mapping[tuple[int, int, int], str]
    hotbar: tuple[str, ...]
    powered_target: tuple[int, int, int] | None = None
    source_templates: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def _template_bundle() -> Mapping[str, object]:
    with gzip.open(TEMPLATE_PATH, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("minecraft_version") != "Java 1.16.1":
        raise ValueError("World Map template bundle is not Java 1.16.1")
    templates = payload.get("templates")
    if not isinstance(templates, dict):
        raise ValueError("World Map template bundle is invalid")
    return templates


def source_template_metadata(name: str) -> Mapping[str, object]:
    """Expose immutable provenance for regression checks and map labels."""
    template = _template_bundle().get(name)
    if not isinstance(template, dict):
        raise KeyError(name)
    return template


def _put(world, x: int, y: int, z: int, block: BlockType, **state) -> None:
    world.setBlock(x, y, z, block)
    if state:
        world.setBlockProperties(x, y, z, BlockProperties(**state))


def _rotated_xy(x: int, y: int, width: int, depth: int, rotation: int) -> tuple[int, int]:
    rotation %= 4
    if rotation == 1:
        return depth - 1 - y, x
    if rotation == 2:
        return width - 1 - x, depth - 1 - y
    if rotation == 3:
        return y, width - 1 - x
    return x, y


def _template_dimensions(name: str, rotation: int = 0) -> tuple[int, int, int]:
    source = source_template_metadata(name)["source_size"]
    width, height, depth = map(int, source)
    if rotation % 2:
        width, depth = depth, width
    return width, depth, height


def _state_properties(world, block: BlockType, state: Mapping[str, str], rotation: int):
    definition = world.catalog.definitions.get(block)
    if not definition or not (
        definition.isDoor or definition.isStair or definition.isSlab or definition.modelKind
    ):
        return None
    facing = {
        "north": Facing.NORTH,
        "east": Facing.EAST,
        "south": Facing.SOUTH,
        "west": Facing.WEST,
    }.get(state.get("facing", "south"), Facing.SOUTH)
    facing = Facing((facing.value + rotation) % 4)
    vertical_half = state.get("half") if definition.isStair else state.get("type")
    return BlockProperties(
        facing=facing,
        isOpen=state.get("open", "false") == "true",
        slabPosition=(
            SlabPosition.TOP if vertical_half == "top" else SlabPosition.BOTTOM
        ),
        stairShape=StairShape.__members__.get(
            state.get("shape", "straight").upper(), StairShape.STRAIGHT
        ),
        doorHalf=DoorHalf.__members__.get(
            state.get("half", "lower").upper(), DoorHalf.LOWER
        ),
        doorHinge=DoorHinge.__members__.get(
            state.get("hinge", "left").upper(), DoorHinge.LEFT
        ),
    )


def _place_template(
    world,
    name: str,
    origin: tuple[int, int, int],
    *,
    rotation: int = 0,
) -> list[tuple[tuple[int, int, int], BlockType]]:
    template = source_template_metadata(name)
    source_width, source_height, source_depth = map(int, template["source_size"])
    ox, oy, oz = map(int, origin)
    placed = []
    for record in template["blocks"]:
        x, y, z = map(int, record[:3])
        block = BlockType[str(record[3])]
        state = record[4] if isinstance(record[4], dict) else {}
        rx, ry = _rotated_xy(x, y, source_width, source_depth, rotation)
        position = (ox + rx, oy + ry, oz + z)
        world.setBlock(*position, block)
        properties = _state_properties(world, block, state, rotation)
        if properties is not None:
            world.setBlockProperties(*position, properties)
        placed.append((position, block))
    world.sceneStructurePositions.update(position for position, _block in placed)
    return placed


def _tree(world, x: int, y: int, base: int) -> None:
    for z in range(base, base + 4):
        _put(world, x, y, z, BlockType.OAK_LOG)
    for z, radius in ((base + 3, 2), (base + 4, 2), (base + 5, 1)):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) + abs(dy) <= radius + 1:
                    _put(world, x + dx, y + dy, z, BlockType.OAK_LEAVES)


def _nether_fungus(world, x: int, y: int, *, warped: bool) -> None:
    top = world.heightIndex.get((x, y), world.min_y - 1)
    if top < world.min_y:
        return
    stem = BlockType.WARPED_STEM if warped else BlockType.CRIMSON_STEM
    cap = BlockType.WARPED_WART_BLOCK if warped else BlockType.NETHER_WART_BLOCK
    height = 5 + (x * 3 + y * 5) % 4
    for z in range(top + 1, top + height + 1):
        _put(world, x, y, z, stem)
    crown = top + height
    for dz, radius in ((0, 2), (1, 3), (2, 2)):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) + abs(dy) <= radius + 1:
                    _put(world, x + dx, y + dy, crown + dz, cap)
    _put(world, x + 1, y, crown, BlockType.SHROOMLIGHT)


def _nether_fossil(world, origin: tuple[int, int, int]) -> None:
    ox, oy, oz = origin
    for x in range(ox, ox + 13):
        _put(world, x, oy, oz, BlockType.BONE_BLOCK)
    for rib_x in range(ox + 2, ox + 12, 3):
        for offset in range(5):
            _put(world, rib_x, oy + offset, oz + offset, BlockType.BONE_BLOCK)
            _put(world, rib_x, oy - offset, oz + offset, BlockType.BONE_BLOCK)


def _path_cell(world, x: int, y: int) -> None:
    """Replace the existing surface; only bridge where the route meets water."""
    top = world.heightIndex.get((x, y), world.min_y - 1)
    if top < world.min_y:
        return
    block = world.getBlock(x, y, top)
    if block == BlockType.WATER:
        _put(world, x, y, top + 1, BlockType.OAK_PLANKS)
    elif block not in (BlockType.OAK_PLANKS, BlockType.COBBLESTONE):
        _put(world, x, y, top, BlockType.DIRT_PATH)


def _village_route(
    world, start: tuple[int, int], end: tuple[int, int], *, bend_x: int | None = None
) -> None:
    sx, sy = start
    ex, ey = end
    bend_x = ex if bend_x is None else bend_x
    for x in range(min(sx, bend_x), max(sx, bend_x) + 1):
        _path_cell(world, x, sy)
    for y in range(min(sy, ey), max(sy, ey) + 1):
        _path_cell(world, bend_x, y)
    for x in range(min(bend_x, ex), max(bend_x, ex) + 1):
        _path_cell(world, x, ey)


def _source_fortress(
    world, origin: tuple[int, int, int]
) -> list[tuple[tuple[int, int, int], BlockType]]:
    """Assemble the Java 1.16.1 Bridge and BridgeCrossing source geometry.

    Nether fortresses are generator pieces rather than NBT templates.  These
    dimensions and fills mirror ``NetherFortressGenerator.Bridge`` and
    ``BridgeCrossing`` from the bundled source reference, then join three
    bridges to one crossing so the map reads as a fortress rather than a
    downsized silhouette.
    """
    ox, oy, oz = map(int, origin)
    placed: dict[tuple[int, int, int], BlockType] = {}

    def brick(x: int, y: int, z: int) -> None:
        position = (x, y, z)
        _put(world, *position, BlockType.NETHER_BRICKS)
        placed[position] = BlockType.NETHER_BRICKS

    def fill(
        start: tuple[int, int, int], end: tuple[int, int, int],
        piece_origin: tuple[int, int, int], *, width: int, depth: int,
        rotation: int = 0,
    ) -> None:
        px, py, pz = piece_origin
        for local_x in range(start[0], end[0] + 1):
            for local_y in range(start[1], end[1] + 1):
                for local_z in range(start[2], end[2] + 1):
                    rx, ry = _rotated_xy(local_x, local_z, width, depth, rotation)
                    brick(px + rx, py + ry, pz + local_y)

    def bridge(piece_origin: tuple[int, int, int], rotation: int = 0) -> None:
        arguments = dict(piece_origin=piece_origin, width=5, depth=19, rotation=rotation)
        for start, end in (
            ((0, 3, 0), (4, 4, 18)),
            ((0, 5, 0), (0, 5, 18)),
            ((4, 5, 0), (4, 5, 18)),
            ((0, 2, 0), (4, 2, 5)),
            ((0, 2, 13), (4, 2, 18)),
            ((0, 0, 0), (4, 1, 3)),
            ((0, 0, 15), (4, 1, 18)),
        ):
            fill(start, end, **arguments)
        for side in (0, 4):
            for local_z in (1, 4, 14, 17):
                fill((side, 3, local_z), (side, 4, local_z), **arguments)

    crossing_origin = (ox + 18, oy + 18, oz)
    arguments = dict(piece_origin=crossing_origin, width=19, depth=19, rotation=0)
    for start, end in (
        ((7, 3, 0), (11, 4, 18)),
        ((0, 3, 7), (18, 4, 11)),
        ((7, 5, 0), (7, 5, 7)),
        ((7, 5, 11), (7, 5, 18)),
        ((11, 5, 0), (11, 5, 7)),
        ((11, 5, 11), (11, 5, 18)),
        ((0, 5, 7), (7, 5, 7)),
        ((11, 5, 7), (18, 5, 7)),
        ((0, 5, 11), (7, 5, 11)),
        ((11, 5, 11), (18, 5, 11)),
        ((7, 2, 0), (11, 2, 5)),
        ((7, 2, 13), (11, 2, 18)),
        ((7, 0, 0), (11, 1, 3)),
        ((7, 0, 15), (11, 1, 18)),
        ((0, 2, 7), (5, 2, 11)),
        ((13, 2, 7), (18, 2, 11)),
        ((0, 0, 7), (3, 1, 11)),
        ((15, 0, 7), (18, 1, 11)),
    ):
        fill(start, end, **arguments)

    # Join exact 5x10x19 bridge pieces to three crossing arms. Their broad
    # generator supports are visible below the deck at the outer ends.
    bridge((ox + 25, oy, oz), 0)
    bridge((ox + 25, oy + 36, oz), 0)
    bridge((ox, oy + 25, oz), 1)
    return list(placed.items())


def _shell_box(
    world, origin: tuple[int, int, int], size: tuple[int, int, int], block: BlockType
) -> None:
    ox, oy, oz = origin
    width, depth, height = size
    for x in range(width):
        for y in range(depth):
            for z in range(height):
                if x in (0, width - 1) or y in (0, depth - 1) or z in (0, height - 1):
                    _put(world, ox + x, oy + y, oz + z, block)


def _ocean_monument(world, origin: tuple[int, int, int]) -> None:
    """Build the complete 58x58 Java 1.16.1 monument exterior and core.

    The coordinate runs below follow ``OceanMonumentGenerator.Base``. Water is
    intentionally represented by the map's screen-space grade rather than by
    scattered translucent blocks, so source ``setAirAndWater`` calls become
    openings in this presentation-only scene.
    """
    ox, oy, oz = origin

    def put(x: int, level: int, depth: int, block: BlockType) -> None:
        _put(world, ox + x, oy + depth, oz + level, block)

    def fill(
        block: BlockType,
        x1: int, level1: int, depth1: int,
        x2: int, level2: int, depth2: int,
    ) -> None:
        for x in range(x1, x2 + 1):
            for depth in range(depth1, depth2 + 1):
                for level in range(level1, level2 + 1):
                    put(x, level, depth, block)

    def clear(x1: int, level1: int, depth1: int, x2: int, level2: int, depth2: int) -> None:
        for x in range(x1, x2 + 1):
            for depth in range(depth1, depth2 + 1):
                for level in range(level1, level2 + 1):
                    world.setBlock(ox + x, oy + depth, oz + level, BlockType.AIR)

    prismarine = BlockType.PRISMARINE
    bricks = BlockType.PRISMARINE_BRICKS
    dark = BlockType.DARK_PRISMARINE
    lantern = BlockType.SEA_LANTERN

    # Deterministic internal room lattice at the vanilla 8x8x4 module scale.
    # It keeps the map monument complete when inspected from below or through
    # its entrance, while the exterior below remains source-coordinate exact.
    for room_x in range(3):
        for room_depth in range(3):
            for room_level in range(2):
                x0 = 17 + room_x * 8
                d0 = 22 + room_depth * 8
                l0 = 1 + room_level * 4
                for x in range(x0, x0 + 8):
                    for depth in range(d0, d0 + 8):
                        for level in range(l0, l0 + 4):
                            boundary = (
                                x in (x0, x0 + 7)
                                or depth in (d0, d0 + 7)
                                or level in (l0, l0 + 3)
                            )
                            if boundary:
                                put(x, level, depth, bricks if level != l0 + 1 else prismarine)
                clear(x0 + 3, l0 + 1, d0, x0 + 4, l0 + 2, d0)
                clear(x0 + 3, l0 + 1, d0 + 7, x0 + 4, l0 + 2, d0 + 7)
                clear(x0, l0 + 1, d0 + 3, x0, l0 + 2, d0 + 4)
                clear(x0 + 7, l0 + 1, d0 + 3, x0 + 7, l0 + 2, d0 + 4)

    # Fixed core room: exact 16x16x8 room proportions with the vanilla dark
    # prismarine vault and 2x2x2 gold core.
    fill(bricks, 21, 1, 22, 36, 1, 37)
    for level, block in ((2, prismarine), (3, bricks), (8, bricks)):
        fill(block, 21, level, 22, 36, level, 22)
        fill(block, 21, level, 37, 36, level, 37)
        fill(block, 21, level, 23, 21, level, 36)
        fill(block, 36, level, 23, 36, level, 36)
    fill(dark, 26, 4, 27, 31, 7, 32)
    fill(BlockType.GOLD_BLOCK, 28, 5, 29, 29, 6, 30)

    # Front wings (Base.method_14761), mirrored around the central entrance.
    for mirrored, offset in ((False, 0), (True, 33)):
        fill(prismarine, offset, 0, 0, offset + 24, 0, 20)
        for step in range(4):
            fill(bricks, offset + step, step + 1, step, offset + step, step + 1, 20)
            fill(bricks, offset + step + 7, step + 5, step + 7, offset + step + 7, step + 5, 20)
            fill(bricks, offset + 17 - step, step + 5, step + 7, offset + 17 - step, step + 5, 20)
            fill(bricks, offset + 24 - step, step + 1, step, offset + 24 - step, step + 1, 20)
            fill(bricks, offset + step + 1, step + 1, step, offset + 23 - step, step + 1, step)
            fill(bricks, offset + step + 8, step + 5, step + 7, offset + 16 - step, step + 5, step + 7)
        fill(prismarine, offset + 4, 4, 4, offset + 6, 4, 20)
        fill(prismarine, offset + 7, 4, 4, offset + 17, 4, 6)
        fill(prismarine, offset + 18, 4, 4, offset + 20, 4, 20)
        fill(prismarine, offset + 11, 8, 11, offset + 13, 8, 20)
        for depth in (12, 15, 18):
            put(offset + 12, 9, depth, bricks)
        first = offset + (19 if mirrored else 5)
        second = offset + (5 if mirrored else 19)
        for depth in range(20, 4, -3):
            put(first, 5, depth, bricks)
        for depth in range(19, 6, -3):
            put(second, 5, depth, bricks)
        for step in range(4):
            x = offset + 24 - (17 - step * 3) if mirrored else offset + 17 - step * 3
            put(x, 5, 5, bricks)
        put(second, 5, 5, bricks)
        fill(prismarine, offset + 11, 1, 12, offset + 13, 7, 12)
        fill(prismarine, offset + 12, 1, 11, offset + 12, 7, 13)

    # Central entrance ribs (method_14763).
    for step in range(4):
        depth = 5 + step * 4
        fill(bricks, 24, 2, depth, 24, 4, depth)
        fill(bricks, 22, 4, depth, 23, 4, depth)
        put(25, 5, depth, bricks)
        put(26, 6, depth, bricks)
        put(26, 5, depth, lantern)
        fill(bricks, 33, 2, depth, 33, 4, depth)
        fill(bricks, 34, 4, depth, 35, 4, depth)
        put(32, 5, depth, bricks)
        put(31, 6, depth, bricks)
        put(31, 5, depth, lantern)
        fill(prismarine, 27, 6, depth, 30, 6, depth)

    # Monument facade and dark-prismarine arch (method_14762).
    fill(prismarine, 15, 0, 21, 42, 0, 21)
    fill(prismarine, 21, 12, 21, 36, 12, 21)
    fill(prismarine, 17, 11, 21, 40, 11, 21)
    fill(prismarine, 16, 10, 21, 41, 10, 21)
    fill(prismarine, 15, 7, 21, 42, 9, 21)
    fill(prismarine, 16, 6, 21, 41, 6, 21)
    fill(prismarine, 17, 5, 21, 40, 5, 21)
    fill(prismarine, 21, 4, 21, 36, 4, 21)
    fill(prismarine, 22, 3, 21, 26, 3, 21)
    fill(prismarine, 31, 3, 21, 35, 3, 21)
    fill(prismarine, 23, 2, 21, 25, 2, 21)
    fill(prismarine, 32, 2, 21, 34, 2, 21)
    fill(bricks, 28, 4, 20, 29, 4, 21)
    for x, level in ((27, 3), (30, 3), (26, 2), (31, 2), (25, 1), (32, 1)):
        put(x, level, 21, bricks)
    for step in range(7):
        put(28 - step, 6 + step, 21, dark)
        put(29 + step, 6 + step, 21, dark)
    for step in range(4):
        put(28 - step, 9 + step, 21, dark)
        put(29 + step, 9 + step, 21, dark)
    put(28, 12, 21, dark)
    put(29, 12, 21, dark)
    for step in range(3):
        for level in (8, 9):
            put(22 - step * 2, level, 21, dark)
            put(35 + step * 2, level, 21, dark)
    clear(26, 1, 21, 31, 3, 21)

    # Central roof and lantern crown (method_14765).
    fill(prismarine, 21, 0, 22, 36, 0, 36)
    for step in range(4):
        fill(bricks, 21 + step, 13 + step, 21 + step, 36 - step, 13 + step, 21 + step)
        fill(bricks, 21 + step, 13 + step, 36 - step, 36 - step, 13 + step, 36 - step)
        fill(bricks, 21 + step, 13 + step, 22 + step, 21 + step, 13 + step, 35 - step)
        fill(bricks, 36 - step, 13 + step, 22 + step, 36 - step, 13 + step, 35 - step)
    fill(prismarine, 25, 16, 25, 32, 16, 32)
    for x, depth in ((25, 25), (32, 25), (25, 32), (32, 32)):
        fill(bricks, x, 17, depth, x, 19, depth)
    for brick_pos, lamp_pos in (
        ((26, 20, 26), (27, 20, 27)), ((26, 20, 31), (27, 20, 30)),
        ((31, 20, 31), (30, 20, 30)), ((31, 20, 26), (30, 20, 27)),
    ):
        put(*brick_pos, bricks)
        put(lamp_pos[0], 21, lamp_pos[2], bricks)
        put(*lamp_pos, lantern)

    # Outer side and rear terraces (methods 14764, 14766, 14767).
    for left in (True, False):
        edge_x = 0 if left else 51
        fill(prismarine, edge_x, 0, 21, edge_x + 6, 0, 57)
        inner_x = 4 if left else 51
        fill(prismarine, inner_x, 4, 21, inner_x + 2, 4, 53)
        for step in range(4):
            x = step if left else 57 - step
            fill(bricks, x, step + 1, 21, x, step + 1, 57 - step)
        lamp_x = 5 if left else 52
        for depth in range(23, 53, 3):
            put(lamp_x, 5, depth, bricks)
        put(lamp_x, 5, 52, bricks)
        if left:
            fill(prismarine, 4, 1, 52, 6, 3, 52)
            fill(prismarine, 5, 1, 51, 5, 3, 53)
        else:
            fill(prismarine, 51, 1, 52, 53, 3, 52)
            fill(prismarine, 52, 1, 51, 52, 3, 53)
    fill(prismarine, 7, 0, 51, 50, 0, 57)
    for step in range(4):
        fill(bricks, step + 1, step + 1, 57 - step, 56 - step, step + 1, 57 - step)

    for left in (True, False):
        x0 = 7 if left else 44
        fill(prismarine, x0, 0, 21, x0 + 6, 0, 50)
        wall_x = 11 if left else 44
        fill(prismarine, wall_x, 8, 21, wall_x + 2, 8, 53)
        for step in range(4):
            x = step + 7 if left else 50 - step
            fill(bricks, x, step + 5, 21, x, step + 5, 54)
        lamp_x = 12 if left else 45
        for depth in range(21, 46, 3):
            put(lamp_x, 9, depth, bricks)
    fill(prismarine, 14, 0, 44, 43, 0, 50)
    for x in range(12, 46, 3):
        put(x, 9, 45, bricks)
        put(x, 9, 52, bricks)
        if x in (12, 18, 24, 33, 39, 45):
            for level, depth in ((9, 47), (9, 50), (10, 45), (10, 46), (10, 51), (10, 52), (11, 47), (11, 50), (12, 48), (12, 49)):
                put(x, level, depth, bricks)
    for step in range(3):
        fill(prismarine, 8 + step, 5 + step, 54, 49 - step, 5 + step, 54)
    fill(bricks, 11, 8, 54, 46, 8, 54)
    fill(prismarine, 14, 8, 44, 43, 8, 53)

    for left in (True, False):
        x0 = 14 if left else 37
        fill(prismarine, x0, 0, 21, x0 + 6, 0, 43)
        wall_x = 18 if left else 37
        fill(prismarine, wall_x, 12, 22, wall_x + 2, 12, 39)
        fill(bricks, wall_x, 12, 21, wall_x + 2, 12, 21)
        for step in range(4):
            x = step + 14 if left else 43 - step
            fill(bricks, x, step + 9, 21, x, step + 9, 43 - step)
        lamp_x = 19 if left else 38
        for depth in range(23, 40, 3):
            put(lamp_x, 13, depth, bricks)
    fill(prismarine, 21, 0, 37, 36, 0, 43)
    fill(prismarine, 21, 12, 37, 36, 12, 39)
    for step in range(4):
        fill(bricks, 15 + step, step + 9, 43 - step, 42 - step, step + 9, 43 - step)

    # Four-by-four foundation pads used by Base.generate.
    for grid_x in range(7):
        grid_depth = 0
        while grid_depth < 7:
            if grid_depth == 0 and grid_x == 3:
                grid_depth = 6
            fill(bricks, grid_x * 9, 0, grid_depth * 9, grid_x * 9 + 3, 0, grid_depth * 9 + 3)
            grid_depth += 6 if grid_x not in (0, 6) else 1


def _overworld_hub(world) -> MapScene:
    world.resize(48, 48, 72, min_y=-40, preserve=False)
    world.setDimension("overworld")
    with world.bulkUpdate():
        footprint = set()
        for x in range(48):
            for y in range(48):
                corner = min(
                    math.hypot(x - 3, y - 3),
                    math.hypot(x - 44, y - 3),
                    math.hypot(x - 3, y - 44),
                    math.hypot(x - 44, y - 44),
                )
                edge_wave = 1.3 * math.sin(x * 0.73) + 0.9 * math.cos(y * 0.61)
                if corner < 3.7 + edge_wave * 0.35:
                    continue
                footprint.add((x, y))
                height = 1 + int(((x - 38) ** 2 + (y - 8) ** 2) < 55)
                if 22 <= y <= 24:
                    _put(world, x, y, 0, BlockType.SAND)
                    _put(world, x, y, 1, BlockType.WATER)
                else:
                    _put(world, x, y, 0, BlockType.DIRT)
                    _put(world, x, y, height, BlockType.GRASS)
        for x, y in footprint:
            if any((x + dx, y + dy) not in footprint for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    for z in range(-40, 0):
                        _put(world, x, y, z, BlockType.STONE if z < -4 else BlockType.DIRT)

        _place_template(world, "plains_house", (6, 7, 2))
        _place_template(world, "plains_house", (32, 29, 2), rotation=2)
        _place_template(world, "plains_farm", (13, 31, 2), rotation=1)
        _place_template(world, "plains_center", (29, 6, 2), rotation=1)
        junction = (24, 20)
        _village_route(world, (7, 10), junction, bend_x=17)
        _village_route(world, junction, (34, 11), bend_x=28)
        _village_route(world, junction, (18, 34), bend_x=24)
        _village_route(world, junction, (37, 32), bend_x=30)
        for x, y in ((16, 14), (28, 15), (11, 36), (42, 35)):
            _tree(world, x, y, 2)

    return MapScene(
        "overworld",
        "Overworld Survey",
        "Canonical plains pieces surround two damaged village routes.",
        ((9, 10, 9), (35, 32, 9)),
        ((34, 10, 8), (40, 38, 4)),
        ("Plains House", "Village Hub", "East Road", "Forest Watch"),
        ((4, 5, 0), (43, 42, 12)),
        ("plains_house", "plains_farm", "plains_center"),
        (
            ((8, 20, 3), (24, 20, 3), (37, 31, 3)),
            ((17, 9, 3), (24, 20, 3), (18, 34, 3)),
            ((30, 20, 3), (34, 11, 3), (40, 18, 3)),
        ),
    )


def _nether_hub(world) -> MapScene:
    # Keep every source-scale structure readable in the locked map camera. The
    # 84x78 field is large enough for the native bastion pieces and the exact
    # fortress-piece assembly without the excessive dead border of the older
    # 92x92 presentation.
    world.resize(84, 78, 64, min_y=-16, preserve=False)
    world.setDimension("nether")
    with world.bulkUpdate():
        footprint = set()
        for x in range(84):
            for y in range(78):
                nx = (x - 41.5) / 40.0
                ny = (y - 38.5) / 36.5
                edge = nx * nx + ny * ny
                edge += 0.07 * math.sin(x * 0.41 + y * 0.23)
                edge += 0.045 * math.cos(x * 0.19 - y * 0.37)
                if edge > 1.0:
                    continue
                footprint.add((x, y))
                lava_rift = abs((y - 39) - (x - 40) * 0.27) < 2.2
                if lava_rift and 10 < x < 74:
                    for z in range(-5, -1):
                        _put(world, x, y, z, BlockType.BASALT)
                    _put(world, x, y, -1, BlockType.MAGMA_BLOCK)
                    _put(world, x, y, 0, BlockType.LAVA)
                    continue
                height = 2 + round(
                    1.8 * math.sin(x * 0.15)
                    + 1.5 * math.cos(y * 0.17)
                    + 0.9 * math.sin((x + y) * 0.11)
                )
                height = max(0, min(7, height))
                warped = x < 35 and y < 43
                crimson = 31 <= x < 61 and y < 31
                soul_valley = y >= 44 and x < 56
                basalt_delta = x >= 57 and y >= 42
                surface = (
                    BlockType.WARPED_NYLIUM if warped
                    else BlockType.CRIMSON_NYLIUM if crimson
                     else (BlockType.SOUL_SAND if (x + y) % 5 < 2 else BlockType.SOUL_SOIL) if soul_valley
                    else BlockType.BASALT if basalt_delta
                    else BlockType.NETHERRACK
                )
                lower = -4 if edge < 0.82 else -9
                for z in range(lower, height + 1):
                    block = surface if z == height else (
                        BlockType.BLACKSTONE if basalt_delta and z >= height - 2
                        else BlockType.NETHERRACK
                    )
                    _put(world, x, y, z, block)

        for x, y in ((9, 13), (18, 29), (29, 12), (31, 37), (12, 40)):
            _nether_fungus(world, x, y, warped=True)
        for x, y in ((37, 8), (47, 17), (55, 27)):
            _nether_fungus(world, x, y, warped=False)
        for x, y, height in ((64, 52, 12), (75, 61, 17), (63, 70, 10), (79, 48, 14)):
            top = world.heightIndex.get((x, y), 0)
            for z in range(top + 1, top + height):
                _put(world, x, y, z, BlockType.BASALT)
            if (x + y) % 2:
                _put(world, x, y, top + height, BlockType.GLOWSTONE)
        _nether_fossil(world, (13, 63, 5))

        # The bastion uses complete canonical NBT pieces at native block scale.
        _place_template(world, "bastion_bridge", (48, 5, 8))
        _place_template(world, "bastion_gate", (65, 27, 7))
        _source_fortress(world, (3, 21, 9))

    return MapScene(
        "nether",
        "Nether War Table",
        "A bastion watches a warped forest while a fortress crosses the soul valley.",
        ((65, 20, 29), (30, 47, 17)),
        ((17, 20, 13), (72, 61, 17)),
        ("Bastion Gate", "Fortress", "Soul Valley", "Warped Route"),
        ((2, 2, -9), (81, 75, 42)),
        ("bastion_bridge", "bastion_gate", "nether_fortress_generator"),
        (
            ((8, 18, 8), (25, 28, 8), (39, 34, 8)),
            ((15, 67, 8), (31, 51, 16), (45, 43, 8)),
            ((68, 69, 13), (77, 57, 15), (67, 42, 8)),
        ),
    )


def _end_hub(world) -> MapScene:
    # The rotated 29-block ship and its 24-block height need this full volume;
    # the old 56x56x32 canvas clipped seven columns and its upper deck.
    world.resize(64, 60, 40, min_y=0, preserve=False)
    world.setDimension("end")
    islands = ((14, 17, 10, 3), (41, 16, 9, 5), (34, 43, 11, 2), (10, 47, 6, 6))
    with world.bulkUpdate():
        for cx, cy, radius, base in islands:
            for x in range(max(0, cx - radius), min(64, cx + radius + 1)):
                for y in range(max(0, cy - radius), min(60, cy + radius + 1)):
                    distance = math.hypot(x - cx, y - cy)
                    if distance <= radius:
                        thickness = max(1, int((radius - distance) / 2))
                        for z in range(max(0, base - thickness), base + 1):
                            _put(world, x, y, z, BlockType.END_STONE)
        _place_template(world, "end_base", (29, 38, 3))
        _place_template(world, "end_tower_base", (31, 40, 7))
        _place_template(world, "end_tower_piece", (31, 40, 14))
        _place_template(world, "end_tower_top", (30, 39, 18))
        _place_template(world, "end_bridge", (11, 15, 5), rotation=1)
        _place_template(world, "end_ship", (34, 7, 11), rotation=1)

    return MapScene(
        "end",
        "The Broken Atlas",
        "Canonical End City pieces mark the surviving island routes.",
        ((34, 43, 23), (15, 18, 10)),
        ((41, 16, 14), (10, 47, 13)),
        ("End Tower", "City Bridge", "Outer Isle", "Void Route"),
        ((5, 5, 0), (63, 56, 35)),
        ("end_base", "end_tower_base", "end_tower_piece", "end_tower_top", "end_bridge", "end_ship"),
        (
            ((9, 17, 9), (19, 19, 11), (33, 39, 15)),
            ((39, 14, 14), (32, 26, 11), (32, 43, 14)),
            ((10, 47, 12), (20, 37, 9), (34, 43, 15)),
        ),
    )


def _ocean_hub(world) -> MapScene:
    world.resize(96, 96, 56, min_y=-16, preserve=False)
    world.setDimension("overworld")
    with world.bulkUpdate():
        footprint = set()
        for x in range(96):
            for y in range(96):
                nx = (x - 47.5) / 46.0
                ny = (y - 47.5) / 46.0
                edge = nx * nx + ny * ny
                edge += 0.055 * math.sin(x * 0.31 + y * 0.19)
                if edge > 1.0:
                    continue
                footprint.add((x, y))
                trench = 4.5 * math.exp(-((x - 49 - 0.18 * (y - 48)) ** 2) / 52.0)
                floor = round(
                    1.8 * math.sin(x * 0.13)
                    + 1.4 * math.cos(y * 0.16)
                    + 0.8 * math.sin((x + y) * 0.09)
                    - trench
                )
                floor = max(-7, min(5, floor))
                material = (
                    BlockType.GRAVEL if (x * 3 + y * 5) % 13 < 4 else BlockType.SAND
                )
                thickness = 2 + round(max(0.0, 1.0 - edge) * 5)
                lower = floor - thickness
                for z in range(lower, floor):
                    _put(world, x, y, z, BlockType.STONE if z < floor - 2 else material)
                _put(world, x, y, floor, material)
        # Full 58x58 Java 1.16.1 monument footprint at native block scale.
        _ocean_monument(world, (19, 19, -1))

        # Vanilla ruin clusters combine one large template with satellite
        # pieces. Keep every member at native block scale and bury its base by
        # one block so it belongs to the seabed rather than sitting on it.
        _place_template(world, "ocean_ruin_warm", (8, 65, 0), rotation=1)
        _place_template(world, "ocean_ruin_warm_small", (24, 74, -1), rotation=2)
        _place_template(world, "ocean_ruin_cold", (69, 8, 0), rotation=3)
        _place_template(world, "ocean_ruin_cold_small", (78, 25, -1), rotation=1)
        _place_template(world, "ocean_shipwreck", (61, 66, 0), rotation=3)

        for x, y in ((12, 18), (24, 51), (82, 44), (47, 83), (73, 31)):
            top = world.heightIndex.get((x, y), 0)
            _put(world, x, y, top + 1, BlockType.WET_SPONGE)
            if (x + y) % 2:
                _put(world, x + 1, y, top + 1, BlockType.SEA_LANTERN)

    return MapScene(
        "ocean",
        "The Drowned Survey",
        "A monument, two ruin fields, and an intact wreck rest below the current.",
        (),
        ((47, 42, 23), (16, 73, 13), (76, 71, 17), (78, 18, 13)),
        ("Monument", "Warm Ruins", "Shipwreck", "Cold Ruins"),
        ((3, 3, -9), (92, 92, 25)),
        (
            "ocean_monument_generator", "ocean_ruin_warm",
            "ocean_ruin_warm_small", "ocean_ruin_cold",
            "ocean_ruin_cold_small", "ocean_shipwreck",
        ),
        (
            ((10, 30, 8), (27, 45, 10), (42, 58, 9)),
            ((62, 77, 10), (76, 67, 13), (88, 52, 9)),
            ((75, 17, 11), (59, 24, 12), (47, 39, 15)),
        ),
    )


def build_hub(world, dimension: str) -> MapScene:
    builders = {
        "overworld": _overworld_hub,
        "nether": _nether_hub,
        "end": _end_hub,
        "ocean": _ocean_hub,
    }
    return builders[dimension](world)


def _choose_repair_targets(
    world,
    placed: Sequence[tuple[tuple[int, int, int], BlockType]],
    allowed: Sequence[BlockType],
    count: int,
) -> Mapping[tuple[int, int, int], str]:
    allowed_set = set(allowed)
    candidates = sorted(
        ((position, block) for position, block in placed if block in allowed_set),
        key=lambda item: (-item[0][2], item[0][0] + item[0][1], item[0]),
    )
    if len(candidates) < count:
        raise ValueError("source template does not contain enough repair cells")
    stride = max(1, len(candidates) // count)
    selected = [candidates[min(index * stride, len(candidates) - 1)] for index in range(count)]
    targets = {}
    for position, block in selected:
        targets[position] = block.name
        world.setBlock(*position, BlockType.AIR)
        world.sceneStructurePositions.discard(position)
    return targets


def _level_terrain(world, dimension: str, width: int, depth: int, height: int) -> None:
    """Build a compact irregular work site instead of a floating square grid."""
    world.resize(width, depth, height, min_y=0, preserve=False)
    world.setDimension(dimension)
    base = {
        "overworld": (BlockType.DIRT, BlockType.GRASS),
        "nether": (BlockType.NETHERRACK, BlockType.BLACKSTONE),
        "end": (BlockType.END_STONE, BlockType.END_STONE),
    }[dimension]
    center_x = (width - 1) / 2.0
    center_y = (depth - 1) / 2.0
    radius_x = max(1.0, width * 0.49)
    radius_y = max(1.0, depth * 0.49)
    for x in range(width):
        for y in range(depth):
            normalized = ((x - center_x) / radius_x) ** 2 + ((y - center_y) / radius_y) ** 2
            edge_noise = 0.065 * math.sin(x * 1.73 + y * 0.91) + 0.035 * math.cos(x * 0.47 - y * 1.31)
            if normalized > 1.0 + edge_noise:
                continue
            _put(world, x, y, 0, base[0])
            _put(world, x, y, 1, base[1])


def _overworld_level(world, route: int) -> ObjectiveSpec:
    _level_terrain(world, "overworld", 24, 24, 20)
    name = "plains_house" if route == 0 else "plains_center"
    origin = (8, 8, 2) if route == 0 else (7, 7, 2)
    placed = _place_template(world, name, origin, rotation=route)
    targets = _choose_repair_targets(
        world, placed,
        (BlockType.OAK_PLANKS, BlockType.COBBLESTONE, BlockType.OAK_STAIRS),
        7,
    )
    title = "Restore the Plains House" if route == 0 else "Repair the Village Center"
    return ObjectiveSpec(
        "overworld",
        title,
        (
            "Restore the highlighted cells with their original village blocks.",
            "This structure is derived from the Java 1.16.1 plains NBT template.",
        ),
        targets,
        ("OAK_PLANKS", "COBBLESTONE", "OAK_STAIRS", "OAK_LOG", "STONE_BRICKS", "GRASS", "DIRT", "GLASS", "LANTERN"),
        source_templates=(name,),
    )


def _nether_level(world, route: int) -> ObjectiveSpec:
    if route == 0:
        _level_terrain(world, "nether", 36, 34, 28)
        name, origin, rotation = "bastion_bridge", (2, 8, 2), 0
        title = "Repair the Bastion Bridge"
    else:
        _level_terrain(world, "nether", 64, 64, 36)
        name, origin, rotation = "nether_fortress_generator", (4, 4, 6), 0
        title = "Repair the Fortress Crossing"
    placed = (
        _source_fortress(world, origin)
        if name == "nether_fortress_generator"
        else _place_template(world, name, origin, rotation=rotation)
    )
    targets = _choose_repair_targets(
        world, placed,
        (
            (BlockType.NETHER_BRICKS,)
            if name == "nether_fortress_generator"
            else (BlockType.POLISHED_BLACKSTONE_BRICKS, BlockType.BLACKSTONE, BlockType.BASALT)
        ),
        8,
    )
    return ObjectiveSpec(
        "nether",
        title,
        (
            "Replace the highlighted Nether masonry without redstone.",
            (
                "The crossing follows Java 1.16.1 fortress generator dimensions."
                if name == "nether_fortress_generator"
                else "Every missing cell comes from the canonical Java 1.16.1 NBT piece."
            ),
        ),
        targets,
        ("POLISHED_BLACKSTONE_BRICKS", "BLACKSTONE", "BASALT", "CRACKED_POLISHED_BLACKSTONE_BRICKS", "GILDED_BLACKSTONE", "NETHER_BRICKS", "MAGMA_BLOCK", "NETHERRACK", "GLOWSTONE"),
        source_templates=(name,),
    )


def _end_level(world, route: int) -> ObjectiveSpec:
    if route == 0:
        _level_terrain(world, "end", 24, 24, 28)
        pieces = (
            ("end_base", (7, 7, 2)),
            ("end_tower_base", (9, 9, 6)),
            ("end_tower_piece", (9, 9, 13)),
            ("end_tower_top", (8, 8, 17)),
        )
        title = "Restore the End City Tower"
    else:
        _level_terrain(world, "end", 16, 16, 18)
        pieces = (("end_bridge", (5, 6, 4)),)
        title = "Repair the End City Bridge"
    placed = []
    for name, origin in pieces:
        placed.extend(_place_template(world, name, origin))
    targets = _choose_repair_targets(
        world, placed,
        (BlockType.PURPUR_BLOCK, BlockType.PURPUR_PILLAR, BlockType.END_STONE_BRICKS),
        7 if route == 0 else 5,
    )
    return ObjectiveSpec(
        "end",
        title,
        (
            "Restore the highlighted End City cells with the original materials.",
            "The geometry comes directly from Java 1.16.1 structure templates.",
        ),
        targets,
        ("PURPUR_BLOCK", "PURPUR_PILLAR", "END_STONE_BRICKS", "PURPUR_STAIRS", "PURPUR_SLAB", "SEA_LANTERN", "MAGENTA_STAINED_GLASS", "END_STONE", "OBSIDIAN"),
        source_templates=tuple(name for name, _origin in pieces),
    )


def build_level(world, dimension: str, route_index: int = 0) -> ObjectiveSpec:
    route_index = max(0, min(1, int(route_index)))
    return {
        "overworld": _overworld_level,
        "nether": _nether_level,
        "end": _end_level,
    }[dimension](world, route_index)


def objective_progress(world, objective: ObjectiveSpec) -> tuple[int, int, bool]:
    correct = sum(
        world.getBlock(*position) == BlockType[block_name]
        for position, block_name in objective.targets.items()
    )
    total = len(objective.targets)
    return correct, total, correct == total


def target_positions(objective: ObjectiveSpec) -> Sequence[tuple[int, int, int]]:
    return tuple(objective.targets)

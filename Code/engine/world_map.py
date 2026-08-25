"""Deterministic dimension hubs and focused builder objectives for World Map."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from domain.blocks import BlockType
from engine.block_state import BlockProperties, Facing


DIMENSION_ORDER = ("overworld", "nether", "end")


@dataclass(frozen=True)
class MapScene:
    dimension: str
    title: str
    subtitle: str
    primary_anchor: tuple[int, int, int]
    future_anchors: tuple[tuple[int, int, int], ...]


@dataclass(frozen=True)
class ObjectiveSpec:
    dimension: str
    title: str
    instructions: tuple[str, ...]
    targets: Mapping[tuple[int, int, int], str]
    hotbar: tuple[str, ...]
    powered_target: tuple[int, int, int] | None = None


OBJECTIVES = {
    "overworld": ObjectiveSpec(
        dimension="overworld",
        title="The Missing Crossing",
        instructions=(
            "Repair the village crossing with oak planks.",
            "Fill every pale-blue bridge marker without damming the stream.",
        ),
        targets={
            (14, y, 2): "OAK_PLANKS" for y in range(11, 18)
        },
        hotbar=(
            "OAK_PLANKS", "OAK_LOG", "COBBLESTONE", "STONE_BRICKS",
            "GRASS", "DIRT", "GLASS", "GLOWSTONE", "WATER",
        ),
    ),
    "nether": ObjectiveSpec(
        dimension="nether",
        title="Signal Through the Bastion",
        instructions=(
            "Complete the redstone line, then use the lever.",
            "The lamp beyond the bastion gate must remain powered.",
        ),
        targets={
            (x, 16, 2): "REDSTONE_DUST" for x in range(5, 12)
        },
        hotbar=(
            "REDSTONE_DUST", "REDSTONE_TORCH", "LEVER", "REPEATER",
            "REDSTONE_BLOCK", "BLACKSTONE", "POLISHED_BLACKSTONE_BRICKS",
            "NETHER_BRICKS", "GLOWSTONE",
        ),
        powered_target=(13, 16, 2),
    ),
    "end": ObjectiveSpec(
        dimension="end",
        title="A Light Between Islands",
        instructions=(
            "Bridge the broken void path with End Stone Bricks.",
            "Place a Sea Lantern on the marked End City beacon.",
        ),
        targets={
            **{(x, 16, 5): "END_STONE_BRICKS" for x in range(11, 19)},
            (25, 16, 10): "SEA_LANTERN",
        },
        hotbar=(
            "END_STONE_BRICKS", "END_STONE", "PURPUR_BLOCK", "PURPUR_PILLAR",
            "SEA_LANTERN", "OBSIDIAN", "GLASS", "STONE_BRICKS", "GLOWSTONE",
        ),
    ),
}


def _put(world, x: int, y: int, z: int, block: BlockType, **state) -> None:
    world.setBlock(x, y, z, block)
    if state:
        world.setBlockProperties(x, y, z, BlockProperties(**state))


def _pillar(world, x: int, y: int, bottom: int, top: int, block: BlockType) -> None:
    for z in range(bottom, top + 1):
        _put(world, x, y, z, block)


def _shell(
    world,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    bottom: int,
    top: int,
    wall: BlockType,
    roof: BlockType,
) -> None:
    for z in range(bottom, top):
        for x in range(x0, x1 + 1):
            _put(world, x, y0, z, wall)
            _put(world, x, y1, z, wall)
        for y in range(y0 + 1, y1):
            _put(world, x0, y, z, wall)
            _put(world, x1, y, z, wall)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            _put(world, x, y, top, roof)


def _overworld_hub(world) -> MapScene:
    world.resize(48, 48, 24, min_y=0, preserve=False)
    world.setDimension("overworld")
    with world.bulkUpdate():
        for x in range(48):
            for y in range(48):
                height = 1
                if (x - 39) ** 2 + (y - 9) ** 2 < 60:
                    height += 1
                if 22 <= y <= 24:
                    _put(world, x, y, 0, BlockType.SAND)
                    _put(world, x, y, 1, BlockType.WATER)
                    continue
                _put(world, x, y, 0, BlockType.DIRT)
                _put(world, x, y, height, BlockType.GRASS)

        # A compact plains village, portal ruin, and watchtower make the hub
        # read as a map without turning its structures into cursor assets.
        _shell(world, 7, 7, 12, 12, 2, 5, BlockType.OAK_PLANKS, BlockType.STONE_BRICKS)
        _put(world, 9, 12, 2, BlockType.AIR)
        _shell(world, 31, 29, 36, 34, 2, 5, BlockType.STONE_BRICKS, BlockType.OAK_PLANKS)
        for z in range(2, 7):
            _put(world, 38, 10, z, BlockType.OBSIDIAN)
            _put(world, 42, 10, z, BlockType.OBSIDIAN)
        for x in range(38, 43):
            _put(world, x, 10, 7, BlockType.OBSIDIAN)
        for x in range(19, 27):
            _put(world, x, 23, 2, BlockType.OAK_PLANKS)
        for x, y in ((17, 14), (28, 10), (14, 34), (40, 37)):
            _pillar(world, x, y, 2, 4, BlockType.OAK_LOG)

    return MapScene(
        "overworld",
        "Overworld Survey",
        "A broad village field where the first road has washed away.",
        (10, 10, 6),
        ((34, 31, 7), (40, 10, 8), (18, 35, 3), (39, 38, 3)),
    )


def _nether_hub(world) -> MapScene:
    world.resize(52, 52, 36, min_y=0, preserve=False)
    world.setDimension("nether")
    with world.bulkUpdate():
        for x in range(52):
            for y in range(52):
                ridge = max(0, 6 - int(math.hypot(x - 26, y - 26) / 5))
                ledge = 3 if x > 31 and y < 26 else 0
                height = 2 + ridge + ledge
                for z in range(max(0, height - 2), height):
                    _put(world, x, y, z, BlockType.NETHERRACK)
                if (x + 2 * y) % 29 == 0:
                    _put(world, x, y, height, BlockType.MAGMA_BLOCK)

        for x in range(6, 46):
            for y in range(24, 27):
                _put(world, x, y, 1, BlockType.LAVA)

        # Bastion mass on the high platform.
        _shell(
            world, 31, 8, 43, 19, 9, 16,
            BlockType.POLISHED_BLACKSTONE_BRICKS, BlockType.BLACKSTONE,
        )
        for x in (32, 42):
            for y in (9, 18):
                _pillar(world, x, y, 9, 19, BlockType.BLACKSTONE)
        for x in range(34, 41):
            _put(world, x, 19, 9, BlockType.AIR)

        # Fortress bridge and small towers on the opposite shelf.
        for x in range(7, 25):
            for y in range(34, 38):
                _put(world, x, y, 5, BlockType.NETHER_BRICKS)
        for x in (7, 23):
            for y in (34, 37):
                _pillar(world, x, y, 5, 11, BlockType.NETHER_BRICKS)
        _put(world, 15, 35, 6, BlockType.GLOWSTONE)

    return MapScene(
        "nether",
        "Nether War Table",
        "Bastion and fortress routes rise above a split lava shelf.",
        (37, 14, 18),
        ((15, 35, 12), (26, 26, 11), (43, 37, 5), (9, 11, 5)),
    )


def _end_hub(world) -> MapScene:
    world.resize(56, 56, 30, min_y=0, preserve=False)
    world.setDimension("end")
    islands = ((16, 18, 10, 3), (39, 17, 8, 6), (31, 39, 11, 2), (10, 42, 6, 7))
    with world.bulkUpdate():
        for cx, cy, radius, base in islands:
            for x in range(max(0, cx - radius), min(56, cx + radius + 1)):
                for y in range(max(0, cy - radius), min(56, cy + radius + 1)):
                    distance = math.hypot(x - cx, y - cy)
                    if distance > radius:
                        continue
                    height = base + max(0, int((radius - distance) / 3))
                    thickness = max(1, int((radius - distance) / 2))
                    for z in range(max(0, height - thickness), height + 1):
                        _put(world, x, y, z, BlockType.END_STONE)

        # Mini End City on the largest island.
        _shell(world, 27, 35, 35, 43, 5, 10, BlockType.PURPUR_BLOCK, BlockType.PURPUR_BLOCK)
        _shell(world, 29, 37, 33, 41, 11, 16, BlockType.PURPUR_PILLAR, BlockType.PURPUR_BLOCK)
        _put(world, 31, 39, 17, BlockType.SEA_LANTERN)
        for x, y in ((16, 18), (39, 17), (10, 42)):
            _pillar(world, x, y, next(base for cx, cy, _r, base in islands if (cx, cy) == (x, y)) + 1,
                    next(base for cx, cy, _r, base in islands if (cx, cy) == (x, y)) + 7,
                    BlockType.OBSIDIAN)

    return MapScene(
        "end",
        "The Broken Atlas",
        "End City fragments drift between islands that no longer agree.",
        (31, 39, 18),
        ((16, 18, 11), (39, 17, 14), (10, 42, 15), (25, 27, 4)),
    )


def build_hub(world, dimension: str) -> MapScene:
    builders = {
        "overworld": _overworld_hub,
        "nether": _nether_hub,
        "end": _end_hub,
    }
    return builders[dimension](world)


def _overworld_level(world) -> None:
    world.resize(32, 32, 20, min_y=0, preserve=False)
    world.setDimension("overworld")
    with world.bulkUpdate():
        for x in range(32):
            for y in range(32):
                _put(world, x, y, 0, BlockType.DIRT)
                if 11 <= y <= 17:
                    _put(world, x, y, 1, BlockType.WATER)
                else:
                    _put(world, x, y, 1, BlockType.GRASS)
        for x in range(9, 20):
            for y in range(5, 10):
                _put(world, x, y, 2, BlockType.COBBLESTONE)
        _shell(world, 11, 6, 17, 10, 3, 6, BlockType.OAK_PLANKS, BlockType.STONE_BRICKS)
        _put(world, 14, 10, 3, BlockType.AIR)
        for y in range(10, 19):
            if y not in range(11, 18):
                _put(world, 14, y, 2, BlockType.OAK_PLANKS)


def _nether_level(world) -> None:
    world.resize(32, 32, 24, min_y=0, preserve=False)
    world.setDimension("nether")
    with world.bulkUpdate():
        for x in range(32):
            for y in range(32):
                _put(world, x, y, 0, BlockType.NETHERRACK)
                _put(world, x, y, 1, BlockType.BLACKSTONE if (x + y) % 2 else BlockType.POLISHED_BLACKSTONE_BRICKS)
        for x in range(3, 15):
            _put(world, x, 16, 1, BlockType.POLISHED_BLACKSTONE_BRICKS)
        _put(world, 4, 16, 2, BlockType.LEVER, facing=Facing.EAST)
        _put(world, 12, 16, 2, BlockType.REDSTONE_DUST)
        _put(world, 13, 16, 2, BlockType.REDSTONE_LAMP)
        for x in range(14, 21):
            _put(world, x, 16, 2, BlockType.NETHER_BRICKS)
        for x in (14, 20):
            _pillar(world, x, 16, 2, 8, BlockType.NETHER_BRICKS)
        for x in range(14, 21):
            _put(world, x, 16, 9, BlockType.NETHER_BRICKS)


def _end_level(world) -> None:
    world.resize(32, 32, 24, min_y=0, preserve=False)
    world.setDimension("end")
    with world.bulkUpdate():
        for cx, radius, base in ((7, 7, 4), (24, 8, 4)):
            for x in range(max(0, cx - radius), min(32, cx + radius + 1)):
                for y in range(8, 25):
                    distance = math.hypot(x - cx, y - 16)
                    if distance <= radius:
                        for z in range(max(0, base - 2), base + 1):
                            _put(world, x, y, z, BlockType.END_STONE)
        _shell(world, 21, 13, 27, 19, 5, 8, BlockType.PURPUR_BLOCK, BlockType.PURPUR_BLOCK)
        _pillar(world, 25, 16, 9, 9, BlockType.PURPUR_PILLAR)


def build_level(world, dimension: str) -> ObjectiveSpec:
    builders = {
        "overworld": _overworld_level,
        "nether": _nether_level,
        "end": _end_level,
    }
    builders[dimension](world)
    return OBJECTIVES[dimension]


def objective_progress(world, objective: ObjectiveSpec) -> tuple[int, int, bool]:
    correct = sum(
        world.getBlock(*position) == BlockType[block_name]
        for position, block_name in objective.targets.items()
    )
    powered = True
    if objective.powered_target is not None:
        properties = world.getBlockProperties(*objective.powered_target)
        powered = bool(properties and properties.powered)
    total = len(objective.targets) + int(objective.powered_target is not None)
    achieved = correct + int(powered and objective.powered_target is not None)
    return achieved, total, correct == len(objective.targets) and powered


def target_positions(objective: ObjectiveSpec) -> Sequence[tuple[int, int, int]]:
    return tuple(objective.targets)

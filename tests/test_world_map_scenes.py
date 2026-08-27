from collections import Counter
from types import SimpleNamespace

from domain.blocks import BlockType
from domain.world_catalog import WorldCatalog
from engine.world import World
from engine.world_map import build_hub


def _world() -> World:
    definitions = {
        block: SimpleNamespace(isDoor=False, isStair=False, isSlab=False, modelKind=None)
        for block in BlockType
    }
    catalog = WorldCatalog(
        BlockType,
        BlockType.AIR,
        BlockType.WATER,
        BlockType.LAVA,
        BlockType.OBSIDIAN,
        BlockType.COBBLESTONE,
        BlockType.STONE,
        definitions,
    )
    return World(1, 1, 1, catalog=catalog)


def test_nether_hub_is_tightly_framed_and_contains_all_five_source_biome_palettes():
    world = _world()
    scene = build_hub(world, "nether")
    assert (world.width, world.depth, world.height, world.min_y) == (84, 78, 64, -16)
    assert scene.framing_bounds == ((2, 2, -9), (81, 75, 42))
    blocks = set(world.blocks.values())
    assert {
        BlockType.NETHERRACK,
        BlockType.WARPED_NYLIUM,
        BlockType.CRIMSON_NYLIUM,
        BlockType.SOUL_SAND,
        BlockType.SOUL_SOIL,
        BlockType.BASALT,
        BlockType.BLACKSTONE,
    } <= blocks
    assert all(world.isInBounds(*position) for position in world.sceneStructurePositions)


def test_end_ship_and_city_templates_are_not_clipped_by_the_map_volume():
    world = _world()
    scene = build_hub(world, "end")
    assert (world.width, world.depth, world.height) == (64, 60, 40)
    assert scene.framing_bounds == ((5, 5, 0), (63, 56, 35))
    assert world.occupiedBounds[1][2] == 34
    assert all(world.isInBounds(*position) for position in world.sceneStructurePositions)


def test_ocean_hub_has_full_58_block_monument_without_decorative_water_blocks():
    world = _world()
    scene = build_hub(world, "ocean")
    counts = Counter(world.blocks.values())
    monument = [
        position
        for position, block in world.blocks.items()
        if block in (
            BlockType.PRISMARINE,
            BlockType.PRISMARINE_BRICKS,
            BlockType.DARK_PRISMARINE,
        )
    ]
    assert tuple(min(position[axis] for position in monument) for axis in range(3)) == (19, 19, -1)
    assert tuple(max(position[axis] for position in monument) for axis in range(3)) == (76, 76, 20)
    assert counts[BlockType.PRISMARINE] > 4_000
    assert counts[BlockType.PRISMARINE_BRICKS] > 5_000
    assert counts[BlockType.SEA_LANTERN] >= 15
    assert counts[BlockType.GOLD_BLOCK] == 8
    assert counts[BlockType.WATER] == 0
    assert scene.source_templates[0] == "ocean_monument_generator"

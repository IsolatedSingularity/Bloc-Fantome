"""Spatial indexes remain equivalent for edits and bulk replacement."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

from domain.world_catalog import WorldCatalog
from engine.world import World
from engine.world_snapshot import WorldSnapshot


class Block(Enum):
    AIR = 0
    STONE = 1
    WATER = 2
    LAVA = 3
    OBSIDIAN = 4
    COBBLESTONE = 5


@dataclass(frozen=True)
class Definition:
    lightLevel: int = 0
    lightColor: tuple = (255, 255, 255)
    transparent: bool = False
    isLiquid: bool = False


DEFINITIONS = {block: Definition() for block in Block}
CATALOG = WorldCatalog(
    block_type=Block,
    air=Block.AIR,
    water=Block.WATER,
    lava=Block.LAVA,
    obsidian=Block.OBSIDIAN,
    cobblestone=Block.COBBLESTONE,
    stone=Block.STONE,
    definitions=DEFINITIONS,
)


def make_world():
    return World(8, 8, 8, catalog=CATALOG)


def test_single_edits_keep_type_bounds_height_chunk_and_surface_indexes_current():
    world = World(32, 32, 8, catalog=CATALOG)
    world.setBlock(1, 2, 3, Block.STONE)
    world.setBlock(20, 20, 5, Block.WATER)

    assert world.blockTypeCounts == {Block.STONE: 1, Block.WATER: 1}
    assert world.positionsOfType(Block.STONE) == {(1, 2, 3)}
    assert world.occupiedBounds == ((1, 2, 3), (20, 20, 5))
    assert world.heightIndex == {(1, 2): 3, (20, 20): 5}
    assert set(dict(world.iterBlocksInChunkRadius(1, 2, 0))) == {(1, 2, 3)}
    assert world.surfaceBlocks == {(1, 2, 3), (20, 20, 5)}

    world.setBlock(20, 20, 5, Block.AIR)
    assert world.blockTypeCounts == {Block.STONE: 1}
    assert world.occupiedBounds == ((1, 2, 3), (1, 2, 3))


def test_bulk_replace_matches_reference_interactive_indexes():
    blocks = {
        (x, y, z): Block.STONE
        for x in range(1, 5)
        for y in range(1, 4)
        for z in range(1, 4)
    }
    blocks[(6, 6, 2)] = Block.WATER
    snapshot = WorldSnapshot(
        width=8,
        depth=8,
        height=8,
        min_y=0,
        dimension="overworld",
        blocks=blocks,
        liquid_levels={(6, 6, 2): 8},
        liquid_sources=frozenset({(6, 6, 2)}),
        structure_positions=frozenset({(1, 1, 1), (2, 2, 2)}),
    )
    bulk = make_world()
    revision = bulk.revision
    bulk.replace(snapshot)

    reference = make_world()
    with reference.bulkUpdate():
        for pos, block in blocks.items():
            reference.setBlock(*pos, block)

    assert bulk.revision == revision + 1
    assert bulk.blocks == reference.blocks
    assert bulk.heightIndex == reference.heightIndex
    assert bulk.surfaceBlocks == reference.surfaceBlocks
    assert bulk.surfaceChunks == reference.surfaceChunks
    assert bulk.blockTypeCounts == reference.blockTypeCounts
    assert bulk.occupiedBounds == reference.occupiedBounds
    assert bulk.liquidLevels == {(6, 6, 2): 8}
    assert bulk.liquidSources == {(6, 6, 2)}
    assert set(bulk.iterStructurePositionsInChunkRadius(1, 1, 0)) == {
        (1, 1, 1), (2, 2, 2)
    }
    assert bulk.sceneStructureBounds == ((1, 1, 1), (2, 2, 2))
    assert (1, 1, 1) in bulk.structureSurfacePositions(0)

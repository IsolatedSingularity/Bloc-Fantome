import unittest
from dataclasses import dataclass
from enum import Enum
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer_module = load_module("bloc_renderer", ROOT / "Code" / "engine" / "renderer.py")
world_module = load_module("bloc_world", ROOT / "Code" / "engine" / "world.py")
IsometricRenderer = renderer_module.IsometricRenderer
set_tile_dimensions = renderer_module.set_tile_dimensions
World = world_module.World
init_world_module = world_module.init_world_module


class BlockType(Enum):
    AIR = 0
    STONE = 1
    WATER = 2
    LAVA = 3
    OBSIDIAN = 4
    COBBLESTONE = 5


@dataclass
class BlockProperties:
    facing: object = None
    isOpen: bool = False
    slabPosition: object = None


@dataclass
class BlockDefinition:
    lightLevel: int = 0
    lightColor: tuple = (255, 255, 255)


BLOCK_DEFINITIONS = {block: BlockDefinition() for block in BlockType}


class WorldFluidTests(unittest.TestCase):
    def setUp(self):
        init_world_module(BlockType, BlockProperties, BLOCK_DEFINITIONS)
        self.world = World(6, 6, 5)

    def add_floor(self, holes=()):
        holes = set(holes)
        for x in range(self.world.width):
            for y in range(self.world.depth):
                if (x, y) not in holes:
                    self.world.setBlock(x, y, 0, BlockType.STONE)

    def drain(self, limit=200):
        for _ in range(limit):
            if not self.world.waterUpdateQueue and not self.world.lavaUpdateQueue:
                return
            self.world.updateLiquids(BlockType.WATER, 32)
            self.world.updateLiquids(BlockType.LAVA, 32)
        self.fail("fluid scheduler did not settle")

    def test_falling_water_is_not_a_source(self):
        self.add_floor(holes={(2, 2)})
        self.world.setBlock(2, 2, 2, BlockType.WATER)
        self.world.updateLiquids(BlockType.WATER, 1)
        self.assertEqual(self.world.getBlock(2, 2, 1), BlockType.WATER)
        self.assertIn((2, 2, 1), self.world.liquidFalling)
        self.assertNotIn((2, 2, 1), self.world.liquidSources)

    def test_water_prefers_and_descends_into_nearby_hole(self):
        self.add_floor(holes={(4, 2)})
        self.world.setBlock(1, 2, 1, BlockType.WATER)
        self.drain()
        self.assertEqual(self.world.getBlock(4, 2, 1), BlockType.WATER)
        self.assertEqual(self.world.getBlock(4, 2, 0), BlockType.WATER)

    def test_flow_retracts_after_source_is_removed(self):
        self.add_floor()
        self.world.setBlock(2, 2, 1, BlockType.WATER)
        self.drain()
        self.world.setBlock(2, 2, 1, BlockType.AIR)
        self.drain()
        self.assertNotIn(BlockType.WATER, self.world.blocks.values())

    def test_lava_decay_is_dimension_specific(self):
        self.add_floor()
        self.world.setDimension("overworld")
        self.world.setBlock(2, 2, 1, BlockType.LAVA)
        self.world.updateLiquids(BlockType.LAVA, 1)
        overworld_levels = [
            self.world.getLiquidLevel(2 + dx, 2 + dy, 1)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ]
        self.assertIn(6, overworld_levels)

        nether = World(6, 6, 5)
        nether.setDimension("nether")
        for x in range(nether.width):
            for y in range(nether.depth):
                nether.setBlock(x, y, 0, BlockType.STONE)
        nether.setBlock(2, 2, 1, BlockType.LAVA)
        nether.updateLiquids(BlockType.LAVA, 1)
        nether_levels = [
            nether.getLiquidLevel(2 + dx, 2 + dy, 1)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ]
        self.assertIn(7, nether_levels)

    def test_still_lava_next_to_water_becomes_obsidian(self):
        self.add_floor()
        self.world.setBlock(2, 2, 1, BlockType.LAVA)
        self.world.setBlock(3, 2, 1, BlockType.WATER)
        self.world.updateLiquids(BlockType.LAVA, 4)
        self.assertEqual(self.world.getBlock(2, 2, 1), BlockType.OBSIDIAN)

    def test_multiple_waterfalls_settle_without_queue_churn(self):
        world = World(12, 12, 12)
        for x in range(world.width):
            for y in range(world.depth):
                if (x, y) not in {(1, 10), (10, 10)}:
                    world.setBlock(x, y, 0, BlockType.STONE)
        for x, y in ((2, 2), (9, 2), (6, 6)):
            world.setBlock(x, y, 8, BlockType.WATER)

        batches = 0
        while world.waterUpdateQueue and batches < 50:
            world.updateLiquids(BlockType.WATER, 32)
            batches += 1
        self.assertFalse(world.waterUpdateQueue)
        self.assertLess(batches, 50)

    def test_surface_index_excludes_buried_cells_and_tracks_edits(self):
        world = World(5, 5, 5)
        with world.bulkUpdate():
            for x in range(1, 4):
                for y in range(1, 4):
                    for z in range(1, 4):
                        world.setBlock(x, y, z, BlockType.STONE)
        self.assertNotIn((2, 2, 2), world.surfaceBlocks)
        world.setBlock(2, 2, 3, BlockType.AIR)
        self.assertIn((2, 2, 2), world.surfaceBlocks)


class RendererPickingTests(unittest.TestCase):
    def setUp(self):
        set_tile_dimensions(64, 32, 38)
        self.renderer = IsometricRenderer(300, 180)

    @staticmethod
    def centroid(polygon):
        return (
            sum(point[0] for point in polygon) // len(polygon),
            sum(point[1] for point in polygon) // len(polygon),
        )

    def test_face_picking_matches_scaled_geometry_at_every_view(self):
        for zoom in (0.05, 0.1, 0.5, 1.0, 1.4, 2.0):
            self.renderer.setZoom(zoom)
            for rotation in range(4):
                self.renderer.setViewRotation(rotation)
                polygons = self.renderer.getBlockFacePolygons(3, 4, 2)
                for face, polygon in polygons.items():
                    point = self.centroid(polygon)
                    self.assertEqual(
                        self.renderer.detectBlockFace(*point, 3, 4, 2),
                        face,
                        (zoom, rotation, face, point),
                    )

    def test_overview_projection_remains_invertible(self):
        self.renderer.setZoom(0.05)
        for rotation in range(4):
            self.renderer.setViewRotation(rotation)
            screen = self.renderer.worldToScreen(30, 45, 7)
            restored = self.renderer.screenToWorld(*screen, 7)
            self.assertLessEqual(abs(restored[0] - 30), 1)
            self.assertLessEqual(abs(restored[1] - 45), 1)

    def test_depth_key_changes_with_rotation(self):
        expected = (7, -3, -7, 3)
        actual = []
        for rotation in range(4):
            self.renderer.setViewRotation(rotation)
            actual.append(self.renderer.depthKey(2, 5, 0))
        self.assertEqual(tuple(actual), expected)


if __name__ == "__main__":
    unittest.main()

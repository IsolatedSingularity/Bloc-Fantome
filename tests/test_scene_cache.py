from enum import IntEnum
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

from engine import scene_cache
from engine.block_state import BlockProperties, Facing, SlabPosition, StairShape


class FakeBlock(IntEnum):
    STONE = 3
    STAIRS = 20
    WATER = 70


class SceneCacheTests(unittest.TestCase):
    def test_fixed_record_cache_round_trips_roles_states_and_liquids(self):
        digest = bytes(range(32))
        props = BlockProperties(
            facing=Facing.WEST,
            slabPosition=SlabPosition.TOP,
            stairShape=StairShape.OUTER_LEFT,
        )
        staged = [
            (1, 2, -3, FakeBlock.STAIRS, props, None),
            (4, 5, 6, FakeBlock.WATER, None, (7, False, True)),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = str(pathlib.Path(directory) / "scene.bfc")
            scene_cache.write(
                path, digest, "overworld", (16, 16, 32, -8),
                {"kind": "world", "version": "1.21"}, staged, {(1, 2, -3)},
            )
            dimension, bounds, scene, loaded, skipped = scene_cache.load(
                path, digest, FakeBlock
            )
        self.assertEqual(dimension, "overworld")
        self.assertEqual(bounds, (16, 16, 32, -8))
        self.assertEqual(scene["_structure_positions"], {(1, 2, -3)})
        self.assertEqual(loaded[0][4].facing, Facing.WEST)
        self.assertEqual(loaded[0][4].stairShape, StairShape.OUTER_LEFT)
        self.assertEqual(loaded[1][5], (7, False, True))
        self.assertEqual(skipped, 0)


if __name__ == "__main__":
    unittest.main()

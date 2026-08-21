"""Undo commands preserve complete cell state and batch mutations."""

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

from engine.undo import BatchCommand, PlaceBlockCommand, RemoveBlockCommand, UndoManager


class Block(Enum):
    AIR = 0
    STONE = 1
    WATER = 2


@dataclass
class Properties:
    marker: str

    def copy(self):
        return Properties(self.marker)


class FakeWorld:
    def __init__(self):
        self.blocks = {}
        self.blockProperties = {}
        self.liquidLevels = {}
        self.liquidSources = set()
        self.liquidFalling = set()
        self.revision = 0
        self._bulk = 0
        self._changed = False

    def isInBounds(self, *_):
        return True

    def getBlock(self, x, y, z):
        return self.blocks.get((x, y, z), Block.AIR)

    def getBlockProperties(self, x, y, z):
        return self.blockProperties.get((x, y, z))

    def setBlock(self, x, y, z, block):
        pos = (x, y, z)
        if block is Block.AIR:
            self.blocks.pop(pos, None)
        else:
            self.blocks[pos] = block
        self.blockProperties.pop(pos, None)
        self.liquidLevels.pop(pos, None)
        self.liquidSources.discard(pos)
        self.liquidFalling.discard(pos)
        if self._bulk:
            self._changed = True
        else:
            self.revision += 1
        return True

    def setBlockProperties(self, x, y, z, properties):
        self.blockProperties[(x, y, z)] = properties
        if self._bulk:
            self._changed = True
        else:
            self.revision += 1

    @contextmanager
    def bulkUpdate(self):
        self._bulk += 1
        try:
            yield
        finally:
            self._bulk -= 1
            if not self._bulk and self._changed:
                self._changed = False
                self.revision += 1


def test_remove_undo_restores_properties_and_liquid_state():
    world = FakeWorld()
    pos = (1, 2, 3)
    world.blocks[pos] = Block.WATER
    world.blockProperties[pos] = Properties("state")
    world.liquidLevels[pos] = 5
    world.liquidFalling.add(pos)
    manager = UndoManager()

    assert manager.execute(RemoveBlockCommand(world, *pos))
    assert manager.undo()

    assert world.getBlock(*pos) is Block.WATER
    assert world.getBlockProperties(*pos) == Properties("state")
    assert world.liquidLevels[pos] == 5
    assert pos in world.liquidFalling
    assert pos not in world.liquidSources


def test_batch_execute_and_undo_each_increment_world_revision_once():
    world = FakeWorld()
    manager = UndoManager()
    batch = BatchCommand([
        PlaceBlockCommand(world, 1, 1, 1, Block.STONE),
        PlaceBlockCommand(world, 2, 1, 1, Block.STONE),
        PlaceBlockCommand(world, 3, 1, 1, Block.STONE),
    ], "Place row")

    assert manager.execute(batch)
    assert world.revision == 1
    assert len(manager.undo_stack) == 1
    assert manager.undo()
    assert world.revision == 2
    assert not world.blocks

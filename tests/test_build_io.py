"""Build parsing is transactional and independent from the application UI."""

from enum import Enum
import gzip
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

from domain.block_catalog import BlockDefinition
from domain.world_catalog import WorldCatalog
from domain.blocks import BlockProperties, Facing
from engine.build_io import BuildReadPolicy, read_build, write_build
from engine.world_snapshot import WorldSnapshot


class Block(Enum):
    AIR = 0
    STONE = 1
    WATER = 2
    LAVA = 3
    OBSIDIAN = 4
    COBBLESTONE = 5
    DOOR = 6


DEFINITIONS = {
    block: BlockDefinition(block.name, "", "", "", isDoor=block is Block.DOOR)
    for block in Block
}
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


def test_read_build_returns_snapshot_with_nested_state_and_roles(tmp_path):
    path = tmp_path / "build.json.gz"
    payload = {
        "version": 5,
        "dimension": "overworld",
        "bounds": {"width": 16, "depth": 16, "height": 32, "min_y": -8},
        "scene": {"kind": "world"},
        "blocks": [{
            "x": 2,
            "y": 3,
            "z": 4,
            "type": "DOOR",
            "state": {"facing": "west", "half": "upper", "open": True},
            "role": "structure",
        }],
    }
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle)

    result = read_build(path, CATALOG, BuildReadPolicy())

    assert result.skipped_count == 0
    assert result.snapshot.blocks == {(2, 3, 4): Block.DOOR}
    assert result.snapshot.structure_positions == {(2, 3, 4)}
    properties = result.snapshot.properties[(2, 3, 4)]
    assert properties.facing.name == "WEST"
    assert properties.doorHalf.name == "UPPER"
    assert properties.isOpen is True


def test_read_build_rejects_invalid_payload_without_live_world(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"not_blocks": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid build file format"):
        read_build(path, CATALOG, BuildReadPolicy())


def test_write_build_is_atomic_v5_and_round_trips_state(tmp_path):
    path = tmp_path / "round-trip.json.gz"
    snapshot = WorldSnapshot(
        width=16,
        depth=16,
        height=32,
        min_y=-8,
        dimension="overworld",
        blocks={(2, 3, 4): Block.DOOR, (5, 6, 0): Block.WATER},
        properties={(2, 3, 4): BlockProperties(facing=Facing.EAST, isOpen=True)},
        liquid_levels={(5, 6, 0): 7},
        liquid_falling={(5, 6, 0)},
        structure_positions={(2, 3, 4)},
        scene_metadata={"kind": "world", "provider": "test"},
    )

    result = write_build(path, snapshot, DEFINITIONS)
    loaded = read_build(path, CATALOG, BuildReadPolicy()).snapshot

    assert result.block_count == 2
    assert path.is_file()
    assert not path.with_name(path.name + ".tmp").exists()
    assert loaded.blocks == snapshot.blocks
    assert loaded.properties[(2, 3, 4)].facing is Facing.EAST
    assert loaded.properties[(2, 3, 4)].isOpen is True
    assert loaded.liquid_levels == {(5, 6, 0): 7}
    assert loaded.liquid_falling == {(5, 6, 0)}
    assert loaded.structure_positions == {(2, 3, 4)}

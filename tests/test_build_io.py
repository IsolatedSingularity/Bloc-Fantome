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
    REPEATER = 7


DEFINITIONS = {
    block: BlockDefinition(block.name, "", "", "", isDoor=block is Block.DOOR)
    for block in Block
}
DEFINITIONS[Block.REPEATER] = BlockDefinition(
    "Repeater", "", "", "", transparent=True, modelKind="repeater"
)
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


def test_captured_source_palette_round_trips_on_ordinary_blocks(tmp_path):
    path=tmp_path/'capture.json.gz'
    props=BlockProperties(sourceCapture='warped_forest',sourcePalette=7)
    snapshot=WorldSnapshot(8,8,16,blocks={(2,3,4):Block.STONE},properties={(2,3,4):props})
    write_build(path,snapshot,DEFINITIONS)
    loaded=read_build(path,CATALOG,BuildReadPolicy()).snapshot
    assert loaded.properties[(2,3,4)].sourceCapture=='warped_forest'
    assert loaded.properties[(2,3,4)].sourcePalette==7
    assert props.copy().sourceCapture==props.sourceCapture


def test_redstone_component_state_round_trips(tmp_path):
    path = tmp_path / "redstone.json.gz"
    properties = BlockProperties(
        facing=Facing.NORTH,
        powered=True,
        redstonePower=15,
        repeaterDelay=4,
        repeaterLocked=True,
    )
    snapshot = WorldSnapshot(
        width=8, depth=8, height=8,
        blocks={(2, 2, 1): Block.REPEATER},
        properties={(2, 2, 1): properties},
    )

    write_build(path, snapshot, DEFINITIONS)
    loaded = read_build(path, CATALOG, BuildReadPolicy()).snapshot
    restored = loaded.properties[(2, 2, 1)]
    assert restored.facing is Facing.NORTH
    assert restored.powered and restored.redstonePower == 15
    assert restored.repeaterDelay == 4 and restored.repeaterLocked


def test_streamed_write_failure_preserves_existing_save(tmp_path):
    path=tmp_path/'existing.gz'
    original=WorldSnapshot(2,2,2,blocks={(0,0,0):Block.STONE})
    write_build(path,original,DEFINITIONS)
    before=path.read_bytes()
    broken=WorldSnapshot(2,2,2,blocks={(0,0,0):Block.STONE,(1,0,0):object()})
    with pytest.raises(AttributeError):write_build(path,broken,DEFINITIONS)
    assert path.read_bytes()==before
    assert not path.with_name(path.name+'.tmp').exists()


def test_shared_painter_sort_preserves_each_modes_exact_total_order(monkeypatch):
    import random
    from engine import build_io, native_acceleration
    rng=random.Random(731)
    blocks={(rng.randrange(12),rng.randrange(12),rng.randrange(-3,9)):Block.STONE for _ in range(800)}
    positions=list(blocks);structures=set(positions[::3])
    surfaces={r:set(positions[r::5]) & structures for r in range(4)}
    views={r:set(positions[r::2]) for r in range(4)}
    tops={}
    for x,y,z in blocks:tops[x,y]=max(z,tops.get((x,y),-10000))
    terrain={(x,y,z) for (x,y),z in tops.items()}-structures
    expected={mode:{} for mode in ('all','transparent','hidden')}
    for r in range(4):
        for mode,cells in (('all',views[r]),('transparent',terrain|surfaces[r]),('hidden',surfaces[r])):
            ordered=sorted(cells,key=lambda p:(build_io._depth_key(r,p),p[2],p[0],p[1]))
            expected[mode][r]=tuple((build_io._depth_key(r,p),*p,blocks[p]) for p in ordered)
    assert build_io._draw_orders(blocks,structures,surfaces,views)==expected
    monkeypatch.setattr(native_acceleration,'sort_positions',lambda *args:None)
    assert build_io._draw_orders(blocks,structures,surfaces,views)==expected

"""Failure isolation and same-length corruption, with synthetic worlds only."""
from pathlib import Path
import pytest
from engine import scene_cache
from engine.build_io import write_build
from engine.world_snapshot import WorldSnapshot
from test_build_io import Block, DEFINITIONS, CATALOG


def snapshot():
    return WorldSnapshot(width=8, depth=8, height=8, min_y=0,
                         dimension='overworld', blocks={(1, 1, 1): Block.STONE})


def test_save_does_not_reuse_another_writers_staging_file(tmp_path):
    path = tmp_path / 'save.json.gz'
    competing = path.with_name(path.name + '.tmp')
    competing.write_bytes(b'other writer owns this')
    write_build(path, snapshot(), DEFINITIONS)
    assert competing.read_bytes() == b'other writer owns this'


def test_same_length_valid_coordinate_cache_corruption_is_rejected(tmp_path):
    path = str(tmp_path / 'scene.bfc'); digest = bytes(32)
    scene_cache.write(path, digest, 'overworld', (8, 8, 8, 0), {},
                      [(1, 1, 1, Block.STONE, None, None)], set())
    data = bytearray(Path(path).read_bytes())
    _, _, metadata_size = scene_cache.HEADER.unpack(data[:scene_cache.HEADER.size])
    data[scene_cache.HEADER.size + metadata_size + 4] = 2
    Path(path).write_bytes(data)
    with pytest.raises(ValueError):scene_cache.load(path, digest, Block)


def test_damaged_cache_recovers_exact_source_and_rewrites_cache(tmp_path):
    from engine.build_io import read_build, BuildReadPolicy
    source = tmp_path / 'world.json.gz'
    write_build(source, snapshot(), DEFINITIONS)
    policy = BuildReadPolicy(bundled_worlds_dir=tmp_path, derived_cache_dir=tmp_path / 'cache')
    expected = read_build(source, CATALOG, policy)
    assert not expected.cache_hit
    cached = read_build(source, CATALOG, policy)
    assert cached.cache_hit and cached.snapshot.blocks == expected.snapshot.blocks
    cache = next((tmp_path / 'cache').glob('*.bfc'))
    data = bytearray(cache.read_bytes());data[-1] ^= 1;cache.write_bytes(data)
    recovered = read_build(source, CATALOG, policy)
    assert not recovered.cache_hit
    assert recovered.snapshot.blocks == expected.snapshot.blocks
    assert read_build(source, CATALOG, policy).cache_hit

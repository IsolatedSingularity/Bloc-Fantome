"""Prepared-data contracts requiring only tracked Python source, no local media."""
import hashlib
import json
from types import SimpleNamespace
import pytest
import blocFantome as app
from domain.world_catalog import WorldCatalog
from engine.world_snapshot import WorldSnapshot,prepare_snapshot
from engine import tutorial_prepared as bundle
from tools.bake_tutorial import bake_lessons


@pytest.fixture
def tiny_bundle(tmp_path,monkeypatch):
    bt=app.BlockType
    catalog=WorldCatalog(bt,bt.AIR,bt.WATER,bt.LAVA,bt.OBSIDIAN,bt.COBBLESTONE,bt.STONE,app.BLOCK_DEFINITIONS)
    def stage(step):
        return prepare_snapshot(WorldSnapshot(12,12,12,blocks={(2,3,4):bt.GLOWSTONE}),catalog)
    monkeypatch.setattr(bundle,'ROOT',tmp_path)
    fake=SimpleNamespace(_stageTourScene=stage)
    steps=[{'id':key,'capture':'synthetic'} for key in ('blocks','lighting')]
    bake_lessons(fake,steps,tmp_path)
    return tmp_path,catalog,fake,steps


def test_loaded_states_are_independent_and_transfer_once(tiny_bundle):
    root,catalog,_,_=tiny_bundle
    a=bundle.load_lesson('blocks',catalog);b=bundle.load_lesson('blocks',catalog)
    assert a.blocks==b.blocks
    assert a._prepared[0] is not b._prepared[0]
    a._prepared[0].clear()
    assert b.blocks=={(2,3,4):app.BlockType.GLOWSTONE}


def test_partial_rebake_keeps_other_valid_lessons(tiny_bundle):
    root,_,fake,steps=tiny_bundle
    before=bundle.validate_bundle(root)
    after=bake_lessons(fake,steps,root,['blocks'])
    assert after==before
    bundle.validate_bundle(root,{'blocks','lighting'})


@pytest.mark.parametrize('damage',['bytes','manifest','path','python','cells'])
def test_damaged_bundle_falls_back_but_release_validation_fails(tiny_bundle,damage):
    root,catalog,_,_=tiny_bundle
    path=root/'manifest.json';index=json.loads(path.read_text())
    if damage=='bytes':(root/'blocks.prepared').write_bytes(b'corrupt')
    elif damage=='manifest':path.write_text('{')
    elif damage=='path':index['lessons']['blocks']['file']='../outside.prepared'
    elif damage=='python':index['python']=[0,0]
    elif damage=='cells':index['lessons']['blocks']['cells']=999
    if damage not in ('bytes','manifest'):path.write_text(json.dumps(index))
    assert bundle.load_lesson('blocks',catalog) is None
    if damage!='cells':
        with pytest.raises((ValueError,KeyError)):bundle.validate_bundle(root)


def test_fingerprint_includes_worlds_and_compact_cell_records(tmp_path):
    for name in bundle.SOURCES:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'code')
    before=bundle.fingerprint_at(tmp_path)
    world=tmp_path/'worlds/test.json.gz';world.parent.mkdir();world.write_bytes(b'world')
    after=bundle.fingerprint_at(tmp_path);assert after!=before
    cells=tmp_path/'biome_captures/runtime/test.cells.gz';cells.parent.mkdir(parents=True);cells.write_bytes(b'cells')
    assert bundle.fingerprint_at(tmp_path)!=after

"""Regressions for maintenance data loss and delayed load ownership."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Code'))
import gzip
import json
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import pygame
import blocFantome as module
from engine.build_io import BuildReadPolicy, read_build, write_build
from engine.undo import BatchCommand, PlaceBlockCommand, UndoManager
from engine.world import World
from engine.world_snapshot import WorldSnapshot
from domain.blocks import BlockProperties
from domain.world_catalog import WorldCatalog


def app_stub():
    app=module.BlocFantome.__new__(module.BlocFantome)
    bt=module.BlockType
    catalog=WorldCatalog(bt,bt.AIR,bt.WATER,bt.LAVA,bt.OBSIDIAN,bt.COBBLESTONE,bt.STONE,module.BLOCK_DEFINITIONS)
    app.world=World(64,64,32,min_y=-8,catalog=catalog)
    app.currentDimension='overworld';app.sceneMetadata={'kind':'world','label':'retained'}
    app.sceneStructurePositions={(30,31,-4)};app.currentBuildPath=None
    app.worldMapActive=False;app.redstoneLabActive=False;app._tutorialSessionSnapshot=None
    return app


def test_backup_roundtrip_and_failed_replacement_retains_history(tmp_path,monkeypatch):
    app=app_stub();app.backupDir=str(tmp_path);app.maxBackups=1
    app.world.setBlock(30,31,-4,module.BlockType.REPEATER)
    app.world.setBlockProperties(30,31,-4,BlockProperties(powered=True,redstonePower=15,repeaterDelay=4,repeaterLocked=True,sourceCapture='fixture',sourcePalette=7))
    app.world.setBlock(40,40,-5,module.BlockType.WATER)
    app.world.liquidLevels[(40,40,-5)]=3;app.world.liquidSources.discard((40,40,-5));app.world.liquidFalling.add((40,40,-5))
    assert app._createRollingBackup()
    path=next(tmp_path.glob('*.gz'));original=path.read_bytes()
    loaded=read_build(path,app.world.catalog,BuildReadPolicy()).snapshot
    assert (loaded.width,loaded.depth,loaded.height,loaded.min_y)==(64,64,32,-8)
    assert loaded.blocks==app.world.blocks
    assert loaded.properties==app.world.blockProperties
    assert loaded.liquid_levels==app.world.liquidLevels
    assert loaded.liquid_sources==app.world.liquidSources
    assert loaded.liquid_falling==app.world.liquidFalling
    assert loaded.structure_positions==app.sceneStructurePositions
    assert loaded.scene_metadata['label']=='retained'
    monkeypatch.setattr('engine.build_io.os.replace',Mock(side_effect=OSError('disk full')))
    assert not app._createRollingBackup()
    assert list(tmp_path.glob('*.gz'))==[path] and path.read_bytes()==original
    assert not list(tmp_path.glob('*.tmp'))


def test_failed_autosave_does_not_claim_success():
    app=app_stub();app.autoSaveEnabled=True;app.autoBackupEnabled=False
    app.lastAutoSaveTime=-100000;app.autoSaveInterval=1;app.autoSavePath='auto.json.gz'
    app.autoSaveFlashTimer=0;app._saveBuilding=Mock(return_value=False)
    app._autoSave()
    assert app.lastAutoSaveTime==-100000 and app.autoSaveFlashTimer==0
    assert 'failed' in app.tooltipText


@pytest.mark.parametrize('payload',[{'version':999,'blocks':[]},{'version':5,'blocks':[{'type':'bad'}]}])
def test_invalid_build_preserves_live_world(tmp_path,payload):
    app=app_stub();app.world.setBlock(1,1,1,module.BlockType.STONE)
    path=tmp_path/'bad.json';path.write_text(json.dumps(payload))
    assert not app._loadBuildingFromPath(str(path))
    assert app.world.getBlock(1,1,1)==module.BlockType.STONE


@pytest.mark.parametrize('data',[gzip.compress(b'{"blocks":[]}')[:-6],b'\xff\xfe',b'{"blocks":'])
def test_corrupt_build_preserves_live_world(tmp_path,data):
    app=app_stub();before=app.world
    path=tmp_path/'bad.json.gz';path.write_bytes(data)
    assert not app._loadBuildingFromPath(str(path))
    assert app.world is before


def test_duplicate_last_row_replaces_entire_cell_and_empty_is_valid(tmp_path):
    app=app_stub();path=tmp_path/'build.json'
    path.write_text(json.dumps({'version':5,'blocks':[
        {'x':1,'y':1,'z':1,'type':'WATER','role':'structure','sourceCapture':'test','sourcePalette':2},
        {'x':1,'y':1,'z':1,'type':'STONE'}]}))
    snap=read_build(path,app.world.catalog,BuildReadPolicy()).snapshot
    assert snap.blocks[(1,1,1)]==module.BlockType.STONE
    assert not snap.properties and not snap.liquid_levels and not snap.structure_positions
    path.write_text('{"version":5,"blocks":[]}')
    assert not read_build(path,app.world.catalog,BuildReadPolicy()).snapshot.blocks


def test_cache_preserves_modern_properties_and_large_bounds(tmp_path):
    app=app_stub();path=tmp_path/'build.json.gz'
    props=BlockProperties(powered=True,redstonePower=15,repeaterDelay=4,repeaterLocked=True,sourceCapture='fixture',sourcePalette=22)
    write_build(path,WorldSnapshot(300,16,16,blocks={(299,1,1):module.BlockType.REPEATER},properties={(299,1,1):props}),module.BLOCK_DEFINITIONS)
    policy=BuildReadPolicy(bundled_worlds_dir=tmp_path,derived_cache_dir=tmp_path/'cache')
    cold=read_build(path,app.world.catalog,policy);warm=read_build(path,app.world.catalog,policy)
    assert warm.cache_hit
    assert cold.snapshot==warm.snapshot


@pytest.mark.parametrize('raises',[False,True])
def test_batch_failure_rolls_back_and_leaves_history_unchanged(raises):
    app=app_stub();manager=UndoManager()
    failure=Mock(world=None);failure.execute=Mock(side_effect=RuntimeError('failed')) if raises else Mock(return_value=False)
    batch=BatchCommand([PlaceBlockCommand(app.world,1,1,1,module.BlockType.STONE),failure,PlaceBlockCommand(app.world,2,1,1,module.BlockType.STONE)])
    if raises:
        with pytest.raises(RuntimeError):manager.execute(batch)
    else:assert not manager.execute(batch)
    assert not app.world.blocks and manager.get_history_count()==(0,0)


def test_stale_load_cannot_replace_later_edit():
    app=app_stub();future=Future();future.set_result(('overworld',(),{},None,0))
    entry=SimpleNamespace(name='test');app.pendingWorldLoad=(future,entry,'path')
    app._worldLoadOwner=(app.world,app.world.revision,app.currentDimension,False,False,None)
    app.world.setBlock(1,1,1,module.BlockType.STONE);app._applyStagedBuild=Mock()
    app._pollWorldLoad()
    app._applyStagedBuild.assert_not_called();assert app.pendingWorldLoad is None


def test_pending_load_blocks_input_and_escape_detaches_running_future():
    pygame.init();app=app_stub();app.running=True
    future=Future();future.set_running_or_notify_cancel()
    app.pendingWorldLoad=(future,SimpleNamespace(name='test'),'path')
    pygame.event.clear();pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_r))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
    app._handleEvents();assert app.pendingWorldLoad is None
    future.set_result(None);app._applyStagedBuild=Mock();app._pollWorldLoad()
    app._applyStagedBuild.assert_not_called()



def test_failed_batch_undo_restores_edits_and_history():
    app=app_stub();manager=UndoManager()
    first=PlaceBlockCommand(app.world,1,1,1,module.BlockType.STONE)
    second=PlaceBlockCommand(app.world,2,1,1,module.BlockType.STONE)
    batch=BatchCommand([first,second]);assert manager.execute(batch)
    first.undo=Mock(return_value=False)
    assert manager.undo() is None
    assert app.world.getBlock(2,1,1)==module.BlockType.STONE
    assert manager.get_history_count()==(1,0)


def test_corrupt_deflate_preserves_live_world(tmp_path):
    app=app_stub();before=app.world
    data=bytearray(gzip.compress(b'{"version":5,"blocks":[]}'))
    data[10]=7  # Reserved DEFLATE block type, not merely a bad checksum.
    path=tmp_path/'corrupt.gz';path.write_bytes(data)
    assert not app._loadBuildingFromPath(str(path))
    assert app.world is before


def test_visibility_classification_matches_catalog_for_every_block():
    app=app_stub()
    expected={block for block,definition in module.BLOCK_DEFINITIONS.items()
              if module.BlocFantome._isOpaqueCubeDefinition(definition)}
    assert app.world._opaqueCubeTypes==expected


def test_autosave_reports_backup_failure_even_when_main_save_succeeds(tmp_path):
    from engine.save_job import capture_save, write_timed, SaveJob
    app=app_stub();app.lastAutoSaveTime=-100000;app.autoSaveFlashTimer=0
    app.workshop=SimpleNamespace(status='',error='',saved_revision=-1)
    blocker=tmp_path/'blocked';blocker.write_text('preserved')
    path=tmp_path/'auto.json.gz'
    snapshot=capture_save(app.world,'overworld',app.sceneMetadata,app.sceneStructurePositions)
    result=write_timed(path,snapshot,module.BLOCK_DEFINITIONS,(blocker,1))
    future=Future();future.set_result(result)
    app._pendingSave=SaveJob(future,app.world,app.world.revision,str(path),False,True,0,0,autosave=True)
    app._pollSave()
    assert app.autoSaveFlashTimer==60 and app.lastAutoSaveTime!=-100000
    assert 'backup failed' in app.tooltipText
    assert app.workshop.saved_revision==-1 and path.is_file() and blocker.read_text()=='preserved'


@pytest.mark.parametrize('operation', ['undo', 'redo'])
def test_history_survives_command_exception(operation):
    manager=UndoManager()
    command=Mock()
    source=manager.undo_stack if operation=='undo' else manager.redo_stack
    source.append(command)
    getattr(command,'undo' if operation=='undo' else 'execute').side_effect=OSError('injected')
    with pytest.raises(OSError):getattr(manager,operation)()
    assert source==[command]
    assert manager.get_history_count()==((1,0) if operation=='undo' else (0,1))


@pytest.mark.parametrize('change', ['edit', 'canvas', 'mode'])
def test_stale_biome_load_cannot_replace_newer_canvas(change):
    app=app_stub();future=Future()
    app.worldLoadExecutor=Mock();app.worldLoadExecutor.submit.return_value=future
    app.pendingBiomeLoad=app.pendingWorldLoad=app.pendingBiomeWarmup=None
    app._queueBiomeScene('fixture')
    if change=='edit':app.world.setBlock(1,1,1,module.BlockType.STONE)
    elif change=='canvas':app.world=World(12,12,12,catalog=app.world.catalog)
    else:app.worldMapActive=True
    future.set_result((object(),{}));app._applyBiomeScene=Mock()
    app._pollBiomeLoad()
    app._applyBiomeScene.assert_not_called()
    assert app.pendingBiomeLoad is None


@pytest.mark.parametrize('kind',['Biome','World'])
def test_cancelled_load_does_not_retain_replaced_world(kind):
    import weakref,gc
    app=app_stub();previous=weakref.ref(app.world)
    setattr(app,'_'+kind.lower()+'LoadOwner',app._captureLoadOwner())
    app.world=World(12,12,12,catalog=app.world.catalog)
    setattr(app,'pending'+kind+'Load',None)
    getattr(app,'_poll'+kind+'Load')()
    gc.collect()
    assert previous() is None

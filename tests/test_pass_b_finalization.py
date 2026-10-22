"""Save ownership, modal precedence and real weather state contracts."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import patch
import time
import pygame
import pytest
from blocFantome import BlocFantome, BlockType, BlockProperties
from engine.save_job import capture_save
from engine.input_commands import Command


@pytest.fixture(scope='module')
def app():
    app = BlocFantome()
    app.autoSaveEnabled = False
    app.tutorialScreen.visible = False
    assert app.assetManager.loadAllAssets()
    app._createInitialFloor()
    yield app
    if hasattr(app, '_saveExecutor'):app._saveExecutor.shutdown(wait=True)
    if hasattr(app, '_mapExecutor'):app._mapExecutor.shutdown(wait=True)
    app.worldLoadExecutor.shutdown(wait=True)


def poll_save(app):
    deadline = time.monotonic()+10
    while getattr(app, '_pendingSave', None) and time.monotonic()<deadline:
        app._pollSave()
        time.sleep(.005)
    assert app._pendingSave is None


def test_snapshot_owns_nested_state(app):
    p=(2,2,1)
    app.world.setBlock(*p,BlockType.OAK_STAIRS)
    app.world.setBlockProperties(*p,BlockProperties())
    app.sceneMetadata={'nested': {'values': [1]}}
    app.sceneStructurePositions={p}
    snap=capture_save(app.world,'overworld',app.sceneMetadata,app.sceneStructurePositions)
    old_facing=snap.properties[p].facing
    app.world.blockProperties[p].isOpen=True
    app.world.blocks[p]=BlockType.DIAMOND_BLOCK
    app.sceneMetadata['nested']['values'].append(2)
    app.sceneStructurePositions.clear()
    assert snap.blocks[p] is BlockType.OAK_STAIRS
    assert not snap.properties[p].isOpen and snap.properties[p].facing is old_facing
    assert snap.scene_metadata['nested']['values']==[1] and p in snap.structure_positions


def test_large_property_capture_is_owned_immutable_and_cooperative():
    props = {(x, 0, 0): BlockProperties(sourceCapture='ocean', sourcePalette=x%3)
             for x in range(9000)}
    world = SimpleNamespace(width=9000, depth=1, height=1, min_y=0,
        blocks={p: BlockType.STONE for p in props}, blockProperties=props,
        liquidLevels={}, liquidSources=set(), liquidFalling=set())
    progress=[]
    snap=capture_save(world,'overworld',{},set(),lambda n,total:progress.append((n,total)))
    assert len(progress)>=3 and all(total==9000 for n,total in progress)
    props[(0,0,0)].sourcePalette=999
    assert snap.properties[(0,0,0)].sourcePalette==0
    assert snap.properties[(0,0,0)] is snap.properties[(3,0,0)]
    with pytest.raises(AttributeError):snap.properties[(0,0,0)].sourcePalette=3


def test_save_keeps_midflight_edits_dirty_and_rejects_overlap(app,tmp_path):
    from engine.save_job import write_timed
    future=Future();calls=[]
    executor=SimpleNamespace(submit=lambda *args: (calls.append(args),future)[1])
    app._saveExecutor=executor
    before=app.world.revision
    path=tmp_path/'owned.json.gz'
    assert app._saveBuilding(filepath=str(path)) is None
    assert app.workshop.status=='Saving…' and not path.exists()
    assert app._saveBuilding(filepath=str(tmp_path/'overlap.gz')) is None
    assert len(calls)==1
    app.world.setBlock(3,3,2,BlockType.QUARTZ_BLOCK)
    future.set_result(write_timed(*calls[0][1:]))
    app._pollSave()
    assert path.is_file() and app.workshop.saved_revision==before
    assert app.world.revision!=app.workshop.saved_revision
    assert not (tmp_path/'overlap.gz').exists()
    del app._saveExecutor


def test_save_failure_and_exit_cancel_retain_world(app,tmp_path):
    app.running=True
    blocker=tmp_path/'file';blocker.write_text('keep')
    original=dict(app.world.blocks)
    app._requestExit()
    app.currentBuildPath=str(blocker/'bad.gz')
    app._exitAction('save')
    poll_save(app)
    assert app.running and app._exitDialog and app.workshop.error
    assert app.world.blocks==original and blocker.read_text()=='keep'
    app.workshop.error=''
    app.currentBuildPath=None
    with patch.object(app,'_openSaveAsDialog',return_value=None):app._exitAction('save')
    assert app.running and not app._exitAfterSave
    app._exitAction('stay')
    assert app._exitDialog is None


def test_escape_modal_precedence_and_window_close(app):
    app.running=True;app.settingsMenuOpen=True
    app._executeInputCommand(Command.CLOSE_SETTINGS)
    assert not app.settingsMenuOpen and app._exitDialog is None
    app._executeInputCommand(Command.QUIT)
    assert app.running and app._exitDialog
    app._exitAction('stay')
    pygame.event.clear();pygame.event.post(pygame.event.Event(pygame.QUIT))
    app._handleEvents()
    assert app.running and app._exitDialog
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0))
    app._handleEvents()
    assert not app.running
    app.running=True;app._exitDialog=None


def test_save_and_exit_waits_for_actual_write(app,tmp_path):
    app.workshop.error='';app.currentBuildPath=str(tmp_path/'exit.gz')
    app._requestExit();app._exitAction('save')
    assert app.running and app._pendingSave
    poll_save(app)
    assert not app.running and Path(app.currentBuildPath).is_file()
    app.running=True;app._exitDialog=None


from pathlib import Path

def test_horror_rain_actual_particles_render_and_cleanup(app):
    app.horrorRainEnabled=False;app.rainEnabled=False;app.snowEnabled=False
    for _ in range(3):
        app._toggleHorrorRain()
        assert app.horrorRainEnabled and len(app.horrorRainDrops)==200
        before=app.horrorRainDrops[0]['y']
        app._updateHorrorRain(16)
        assert app.horrorRainDrops[0]['y']!=before
        app._renderHorrorRain()
        app._toggleRain()
        assert app.rainEnabled and not app.horrorRainEnabled
        assert not app.horrorRainDrops and app.horrorRainSoundChannel is None
        app._toggleRain()
    app._toggleHorrorRain();app._switchDimension('nether')
    assert not app.horrorRainEnabled and app.horrorRainSoundChannel is None
    app._switchDimension('overworld')


def test_minimized_tutorial_avoids_hotbar(app):
    for size in ((960,640),(1200,800),(1920,1080)):
        app._applyWindowSize(*size)
        app.workshop.render(app)
        tile=app.tutorialScreen._restoreTileRect()
        assert app.screen.get_rect().contains(tile)
        assert not tile.colliderect(app.workshop.hotbar_bounds)
        assert tile.left==app.workshop.context.right+8
        app.tutorialScreen.visible=True;app.tutorialScreen.minimized=True
        assert app.tutorialScreen.handleEvent(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=tile.center))
        assert not app.tutorialScreen.minimized
        app.tutorialScreen.visible=False


@pytest.mark.parametrize('edit_after_capture',[False,True])
def test_save_completion_updates_retained_map_document(app,tmp_path,edit_after_capture):
    from engine.save_job import write_timed
    future=Future();calls=[]
    if hasattr(app,'_saveExecutor'):app._saveExecutor.shutdown(wait=True)
    app._saveExecutor=SimpleNamespace(submit=lambda *args:(calls.append(args),future)[1])
    app._worldMapSessionSnapshot=None;app.worldMapActive=False
    path=tmp_path/'retained.gz'
    app._saveBuilding(filepath=str(path))
    if edit_after_capture:app.world.setBlock(4,4,2,BlockType.DIAMOND_BLOCK)
    app._captureWorldMapSession();app.worldMapActive=True;app.world.clear();app.currentBuildPath=None
    future.set_result(write_timed(*calls[0][1:]));app._pollSave()
    assert app.currentBuildPath is None
    assert app._worldMapSessionSnapshot['currentBuildPath']==str(path)
    with patch.object(app,'_playMenuMusic'):
        app._exitWorldMap()
    assert app.currentBuildPath==str(path)
    assert (app.workshop.saved_revision==app.world.revision) is (not edit_after_capture)
    del app._saveExecutor


def test_saved_sky_choice_is_honored_without_old_migration_version(app,tmp_path):
    import json
    path=tmp_path/'config.json';path.write_text(json.dumps({'skyboxesEnabled':False}))
    with patch('blocFantome.APP_CONFIG_FILE',str(path)):
        app.skyboxesEnabled=True;app._loadAppConfig()
        assert not app.skyboxesEnabled
    app.skyboxesEnabled=True

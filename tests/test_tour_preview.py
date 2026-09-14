"""Session safety, source fidelity and preview navigation for the demonstration tour."""
import os
import sys
from pathlib import Path
from concurrent.futures import Future
from unittest.mock import patch
import pytest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Code'))
import pygame
from blocFantome import BlocFantome, BlockType
from engine.tutorial_lessons import TOUR


@pytest.fixture(scope='module')
def app():
    app=BlocFantome();assert app.assetManager.loadAllAssets()
    app._generateStructurePreviews()
    app.tutorialScreen.setAssets(app.assetManager.buttonNormal,app.assetManager.buttonHover,
        app.assetManager.checkboxTexture,app.assetManager.checkboxSelectedTexture,app.assetManager.clickSound,app.assetManager)
    app.tutorialScreen.visible=False
    yield app
    app._cancelTourLoad();app.worldLoadExecutor.shutdown(wait=True)
    pygame.display.quit()


def test_late_import_cannot_replace_next_page_or_restored_editor(app):
    original=dict(app.world.blocks)
    app._beginTutorial(advanced=False)
    index=next(i for i,p in enumerate(TOUR) if p['id']=='biomes')
    future=Future();future.set_running_or_notify_cancel()
    with patch.object(app.worldLoadExecutor,'submit',return_value=future):
        app.tutorialScreen.selectLesson(index)
    app.tutorialScreen.selectLesson(0)
    welcome=dict(app.world.blocks)
    from engine.tutorial_scenes import scene_snapshot
    future.set_result(scene_snapshot('mirror'))
    app._pollTourLoad()
    assert dict(app.world.blocks)==welcome
    app.tutorialScreen.hide();app._pollTourLoad()
    assert dict(app.world.blocks)==original


def test_map_excursion_returns_to_same_tutorial_and_original_canvas(app):
    original=dict(app.world.blocks)
    app._beginTutorial(advanced=False)
    index=next(i for i,p in enumerate(TOUR) if p['id']=='worldmap')
    app.tutorialScreen.selectLesson(index)
    assert app.worldMapActive
    demo=dict(app._worldMapSessionSnapshot['world'].blocks)
    assert app.worldMapActive and not app.tutorialScreen.visible
    app._exitWorldMap()
    assert app.tutorialScreen.visible and app.tutorialScreen.currentStep==index
    assert dict(app.world.blocks)==demo
    app.tutorialScreen.hide()
    assert dict(app.world.blocks)==original


def test_city_keeps_every_source_cell_and_four_atlases(app):
    from engine.biome_capture import capture,atlas
    source=capture('_tutorial_end_city')
    snapshot=app._stageBiomeScene('_tutorial_end_city')[0]
    assert len(snapshot.blocks)==len(source['blocks'])
    assert source['structure_bounds']==[-1188,61,-352,-1148,175,-220]
    for x,y,z,palette in source['blocks']:
        prop=snapshot.properties[x,y,z]
        assert prop.sourceCapture=='_tutorial_end_city' and prop.sourcePalette==palette
    assert BlockType.END_ROD in snapshot.blocks.values()
    for view in range(4):assert atlas('_tutorial_end_city',view) is not None


def test_preview_shelves_use_displayed_hitboxes_and_explicit_open(app):
    app.tutorialScreen.visible=False
    app.blocksExpanded=app.experimentalExpanded=False
    browser=app.previewBrowser
    browser.expand(app,'Worlds');app.inventoryScroll=app.inventoryScrollTarget=0
    app._renderPanel()
    before=dict(app.world.blocks)
    hit=next(h for h in browser.hits if h[1]=='item')
    app._handlePanelClick(*hit[0].center)
    assert dict(app.world.blocks)==before
    assert browser.catalog.pending==hit[2]
    app._renderPanel()
    with patch.object(app,'_handleWorldLibraryAction') as opened:
        action=next(h for h in browser.hits if h[1]=='open')
        app._handlePanelClick(*action[0].center)
        opened.assert_called_once_with(('open',hit[2]['value']))
    browser.expand(app,'Structures');app._renderPanel()
    hit=next(h for h in browser.hits if h[1]=='item')
    app._handlePanelClick(*hit[0].center)
    assert app.structurePlacementMode and app.selectedStructure==hit[2]['value']
    assert dict(app.world.blocks)==before
    app.structurePlacementMode=False


def test_every_world_has_a_real_preview_and_catalogs_do_not_mix_tutorials(app):
    from engine.world_catalog import world_catalog
    from runtime_paths import WORLDS_DIR
    for world in world_catalog(WORLDS_DIR):
        entry=dict(key=world.filename,kind='world',value=world)
        preview=app.previewImages.get(app,entry,(360,240))
        assert preview is not None and preview.get_bounding_rect().width>100
    for tab in ('Structures','Saved Builds'):
        app.library.open(app,tab)
        assert all(e['kind']!='build' or e['value'].kind!='tutorial' for e in app.library.entries)
    app.library.visible=False


def test_tutorial_draws_only_three_navigation_buttons_plus_header_and_minimize(app):
    app._beginTutorial(advanced=False)
    with patch.object(app.assetManager,'drawButton',wraps=app.assetManager.drawButton) as draw:
        app.tutorialScreen.render(app.screen)
        labels=[call.args[2] for call in draw.call_args_list]
    assert labels==['TUTORIAL  1 / 16','-','Back','Next','Leave']
    app.tutorialScreen.hide()


def test_tutorial_lab_returns_to_page_and_preserves_original_editor(app):
    original=dict(app.world.blocks)
    app._beginTutorial(advanced=False)
    app.tutorialScreen.currentStep=next(i for i,p in enumerate(TOUR) if p['id']=='redstone')
    step=app.tutorialScreen.lesson
    app._applyTourScene(app._stageTourScene(step),step)
    assert app.redstoneLabActive and app.redstoneLabCircuitKey=='counter'
    assert not app.tutorialScreen.visible
    app._toggleRedstoneLab()
    assert app.tutorialScreen.visible and app.tutorialScreen.lesson['id']=='redstone'
    app.tutorialScreen.hide()
    assert dict(app.world.blocks)==original


def test_persistent_question_mark_and_centered_controls(app):
    app.tutorialScreen.visible=False
    app._renderPanel();app._layoutWindowControls()
    assert app.tutorialTomeRect.right+6==app.settingsGearRect.left
    assert app.tutorialTomeRect.y==app.settingsGearRect.y
    assert app.redstoneLabButtonRect.bottom+6==app.settingsGearRect.top
    left=app.terrainViewButtonRect.left if app.sceneStructurePositions else app.worldMapButtonRect.left
    assert abs((left+app.fitWorldButtonRect.right)/2-app._worldViewportRight()/2)<=1
    with patch.object(app,'_beginTutorial') as opened:
        app._handlePanelClick(*app.tutorialTomeRect.center)
        opened.assert_called_once()


@pytest.mark.parametrize('destination', ['tutorial', 'worldmap', 'redstone'])
def test_tour_excursions_never_save_demo_preferences_or_autosave(app, tmp_path, destination):
    import json
    import blocFantome as module
    original_grid = app.showGrid
    original_sky = app.skyboxesEnabled
    original_hotbar = [block.name for block in app.hotbar]
    app._beginTutorial(advanced=False)
    if destination == 'worldmap':
        app.tutorialScreen.selectLesson(next(i for i, p in enumerate(TOUR) if p['id'] == destination))
    elif destination == 'redstone':
        app._toggleRedstoneLab()
    app.showGrid = not original_grid
    app.skyboxesEnabled = not original_sky
    target = tmp_path / 'preferences.json'
    with patch.object(module, 'APP_CONFIG_FILE', str(target)):
        app._saveAppConfig()
    saved = json.loads(target.read_text())
    assert saved['showGrid'] == original_grid
    assert saved['skyboxesEnabled'] == original_sky
    assert saved['hotbar'] == original_hotbar
    with patch.object(app, 'autoSaveEnabled', True), patch.object(app, 'lastAutoSaveTime', -10**9), patch.object(app, '_saveBuilding') as save:
        app._autoSave()
        save.assert_not_called()
    if app.worldMapActive:
        app._exitWorldMap()
    if app.redstoneLabActive:
        app._toggleRedstoneLab()
    app.tutorialScreen.hide()


def test_hidden_source_water_does_not_intercept_monument_clicks(app):
    from blocFantome import BlockProperties
    props = BlockProperties()
    props.sourceCapture = '_scene_ocean'
    with patch.object(app, 'sceneMetadata', {'water_cutaway': True}), patch.object(app.world, 'getBlockProperties', return_value=props):
        assert app._pickRenderedBlockFace(10, 10, 1, 1, 1, BlockType.WATER) is None

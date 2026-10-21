"""Production actions, layout and gestures, with isolated preferences and saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from unittest.mock import patch
import pygame
import pytest
import blocFantome as b
from ui.fonts import set_text_scale
from ui.workshop import Workshop
from ui.workshop_actions import ACTIONS


@pytest.fixture(scope='module')
def app(tmp_path_factory):
    root=tmp_path_factory.mktemp('workshop-production')
    with patch.object(b,'APP_CONFIG_FILE',str(root/'config.json')),patch.object(b,'SAVES_DIR',str(root)),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'):
        value=b.BlocFantome();value.autoSaveEnabled=False;value.tutorialScreen.visible=False
        assert value.assetManager.loadAllAssets()
        yield value
        value.worldLoadExecutor.shutdown(wait=True,cancel_futures=True)
        set_text_scale(1)


@pytest.fixture(autouse=True)
def reset(app):
    app.workshop=Workshop(categories=b.BLOCK_CATEGORIES);set_text_scale(1)
    app.openingScene=None;app.redstoneLabActive=False;app.worldMapActive=False
    app.settingsMenuOpen=False;app.library.visible=False;app.historyPanelOpen=False
    app.searchActive=False;app.tutorialScreen.visible=False;app.panning=False;app.draggingSlider=None
    app.fillToolActive=False;app.selectionActive=False;app.mirrorModeX=False;app.mirrorModeY=False
    app.blueprintMode=False;app.replaceMode=False;app.magicWandMode=False
    app.measurementMode=False;app.stampMode=False;app.structurePlacementMode=False
    app.layerViewEnabled=False;app.brushSize=1;app.radialSymmetry=0
    app.world.resize(32,32,32,min_y=0,preserve=False);app.undoManager.clear()
    app.currentBuildPath=None;app._applyWindowSize(1200,800)
    app.favoriteBlocks=[];app.recentBlocks=[];app.selectedBlock=b.BlockType.STONE
    yield
    set_text_scale(1)


def test_full_catalog_search_categories_and_favorites(app):
    shell=app.workshop
    visible=set(app.world.catalog.definitions)-{b.BlockType.AIR}
    assert set(shell.filtered_blocks(app))==visible
    shell.query='oxidized copper';found=shell.filtered_blocks(app)
    assert found and all('oxidized' in block.name.lower() and 'copper' in block.name.lower() for block in found)
    shell.query='';shell.category='Favorites';assert not shell.filtered_blocks(app)
    app.favoriteBlocks=[b.BlockType.DIAMOND_BLOCK]
    assert shell.filtered_blocks(app)==[b.BlockType.DIAMOND_BLOCK]
    for name,blocks in b.BLOCK_CATEGORIES.items():
        shell.category=name
        assert set(shell.filtered_blocks(app))==visible.intersection(blocks)


def test_copy_and_radial_use_real_handlers_without_clear_or_tree(app):
    app.world.setBlock(2,3,1,b.BlockType.DIAMOND_BLOCK)
    app.selectionActive=True;app.selectionStart=(2,3,1);app.selectionEnd=(2,3,1)
    app.selectedBlocks={(2,3,1)}
    original=dict(app.world.blocks)
    app.workshop.act('copy',app)
    assert app.clipboard and app.world.blocks==original
    app.workshop.act('radial',app)
    assert app.radialSymmetry==4 and not app.structurePlacementMode
    app.workshop.act('radial',app);assert app.radialSymmetry==8
    app.workshop.act('radial',app);assert app.radialSymmetry==0


def test_fill_mirror_half_and_undo_reach_original_state(app):
    app.workshop.act('fill',app);assert app.fillToolActive
    app.workshop.act('mirror_x',app);assert app.mirrorModeX
    app.workshop.act('mirror_y',app);assert app.mirrorModeY
    half=app.previewSlabPosition;app.workshop.act('half',app);assert app.previewSlabPosition!=half
    app.mirrorModeX=False;app.mirrorModeY=False
    app._placeBlockWithUndo(2,3,1,b.BlockType.STONE)
    app.workshop.act('undo',app);assert app.world.getBlock(2,3,1)==b.BlockType.AIR
    app.workshop.act('redo',app);assert app.world.getBlock(2,3,1)==b.BlockType.STONE


def test_every_method_destination_exists(app):
    for action,label,route,args,field in ACTIONS.values():
        if route=='method':assert callable(getattr(app,args[0],None)),action
        if field:assert hasattr(app,field),action


def test_drag_assigns_hotbar_then_consumes_release(app):
    shell=app.workshop;shell.render(app)
    source=shell.hotbar_rects[0].center;target=shell.hotbar_rects[3].center
    block=app.hotbar[0]
    assert shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=source),app)
    assert shell.handle_event(pygame.event.Event(pygame.MOUSEMOTION,pos=target,rel=(30,0),buttons=(1,0,0)),app)
    assert shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=target),app)
    assert app.hotbar[3]==block and not shell.captured


def test_hidden_hotbar_has_no_hits_and_outside_mouse_does_not_reveal(app):
    shell=app.workshop;shell.visibility.last_activity=-100;shell.last_time=-100
    with patch('pygame.mouse.get_pos',return_value=(11,819)),patch('pygame.mouse.get_pressed',return_value=(False,False,False)):
        shell.render(app)
    assert shell.visibility.alpha==0
    assert not shell.hotbar_rects and not any(action.startswith('slot:') for _,action,_ in shell.hits)
    assert not shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(600,770)),app)


@pytest.mark.parametrize('size',[(960,640),(1200,800),(1920,1080)])
@pytest.mark.parametrize('scale',[1,1.25,1.5])
def test_settings_controls_and_drawer_hits_stay_inside_native_canvas(app,size,scale):
    app._applyWindowSize(*size);set_text_scale(scale);app.workshop.text_scale=scale
    bounds=app.screen.get_rect()
    box,sliders,controls=app._settingsLayout()
    assert bounds.contains(box)
    assert all(box.contains(rect) for _,rect in sliders)
    assert all(box.contains(rect) for _,_,rect in controls)
    app.workshop.page='build';app.workshop.render(app)
    assert all(bounds.contains(rect) for rect,_,_ in app.workshop.hits)
    assert all(app.workshop.list_rect.contains(rect) for rect,action,_ in app.workshop.hits if action.startswith('block:'))


def test_modern_resize_preserves_center_world_anchor(app):
    app.renderer.offsetX=412;app.renderer.offsetY=287
    before=app.renderer.screenToWorld(600,400,0)
    app._applyWindowSize(1920,1080)
    after=app.renderer.screenToWorld(960,540,0)
    assert after==pytest.approx(before)
    assert app._worldViewportRight()==1920


def test_textinput_commits_unicode_once_and_retains_editing_keys(app):
    shell=app.workshop;shell.page='build';app.searchActive=True
    shell.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e,mod=0,unicode='é'),app)
    assert shell.query==''
    assert shell.handle_event(pygame.event.Event(pygame.TEXTINPUT,text='é'),app)
    assert shell.query=='é'
    shell.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_BACKSPACE,mod=0),app)
    assert shell.query==''


def test_fullscreen_requests_desktop_instead_of_window_resolution(app):
    app.fullscreen=False
    with patch('pygame.display.get_desktop_sizes',return_value=[(1920,1080)]),patch.object(app,'_applyWindowSize') as resize:
        app._toggleFullscreen();resize.assert_called_once_with(1920,1080)
        assert app.windowedSize==(1200,800)
        app._toggleFullscreen();assert resize.call_args.args==(1200,800)


def test_fullscreen_round_trip_does_not_reduce_zoom_on_each_visit(app):
    app.zoomLevel=1.234;app.renderer.setZoom(app.zoomLevel)
    app.renderer.offsetX=412;app.renderer.offsetY=287
    before=app.renderer._screenToWorldPoint(600,400,app.cameraFocusZ)
    with patch('pygame.display.get_desktop_sizes',return_value=[(1920,1080)]):
        for _ in range(3):app._toggleFullscreen();app._toggleFullscreen()
    assert app.zoomLevel==pytest.approx(1.234,abs=.001)
    assert app.renderer._screenToWorldPoint(600,400,app.cameraFocusZ)==pytest.approx(before,abs=.03)


def test_clear_confirmation_owns_keyboard_and_escape_keeps_build(app):
    app.world.setBlock(3,3,1,b.BlockType.DIAMOND_BLOCK)
    app.workshop.act('clear_world',app)
    assert app.workshop.confirm and app.workshop.focus=='confirm:cancel'
    assert app.workshop.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_c,mod=0),app)
    assert app.world.getBlock(3,3,1)==b.BlockType.DIAMOND_BLOCK
    app.workshop.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0),app)
    assert app.workshop.confirm is None and app.world.getBlock(3,3,1)==b.BlockType.DIAMOND_BLOCK


def test_combined_modes_reflow_above_drawer_at_large_text(app):
    app._applyWindowSize(960,640);set_text_scale(1.5);app.workshop.text_scale=1.5
    for field in ('fillToolActive','selectionActive','mirrorModeX','mirrorModeY','replaceMode','measurementMode','stampMode','blueprintMode','magicWandMode'):
        setattr(app,field,True)
    app.workshop.page='tools';app.workshop.render(app)
    assert app.workshop.operation_rect.height>42
    assert app.workshop.list_rect.top>app.workshop.operation_rect.bottom
    assert app.workshop.list_rect.height>0
    assert all(app.screen.get_rect().contains(rect) for rect,_,_ in app.workshop.hits)

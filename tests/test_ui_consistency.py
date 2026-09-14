"""Regression checks for shared chrome, navigation, input and captured scenes."""
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
from ui.chrome import button_surface
from ui.biomes import BIOME_FAMILIES, CURATED_IDS
from engine.biome_catalog import BY_ID


@pytest.fixture(scope='module')
def app():
    instance=BlocFantome()
    assert instance.assetManager.loadAllAssets()
    instance.tutorialScreen.visible=False
    yield instance
    instance.worldLoadExecutor.shutdown(wait=True)
    pygame.display.quit()


def test_button_edges_survive_small_and_square_sizes():
    pygame.init()
    source=pygame.Surface((200,20))
    source.fill((90,90,90));pygame.draw.rect(source,(255,255,255),source.get_rect(),2)
    for size in ((28,28),(96,27),(235,35)):
        result=button_surface(source,size)
        for pos in ((0,0),(size[0]-1,0),(0,size[1]-1),(size[0]-1,size[1]-1)):
            assert result.get_at(pos)[:3]==(255,255,255)
        assert result.get_at((size[0]//2,size[1]//2))[:3]==(90,90,90)


def test_curated_roster_retains_distinct_families_and_source_catalog():
    assert len(CURATED_IDS)==len(set(CURATED_IDS))<len(BY_ID)
    assert all(1<=len(names)<=2 for names in BIOME_FAMILIES.values())
    assert all(name in BY_ID for name in CURATED_IDS)
    assert 'the_void' in BY_ID and 'the_void' not in CURATED_IDS


def test_capture_is_settled_and_actual_keyboard_events_rotate_without_losing_scene(app):
    app._openBiomeScene('plains')
    assert not app.world.waterUpdateQueue
    assert not app.world.lavaUpdateQueue
    app.hoveredSourceBlock=None
    app._render()
    original=app.renderer.viewRotation
    for _ in range(4):
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e,unicode='e',mod=0))
        app._handleEvents()
        import time
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            app._render()
            if app._worldSurfaceBuild is None:break
        assert app.renderStats['drawn']>100
        assert app._worldSurfaceBuild is None
    assert app.renderer.viewRotation==original
    # An edit still enters ordinary liquid simulation.
    app.world.setBlock(2,2,app.world.height-2,BlockType.WATER)
    assert app.world.waterUpdateQueue


def test_cancelled_biome_future_does_not_replace_live_build(app):
    before=dict(app.world.blocks)
    future=Future()
    app.pendingBiomeLoad=(future,'plains')
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,unicode='',mod=0))
    app._handleEvents()
    assert app.pendingBiomeLoad is None
    app._pollBiomeLoad()
    assert dict(app.world.blocks)==before


def test_library_close_and_blank_clicks_do_not_edit_canvas(app):
    app.library.open(app,'Structures');app.library.render(app)
    before=dict(app.world.blocks)
    with patch.object(app.assetManager,'playClickSound') as click:
        event=pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(2,2))
        assert app.library.handle_event(event,app)
        click.assert_not_called()
    assert dict(app.world.blocks)==before
    app.library.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE),app)
    assert not app.library.visible


def test_settings_slider_and_mute_use_displayed_hitboxes(app):
    app.settingsMenuOpen=True
    app._render()
    control=app.volumeControlRects['effects']
    app._handleSettingsClick(control['track'].left,control['track'].centery)
    assert app.effectsVolume==0
    app._handleSettingsClick(control['track'].right-1,control['track'].centery)
    assert app.effectsVolume>0.99
    app._handleSettingsClick(*control['mute'].center)
    assert app.effectsMuted
    assert app.assetManager.audioRouter._group_volume['ui']==0
    app.effectsMuted=False;app._setVolume('effects',0.8)
    app.settingsMenuOpen=False


def test_tutorial_blank_panel_click_is_silent(app):
    guide=app.tutorialScreen
    guide.visible=True;guide.minimized=False
    guide.render(app.screen)
    with patch.object(guide,'_playClickSound') as click:
        guide.handleEvent(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(guide.panelX+8,guide.panelY+guide.panelHeight-10)))
        click.assert_not_called()
    guide.visible=False


def test_invisible_expensive_animations_are_skipped_and_resume_on_demand(app):
    assets=app.assetManager
    assets._animationDemand=set()
    with patch.object(assets,'_createMatrixBlock',return_value=pygame.Surface((64,70))) as matrix:
        assets.updateAnimation(200)
        matrix.assert_not_called()
        assets._animationDemand={BlockType.MATRIX}
        assets.updateAnimation(200)
        matrix.assert_called_once()
    assets._animationDemand=None


def test_queued_capture_prepares_four_views_then_releases_input(app):
    import time
    app._queueBiomeScene('small_end_islands')
    deadline=time.monotonic()+15
    while app.pendingBiomeLoad is not None and time.monotonic()<deadline:
        app._update();app._render()
        time.sleep(0.005)
    assert app.pendingBiomeLoad is None
    assert app.pendingBiomeWarmup is None
    assert len(app._biomeViewSurfaces)==4
    assert app.renderStats['drawn']>0

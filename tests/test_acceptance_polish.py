"""Final Pass B lifecycle, input and native-size layout regressions."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pygame
import pytest
from test_workshop_production import app, reset
from ui import chrome, feedback
from ui.fonts import set_text_scale
from ui.lifecycle import GoodbyeScreen, cover_rect, jump_height, FAREWELLS
from ui.motion import Opacity


def test_jump_is_ordered_settled_and_seamless():
    for index in range(3):
        t=index*.9+.32
        assert jump_height(t,index)==13
        assert all(jump_height(t,j)==0 for j in range(3) if j!=index)
        assert jump_height(index*.9+.8,index)==0
    for t in (0,2.7,5.4):assert all(abs(jump_height(t,i))<1e-9 for i in range(3))
    for i in range(3):
        for t in (.28,.38,.64,.76):
            assert abs(jump_height(i*.9+t-1e-6,i)-jump_height(i*.9+t+1e-6,i))<.001


@pytest.mark.parametrize('size',[(960,640),(1200,800),(1920,1080),(800,960),(2560,1080)])
def test_night_cover_protects_moon_and_figures(size):
    crop=cover_rect((2560,1419),size)
    assert crop.contains(pygame.Rect((0,0),size))
    assert abs(crop.width/crop.height-2560/1419)<.003
    for x,y in ((.59,.15),(.65,.24),(.665,.63),(.78,.805)):
        assert pygame.Rect((0,0),size).collidepoint(crop.x+x*crop.width,crop.y+y*crop.height)


def test_old_tutorial_preferences_cannot_autolaunch(app,tmp_path):
    import runtime_paths
    path=tmp_path/'.tutorial_config.json'
    original=json.dumps({'showOnStartup':True,'guidedVersion':2})
    path.write_text(original)
    with patch.object(runtime_paths,'BASE_DIR',str(tmp_path)):
        app.tutorialScreen._loadConfig()
    assert not app.tutorialScreen.showOnStartup
    assert not app.tutorialScreen.shouldShowOnStartup()
    assert path.read_text()==original


def test_boot_preload_does_not_decode_other_cues(app):
    assets=SimpleNamespace()
    with patch.object(pygame.mixer,'Sound',return_value=object()) as decode:
        feedback.preload(assets,('boot',))
        feedback.preload(assets,('boot',))
    assert decode.call_count==1 and set(assets._selected_cues)=={'boot'}


def test_opacity_uses_elapsed_time_and_reverses_without_jump():
    a=Opacity();b=Opacity();a.last=b.last=0
    for t in (.01,.02,.04,.11,.2):a.update(True,t)
    b.update(True,.2)
    assert a.value==pytest.approx(b.value)
    before=a.value
    assert a.update(False,.2)==before
    middle=a.update(False,.23)
    assert 0<middle<before
    assert a.update(True,.23)==middle
    assert a.update(True,.25)>middle
    assert a.update(False,.25,True)==0


@pytest.mark.parametrize('size',[(960,640),(1200,800),(1920,1080)])
@pytest.mark.parametrize('scale',[1,1.25,1.5])
def test_tutorial_footer_and_manual_dock_fit(app,size,scale):
    set_text_scale(scale);app.workshop.text_scale=scale;app._applyWindowSize(*size)
    app.workshop.render(app)
    tile=app.tutorialScreen._restoreTileRect()
    assert not tile.colliderect(app.workshop.hotbar_bounds)
    tutorial=app.tutorialScreen;tutorial.visible=True;tutorial.minimized=False
    tutorial.render(app.screen)
    bottom=tutorial.backButtonRect.bottom+10+tutorial.smallFont.get_height()
    assert bottom<=tutorial.panelY+tutorial.panelHeight-6
    tutorial.visible=False
    app.workshop.render(app)
    rect=next(r for r,a,e in app.workshop.hits if a=='tutorial')
    with patch.object(app,'_beginTutorial') as begin:
        app.workshop.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center),app)
        begin.assert_called_once()


def test_exit_clears_startup_art_and_resize_refreshes_snapshot(app):
    app._startupOverlay=pygame.Surface(app.screen.get_size());app._startupOverlay.fill((255,0,255))
    app._startupRevealStarted=None;app._requestExit()
    assert app._startupOverlay is None
    assert app._exitDialog.background.get_at((0,0))[:3]!=(255,0,255)
    app._applyWindowSize(960,640);app._render()
    assert app._exitDialog.background.get_size()==(960,640)
    app._exitAction('stay')


def test_goodbye_overwrites_stale_clip_and_has_no_per_frame_transforms(app):
    screen=pygame.Surface((960,640));screen.fill((255,0,255))
    screen.set_clip((100,100,100,100));view=GoodbyeScreen(screen,True)
    view.render(800)
    assert screen.get_clip()==screen.get_rect()
    assert screen.get_at((0,0))[:3]!=(255,0,255)
    before=pygame.image.tobytes(screen,'RGB')
    with patch.object(pygame.transform,'smoothscale',side_effect=AssertionError('frame transform')):
        view.render(1500)
    assert pygame.image.tobytes(screen,'RGB')==before
    assert len(FAREWELLS)==8


def test_shared_outline_is_continuous_and_transparent_inside(app):
    layer=chrome._outline((100,50),(173,203,235),7,1)
    assert layer.get_at((50,0)).a==255
    assert layer.get_at((0,25)).a==255
    assert layer.get_at((50,49)).a==255
    assert layer.get_at((99,25)).a==255
    assert layer.get_at((50,25)).a==0
    assert chrome._rounded_bytes<=12*1024*1024


def test_rapid_close_and_library_reversal_clear_old_actions(app):
    app.workshop.open_drawer('menu',app);app.workshop.render(app)
    assert app.workshop.menu_hits
    app.workshop.close_drawer(app)
    assert not app.workshop.menu_hits
    assert not any(a.startswith('menu_group:') for r,a,e in app.workshop.hits)
    app.library.open(app);app.library.render(app)
    assert app.library.tab_rects
    app.library.change_view(app,'Worlds')
    assert not app.library.tab_rects and not app.library.rows
    assert app.library.open_rect.width==0


def test_enlarged_cube_is_cached_and_normal_view_unchanged(app):
    from engine import native_cube
    import blocFantome as module
    sprite=app.assetManager.getBlockSprite(module.BlockType.GRASS)
    assert app.assetManager.getScaledSprite(sprite,1) is sprite
    app.assetManager.clearZoomCache()
    first=app.assetManager.getScaledSprite(sprite,2)
    assert first.get_size()==(128,140)
    assert pygame.image.tobytes(first,'RGBA')!=pygame.image.tobytes(pygame.transform.scale(sprite,(128,140)),'RGBA')
    with patch.object(native_cube,'enlarged',side_effect=AssertionError('uncached reproject')):
        assert app.assetManager.getScaledSprite(sprite,2) is first

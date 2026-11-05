"""Owner-requested direct galleries, quiet controls and release identity."""
from unittest.mock import patch
from types import SimpleNamespace
import pygame
import pytest
from test_workshop_production import app, reset
from ui.fonts import set_text_scale


def test_toolbar_save_help_and_canvas_order(app):
    shell=app.workshop;shell.render(app)
    hits={a:r for r,a,e in shell.hits if e}
    assert 'save' not in hits
    assert hits['tutorial'].colliderect(hits['settings'])
    assert [a for r,a in shell.canvas_controls(app.screen.get_size())]==['shrink','grow','noise']
    shell.page='menu';shell.render(app)
    assert any(a=='save' for r,a,e in shell.hits)


def test_closing_chrome_close_does_not_reopen_save_dialog(app):
    from ui.window_chrome import WindowChrome
    chrome=WindowChrome();chrome.enabled=True;chrome.width=1200
    pos=chrome.rects()[2].center
    with patch.object(app,'_requestExit') as request:
        for kind in (pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP):
            assert chrome.handle(pygame.event.Event(kind,button=1,pos=pos),app,closing=True)
        assert app._closingSkipRequested
        request.assert_not_called()


def test_world_tile_has_continuous_top_edge():
    from ui.world_material import material
    surface=pygame.Surface((100,100),pygame.SRCALPHA)
    material(surface,pygame.Rect(0,0,100,100),(113,176,229),1)
    assert surface.get_at((50,1))==surface.get_at((50,30))


def test_visible_saved_previews_finish_without_restarting_each_other(tmp_path):
    from concurrent.futures import Future
    from itertools import count
    from ui.preview_browser import PreviewImages
    pygame.init();cache=PreviewImages();requests=[]
    def submit(*args):
        requests.append(args)
        future=Future();future.set_result(([(i,0,0,1) for i in range(40)],.2,(30,30)))
        return future
    fake=SimpleNamespace(worldLoadExecutor=SimpleNamespace(submit=submit),
        assetManager=SimpleNamespace(getBlockSprite=lambda block:pygame.Surface((64,64))))
    entries=[dict(kind='build',key=str(i),value=SimpleNamespace(path=str(tmp_path/f'{i}.json'))) for i in range(2)]
    ticks=count()
    with patch('ui.preview_browser.time.perf_counter',side_effect=lambda:next(ticks)*.001):
        for frame in range(150):
            results=[cache.get(fake,e) for e in entries]
            if all(result is not None for result in results):break
        else:pytest.fail('Visible gallery previews starved one another')
    assert len(requests)==2 and not cache.jobs


@pytest.mark.parametrize('page',['build','world','tools','menu'])
def test_repeated_menu_button_closes(app,page):
    app.workshop.page=''
    app.workshop.act('nav:'+page,app)
    assert app.workshop.page==page
    app.workshop.act('nav:'+page,app)
    assert app.workshop.page==''


def test_tutorial_restores_previous_panel_and_world(app):
    app.workshop.page='world'
    blocks=dict(app.world.blocks)
    app._beginTutorial(advanced=False)
    app.tutorialScreen.hide()
    assert app.world.blocks==blocks
    assert app.workshop.page=='world'
    assert app._tutorialSessionSnapshot is None


def test_major_panels_have_transparent_rounded_corners():
    from ui.chrome import panel
    surface=pygame.Surface((100,100),pygame.SRCALPHA)
    panel(surface,surface.get_rect(),major=True)
    assert surface.get_at((0,0)).a==0
    assert surface.get_at((50,50)).a>200


def test_world_drawer_keeps_rounded_corners(app):
    app.workshop.page='world'
    app.workshop.render(app)
    bounds=app.workshop._drawer_bounds
    assert app.workshop._drawer_layer.get_at(bounds.topleft).a==0

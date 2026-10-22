"""Owner's final 2.9.9 interaction requirements."""
from unittest.mock import patch
import pygame
from test_workshop_production import app, reset


def test_library_navigation_toggles_through_modal(app):
    shell=app.workshop;shell.render(app);shell.act('nav:library',app)
    shell.render(app);app.library.render(app)
    rect=next(r for r,a,_ in shell.hits if a=='nav:library')
    app.library.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center),app)
    assert not app.library.visible


def test_child_gallery_has_two_columns_and_back_only(app):
    library=app.library;library.open(app,'Worlds');library.render(app)
    assert library.columns==2 and library.close_rect.width==0
    assert len({r.x for r in library.dimension_rects.values()})==1
    assert library.back_rect.width>0


def test_first_save_asks_and_cancel_does_not_write(app):
    with patch.object(app,'_openSaveAsDialog',return_value=None) as dialog, patch.object(app,'_saveBuilding') as save:
        app.workshop.act('save',app)
        dialog.assert_called_once();save.assert_not_called()
        assert not app.workshop.error and not app.workshop.status
    app.currentBuildPath='named.json.gz'
    with patch.object(app,'_saveBuilding',return_value=True) as save,patch.object(app,'_openSaveAsDialog') as dialog:
        app.workshop.act('save',app)
        save.assert_called_once();dialog.assert_not_called()


def test_world_controls_remain_open(app):
    for action,method in (('horror_rain','_toggleHorrorRain'),('overworld','_switchDimension'),('nether','_switchDimension'),('end','_switchDimension')):
        app.workshop.page='world'
        with patch.object(app,method):app.workshop.act(action,app)
        assert app.workshop.page=='world'


def test_keyboard_first_save_and_cancel_preserve_unnamed_world(app):
    before=dict(app.world.blocks)
    with patch.object(app,'_openSaveAsDialog',return_value=None) as dialog:
        app._handleKeyDown(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_s,mod=pygame.KMOD_CTRL,unicode=''))
        dialog.assert_called_once()
    assert app.currentBuildPath is None and app.world.blocks==before


def test_map_initial_framing_covers_projected_diamond():
    from types import SimpleNamespace
    from ui.source_map import SourceMap
    renderer=SimpleNamespace(zoomLevel=0,setZoom=lambda z:setattr(renderer,'zoomLevel',z))
    source=SimpleNamespace(projected_bounds=(-3000,-1500,3000,1500))
    SourceMap.frame_overview(source,renderer,(1200,800))
    for x,y in ((0,0),(1200,0),(0,800),(1200,800)):
        assert abs((x-renderer.offsetX)/renderer.zoomLevel)/3000+abs((y-renderer.offsetY)/renderer.zoomLevel)/1500<1


def test_expanding_gallery_clips_art_and_hits_to_animated_panel(app):
    library=app.library;library.open(app);library.render(app)
    library.change_view(app,'Worlds')
    for elapsed in (0,30,90,180):
        app.screen.fill((0,0,0))
        with patch('pygame.time.get_ticks',return_value=library._morph_at+elapsed):library.render(app)
        assert all(library.rect.contains(r) for r in library.dimension_rects.values())
        assert app.screen.get_clip()==app.screen.get_rect()
        # Allow the shared panel's subtle shadow, but no gallery art beyond it.
        mask=pygame.mask.from_threshold(app.screen,(0,0,0),(1,1,1,255))
        mask.invert()
        assert all(library.rect.inflate(16,16).contains(r) for r in mask.get_bounding_rects())

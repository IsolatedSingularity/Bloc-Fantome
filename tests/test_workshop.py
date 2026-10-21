import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from types import SimpleNamespace
from concurrent.futures import Future
import pygame
import pytest
from ui.workshop import Visibility,Workshop
from ui.preview_browser import PreviewImages,PreviewBrowser


def test_context_fade_is_time_based_and_occupied_controls_never_hide():
    v=Visibility()
    assert v.update(3.9,.016)==1
    assert v.update(4.1,.09)==pytest.approx(.5)
    assert v.update(4.2,.09)==0
    assert v.update(4.3,.18,occupied=True)==1
    v.pinned=True;assert v.update(99,.2)==1
    v.pinned=False;v.reduced_motion=True;assert v.update(100,.001)==0


def test_ui_press_consumes_release_after_fade_without_world_edit():
    pygame.init();shell=Workshop();shell.hits=[(pygame.Rect(5,5,100,30),'reveal',True)]
    app=SimpleNamespace(openingScene=None,worldMapActive=False,redstoneLabActive=False,tutorialScreen=SimpleNamespace(visible=False))
    assert shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(10,10)),app)
    shell.hits=[];shell.visibility.alpha=0
    assert shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=(400,400)),app)
    assert not shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(10,10)),app)


def test_save_failure_stays_visible_and_has_no_saved_revision():
    pygame.init();shell=Workshop();shell.act('save',SimpleNamespace(_saveBuilding=lambda:False))
    assert shell.error and shell.saved_revision is None and not shell.status


def test_blank_chrome_consumes_whole_gesture():
    pygame.init();shell=Workshop();shell.panels=[pygame.Rect(12,12,500,53)]
    app=SimpleNamespace(openingScene=None,worldMapActive=False,redstoneLabActive=False,tutorialScreen=SimpleNamespace(visible=False))
    assert shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(400,30)),app)
    assert shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=(400,300)),app)


def test_ui_navigation_preserves_minimap_and_original_hud_route():
    pygame.init();shell=Workshop();shell.hits=[(pygame.Rect(0,0,60,30),'menu',True)]
    app=SimpleNamespace(workshop=shell,openingScene=None,worldMapActive=False,redstoneLabActive=False,tutorialScreen=SimpleNamespace(visible=False))
    assert not shell.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB,mod=0),app)
    assert shell.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB,mod=pygame.KMOD_CTRL),app)
    assert shell.focus=='menu'
    shell.act('legacy',app);assert not shell.active(app)
    assert shell.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB,mod=pygame.KMOD_CTRL),app)
    assert shell.active(app)


def test_search_retains_keyboard_ownership_after_shell_focus():
    pygame.init();shell=Workshop();shell.focus='save'
    app=SimpleNamespace(workshop=shell,openingScene=None,worldMapActive=False,redstoneLabActive=False,
                        tutorialScreen=SimpleNamespace(visible=False),searchActive=True)
    assert not shell.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,mod=0),app)
    assert shell.focus is None


def test_leaving_partial_preview_cannot_starve_new_selection(tmp_path):
    pygame.init();cache=PreviewImages()
    cache.jobs[('build','old')]=[iter([(0,0,0,1)]),pygame.Surface((600,400)),1,(0,0),{}]
    ready=Future();ready.set_result(([(0,0,0,1)],1,(300,200)))
    app=SimpleNamespace(worldLoadExecutor=SimpleNamespace(submit=lambda *args:ready),
        assetManager=SimpleNamespace(getBlockSprite=lambda block:pygame.Surface((64,64))))
    entry=dict(kind='build',key='new',value=SimpleNamespace(path=str(tmp_path/'new.json')))
    assert cache.get(app,entry) is not None
    assert not cache.jobs


def test_preview_cache_is_byte_bounded_and_content_namespaced(tmp_path):
    pygame.init();cache=PreviewImages(1000)
    for i in range(10):cache._retain(i,pygame.Surface((10,10),pygame.SRCALPHA))
    assert cache.retained_bytes<=1000 and len(cache.images)==2
    cache._retain('too-large',pygame.Surface((100,100)))
    assert cache.retained_bytes<=1000 and 'too-large' not in cache.images
    path=tmp_path/'build.json';path.write_text('one')
    entry=dict(kind='build',key='same',value=SimpleNamespace(path=str(path)))
    before=cache._identity(entry);path.write_text('changed')
    assert cache._identity(entry)!=before
    assert cache._identity(dict(kind='structure',key='same',value='same'))!=before


def test_preview_bounds_prepared_without_display_work():
    cells={(0,0,0):1,(1,0,0):1,(0,0,1):2}
    rows,scale,offset=PreviewImages._stage(SimpleNamespace(_readBuildFile=lambda p:(None,None,None,SimpleNamespace(blocks=cells))),'unused')
    left=min((x-y)*32 for x,y,z,b in rows)-32;right=max((x-y)*32 for x,y,z,b in rows)+32
    top=min((x+y)*16-z*32 for x,y,z,b in rows);bottom=max((x+y)*16-z*32 for x,y,z,b in rows)+64
    assert scale==min(580/(right-left),380/(bottom-top))
    assert offset==((600-(right-left)*scale)/2-left*scale,(400-(bottom-top)*scale)/2-top*scale)


def test_shelf_selection_previews_before_explicit_placement():
    pygame.init();browser=PreviewBrowser()
    entry=dict(kind='structure',key='house',value='house')
    browser.hits=[(pygame.Rect(0,0,100,100),'item',entry)]
    calls=[];browser.catalog.activate=lambda app:calls.append('activate')
    app=SimpleNamespace(assetManager=SimpleNamespace(playClickSound=lambda:None))
    assert browser.click(app,(20,20)) and browser.catalog.pending is entry and not calls

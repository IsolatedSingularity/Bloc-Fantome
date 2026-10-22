"""Focused UI/audio/lifecycle contracts; no cinematic content or benchmarks."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pygame
import pytest
from test_workshop_production import app, reset
from ui import feedback
from ui.command_palette import GROUPS
from ui.workshop_actions import MENU
from ui.exit_dialog import ExitDialog
from ui.lifecycle import GoodbyeScreen
from ui.refined_icons import frames


def test_palette_retains_commands_and_compacts_default(app):
    represented={'save','open','settings',*(a for group in GROUPS.values() for a in group)}
    assert {r[0] for r in MENU if not r[0].startswith('quick_')} <= represented
    app.workshop.page='menu';app.workshop.render(app)
    assert app.workshop.panels[-1].height<300
    assert not any(action.startswith('quick_') for _,action,_ in app.workshop.hits)
    app.workshop.act('menu_slots',app);app.workshop.render(app)
    assert len([a for _,a,_ in app.workshop.hits if a.startswith('quick_')])==8
    event=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0)
    app.workshop.handle_event(event,app)
    assert app.workshop.page=='menu' and not app.workshop.menu_slots
    app.workshop.handle_event(event,app);assert app.workshop.page==''


def test_palette_keyboard_groups_focus_and_mouse_routing(app):
    app.workshop.page='menu';app.workshop.render(app)
    app.workshop.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT,mod=0),app)
    assert app.workshop.menu_group=='Edit'
    app.workshop.render(app)
    app.workshop.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_DOWN,mod=0),app)
    assert app.workshop.focus is not None
    target=next(r for r,a,e in app.workshop.menu_hits if a=='menu_group:View')
    app.workshop.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=target.center),app)
    assert app.workshop.menu_group=='View'


def test_palette_preserves_visible_operation_status(app):
    app.workshop.page='menu';app.workshop.error='Save failed: destination unavailable'
    try:
        app.workshop.render(app)
        assert app.workshop.panels[-1].top>=app.workshop.operation_rect.bottom+8
    finally:app.workshop.error=''


def test_library_open_close_one_short_cue(app):
    for action in ('nav:library','nav:library'):
        app.assetManager._feedback_last={}
        with patch.object(app.assetManager.audioRouter,'play') as play:
            app.workshop.act(action,app)
            assert play.call_count==1
            assert play.call_args.args[0] is feedback.preload(app.assetManager)['close']
    assert not app.library.visible
    assert feedback.preload(app.assetManager)['close'].get_length()==pytest.approx(.4,abs=.001)


def test_derivative_provenance_and_natural_tail():
    import wave
    import numpy as np
    p=feedback.sound_path('close-short.wav');record=json.loads(p.with_suffix('.json').read_text())
    original=feedback.sound_path('close.wav')
    assert hashlib.sha256(original.read_bytes()).hexdigest()==record['source_sha256']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256']
    with wave.open(str(p)) as f:a=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2')
    assert a[-1]==0 and a[-2]==0 and abs(a).max()<32767


def test_exit_defaults_stay_escape_cancels_and_explicit_exit_confirms(app):
    app.running=True;app._requestExit();dialog=app._exitDialog
    assert dialog.focus=='stay'
    action=dialog.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
    assert action=='stay';app._exitAction(action)
    assert app.running and app._exitDialog is None
    app._requestExit();app._exitDialog.render(app.screen)
    action=app._exitDialog.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=app._exitDialog.rects['exit'].center))
    assert action=='exit';app._exitAction(action);assert not app.running
    app.running=True;app._exitDialog=None


def test_goodbye_skip_and_reduced_motion():
    assert GoodbyeScreen.skip_requested([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE)])
    assert GoodbyeScreen.skip_requested([pygame.event.Event(pygame.QUIT)])
    assert not GoodbyeScreen.skip_requested([pygame.event.Event(pygame.MOUSEMOTION)])
    screen=pygame.Surface((960,640));view=GoodbyeScreen(screen,True)
    view.render(200);before=pygame.image.tobytes(screen,'RGB')
    view.render(1200);assert pygame.image.tobytes(screen,'RGB')==before


@pytest.mark.parametrize('size',(24,38,64))
def test_dimension_recognition_buffers_are_shared_and_motion_cached(size):
    from ui.refined_icons import draw
    from ui import tool_icons, generated_icons
    for name in ('overworld','end'):
        a=pygame.Surface((size,size),pygame.SRCALPHA);b=a.copy()
        tool_icons.draw(a,name,a.get_rect(),(255,255,255))
        generated_icons.draw(b,name,b.get_rect())
        assert pygame.image.tobytes(a,'RGBA')==pygame.image.tobytes(b,'RGBA')
        library=frames('dimension_'+name,(size,size))[0]
        assert pygame.image.tobytes(library,'RGBA')!=pygame.image.tobytes(a,'RGBA')
        assert library.get_bounding_rect().width>size*.6
        rgb=pygame.surfarray.array3d(library);alpha=pygame.surfarray.array_alpha(library)
        visible=rgb[alpha>0]
        # SDL smoothscale can round white down by two levels, as on existing masks.
        assert (visible[:,0]==visible[:,1]).all() and (visible[:,1]==visible[:,2]).all()
        assert visible.min()>=250
    for name in ('lighting','clouds'):
        sequence=frames(name,(size,size));assert frames(name,(size,size)) is sequence
        assert pygame.image.tobytes(sequence[0],'RGBA')!=pygame.image.tobytes(sequence[8],'RGBA')


def test_vsync_unavailable_is_not_a_fake_preference(app):
    app.settingsMenuOpen=True
    _,_,controls=app._settingsLayout()
    rect=next(rect for _,attr,rect in controls if attr=='vsync_unavailable')
    with patch.object(app.assetManager,'playClickSound') as sound:
        app._handleSettingsClick(*rect.center);sound.assert_not_called()
    assert not hasattr(app,'vsync_unavailable')


def test_animated_tiles_reuse_buffers_without_per_frame_transforms():
    from ui import generated_icons
    surface=pygame.Surface((64,64),pygame.SRCALPHA)
    for name in ('rain','snow','sun','sky','horror_rain','flow','nether'):
        generated_icons.draw(surface,name,surface.get_rect(),phase=1)
        with patch.object(generated_icons,'_draw_frame',side_effect=AssertionError('regenerated frame')), \
             patch.object(pygame.transform,'rotozoom',side_effect=AssertionError('transformed frame')):
            for phase in (1.1,2.3,4.6):generated_icons.draw(surface,name,surface.get_rect(),phase=phase)

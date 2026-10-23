"""Finishing contracts: physical motion, native hit regions and audio ownership."""
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pygame
import pytest
from ui.lifecycle import block_pose, assembly, GoodbyeScreen
from ui.window_chrome import hit_region,WindowChrome
from ui.world_material import icon
from engine.audio_decode import load_sound
from test_workshop_production import app,reset


def test_contact_converts_fall_into_compression_and_settles():
    h0=block_pose(.48,0)[0];h1=block_pose(.54,0)[0];h2=block_pose(.60,0)[0]
    assert h2-h1<h1-h0<0  # Downward velocity increases before contact.
    assert block_pose(.69,0)[1]<1
    assert block_pose(.77,0)[1]>1
    assert block_pose(.95,0)==(0.,1.,0.)


def test_lifecycle_cubes_keep_sequence_spacing_and_reduced_motion():
    def frame(seconds, closing=False, reduced=False):
        surface=pygame.Surface((100,80),pygame.SRCALPHA)
        assembly(surface,(50,40),seconds,reduced,closing)
        return surface
    def tops(surface):
        return [pygame.mask.from_surface(surface.subsurface((x,0,18,80))).get_bounding_rects()[0].top
                for x in (23,41,59)]
    rest=tops(frame(0))
    for closing in (False,True):
        rate=1.06*(1.14 if closing else 1)
        for step in range(3):
            active=2-step if closing else step
            peak=tops(frame((step*1.02+.37)/rate,closing))
            assert peak[active]<rest[active]-7
            assert all(peak[i]==rest[i] for i in range(3) if i!=active)
        still=pygame.image.tobytes(frame(0,closing,True),'RGBA')
        for tick in range(361):
            surface=frame(tick/120,closing)
            # No adjacent cubes touch even during compression/recoil.
            assert len(pygame.mask.from_surface(surface).get_bounding_rects())==3
            assert pygame.image.tobytes(frame(tick/120,closing,True),'RGBA')==still
    assert pygame.image.tobytes(frame(2.65,True),'RGBA')==pygame.image.tobytes(frame(0,True),'RGBA')
    assert GoodbyeScreen.duration_ms==3000 and GoodbyeScreen.fade_ms==350


def test_native_hit_regions_keep_title_buttons_and_world_as_clients():
    assert hit_region(400,14,1200,800)==1
    assert hit_region(1190,14,1200,800)==0
    assert hit_region(400,200,1200,800)==0
    assert hit_region(1,1,1200,800)==2
    assert hit_region(1199,799,1200,800)==6
    assert hit_region(1,400,1200,800)==9
    assert hit_region(1,1,1200,800,True)==0


@pytest.mark.parametrize('name',['rain','snow','sun','clouds','lighting','sky','horror_rain','flow'])
def test_world_motion_is_frozen_when_reduced_and_truthful_when_disabled(name):
    def frame(t,level=1,reduced=False):
        s=pygame.Surface((64,64),pygame.SRCALPHA)
        icon(s,name,s.get_rect(),t,level,reduced,celestial=t*28)
        return pygame.image.tobytes(s,'RGBA')
    # Keep the feature state fixed while freezing its decoration.
    assert frame(1,reduced=True)==frame(3,reduced=True)
    assert frame(1)!=frame(3)
    assert frame(1,level=0)!=frame(1,level=1)


def test_settings_keyboard_changes_volume_switch_and_mute(app):
    from ui.settings_inspector import key,focus_targets
    app.settingsMenuOpen=True;app._renderSettingsMenu()
    app._settingsFocus=0;old=app.musicVolume
    key(app,pygame.event.Event(pygame.KEYDOWN,key=pygame.K_HOME))
    assert app.musicVolume==0
    key(app,pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT))
    assert app.musicVolume==pytest.approx(.05)
    targets=focus_targets(app)
    app._settingsFocus=next(i for i,(name,_) in enumerate(targets) if name=='music_mute')
    muted=app.musicMuted;key(app,pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
    assert app.musicMuted!=muted
    app._settingsFocus=next(i for i,(name,_) in enumerate(targets) if name=='showCoordinates')
    value=app.showCoordinates;key(app,pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
    assert app.showCoordinates!=value
    app._setVolume('music',old)


def test_compressed_decode_passes_only_pcm_to_sdl_and_preserves_duration(tmp_path):
    import soundfile
    rate=22050
    data=(np.sin(np.arange(rate)*2*np.pi*440/rate)*.1).astype('float32')
    source=tmp_path/'test.ogg';soundfile.write(source,data,rate,format='OGG',subtype='VORBIS')
    original=pygame.mixer.Sound;calls=[]
    def sound(*a,**k):
        assert not a  # No compressed path may enter SDL's blocking decoder.
        calls.append(k);return original(*a,**k)
    with patch.object(pygame.mixer,'Sound',sound):decoded=load_sound(source)
    assert calls and decoded.get_length()==pytest.approx(1,abs=.01)


def test_original_selected_wav_bytes_use_unchanged_decoder():
    path=Path(__file__).parents[1]/'Assets/Sound Hub/ui/selected/bootUp.wav'
    original=pygame.mixer.Sound(str(path));actual=load_sound(path)
    assert actual.get_raw()==original.get_raw()


def test_map_mp3_with_estimated_frame_count_decodes_to_actual_length():
    path=Path(__file__).parents[1]/'Assets/World Map/WorldBuilder/audio/m_intro_1.mp3'
    actual=load_sound(path)
    assert 4 < actual.get_length() < 6


def test_title_keyboard_and_close_use_application_confirmation(app):
    title=app.windowChrome;enabled=title.enabled;title.enabled=True;title.focus=None
    try:
        title.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F10),app)
        title.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_LEFT),app)
        assert title.focus==2
        with patch.object(app,'_requestExit') as request:
            title.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN),app)
            request.assert_called_once()
    finally:title.enabled=enabled;title.focus=None


def test_gpu_title_uses_actual_window_size_when_display_surface_is_stale(app):
    from types import SimpleNamespace
    from unittest.mock import Mock
    gpu=Mock();previous=app.openingScene;overlay=getattr(app,'_startupOverlay',None)
    try:
        app.openingScene=SimpleNamespace(gpu=gpu);app._startupOverlay=None
        with patch('pygame.display.get_window_size',return_value=(960,640)),patch('pygame.display.flip'):
            app._presentFrame()
        surface,rect,viewport=gpu.overlay_region.call_args.args
        assert surface.get_size()==(960,28) and rect==(0,0,960,28) and viewport==(960,640)
    finally:app.openingScene=previous;app._startupOverlay=overlay


def test_fullscreen_keeps_latest_borrowed_sdl_window_wrapper_alive(app):
    import gc,weakref
    from types import SimpleNamespace
    refs=[]
    class Window:
        position=(135,90);display_index=0
    def borrow():
        window=Window();refs.append(weakref.ref(window));return window
    previous=app.fullscreen;previous_window=app._displayWindow;app.fullscreen=False
    try:
        with patch('pygame._sdl2.Window',SimpleNamespace(from_display_module=borrow)),patch.object(app,'_applyWindowSize'),patch('pygame.display.get_desktop_sizes',return_value=[(1920,1080)]):
            app._toggleFullscreen();gc.collect()
            assert refs[-1]() is app._displayWindow
            app._toggleFullscreen();gc.collect()
            assert refs[-1]() is app._displayWindow
            assert app._displayWindow.position==(135,90)
    finally:app.fullscreen=previous;app._displayWindow=previous_window

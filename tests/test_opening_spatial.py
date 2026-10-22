"""Recorded-event placement, bounded overlap, propagation and cleanup."""
import os
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import numpy as np
import pygame
from ui.opening_audio import OpeningAudio, OPENING_CHANNELS
from ui.opening_spatial import spatial_gain
from ui.opening_rig import ThornRig
from ui.presentation_renderer import Camera
from ui.encounter_timeline import SKULL_CONTACTS, CONTACT_EVENTS, VOCAL_EVENTS


def test_distance_gain_and_camera_relative_position():
    camera=Camera((1200,800));camera.center=np.zeros(3);camera.half=30;camera.angle=0
    close=spatial_gain(camera,(10,0,0));far=spatial_gain(camera,(200,0,0))
    assert 0<far[0]<close[0]<=1 and close[1]>0
    assert spatial_gain(camera,(-10,0,0))[1]<0
    camera.angle=180
    assert spatial_gain(camera,(10,0,0))[1]<0


def test_recorded_contact_and_reflections_play_once_on_owned_channels():
    pygame.mixer.init(44100,-16,2)
    audio=OpeningAudio(.8);rig=ThornRig();camera=Camera((1200,800));camera.half=55
    assert audio.spatial.ready
    assert audio.spatial.sounds['contact'].get_length()<.9
    assert audio.spatial.sounds['reflection'].get_length()<.9
    audio.start_encounter()
    try:
        audio.update_encounter(.99,.99,camera,rig)
        assert not pygame.mixer.Channel(36).get_busy()
        audio.update_encounter(1.,.01,camera,rig)
        assert pygame.mixer.Channel(36).get_sound() is audio.spatial.sounds['contact']
        assert len(audio.spatial.pending)==2
        audio.update_encounter(1.01,.01,camera,rig)
        assert len(audio.spatial.pending)==2
        audio.update_encounter(1.08,.07,camera,rig)
        assert pygame.mixer.Channel(39).get_sound() is audio.spatial.sounds['reflection']
        assert len(audio.spatial.pending)==1
        audio.update_encounter(3.3,2.22,camera,rig)
        assert pygame.mixer.Channel(37).get_sound() is audio.spatial.sounds['voice11']
        # Muting updates active spatial gains, with no restart or queued voices.
        audio.volume=0;audio.update_encounter(3.31,.01,camera,rig)
        assert len(audio.spatial.active)<=5
        assert {t for t,k,_ in CONTACT_EVENTS if k=='skull'}==set(SKULL_CONTACTS)
        assert len({name for _,name,_ in VOCAL_EVENTS})==11
    finally:audio.close()
    assert not any(pygame.mixer.Channel(i).get_busy() for i in OPENING_CHANNELS.values())


def test_release_rejects_missing_recorded_presentation_media(tmp_path):
    from pathlib import Path
    import pytest
    from engine.selected_audio import validate_presentation_audio
    root=Path(__file__).resolve().parents[1]
    manifest=root/'docs/design/pass-b-derived-audio.json'
    assert len(validate_presentation_audio(root/'Assets/Sound Hub',manifest))==14
    with pytest.raises(FileNotFoundError):validate_presentation_audio(tmp_path,manifest)

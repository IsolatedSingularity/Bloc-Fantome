"""Real SDL mixer regression for suspended editor loops and opening ownership."""
import os
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from ui.opening_audio import OpeningAudio, OPENING_CHANNELS
from engine.audio import DEFAULT_CHANNEL_GROUPS


def test_opening_never_claims_or_stops_paused_editor_channels():
    pygame.mixer.init(44100,-16,2)
    pygame.mixer.set_num_channels(37)
    sentinel=pygame.mixer.Sound(buffer=bytes(44100*4))
    for index in (25,26):pygame.mixer.Channel(index).play(sentinel,loops=-1)
    pygame.mixer.pause()
    opening=OpeningAudio()
    try:
        editor={i for group in DEFAULT_CHANNEL_GROUPS.values() for i in group}
        assert not editor.intersection(OPENING_CHANNELS.values())
        assert not {30,31}.intersection(OPENING_CHANNELS.values())
        # Independent of private assets: inject a real decoded buffer for the bed.
        opening.sounds['ambience']=pygame.mixer.Sound(buffer=bytes(44100*4))
        opening.update_orbit(0,.1)
        assert pygame.mixer.Channel(OPENING_CHANNELS['ambience']).get_sound() is opening.sounds['ambience']
        opening.start_encounter()
        opening.close()
        assert all(pygame.mixer.Channel(i).get_sound() is sentinel for i in (25,26))
        assert not any(pygame.mixer.Channel(i).get_busy() for i in OPENING_CHANNELS.values())
    finally:
        pygame.mixer.stop();pygame.mixer.unpause()


def test_missing_cues_are_diagnosable_without_aborting(monkeypatch,tmp_path,caplog):
    monkeypatch.setattr('ui.opening_audio.SOUNDS_DIR',str(tmp_path))
    opening=OpeningAudio()
    assert set(opening.load_errors)=={'hover','orbit','rise','ambience','encounter','touch','settle','place','move'}
    assert not opening.sounds
    opening.update_orbit(0,.1);opening.close()
    assert 'Opening cue ambience unavailable' in caplog.text

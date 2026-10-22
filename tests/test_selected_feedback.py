"""Real decoded cues, transaction routing and successful-write semantics."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pygame
import pytest
from engine.audio import AudioRouter, DEFAULT_CHANNEL_GROUPS
from engine.selected_audio import validate_selected_audio
from ui import feedback
from test_workshop_production import app, reset

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def assets():
    pygame.mixer.init(44100, -16, 2)
    pygame.mixer.set_num_channels(45)
    pygame.mixer.stop()
    value = SimpleNamespace(audioRouter=AudioRouter(pygame.mixer))
    yield value
    pygame.mixer.stop()


def test_all_seven_originals_decode_play_and_respect_mute(assets):
    records = validate_selected_audio(ROOT/'Assets/Sound Hub', ROOT/'docs/design/selected-audio.json')
    assert len(records) == 11
    for row in records:
        assert hashlib.sha256((ROOT/row['source']).read_bytes()).hexdigest() == row['sha256']
    for name, (_, gain, _, _, group) in feedback.CUES.items():
        pygame.mixer.stop();feedback.set_volume(assets, .5)
        channel = feedback.play(assets, name)
        assert channel is not None and channel.get_busy()
        assert channel.get_sound() is assets._selected_cues[name]
        feedback.set_volume(assets, 0)
        # SDL's stereo set_volume is a panning effect: get_volume only reports
        # its independent scalar and cannot measure that output. Check the
        # router bus here; the fake-channel suite checks both applied gains.
        assert assets.audioRouter._group_volume[group] == 0
        assert set(DEFAULT_CHANNEL_GROUPS[group]).isdisjoint({30,31,32,33,34,35,36})


def test_specific_event_wins_and_busy_pools_are_not_stolen(assets):
    with feedback.event(assets):
        feedback.play(assets, 'button')
        with feedback.event(assets):feedback.play(assets, 'save')
        feedback.play(assets, 'close')
    assert not pygame.mixer.Channel(0).get_busy()
    assert pygame.mixer.Channel(27).get_sound() is assets._selected_cues['save']
    feedback.play(assets, 'error')
    before=[pygame.mixer.Channel(i).get_sound() for i in (27,28)]
    assert feedback.play(assets, 'world_map') is None
    assert before == [pygame.mixer.Channel(i).get_sound() for i in (27,28)]
    assert feedback.play(assets, 'error') is None


def test_missing_optional_cues_silent_but_release_rejects(assets, tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, 'SOUNDS_DIR', str(tmp_path))
    assert feedback.play(assets, 'boot') is None
    assert feedback.play(assets, 'focus') is None
    with pytest.raises(FileNotFoundError):
        validate_selected_audio(tmp_path, ROOT/'docs/design/selected-audio.json')


def test_save_cue_owned_by_successful_write_for_keyboard_and_toolbar(app, tmp_path):
    with patch.object(app.assetManager.audioRouter, 'play') as play:
        assert app._saveBuilding(filepath=str(tmp_path/'real.json.gz')) is None
        assert play.call_count == 0
        app._pendingSave.future.result(timeout=10)
        app._pollSave()
        assert play.call_args.args[0] is app.assetManager._selected_cues['save']
        play.reset_mock()
        with patch('engine.build_io.write_build', side_effect=OSError('disk unavailable')):
            app.assetManager._feedback_last = {}
            assert app._saveBuilding(filepath=str(tmp_path/'failed.json.gz')) is None
            with pytest.raises(OSError):app._pendingSave.future.result(timeout=10)
            app._pollSave()
        assert play.call_args.args[0] is app.assetManager._selected_cues['error']
        play.reset_mock()
        app.currentBuildPath = None
        with patch.object(app, '_openSaveAsDialog', return_value=None):app.workshop.act('save', app)
        play.assert_not_called()


def test_keyboard_and_mouse_panel_close_use_close_cue(app):
    for mode in ('keyboard','mouse'):
        app.workshop.page='build';app.assetManager._feedback_last={}
        with patch.object(app.assetManager.audioRouter,'play') as play:
            if mode=='keyboard':
                app.workshop.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0), app)
            else:app.workshop.act('close',app)
            assert not app.workshop.page
            assert play.call_args.args[0] is app.assetManager._selected_cues['close']


def test_map_transition_cancel_reduced_motion_and_editor_restore(app):
    before=dict(app.world.blocks)
    app._mapTransition=None
    app._requestWorldMap()
    assert not app.worldMapActive and app.world.blocks==before
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0))
    app._handleEvents()
    assert app._mapTransition is None and not app.worldMapActive
    app.workshop.visibility.reduced_motion=True
    app._requestWorldMap()
    app._mapTransition.future.result(timeout=10)
    app._update()
    try:
        assert app.worldMapActive and app._mapTransition.finished
        app._render()
        assert app._mapTransition is None
    finally:app._exitWorldMap()
    assert app.world.blocks==before


def test_lifecycle_once_uses_selected_files_and_effects_volume(app):
    app._lifecyclePlayed=set();app.assetManager._feedback_last={}
    with patch.object(app.assetManager.audioRouter,'play') as play:
        app._playLifecycleCue('boot');app._playLifecycleCue('boot')
        assert play.call_count==1 and play.call_args.args[0] is app.assetManager._selected_cues['boot']
        app._playLifecycleCue('shutdown')
        assert play.call_count==2 and play.call_args.args[0] is app.assetManager._selected_cues['shutdown']
        assert app.assetManager.audioRouter._group_volume['lifecycle']==app.effectsVolume


def test_confirmed_save_preempts_a_lower_priority_tail_only(assets):
    feedback.play(assets,'world_map');feedback.play(assets,'close')
    protected=pygame.mixer.Channel(31)
    protected.play(assets._selected_cues['boot'],loops=-1)
    assert feedback.play(assets,'save') is not None
    assert any(pygame.mixer.Channel(i).get_sound() is assets._selected_cues['save'] for i in (27,28))
    assert protected.get_busy() and protected.get_sound() is assets._selected_cues['boot']

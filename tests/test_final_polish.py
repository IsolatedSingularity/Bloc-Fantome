"""Regression contracts for the final consistency pass."""
import pygame
import pytest
from unittest.mock import patch
from test_workshop_production import app, reset
from ui.workshop_actions import WORLD


@pytest.mark.parametrize('action', [r[0] for r in WORLD if r[0] != 'map'])
def test_world_internal_actions_keep_drawer_and_own_release(app, action):
    shell = app.workshop; shell.page = 'world'
    if action == 'clear_world':
        shell.act(action, app)
        assert shell.confirm == action and shell.page == 'world'
        shell.act('confirm:cancel', app)
    else:
        shell.act(action, app)
    assert shell.page == 'world'
    assert not shell.error


def test_dimension_click_keeps_world_and_consumes_release(app):
    shell = app.workshop; shell.page = 'world'; shell.render(app)
    point = next(r.center for r, a, enabled in shell.hits if a == 'nether')
    assert shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point), app)
    assert shell.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point), app)
    assert shell.page == 'world' and app.currentDimension == 'nether'
    assert shell.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE), app)
    assert not shell.page


def test_world_navigation_does_not_toggle_itself_closed(app):
    app.workshop.page = 'world'
    app.workshop.act('nav:world', app)
    assert app.workshop.page == 'world'


def test_piano_probability_weighting_playlist_resume_and_no_repeats():
    import random
    from engine.audio import MusicController
    from test_audio import FakeMusic
    music=FakeMusic()
    controller=MusicController(music, shuffle=lambda tracks:None,
                               piano_chapters=(('one',2),('three',2),('seven',1)),rng=random.Random(41))
    controller.set_playlist(['normal-a','normal-b'],fade=False)
    assert music.loaded==['normal-a']  # Startup has no piano lottery.
    for _ in range(12000):controller.handle_end_event()
    from collections import Counter
    counts=Counter(music.loaded[1:])
    assert .31 < sum(counts[p] for p in ('one','three','seven'))/12000 < .35
    assert counts['one']>counts['seven'] and counts['three']>counts['seven']
    assert all(a!=b for a,b in zip(music.loaded,music.loaded[1:]))
    ordinary=[p for p in music.loaded if p.startswith('normal')]
    assert ordinary==['normal-a','normal-b']*(len(ordinary)//2)+(['normal-a'] if len(ordinary)%2 else [])


def test_piano_waits_for_preparation_without_blocking_or_replacing_current():
    from engine.audio import MusicController
    from test_audio import FakeMusic
    music=FakeMusic();ready=False
    music.prepare=lambda path:ready
    controller=MusicController(music,piano_chapters=(('one',2),),shuffle=lambda tracks:None)
    controller.set_playlist(['normal'],fade=False)
    controller._next_track=('one',False)
    assert not controller.handle_end_event()
    assert music.loaded==['normal']
    ready=True;controller.update(10)
    assert music.loaded==['normal','one']


def test_derived_scenes_are_exact_subsets_and_islands_are_complete():
    import gzip,hashlib,json
    from pathlib import Path
    root=Path(__file__).parents[1]/'Code/biome_captures'
    for name in ('swamp','small_end_islands'):
        derived=json.loads(gzip.decompress((root/'derived'/(name+'.json.gz')).read_bytes()))
        provenance=derived['derived_from'];source=root/provenance['file']
        assert hashlib.sha256(source.read_bytes()).hexdigest()==provenance['sha256']
        original=json.loads(gzip.decompress(source.read_bytes()))
        cells={tuple(r) for r in original['blocks']}
        dx,dy=(a-b for a,b in zip(derived['origin'],original['origin']))
        assert all((x+dx,y+dy,z,p) in cells for x,y,z,p in derived['blocks'])
        assert derived['palette']==original['palette']
        if name=='small_end_islands':assert sum(c['complete'] for c in provenance['components'])==3


def test_special_sequence_fallback_never_selects_piano():
    from engine.audio import MusicController
    from test_audio import FakeMusic
    music=FakeMusic();controller=MusicController(music,piano_chapters=(('piano',1),))
    controller.set_sequence(['map-a','map-b'])
    for _ in range(100):controller.handle_end_event()
    assert set(music.loaded)=={'map-a','map-b'}


def test_library_subset_does_not_change_tutorial_capture():
    from engine.biome_capture import capture
    assert capture('swamp')['size'][:2]==[96,96]
    assert capture('swamp',library=True)['size'][:2]==[32,32]


def test_contextual_feedback_keeps_general_cues_and_originals(app):
    from ui import feedback
    assets=app.assetManager;heard=[]
    with patch.object(assets.audioRouter,'play',side_effect=lambda sound,**kw:heard.append((sound,kw))):
        assets._feedback_last={};assets._feedback_context=None
        feedback.play(assets,'toggle')
        assets._feedback_context='world';feedback.play(assets,'toggle')
        assets._feedback_context=None
    assert heard[1][0].get_length()<heard[0][0].get_length()
    assert heard[1][1]['volume']<heard[0][1]['volume']


def test_cached_next_track_survives_retaining_current_track():
    from engine.audio import PreloadedMusicBackend
    from test_audio import FakeMixer
    backend=PreloadedMusicBackend(FakeMixer())
    backend.load('current.ogg')
    for path in ('next.ogg','other-a.ogg','other-b.ogg'):backend.preload(path)
    assert backend.prepare('next.ogg')
    with patch.object(backend,'_decode',side_effect=AssertionError('decode on transition')):
        backend.load('next.ogg')
        backend.load('next.ogg')  # A single-track playlist also stays decoded.
    assert backend.path=='next.ogg'
    assert len(backend._preloaded)<=3

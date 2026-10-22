"""Owner-selected semantic feedback, coalesced at the input-action boundary."""
from contextlib import contextmanager
from functools import wraps
import logging
import os
import pygame
from runtime_paths import SOUNDS_DIR

# filename, gain before router headroom, cooldown seconds, priority, channel pool
CUES = {
    'button': ('pressButton.wav', .90, .075, 1, 'ui'),
    'close': ('close-short.wav', .72, .15, 2, 'ui_semantic'),
    'world_map': ('worldMap.wav', .82, .5, 3, 'ui_semantic'),
    'save': ('save.wav', .78, .2, 4, 'ui_semantic'),
    'error': ('error.wav', .80, .65, 5, 'ui_semantic'),
    'boot': ('bootUp.wav', .76, 1, 6, 'lifecycle'),
    'shutdown': ('shutDown.wav', .76, 1, 6, 'lifecycle'),
}
ALIASES = {'select': 'button', 'open': 'button', 'cancel': 'close',
           'success': 'save', 'failure': 'error'}


def sound_path(filename):
    from pathlib import Path
    if filename=='close-short.wav':return Path(__file__).with_name('audio')/filename
    return Path(SOUNDS_DIR)/'ui'/'selected'/filename


def preload(assets, names=None):
    """Decode once; missing optional development files remain diagnosable."""
    if not pygame.mixer.get_init():return {}
    cache = getattr(assets, '_selected_cues', None)
    if cache is None:cache = assets._selected_cues = {}
    for name in CUES if names is None else names:
        if name in cache:continue
        filename = CUES[name][0]
        try:cache[name] = pygame.mixer.Sound(str(sound_path(filename)))
        except (OSError, pygame.error) as error:
            cache[name] = None
            logging.getLogger(__name__).warning('Selected UI cue %s unavailable: %s', name, error)
    return cache


def set_volume(assets, volume):
    for group in ('ui', 'ui_semantic', 'lifecycle'):
        assets.audioRouter.set_group_volume(group, volume)


def play(assets, name):
    name = ALIASES.get(name, name)
    # Hover/focus, text input and scrolling are intentionally silent.
    if name not in CUES or not pygame.mixer.get_init():return None
    state = getattr(assets, '_feedback_event', None)
    if state is not None:
        if state[0] is None or CUES[name][3] > CUES[state[0]][3]:state[0] = name
        return None
    sound = preload(assets, (name,)).get(name)
    if sound is None:return None
    now = pygame.time.get_ticks() / 1000
    last = getattr(assets, '_feedback_last', None)
    if last is None:last = assets._feedback_last = {}
    filename, gain, cooldown, priority, group = CUES[name]
    if now-last.get(name, -100) < cooldown:return None
    if group == 'ui_semantic':
        candidates=[]
        cache=preload(assets)
        for index in (27,28):
            candidate=pygame.mixer.Channel(index)
            current=candidate.get_sound()
            current_priority=next((CUES[key][3] for key,value in cache.items() if value is current),99)
            if candidate.get_busy():candidates.append((current_priority,index))
        if len(candidates)==2 and min(candidates)[0] < priority:
            pygame.mixer.Channel(min(candidates)[1]).stop()
    channel = assets.audioRouter.play(sound, group=group, volume=gain, replace=group=='ui')
    if channel is not None:last[name] = now
    return channel


@contextmanager
def event(assets):
    """One highest-priority cue per dispatch; nested callers share the decision."""
    if assets is None or getattr(assets, '_feedback_event', None) is not None:
        yield
        return
    state = assets._feedback_event = [None]
    try:yield
    finally:
        assets._feedback_event = None
        if state[0] is not None:play(assets, state[0])


def action(method):
    """Wrap a UI method whose final argument is the application."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        app = args[-1] if args else kwargs['app']
        with event(getattr(app,'assetManager',None)):return method(self, *args, **kwargs)
    return wrapped

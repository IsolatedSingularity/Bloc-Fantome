"""Small semantic cue family, routed through the existing effects volume owner."""
import os
import pygame
from runtime_paths import SOUNDS_DIR


def play(assets, name):
    if not pygame.mixer.get_init():return
    cache=getattr(assets,'_workshop_cues',None)
    if cache is None:cache={};assets._workshop_cues=cache
    if name not in cache:
        try:cache[name]=pygame.mixer.Sound(os.path.join(SOUNDS_DIR,'ui','workshop',name+'.ogg'))
        except (OSError,pygame.error):cache[name]=None
    sound=cache[name]
    if sound is not None:return assets.audioRouter.play(sound,group='ui',volume=.48,replace=True)

"""Sparse presentation cues on channels unused by the builder and piano."""
import os
import math
import pygame
from runtime_paths import SOUNDS_DIR


class OpeningAudio:
    def __init__(self, volume=1):
        self.volume=volume
        self.sounds={}
        self.last={}
        self.orbit_gain=0.0
        self.encounter_started=False
        if not pygame.mixer.get_init():return
        for name,path in {'hover':'note/harp.ogg','orbit':'opening/orbit-bed.wav',
                          'rise':'opening/sanctuary-rise.wav',
                          'ambience':'opening/abyss-bed.wav','encounter':'opening/encounter.wav',
                          'touch':'note/icechime.ogg','settle':'block/lodestone/place1.ogg',
                          'place':'dig/stone1.ogg','move':'opening/monument-move.wav'}.items():
            try:self.sounds[name]=pygame.mixer.Sound(os.path.join(SOUNDS_DIR,path))
            except (OSError,pygame.error):pass

    def start_encounter(self):
        self.encounter_started=True
        if not pygame.mixer.get_init():return
        for number in (25,26,27,28,29):pygame.mixer.Channel(number).stop()
        if 'encounter' in self.sounds:
            channel=pygame.mixer.Channel(27)
            channel.set_volume(self.volume*.82)
            channel.play(self.sounds['encounter'])

    def update_encounter(self,seconds,dt):
        # The offline score and visual timeline share the same zero point.
        # Playback continues on focus loss; no per-frame restart or short loop.
        if pygame.mixer.get_init():pygame.mixer.Channel(27).set_volume(self.volume*.82)

    def update_orbit(self, speed, seconds):
        """One loop follows actual angular velocity, including its damped tail."""
        if self.encounter_started:return
        if 'ambience' in self.sounds and pygame.mixer.get_init():
            ambience=pygame.mixer.Channel(26)
            if not ambience.get_busy():ambience.play(self.sounds['ambience'],loops=-1,fade_ms=1800)
            ambience.set_volume(self.volume*.1)
        if 'orbit' not in self.sounds:return
        target=min(1.0,abs(speed)/90) if abs(speed)>.4 else 0.0
        self.orbit_gain+=(target-self.orbit_gain)*(1-math.exp(-max(0,seconds)*(12 if target>self.orbit_gain else 6)))
        channel=pygame.mixer.Channel(25)
        if self.orbit_gain>.002 and self.volume>0:
            channel.set_volume(self.volume*.065*self.orbit_gain)
            if not channel.get_busy():channel.play(self.sounds['orbit'],loops=-1,fade_ms=80)
        else:channel.stop()

    def play(self,name,now):
        if name not in self.sounds or now-self.last.get(name,-100)<(.4 if name=='hover' else .12):return
        self.last[name]=now
        if self.encounter_started:return
        channel=pygame.mixer.Channel(27 if name in ('rise','move') else 28 if name=='hover' else 29)
        gains={'hover':.04,'touch':.22,'settle':.35,'place':.24,'rise':.88,'move':.3}
        channel.set_volume(self.volume*gains[name])
        channel.play(self.sounds[name],fade_ms=80 if name=='hover' else 160 if name=='rise' else 35)

    def close(self):
        if pygame.mixer.get_init():
            for number in (25,26,27,28,29):pygame.mixer.Channel(number).stop()

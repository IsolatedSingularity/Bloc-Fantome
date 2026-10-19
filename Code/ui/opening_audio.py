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
        if not pygame.mixer.get_init():return
        for name,path in {'hover':'note/harp.ogg','orbit':'opening/orbit-bed.wav',
                          'rise':'opening/sanctuary-rise.wav',
                          'touch':'note/icechime.ogg','settle':'block/lodestone/place1.ogg',
                          'place':'dig/stone1.ogg','move':'block/grindstone/grindstone2.ogg'}.items():
            try:self.sounds[name]=pygame.mixer.Sound(os.path.join(SOUNDS_DIR,path))
            except (OSError,pygame.error):pass
    def update_orbit(self, speed, seconds):
        """One loop follows actual angular velocity, including its damped tail."""
        if 'orbit' not in self.sounds:return
        target=min(1.0,abs(speed)/90) if abs(speed)>.4 else 0.0
        self.orbit_gain+=(target-self.orbit_gain)*(1-math.exp(-max(0,seconds)*(12 if target>self.orbit_gain else 6)))
        channel=pygame.mixer.Channel(25)
        if self.orbit_gain>.002 and self.volume>0:
            channel.set_volume(self.volume*.32*self.orbit_gain)
            if not channel.get_busy():channel.play(self.sounds['orbit'],loops=-1,fade_ms=80)
        else:channel.stop()

    def play(self,name,now):
        if name not in self.sounds or now-self.last.get(name,-100)<(.4 if name=='hover' else .12):return
        self.last[name]=now
        channel=pygame.mixer.Channel(27 if name=='rise' else 26 if name=='move' else 28 if name=='hover' else 29)
        gains={'hover':.04,'touch':.22,'settle':.35,'place':.24,'rise':.88,'move':.3}
        channel.set_volume(self.volume*gains[name])
        channel.play(self.sounds[name],fade_ms=80 if name=='hover' else 160 if name=='rise' else 35)

    def close(self):
        if pygame.mixer.get_init():
            for number in (25,26,27,28,29):pygame.mixer.Channel(number).stop()

"""Sparse presentation cues on channels unused by the builder and piano."""
import os
import math
import logging
import pygame
from runtime_paths import SOUNDS_DIR
from ui.opening_spatial import SpatialEncounterAudio, CHANNELS, spatial_gain

# Editor groups occupy 0..26, opening piano 30, editor music 31.
# Paused channels remain busy in SDL_mixer, so sharing 25/26 can suppress the
# opening bed and destroy the editor's suspended portal/horror loops on exit.
OPENING_CHANNELS = dict(orbit=32, ambience=33, score=34, hover=35, contact=36)
OPENING_CHANNELS.update(CHANNELS)
RESERVED_CHANNEL_COUNT = 41
# Automatic Sound.play() callers retain their own bounded unreserved pool.
MIXER_CHANNEL_COUNT = RESERVED_CHANNEL_COUNT + 8


class OpeningAudio:
    def __init__(self, volume=1):
        self.volume=volume
        self.sounds={}
        self.load_errors={}
        self.last={}
        self.orbit_gain=0.0
        self.encounter_started=False
        self.spatial=None;self.listener=None;self.positioned={}
        if not pygame.mixer.get_init():return
        if pygame.mixer.get_num_channels() < MIXER_CHANNEL_COUNT:
            pygame.mixer.set_num_channels(MIXER_CHANNEL_COUNT)
        pygame.mixer.set_reserved(RESERVED_CHANNEL_COUNT)
        self.spatial=SpatialEncounterAudio()
        for name,path in {'hover':'note/harp.ogg','orbit':'opening/orbit-bed.wav',
                          'rise':'opening/sanctuary-rise.wav',
                          'ambience':'opening/abyss-bed.wav','encounter':'opening/encounter.wav',
                          'touch':'note/icechime.ogg','settle':'block/lodestone/place1.ogg',
                          'place':'dig/stone1.ogg','move':'opening/monument-move.wav'}.items():
            if name=='rise' and os.path.isfile(os.path.join(SOUNDS_DIR,'opening','sanctuary-rise-b4.ogg')):
                path='opening/sanctuary-rise-b4.ogg'
            try:self.sounds[name]=pygame.mixer.Sound(os.path.join(SOUNDS_DIR,path))
            except (OSError,pygame.error) as error:
                self.load_errors[name]=str(error)
                logging.getLogger(__name__).warning('Opening cue %s unavailable: %s',name,error)

    def start_encounter(self):
        self.encounter_started=True
        if not pygame.mixer.get_init():return
        for number in OPENING_CHANNELS.values():pygame.mixer.Channel(number).stop()
        if self.spatial and self.spatial.ready:
            self.spatial.reset()
            if 'ambience' in self.sounds:
                channel=pygame.mixer.Channel(OPENING_CHANNELS['ambience'])
                channel.set_volume(self.volume*.07);channel.play(self.sounds['ambience'],loops=-1,fade_ms=900)
            return
        if 'encounter' in self.sounds:
            channel=pygame.mixer.Channel(OPENING_CHANNELS['score'])
            channel.set_volume(self.volume*.82)
            channel.play(self.sounds['encounter'])

    def update_encounter(self,seconds,dt,camera=None,rig=None,offset=(0,0,0)):
        if self.spatial and self.spatial.ready:
            if camera is not None and rig is not None:self.spatial.update(seconds,dt,camera,rig,offset,self.volume)
            pygame.mixer.Channel(OPENING_CHANNELS['ambience']).set_volume(self.volume*.07*max(0,min(1,(43-seconds)/3)))
            return
        # The offline score and visual timeline share the same zero point.
        # Playback continues on focus loss; no per-frame restart or short loop.
        if pygame.mixer.get_init():pygame.mixer.Channel(OPENING_CHANNELS['score']).set_volume(self.volume*.82)

    def update_orbit(self, speed, seconds):
        """One loop follows actual angular velocity, including its damped tail."""
        if self.encounter_started:return
        if 'ambience' in self.sounds and pygame.mixer.get_init():
            ambience=pygame.mixer.Channel(OPENING_CHANNELS['ambience'])
            if not ambience.get_busy():ambience.play(self.sounds['ambience'],loops=-1,fade_ms=1800)
            ambience.set_volume(self.volume*.1)
        if 'orbit' not in self.sounds:return
        target=min(1.0,abs(speed)/90) if abs(speed)>.4 else 0.0
        self.orbit_gain+=(target-self.orbit_gain)*(1-math.exp(-max(0,seconds)*(12 if target>self.orbit_gain else 6)))
        channel=pygame.mixer.Channel(OPENING_CHANNELS['orbit'])
        if self.orbit_gain>.002 and self.volume>0:
            channel.set_volume(self.volume*.065*self.orbit_gain)
            if not channel.get_busy():channel.play(self.sounds['orbit'],loops=-1,fade_ms=80)
        else:channel.stop()

    def set_listener(self,camera,source):
        self.listener=(camera,source)
        for number,(sound,base,position) in tuple(self.positioned.items()):
            channel=pygame.mixer.Channel(number)
            if not channel.get_busy() or channel.get_sound() is not sound:
                self.positioned.pop(number);continue
            gain,pan,_=spatial_gain(camera,position,reference=28)
            gain*=base*self.volume
            channel.set_volume(gain*(1 if pan<=0 else 1-pan),gain*(1 if pan>=0 else 1+pan))

    def play(self,name,now):
        if name not in self.sounds or now-self.last.get(name,-100)<(.4 if name=='hover' else .12):return
        self.last[name]=now
        if self.encounter_started:return
        number=OPENING_CHANNELS['score' if name in ('rise','move') else 'hover' if name=='hover' else 'contact']
        channel=pygame.mixer.Channel(number)
        gains={'hover':.04,'touch':.22,'settle':.35,'place':.24,'rise':.88,'move':.3}
        gain=self.volume*gains[name]
        if self.listener is not None and name in ('rise','move','settle','place'):
            camera,source=self.listener
            self.positioned[number]=(self.sounds[name],gains[name],source)
            attenuation,pan,_=spatial_gain(camera,source,reference=28)
            gain*=attenuation
            channel.set_volume(gain*(1 if pan<=0 else 1-pan),gain*(1 if pan>=0 else 1+pan))
        else:channel.set_volume(gain)
        channel.play(self.sounds[name],fade_ms=80 if name=='hover' else 160 if name=='rise' else 35)

    def close(self):
        self.positioned.clear()
        if pygame.mixer.get_init():
            if self.spatial:self.spatial.close()
            for number in OPENING_CHANNELS.values():pygame.mixer.Channel(number).stop()

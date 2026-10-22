"""Bounded, source-positioned recorded phrases and architectural contacts."""
import math
from pathlib import Path
import numpy as np
import pygame
from engine.audio import AudioRouter
from runtime_paths import SOUNDS_DIR
from ui.encounter_timeline import CONTACT_EVENTS, VOCAL_EVENTS

CHANNELS = {'voice_a':37, 'voice_b':38, 'reflection_a':39, 'reflection_b':40}


def spatial_gain(camera, source, reference=42.0):
    """Virtual orthographic listener, inverse-distance amplitude and bounded pan.

    One scene unit is treated as a metre for delay/attenuation, an artistic scale
    assumption rather than a measured acoustic reconstruction of the block scene.
    """
    source=np.asarray(source,dtype=float)
    listener=camera.center+camera.matrix()[2]*max(24,camera.half*1.4)
    distance=float(np.linalg.norm(source-listener))
    gain=reference/max(reference,distance)
    pan=float(np.clip((camera.project(source)[0]/camera.size[0]-.5)*1.5,-.85,.85))
    return gain,pan,distance


class SpatialEncounterAudio:
    def __init__(self):
        self.router=AudioRouter(pygame.mixer, {'voice':(37,38),'impact':(36,), 'reflection':(39,40)})
        self.sounds={};self.active=[];self.pending=[];self.last=-.001
        root=Path(SOUNDS_DIR)/'opening/pass-b'
        for name in (*(f'voice{i:02d}' for i in range(1,12)),'contact','fall','reflection'):
            try:self.sounds[name]=pygame.mixer.Sound(root/(name+'.wav'))
            except (OSError,pygame.error):pass
        self.ready=len(self.sounds)==14
        self.events=sorted([(t,'voice',name,gain) for t,name,gain in VOCAL_EVENTS]+
                           [(t,'impact',kind,gain) for t,kind,gain in CONTACT_EVENTS])

    def reset(self):
        self.close();self.last=-.001

    def close(self):
        for group in ('voice','impact','reflection'):self.router.stop_group(group)
        self.pending.clear();self.active.clear()

    @staticmethod
    def source(rig,t,kind,offset):
        if kind=='voice':return rig.geometry(t)[1]+offset
        if kind=='skull':return np.array((13.2,21.6,49.))+offset
        if kind=='grip':return np.array((14 if t<8 else -12,20,48.))+offset
        if kind=='foot':
            contacts=rig.contacts(min(t,5.999))
            return np.asarray(contacts[int(round(t))%2][3])+offset
        return rig.hip_path(t)+offset

    def _play(self,name,group,base,source,camera,volume,*,moving=False):
        gain,pan,_=spatial_gain(camera,source)
        channel=self.router.play(self.sounds.get(name),group=group,volume=base*gain*volume,pan=pan)
        if channel is not None:
            self.active.append((channel,self.sounds[name],base,np.asarray(source),moving))

    def update(self,t,dt,camera,rig,offset,volume):
        if not self.ready:return
        if t<self.last:self.reset()
        offset=np.asarray(offset)
        for when,group,name,base in self.events:
            if not self.last<when<=t or t-when>.25:continue
            source=self.source(rig,when,'voice' if group=='voice' else name,offset)
            sound=name if group=='voice' else 'fall' if name in ('fall','collapse') else 'contact'
            self._play(sound,group,base,source,camera,volume,moving=group=='voice')
            if group=='impact':
                # Two sparse reflected paths, longer and quieter than direct.
                # No full-scene convolution, feedback loop or limitless tail.
                for extra,side in ((24,-1),(51,1)):
                    reflected=source+np.array((side*extra*.5,extra*.15,8))
                    self.pending.append((when+extra/343,base*.18,reflected))
        for when,base,source in self.pending:
            if self.last<when<=t and t-when<=.25:
                self._play('reflection','reflection',base,source,camera,volume)
        self.pending=[row for row in self.pending if row[0]>t]
        live=[]
        for channel,sound,base,source,moving in self.active:
            if not channel.get_busy() or channel.get_sound() is not sound:continue
            if moving:source=rig.geometry(t)[1]+offset
            gain,pan,_=spatial_gain(camera,source)
            value=min(1,base*gain*volume)*self.router.peak_headroom
            channel.set_volume(value*(1 if pan<=0 else 1-pan),value*(1 if pan>=0 else 1+pan))
            live.append((channel,sound,base,source,moving))
        self.active=live;self.last=t

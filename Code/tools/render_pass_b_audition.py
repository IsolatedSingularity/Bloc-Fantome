"""Offline audition of recorded live-event routing; not a speaker-loopback claim."""
import json,os,sys,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Code'))
os.environ.setdefault('SDL_AUDIODRIVER','dummy');os.environ.setdefault('SDL_VIDEODRIVER','dummy')
import pygame
from ui.opening_scene import OpeningScene
from ui.opening_spatial import SpatialEncounterAudio,spatial_gain
from ui.encounter_timeline import CONTACT_EVENTS,VOCAL_EVENTS

RATE=48000


def read(path):
    with wave.open(str(path),'rb') as handle:
        assert handle.getframerate()==RATE and handle.getsampwidth()==2
        channels=handle.getnchannels()
        return np.frombuffer(handle.readframes(handle.getnframes()),dtype='<i2').reshape(-1,channels)/32768.


def main():
    out=ROOT/'.qa/pass-b';out.mkdir(parents=True,exist_ok=True)
    root=ROOT/'Assets/Sound Hub/opening';mix=np.zeros((44*RATE,2),dtype=np.float64)
    pygame.init();pygame.display.set_mode((1200,800),pygame.HIDDEN)
    scene=OpeningScene((1200,800),None,effects_volume=0)
    scene.update(5);scene.place();scene.update(5);scene.activate('door');scene.update(scene.RISE_DURATION);scene.activate('heart')
    start=scene.awakened_at;events=[]
    def camera(t):
        scene.elapsed=start+t;scene.update(0);return scene.renderer
    def add(name,when,base,kind,source=None):
        samples=read(root/'pass-b'/(name+'.wav'));count=min(len(samples),len(mix)-round(when*RATE))
        if count<=0:return
        times=np.arange(0,count/RATE+.101,.1);gains=[]
        for age in times:
            t=when+age;cam=camera(t)
            pos=(SpatialEncounterAudio.source(scene.encounter.rig,t,kind,scene.SANCTUARY_OFFSET)
                 if source is None else source)
            gain,pan,_=spatial_gain(cam,pos);gain*=base*.8*.72
            gains.append((gain*(1 if pan<=0 else 1-pan),gain*(1 if pan>=0 else 1+pan)))
        curve=np.column_stack([np.interp(np.arange(count)/RATE,times,np.asarray(gains)[:,i]) for i in (0,1)])
        offset=round(when*RATE);mix[offset:offset+count]+=samples[:count]*curve
        events.append(dict(time=when,file=name,kind=kind,base_gain=base,seconds=count/RATE))
    try:
        for when,name,base in VOCAL_EVENTS:add(name,when,base,'voice')
        for when,kind,base in CONTACT_EVENTS:
            source=SpatialEncounterAudio.source(scene.encounter.rig,when,kind,scene.SANCTUARY_OFFSET)
            add('fall' if kind in ('fall','collapse') else 'contact',when,base,kind,source)
            for extra,side in ((24,-1),(51,1)):
                add('reflection',when+extra/343,base*.18,kind,source+np.array((side*extra*.5,extra*.15,8)))
        bed=read(root/'abyss-bed.wav')
        times=np.arange(len(mix))/RATE
        envelope=np.minimum(1,times/.9)*np.clip((43-times)/3,0,1)
        mix+=bed[np.arange(len(mix))%len(bed)]*(envelope*.07*.8)[:,None]
        peak=float(abs(mix).max());assert peak<1 and np.isfinite(mix).all()
        with wave.open(str(out/'encounter-audition.wav'),'wb') as handle:
            handle.setparams((2,2,RATE,0,'NONE','not compressed'));handle.writeframes((mix*32767).astype('<i2').tobytes())
        report=dict(kind='offline audition of recorded cues, no device capture',effects_volume=.8,
                    peak=peak,rms=float(np.sqrt(np.mean(mix*mix))),clipped_samples=int((abs(mix)>=1).sum()),
                    events=sorted(events,key=lambda r:r['time']))
        (out/'audition.json').write_text(json.dumps(report,indent=2)+'\n')
        print({k:v for k,v in report.items() if k!='events'})
    finally:scene.close();pygame.quit()


if __name__=='__main__':main()

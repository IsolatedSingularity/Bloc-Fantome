"""Reproduce the two intro cues with installed SuperCollider, without dependencies.

Python only decodes source assets, crossfades the loop seam and applies gain.
SuperCollider performs all sound design. Worker logs and OSC scores stay in .qa.
"""
import json
import os
from pathlib import Path
import subprocess
import wave
import numpy as np
import pygame

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'.qa/intro-296/audio'
DEST=ROOT/'Assets/Sound Hub/opening'
SC=Path(r'C:\Program Files\SuperCollider-3.14.1')


def write_wav(path, samples):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(48000)
        f.writeframes(np.asarray(samples,dtype='<i2').tobytes())


def worker(command, log):
    with log.open('w',encoding='utf-8') as f:
        result=subprocess.run(list(map(str,command)),cwd=WORK,stdout=f,stderr=subprocess.STDOUT,
                              timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    text=log.read_text(encoding='utf-8',errors='replace')
    if result.returncode or 'ERROR:' in text or 'FAILURE IN SERVER' in text:
        raise RuntimeError(f'Native render failed: {log}')


def main():
    WORK.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    os.environ['SDL_AUDIODRIVER']='dummy'
    pygame.mixer.init(48000,-16,2)
    sources={}
    for name,relative in [('air','block/beacon/ambient.ogg'),('stone','block/grindstone/grindstone2.ogg')]:
        source=ROOT/'Assets/Sound Hub'/relative
        sound=pygame.mixer.Sound(str(source))
        samples=pygame.sndarray.array(sound)
        if samples.ndim==1:samples=np.column_stack((samples,samples))
        sources[name]=WORK/f'{name}.wav';write_wav(sources[name],samples)
    pygame.mixer.quit()
    template=Path(__file__).with_suffix('.scd').with_name('opening_audio.scd').read_text()
    report={}
    for cue,filename,duration in [('orbitBed','orbit-bed',9),('sanctuaryRise','sanctuary-rise',5.5)]:
        script=WORK/f'{filename}.scd';score=WORK/f'{filename}.osc';raw=WORK/f'{filename}-raw.wav'
        text=template
        for key,value in dict(WORK=WORK,AIR=sources['air'],STONE=sources['stone'],CUE=cue,
                              DURATION=duration,SCORE=score).items():
            text=text.replace(f'@{key}@',value.as_posix() if isinstance(value,Path) else str(value))
        script.write_text(text,encoding='utf-8')
        worker([SC/'sclang.exe','-D',script],WORK/f'{filename}-sclang.log')
        worker([SC/'scsynth.exe','-N',score,'_',raw,'48000','WAV','int16','-o','2','-i','0','-z','64','-m','262144'],WORK/f'{filename}-scsynth.log')
        with wave.open(str(raw),'rb') as f:
            assert f.getnchannels()==2 and f.getframerate()==48000
            samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').reshape(-1,2).astype(float)/32768
        if cue=='orbitBed':
            samples=samples[48000:8*48000]
            n=48000;fade=np.linspace(0,1,n)[:,None]
            seam=samples[-n:]*(1-fade)+samples[:n]*fade
            samples=np.concatenate((seam,samples[n:-n]))
        peak=float(np.max(np.abs(samples)))
        assert peak>.0001 and np.isfinite(samples).all()
        samples*= (.72 if cue=='orbitBed' else .85)/peak
        write_wav(DEST/f'{filename}.wav',samples*32767)
        report[filename]=dict(seconds=len(samples)/48000,peak=float(np.abs(samples).max()),
                              rms=float(np.sqrt(np.mean(samples*samples))),engine='SuperCollider 3.14.1')
    (WORK/'evidence.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

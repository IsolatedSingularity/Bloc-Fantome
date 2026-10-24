"""Reproduce recorded rain derivatives. Originals are never modified.

The continuous bed keeps the owner's natural stereo recording and adds a sparse
weave of the eight supplied Java rain recordings. Material profiles are designed
responses to those recordings, not claims of new material-specific field captures.
No synthetic noise, pitch shifting, compression, or reverb is introduced.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tempfile

import numpy as np
import soundfile as sf


PROFILES = dict(stone=(120,14500),masonry=(200,11000),wood=(140,6500),
                foliage=(850,15500),glass_metal=(550,17500),water=(100,10500))


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root):
    root=Path(root)
    path=root/'Assets/Sound Hub/ambient/weather/atmosphere/manifest.json'
    report=json.loads(path.read_text(encoding='utf-8'))
    expected={'rain-bed.ogg'}|{f'rain-{name}-{i}.ogg' for name in PROFILES for i in range(1,4)}
    if {Path(name).name for name in report['outputs']}!=expected:
        raise ValueError('Incomplete atmospheric rain asset manifest')
    for relative,row in {**report['inputs'],**report['outputs']}.items():
        candidate=(root/relative).resolve()
        if not candidate.is_relative_to(root.resolve()):raise ValueError('Invalid rain asset path')
        if digest(candidate)!=row['sha256']:raise ValueError('Rain asset changed: '+relative)
    return report


def loop_join(data, frames):
    """Linear overlap with unity gain for correlated recordings, no gain bump."""
    weight=np.linspace(0,1,frames,endpoint=False,dtype=np.float32)[:,None]
    join=data[-frames:]*(1-weight)+data[:frames]*weight
    return np.concatenate((join,data[frames:-frames]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--masters',type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve();sources=root/'Assets/Sound Hub/ambient/weather'
    output=sources/'atmosphere';output.mkdir(exist_ok=True)
    args.masters.mkdir(parents=True,exist_ok=True)
    report=dict(recipe='recorded-rain-v1',rate=48000,source_start_seconds=360,
                source_seconds=76,overlap_seconds=4,bed_gain=1.6,weave_gain=.24,
                material_profiles_hz=PROFILES,inputs={},outputs={})
    for path in [sources/'relaxingrain.mp3',*[sources/f'rain{i}.ogg' for i in range(1,9)]]:
        info=sf.info(path)
        report['inputs'][path.relative_to(root).as_posix()]=dict(sha256=digest(path),
            rate=info.samplerate,channels=info.channels,seconds=info.duration,encoding=info.subtype)
    rate=48000
    bed,sr=sf.read(sources/'relaxingrain.mp3',start=360*rate,frames=76*rate,dtype='float32',always_2d=True)
    assert sr==rate and bed.shape==(76*rate,2)
    bed=loop_join(bed,4*rate)*1.6
    rng=np.random.default_rng(330)
    variants=[]
    for i in range(1,9):
        data,sr=sf.read(sources/f'rain{i}.ogg',dtype='float32',always_2d=True)
        assert sr==rate
        variants.append(data[:,0])
    cursor=0.
    while cursor<len(bed)/rate:
        sample=variants[int(rng.integers(8))].copy()
        ramp=min(len(sample)//4,rate//5)
        sample[:ramp]*=np.linspace(0,1,ramp);sample[-ramp:]*=np.linspace(1,0,ramp)
        pan=float(rng.uniform(-.65,.65));gain=.24*float(rng.uniform(.75,1.2))
        stereo=sample[:,None]*np.array([1-max(0,pan),1+min(0,pan)])[None,:]*gain
        indexes=(int(cursor*rate)+np.arange(len(sample)))%len(bed)
        bed[indexes]+=stereo
        cursor+=float(rng.uniform(.8,1.8))

    def save(name,data):
        data=np.asarray(data,dtype=np.float32)
        peak=float(np.max(np.abs(data)))
        if peak>.92:raise ValueError(f'{name} exceeds intentional headroom: {peak}')
        master=args.masters/(name+'.flac');runtime=output/(name+'.ogg')
        sf.write(master,data,rate,subtype='PCM_24')
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(master),'-ar','44100',
                        '-c:a','libvorbis','-q:a','7',str(runtime)],check=True)
        decoded,runtime_rate=sf.read(runtime,always_2d=True)
        report['outputs'][runtime.relative_to(root).as_posix()]=dict(sha256=digest(runtime),
            master_sha256=digest(master),seconds=len(decoded)/runtime_rate,
            peak=float(np.max(np.abs(decoded))),rms=float(np.sqrt(np.mean(decoded**2))),
            decoded_bytes=len(decoded)*2*2,master_rate=rate,runtime_rate=runtime_rate,
            clipped_samples=int(np.sum(np.abs(decoded)>=1)),
            boundary_step=float(np.max(np.abs(decoded[-1]-decoded[0]))))
    save('rain-bed',bed)
    for name,(low,high) in PROFILES.items():
        for i in range(3):
            source=variants[(i*3+list(PROFILES).index(name))%8]
            spectrum=np.fft.rfft(source)
            frequency=np.fft.rfftfreq(len(source),1/rate)
            # Smooth, mild spectral shaping; original recorded transients remain.
            response=(.45+.55*(frequency/(frequency+low)))*(1/(1+(frequency/high)**4))
            data=np.fft.irfft(spectrum*response,n=len(source)).astype(np.float32)
            attack=round(.006*rate);release=round(.18*rate)
            data[:attack]*=np.linspace(0,1,attack);data[-release:]*=np.linspace(1,0,release)
            save(f'rain-{name}-{i+1}',data)
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(outputs=len(report['outputs']),max_peak=max(v['peak'] for v in report['outputs'].values()),
                         decoded_bytes=sum(v['decoded_bytes'] for v in report['outputs'].values())),indent=2))


if __name__=='__main__':main()

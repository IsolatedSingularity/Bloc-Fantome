"""Reproduce the short UI close cue without modifying the selected original."""
from pathlib import Path
import hashlib
import json
import wave
import numpy as np


def derive(source, destination):
    source=Path(source);destination=Path(destination)
    with wave.open(str(source),'rb') as handle:
        assert handle.getsampwidth()==2
        rate=handle.getframerate();channels=handle.getnchannels()
        audio=np.frombuffer(handle.readframes(handle.getnframes()),dtype='<i2').reshape(-1,channels).astype(np.float64)
    # Retain the first piano attack; omit its 40 ms near-silent lead-in.
    audio=audio[round(.040*rate):round(.440*rate)]*1.25
    fade=round(.150*rate)
    audio[-fade:]*=(.5+.5*np.cos(np.linspace(0,np.pi,fade)))[:,None]
    attack=round(.003*rate);audio[:attack]*=np.linspace(0,1,attack)[:,None]
    assert abs(audio).max()<32767
    destination.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(destination),'wb') as handle:
        handle.setparams((channels,2,rate,0,'NONE','not compressed'))
        handle.writeframes(np.rint(audio).astype('<i2').tobytes())
    record=dict(source='Assets/Sound Hub/ui/selected/'+source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        file=destination.name,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        trim_seconds=[.040,.440],gain=1.25,fade_in_seconds=.003,cosine_fade_out_seconds=.150,
        seconds=len(audio)/rate,peak=float(abs(audio).max()/32768),clipped_samples=0)
    destination.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return record


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(derive(root/'Assets/Sound Hub/ui/selected/close.wav',root/'Code/ui/audio/close-short.wav'),indent=2))

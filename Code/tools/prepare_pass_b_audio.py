"""Reproducible edits of preserved human/stone recordings; no vocal synthesis."""
import hashlib
import json
import subprocess
import wave
import zipfile
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Assets/Private Sources/Opening'
DEST=ROOT/'Assets/Sound Hub/opening/pass-b'
RATE=48000


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(name, source, filters, seconds, ceiling):
    command=['ffmpeg','-hide_banner','-loglevel','error','-i',str(source),'-af',filters,
             '-t',str(seconds),'-ar',str(RATE),'-ac','1','-f','f32le','pipe:1']
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    samples=np.frombuffer(result.stdout,dtype='<f4').copy()
    assert len(samples)>100 and np.isfinite(samples).all()
    # Trim true leading silence, retaining a 10 ms guard around the recorded onset.
    active=np.flatnonzero(abs(samples)>max(.001,float(abs(samples).max())*.015))
    if len(active):samples=samples[max(0,int(active[0])-480):]
    fade=min(len(samples)//4,round(.14*RATE))
    samples[:480]*=np.linspace(0,1,min(480,len(samples)))
    samples[-fade:]*=np.linspace(1,0,fade)
    peak=float(abs(samples).max());assert peak>.00001
    gain=min(3.0,ceiling/peak);samples*=gain
    path=DEST/(name+'.wav')
    with wave.open(str(path),'wb') as out:
        out.setparams((1,2,RATE,0,'NONE','not compressed'))
        out.writeframes((samples*32767).astype('<i2').tobytes())
    return dict(name=name,source=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),
                filters=filters,duration_seconds=len(samples)/RATE,gain=gain,
                peak=float(abs(samples).max()),rms=float(np.sqrt(np.mean(samples*samples))),
                file=path.name,sha256=sha(path))


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    source_records=json.loads((ROOT/'Assets/Sound Hub/opening/encounter-sources.json').read_text())
    report=[]
    # Independent bounded pitch/formant changes. Several brighter phrases retain
    # intelligible human upper harmonics instead of low-passing every voice.
    for i,(pitch,formant,duration) in enumerate(((.72,.82,3.2),(1.02,1.,2.3),(.83,.90,2.2),
        (.68,.78,2.8),(.80,.86,3.1),(.94,.96,1.8),(.76,.84,2.4),(.88,.92,1.7),
        (.70,.80,2.7),(.98,.98,1.5),(.84,.88,1.0)),1):
        filters=(f'asetrate={round(RATE*formant)},aresample={RATE},'
                 f'rubberband=tempo={1/formant:.7f}:pitch={pitch/formant:.7f}:formant=preserved,'
                 'highpass=f=65,lowpass=f=6500')
        row=prepare(f'voice{i:02d}',SOURCE/f'voice{i:02d}.wav',filters,duration,.55)
        row['attribution']=next(r for r in source_records if r['id']==f'voice{i:02d}')
        report.append(row)
    # Fit direct footsteps/skull strikes within their one-second spacing so the
    # owned non-stealing impact pool does not suppress every second contact.
    for name,start,duration,pitch in (('contact',24,.72,.63),('fall',11,2.1,.48),('reflection',24,.65,.63)):
        filters=(f'atrim=start={start}:duration=2.5,asetpts=PTS-STARTPTS,'
                 f'asetrate={round(RATE*pitch)},aresample={RATE},highpass=f=38,'
                 f'lowpass=f={850 if name=="reflection" else 3600}')
        row=prepare(name,SOURCE/'stone.wav',filters,duration,.62)
        row['attribution']=next(r for r in source_records if r['id']=='stone')
        report.append(row)
    manifest=dict(tool=subprocess.run(['ffmpeg','-version'],capture_output=True,text=True,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout.splitlines()[0],
        recipe_sha256=sha(Path(__file__)),files=report)
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'docs/design/pass-b-derived-audio.json').write_text(json.dumps(manifest,indent=2)+'\n')
    backup=ROOT/'.qa/pass-b/presentation-recordings.zip'
    backup.parent.mkdir(parents=True,exist_ok=True)
    originals=list(SOURCE.glob('*'))
    files=originals+list(DEST.glob('*'))+[ROOT/'Assets/Sound Hub/opening/encounter-sources.json']
    with zipfile.ZipFile(backup,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(backup) as archive:
        for path in files:
            assert hashlib.sha256(archive.read(path.relative_to(ROOT).as_posix())).hexdigest()==sha(path)
    (backup.parent/'presentation-backup.json').write_text(json.dumps(dict(
        backup=backup.relative_to(ROOT).as_posix(),sha256=sha(backup),verified_files=len(files),
        off_device=False,files={p.relative_to(ROOT).as_posix():sha(p) for p in files}),indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('name','duration_seconds','peak')} for r in report],indent=2))


if __name__=='__main__':main()

"""Offline review exports and immutable source verification."""
from pathlib import Path
import subprocess,json,hashlib,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent

def run(args):
    subprocess.run(['ffmpeg','-y','-v','error',*map(str,args)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)

for variant in ('B2-foundation','B3-resonant'):
    run(['-i',ROOT/'.qa/pass1/opening1080/source-opening-silent.mp4',
         '-i',OUT/'audio'/f'{variant}.wav','-stream_loop','-1','-i',ROOT/'.qa/pass1/audio/ambience-B.wav',
         '-i',ROOT/'Assets/Sound Hub/opening/panoir-you-have-time.ogg',
         '-filter_complex','[1:a]volume=0.7,adelay=13000|13000[r];[2:a]volume=0.18[a];[3:a]volume=0.3[p];[r][a][p]amix=inputs=3:duration=longest:normalize=0[m]',
         '-map','0:v','-map','[m]','-t',32,'-c:v','copy','-c:a','aac','-b:a','256k',OUT/'audio'/f'{variant}-in-scene.mp4'])

# Retain a loudness-controlled B reference: this is explicitly a remaster,
# not the original master, so volume alone cannot win the comparison.
reference=OUT/'audio/B-reference-limited.wav'
run(['-i',ROOT/'.qa/pass1/audio/rise-B.wav','-af','alimiter=limit=0.07:attack=5:release=140:level=false:latency=true',reference])
with wave.open(str(reference)) as f:
    data=np.frombuffer(f.readframes(f.getnframes()),'<i2').reshape(-1,2)/32768
gain=min(.075/float(np.sqrt(np.mean(data**2))),.71/float(abs(data).max()))
with wave.open(str(OUT/'audio/B-level-matched-reference.wav'),'wb') as f:
    f.setparams((2,2,48000,0,'NONE','not compressed'));f.writeframes((data*gain*32767).astype('<i2').tobytes())
run(['-i',OUT/'audio/B-level-matched-reference.wav','-c:a','libmp3lame','-q:a',2,OUT/'audio/B-level-matched-reference.mp3'])
(OUT/'audio/comparison.json').write_text(json.dumps(dict(reference_original=str(ROOT/'.qa/pass1/audio/rise-B.wav'),reference_processing='5 ms lookahead peak limiting, then RMS gain. Originals untouched.',reference_rms=float(np.sqrt(np.mean((data*gain)**2))),candidate_rms=.075,scene='Offline mix over unchanged native 1080p video, rise starts at 13 seconds. Not runtime loopback.'),indent=2))
before=json.loads((ROOT/'.qa/pass1/preservation-before.json').read_text())
verification=[]
for name,record in before.items():
    path=Path(name);digest=hashlib.sha256(path.read_bytes()).hexdigest()
    verification.append(dict(path=name,unchanged=digest==record['sha256']))
assert all(r['unchanged'] for r in verification)
(OUT/'preservation.json').write_text(json.dumps(verification,indent=2))
previous=json.loads((ROOT/'.qa/pass1/preservation-after.json').read_text())['final_source_hashes']
source_checks={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in previous.items()}
assert all(source_checks.values())
mix_checks={}
for variant in ('B2-foundation','B3-resonant'):
    file=OUT/'audio'/f'{variant}-in-scene.mp4'
    result=subprocess.run(['ffmpeg','-v','error','-i',str(file),'-vn','-ac','2','-ar','48000','-f','f32le','-'],stdout=subprocess.PIPE,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    data=np.frombuffer(result.stdout,'<f4')
    peak=float(abs(data).max());assert np.isfinite(data).all() and peak<1
    mix_checks[variant]=dict(decoded=True,peak=peak,clipped_samples=int((abs(data)>=1).sum()))
(OUT/'verification.json').write_text(json.dumps(dict(previous_production_sources_unchanged=source_checks,mixes=mix_checks),indent=2))
print('Verified',len(verification),'preservation targets; review exports completed.')

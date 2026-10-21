"""Assemble review media; never copy source recordings or installed executables."""
from pathlib import Path
import shutil,json,subprocess,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2];QA=Path(__file__).parent
OUT=ROOT/'docs/reviews/pass1-complete'
for sub in ('native','audio','performance','verification','reproduction'):(OUT/sub).mkdir(parents=True,exist_ok=True)
def copy(src,dst):shutil.copy2(src,OUT/dst)
def run(args):subprocess.run([str(a) for a in args],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
def decode(path):
 p=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-ar','48000','-ac','2','-f','f32le','-'],stdout=subprocess.PIPE,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 return np.frombuffer(p.stdout,'<f4').reshape(-1,2)
def encode(data,path):
 subprocess.run(['ffmpeg','-y','-v','error','-f','f32le','-ar','48000','-ac','2','-i','-','-c:a','libmp3lame','-q:a','2',str(path)],input=data.astype('<f4').tobytes(),check=True,creationflags=subprocess.CREATE_NO_WINDOW)
audio=ROOT/'Assets/Sound Hub';rate=48000
base=np.zeros((32*rate,2),dtype='float32')
def layer(target,data,start,gain):
 n=min(len(data),len(target)-round(start*rate))
 target[round(start*rate):round(start*rate)+n]+=data[:n]*gain
layer(base,decode(audio/'opening/piano-chapters/01-one.ogg'),0,.32)
layer(base,decode(audio/'opening/abyss-bed.wav'),0,.08)
layer(base,decode(audio/'dig/stone1.ogg'),5,.192)
layer(base,decode(audio/'block/lodestone/place1.ogg'),23,.28)
mixes={}
for name in ('ground','chamber'):
 mix=base.copy();layer(mix,decode(QA/f'audio/B4-{name}.wav'),13,.704)
 assert np.isfinite(mix).all() and abs(mix).max()<1
 track=QA/f'audio/in-scene-{name}.mp3';encode(mix,track)
 run(['ffmpeg','-y','-v','error','-i',QA/'opening1080/source-opening-silent.mp4','-i',track,'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',OUT/f'audio/opening-B4-{name}.mp4'])
 copy(QA/f'audio/B4-{name}.mp3',f'audio/B4-{name}.mp3')
 mixes[name]=dict(peak=float(abs(mix).max()),type='Offline synchronized audition, not loopback',rise_at=13,piano_gain=.32,ambient_gain=.08,rise_gain=.704,place_at=5,settle_at=23,omitted='Orbit and contact hover depend on real input; not reconstructed here')
(OUT/'audio/mix-provenance.json').write_text(json.dumps(mixes,indent=2))
cues=[];parts=[]
for name in ('open','select','focus','success','cancel','failure'):
 data=decode(audio/f'ui/workshop/{name}.ogg');parts.extend([data*.48,np.zeros((rate,2))]);cues.append(name)
encode(np.concatenate(parts),OUT/'audio/ui-cues.mp3')
(OUT/'audio/ui-cues.json').write_text(json.dumps(dict(order=cues,gain=.48,gap_seconds=1),indent=2))
parts=[];piano=[];at=0
for path in sorted((audio/'opening/piano-chapters').glob('*.ogg')):
 data=decode(path)
 for edge,part in [('start',data[:12*rate]),('end',data[-12*rate:])]:
  parts.extend([part,np.zeros((rate,2))]);piano.append(dict(file=path.name,edge=edge,audition_start=at,seconds=12));at+=13
encode(np.concatenate(parts),OUT/'audio/piano-boundaries.mp3')
(OUT/'audio/piano-boundaries.json').write_text(json.dumps(piano,indent=2))
for name in ('analysis.json','cue-sheet.json','piano-cue-sheet.json'):copy(QA/'audio'/name,'audio/'+name)
copy(QA/'audio/sources/provenance.json','audio/source-provenance.json')
for name in ('run_performance.py','final_native.py','opening_capture.py','render_audio.py','prepare_piano.py','analyze_audio.py','assemble_review.py'):
 copy(QA/name,'reproduction/'+name)
for path in (QA/'native-matrix2').glob('*.png'):copy(path,'native/'+path.name)
copy(QA/'native-matrix2/matrix.json','native/matrix-iteration2.json')
for path in (QA/'native-final').glob('*.png'):copy(path,'native/final-'+path.name)
copy(QA/'native-final/report.json','native/final-checks.json')
for name in ('native-18.00.png','native-26.00.png'):copy(QA/'opening1080'/name,'native/opening-'+name)
copy(QA/'opening1080/report.json','performance/opening1080.json')
copy(QA/'performance1080.json','performance/editor1080.json')
copy(QA/'staging-profile.json','performance/staging-profile.json')
copy(QA/'native-mouse-verified.mp4','native/mouse-interactions.mp4')
credits=audio/'opening/PASS1_B4_CREDITS.txt'
credits.write_text(credits.read_text().replace('license downloaded','license terms retrieved'),encoding='utf-8')
copy(credits,'audio/CREDITS.txt')
copy(audio/'ui/workshop/CREDITS.txt','audio/UI_CREDITS.txt')
print('Review media assembled:',OUT)

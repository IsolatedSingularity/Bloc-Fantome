"""Offline reference mixes, separate from muted native playback and human approval."""
import os,sys,json,wave
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path.cwd()/'Code'))
import pygame,numpy as np
from ui.feedback import CUES
pygame.mixer.init(frequency=44100,size=-16,channels=2)
rate=44100
out=Path('docs/reviews/pass-b/finalization');out.mkdir(parents=True,exist_ok=True)
source=Path('.qa/pass-b-finalization/native-final-source')
report=json.loads((source/'report.json').read_text())
first=report['presented_frames'][0]['seconds'];end=report['presented_frames'][-1]['seconds']
sounds={key:pygame.sndarray.array(pygame.mixer.Sound(str(Path('Assets/Sound Hub/ui/selected')/value[0]))).astype(np.float64)/32768 for key,value in CUES.items()}
def add(mix,sound,start,gain,length=None,fade=False):
 i=round(start*rate);a=sound[:round(length*rate) if length is not None else len(sound)].copy()*gain
 if fade and len(a)>round(.12*rate):a[-round(.12*rate):]*=np.linspace(1,0,round(.12*rate))[:,None]
 n=min(len(a),len(mix)-i)
 if n>0:mix[i:i+n]+=a[:n]
def save(name,mix):
 peak=float(abs(mix).max());clipped=int((abs(mix)>1).sum())
 assert not clipped
 with wave.open(str(out/name),'wb') as f:
  f.setparams((2,2,rate,0,'NONE','not compressed'));f.writeframes((mix*32767).astype('<i2').tobytes())
 return dict(file=name,seconds=len(mix)/rate,peak=peak,clipped_samples=clipped)
mix=np.zeros((round((end-first+1/60)*rate),2))
for index,event in enumerate(report['cues']):
 start=max(0,event['seconds']-first);key=event['cue'];length=len(sounds[key])/rate
 next_same=next((e for e in report['cues'][index+1:] if e['channel']==event['channel']),None)
 if next_same:length=min(length,next_same['seconds']-event['seconds'])
 if key=='shutdown':length=min(length,.62)
 add(mix,sounds[key],start,CUES[key][1]*.5*.72,length,key=='shutdown')
results=[save('presented-cues-reference.wav',mix)]
old={'button':.48,'close':.42,'world_map':.52,'save':.5,'error':.48,'boot':.48,'shutdown':.48}
rain=pygame.sndarray.array(pygame.mixer.Sound('Assets/Sound Hub/ambient/weather/rain1.ogg')).astype(np.float64)/32768
for label,gains,bus in [('before',old,1),('after',{k:v[1] for k,v in CUES.items()},.6)]:
 mix=np.tile(rain,(int(np.ceil(15*rate/len(rain))),1))[:15*rate]*.8*.55*.5*.72*bus
 for n,key in enumerate(('boot','button','close','world_map','save','error','shutdown')):
  add(mix,sounds[key],.3+n*2,gains[key]*.5*.72,.62 if key=='shutdown' else None,key=='shutdown')
 results.append(save('balance-'+label+'.wav',mix))
(out/'audio-reference.json').write_text(json.dumps(dict(type='offline reference, not speaker loopback',effects=.5,ambient=.8,headroom=.72,rain='rain1.ogg loop; matched ambience reference, not full live weather',cue_order=['boot','button','close','world_map','save','error','shutdown'],results=results),indent=2))
print(json.dumps(results,indent=2));pygame.quit()

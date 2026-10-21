from pathlib import Path
import subprocess,json,hashlib,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent/'audio';SC=Path('C:/Program Files/SuperCollider-3.14.1')
sources={k:OUT/'sources'/(k+'.wav') for k in ('stone_tension','metal_tension','scree','debris')}
sources['mechanism']=ROOT/'.qa/encounter/audio/sources/mechanism.wav'
sources['drain']=ROOT/'.qa/encounter/audio/sources/drain.wav'
names=list(sources);report={};cues={}
def run(args,log):
 with (OUT/log).open('w') as f:r=subprocess.run([str(a) for a in args],stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
 if r.returncode or 'ERROR:' in (OUT/log).read_text(errors='replace'):raise RuntimeError(log)
def decode(path):
 r=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-ac','2','-ar','48000','-f','f32le','-'],stdout=subprocess.PIPE,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 return np.frombuffer(r.stdout,'<f4').reshape(-1,2).copy()
for variant in ('B4-ground','B4-chamber'):
 chamber=variant.endswith('chamber');events=[]
 def cue(t,role,src,**params):events.append((t,role,src,params))
 cue(.04,'foundation strain','mechanism',start=13,rate=.24,dur=13.2,attack=1.1,release=3.2,amp=3.7,lo=28,hi=400,wet=.6,resonance=2.2)
 cue(.15,'stone load spreading','stone_tension',start=135,rate=.43 if chamber else .36,dur=13.5,attack=1.3,release=3,amp=3.6,lo=30,hi=1400,wet=.65 if chamber else .3,resonance=2.6 if chamber else .7)
 cue(.5,'air displaced under the floor','drain',start=19,rate=.39,dur=12.6,attack=2.1,release=3.0,amp=1.7,lo=30,hi=240,wet=.25)
 cue(1.1,'fractures moving through masonry','scree',start=.4,rate=.38,dur=11.4,attack=1.4,release=2.5,amp=.9,lo=110,hi=1800,wet=.45,pan=-.12)
 cue(5.4,'vault structural tension','metal_tension',start=111,rate=.33,dur=9.8,attack=2,release=3.0,amp=21 if chamber else 10,lo=55,hi=520,wet=.8,resonance=1.5 if chamber else .2)
 for i,t in enumerate((.65,3.25,6.8,10.3,12.1)):
  cue(t,'load seating in joints','debris',start=0,rate=(.38,.46,.31,.43,.53)[i],dur=3.1 if i<3 else 2.7,attack=.08,release=1.8,amp=(.7,.6,.8,.55,.38)[i],lo=35,hi=1200,wet=.7,pan=(-1)**i*.1)
 cue(11.0,'late grit and settling reflection','scree',start=5.5,rate=.57,dur=4.8,attack=.3,release=3.4,amp=.75,lo=90,hi=1700,wet=.7,pan=.16)
 lines=[]
 for i,(t,role,src,params) in enumerate(events):
  args=['\\mass',str(1000+i),'0','0','\\buf',str(names.index(src))]
  for k,v in params.items():args+=['\\'+k,str(v)]
  lines.append(f'add.value({t},[\\s_new,'+','.join(args)+']);')
 code=(ROOT/'.qa/pass1-revision2/audio_study.scd').read_text().replace('@WORK@',OUT.as_posix()).replace('@SOURCES@',json.dumps([p.as_posix() for p in sources.values()])).replace('@EVENTS@','\n'.join(lines)).replace('add.value(16,','add.value(17,')
 script=OUT/(variant+'.scd');script.write_text(code)
 run([SC/'sclang.exe','-D',script],variant+'-sclang.log')
 raw=OUT/(variant+'-raw.wav');run([SC/'scsynth.exe','-N',OUT/'score.osc','_',raw,'48000','WAV','float','-D','0','-o','2','-i','0','-m','262144'],variant+'-scsynth.log')
 limited=OUT/(variant+'-limited.wav');run(['ffmpeg','-y','-v','error','-i',raw,'-af','alimiter=limit=0.3:attack=5:release=180:level=false:latency=true','-c:a','pcm_f32le',limited],variant+'-limit.log')
 data=decode(limited);gain=min(.075/max(float(np.sqrt(np.mean(data**2))),1e-9),.71/max(float(abs(data).max()),1e-9));data*=gain
 dest=OUT/(variant+'.wav')
 with wave.open(str(dest),'wb') as f:f.setparams((2,2,48000,0,'NONE','not compressed'));f.writeframes((data*32767).astype('<i2').tobytes())
 run(['ffmpeg','-y','-v','error','-i',dest,'-c:a','libmp3lame','-q:a','2',OUT/(variant+'.mp3')],variant+'-mp3.log')
 mono=data.mean(axis=1);freq=np.fft.rfftfreq(len(mono),1/48000);power=abs(np.fft.rfft(mono))**2
 report[variant]=dict(seconds=len(data)/48000,peak=float(abs(data).max()),rms=float(np.sqrt(np.mean(data**2))),low_30_180=float(power[(freq>=30)&(freq<180)].sum()/power.sum()),tail_rms_12_16=float(np.sqrt(np.mean(data[12*48000:16*48000]**2))),finite=bool(np.isfinite(data).all()),sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
 cues[variant]=events;print(variant,report[variant],flush=True)
(OUT/'analysis.json').write_text(json.dumps(report,indent=2));(OUT/'cue-sheet.json').write_text(json.dumps(cues,indent=2))

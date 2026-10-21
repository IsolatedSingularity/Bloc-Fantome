"""Revised B studies. Original recordings, licenses and earlier auditions stay intact."""
import pathlib, subprocess, json, hashlib, wave
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent/'audio';OUT.mkdir(exist_ok=True)
SC=pathlib.Path('C:/Program Files/SuperCollider-3.14.1')
sources={key:ROOT/f'.qa/encounter/audio/sources/{key}.wav' for key in ('stone','mechanism','drain','chain')}
names=list(sources);report={};cues={}

def run(args,log):
    with (OUT/log).open('w') as f:
        p=subprocess.run([str(a) for a in args],stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
    if p.returncode or 'ERROR:' in (OUT/log).read_text(errors='replace'):raise RuntimeError(log)

def decode(path):
    p=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-ac','2','-ar','48000','-f','f32le','-'],stdout=subprocess.PIPE,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    return np.frombuffer(p.stdout,'<f4').reshape(-1,2).copy()

def stats(data):
    mono=data.mean(axis=1);freq=np.fft.rfftfreq(len(mono),1/48000);power=abs(np.fft.rfft(mono))**2
    rms=float(np.sqrt(np.mean(data**2)));peak=float(abs(data).max())
    return dict(seconds=len(data)/48000,peak=peak,rms=rms,crest_db=float(20*np.log10(peak/max(rms,1e-9))),
        energy_below_180hz=float(power[(freq>=30)&(freq<180)].sum()/power.sum()),
        mono_rms=float(np.sqrt(np.mean(mono**2))),finite=bool(np.isfinite(data).all()))

for variant in ('B2-foundation','B3-resonant'):
    resonant=variant.startswith('B3'); wet=.65 if resonant else .42
    events=[]
    def cue(t,role,src,**kwargs):events.append((t,role,src,kwargs))
    # 24-28s is sustained stone handling; 32-36s in B contained long weak regions.
    cue(.04,'foundation strain','mechanism',start=13,rate=.24,dur=11.8,attack=1.3,release=2.8,amp=5.0,lo=28,hi=360,wet=wet,resonance=2.8 if resonant else .4)
    cue(.3,'moving masonry body','stone',start=24,rate=.32,dur=11.4,attack=1.2,release=2.4,amp=8,lo=38,hi=950,wet=wet,pan=-.12,resonance=1.6 if resonant else .3)
    cue(1.0,'second load path','stone',start=48,rate=.43,dur=10.5,attack=1.7,release=2.1,amp=5,lo=46,hi=730,wet=wet,pan=.14,resonance=1.2 if resonant else 0)
    cue(.12,'air displaced through foundations','drain',start=19,rate=.39,dur=12.2,attack=2.3,release=2.8,amp=2.7,lo=32,hi=260,wet=.22)
    cue(2,'surface texture','stone',start=13,rate=.64,dur=7.8,attack=1.1,release=1.5,amp=.65,lo=260,hi=1900,wet=.3,pan=-.25)
    # Deliberately irregular compression/release, no regular machine-like pulse.
    for i,t in enumerate((.45,3.1,6.8,9.7,10.8)):
        cue(t,'foundation release','stone',start=(24.1,16.1,56.1,25.0,43.1)[i],rate=.27 if not resonant else .33,dur=2.4,attack=.10,release=1.75,amp=2.8 if i<4 else .7,lo=32,hi=560,wet=wet,pan=(-1)**i*.12)
    if resonant:
        cue(7.7,'vault resonance','mechanism',start=31,rate=.37,dur=5.5,attack=1.3,release=2.5,amp=3.2,lo=55,hi=480,wet=.85,resonance=3)
    else:
        cue(9.1,'weight settling into place','stone',start=58,rate=.38,dur=3.7,attack=.3,release=2.5,amp=3.6,lo=32,hi=1200,wet=.5)
    lines=[]
    for i,(t,role,src,params) in enumerate(events):
        args=['\\mass',str(1000+i),'0','0','\\buf',str(names.index(src))]
        for k,v in params.items():args+=['\\'+k,str(v)]
        lines.append(f'add.value({t},[\\s_new,'+','.join(args)+']);')
    code=(OUT.parent/'audio_study.scd').read_text().replace('@WORK@',OUT.as_posix()).replace('@SOURCES@',json.dumps([p.as_posix() for p in sources.values()])).replace('@EVENTS@','\n'.join(lines))
    script=OUT/(variant+'.scd');script.write_text(code)
    run([SC/'sclang.exe','-D',script],variant+'-sclang.log')
    raw=OUT/(variant+'-raw.wav')
    run([SC/'scsynth.exe','-N',OUT/'score.osc','_',raw,'48000','WAV','float','-D','0','-o','2','-i','0','-m','262144'],variant+'-scsynth.log')
    # Control sparse needle peaks before mastering, rather than letting one
    # transient reduce the entire 12-second movement. Preserve the raw render.
    limited=OUT/(variant+'-limited.wav')
    run(['ffmpeg','-y','-v','error','-i',raw,'-af','alimiter=limit=0.3:attack=5:release=140:level=false:latency=true','-c:a','pcm_f32le',limited],variant+'-limit.log')
    data=decode(limited);assert np.isfinite(data).all()
    # Fixed RMS target for the two new candidates, with a common peak ceiling.
    gain=min(.075/max(float(np.sqrt(np.mean(data**2))),1e-9),.71/max(float(abs(data).max()),1e-9))
    data*=gain
    dest=OUT/(variant+'.wav')
    with wave.open(str(dest),'wb') as w:
        w.setparams((2,2,48000,0,'NONE','not compressed'));w.writeframes((data*32767).astype('<i2').tobytes())
    report[variant]=dict(**stats(data),gain=gain)
    run(['ffmpeg','-y','-v','error','-i',dest,'-c:a','libmp3lame','-q:a','2',OUT/(variant+'.mp3')],variant+'-mp3.log')
    cues[variant]=events
    print(variant,report[variant],flush=True)
report['original-B']=stats(decode(ROOT/'.qa/pass1/audio/rise-B.wav'))
records=json.loads((ROOT/'.qa/encounter/audio/sources.json').read_text())
(OUT/'analysis.json').write_text(json.dumps(report,indent=2))
(OUT/'cue-sheet.json').write_text(json.dumps(cues,indent=2))
(OUT/'provenance.json').write_text(json.dumps(dict(sources=[dict(id=k,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in sources.items()],licenses=[r for r in records if r['id'] in names],quality='Existing local decoded HQ preview recordings, not newly acquired lossless masters.',audition='Objective signal validation completed; owner listening needed. No claim of assistant hearing.',intent='B2 sustained physical foundation; B3 longer pitched architectural resonance. No creature vocal source.',sonniss='Earlier selective download blocked; no Sonniss media used.'),indent=2))

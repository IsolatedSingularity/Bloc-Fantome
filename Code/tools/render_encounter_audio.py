"""Small headless SuperCollider workbench for the private opening sequence."""
import json,subprocess,wave
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'.qa/encounter/audio'
DEST=ROOT/'Assets/Sound Hub/opening'
SC=Path(r'C:\Program Files\SuperCollider-3.14.1')


def run(command,log,timeout=90):
    with log.open('w') as handle:
        result=subprocess.run([str(v) for v in command],stdout=handle,stderr=subprocess.STDOUT,
                              timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    text=log.read_text(errors='replace')
    if result.returncode or 'ERROR:' in text or 'FAILURE IN SERVER' in text:raise RuntimeError(str(log))


def main():
    records=json.loads((WORK/'sources.json').read_text())
    ids={r['id']:i for i,r in enumerate(records)}
    paths=[];durations={}
    for row in records:
        name=row['id'];path=WORK/'sources'/(name+'.wav')
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',WORK/'sources'/(name+'.mp3'),
             '-ar','48000','-ac','2',path],WORK/(name+'-decode.log'))
        paths.append(path.as_posix())
        with wave.open(str(path),'rb') as f:durations[name]=f.getnframes()/f.getframerate()
    template=Path(__file__).with_name('encounter_audio.scd').read_text()
    report={}
    for cue,duration in [('sanctuary-rise',11.5),('monument-move',4.6),('abyss-bed',34),('encounter',44)]:
        events=[]
        def event(time,kind,source,**parameters):
            args=[f'\\{kind}',str(1000+len(events)),'0','0','\\buf',str(ids[source])]
            for key,value in parameters.items():args.extend(('\\'+key,str(value)))
            events.append(f'add.value({time},[\\s_new,'+','.join(args)+']);')
        if cue=='sanctuary-rise':
            event(.12,'material','stone',amp=.95,rate=.31,start=7,dur=10.7,cutoff=700)
            event(.2,'material','mechanism',amp=.55,rate=.44,start=10,dur=10.5,cutoff=420)
            event(9.4,'contact','stone',amp=.7,rate=.35,start=24,dur=1.7)
        elif cue=='monument-move':
            event(.12,'material','stone',amp=.6,rate=.52,start=32,dur=4.1,cutoff=620)
        elif cue=='abyss-bed':
            event(.12,'material','drain',amp=.27,rate=.71,start=4,dur=33,cutoff=220)
            event(.12,'material','mechanism',amp=.12,rate=.43,start=15,dur=33,cutoff=320,pan=-.3)
        else:
            event(.12,'material','stone',amp=.4,rate=.41,start=4,dur=42.6,cutoff=350)
            event(.12,'material','drain',amp=.38,rate=.68,start=9,dur=42.6,cutoff=250,pan=.2)
            event(1.1,'buriedVoice','whisper',amp=.28,rate=.73,dur=35,cutoff=390,pan=-.6)
            for i,time in enumerate((1.9,2.9,3.9,4.9,6.7,7.8,8.7,9.8)):
                event(time,'contact','stone',amp=.16+i*.045,rate=.38+i*.012,start=8+i*4.1,pan=(-1)**i*.4)
            for i in range(22):
                name=f'voice{i%11+1:02d}';rate=.57+(i%5)*.055
                event(5.2+i*1.43,'buriedVoice',name,amp=.5+(i%4)*.09,rate=rate,
                      dur=min(7.5,durations[name]/rate+.35),cutoff=720+(i%6)*125,pan=(-1)**i*(.25+i%3*.16))
            for time,start in ((20.5,11),(25.45,22),(26.55,31),(27.65,36),(32.6,41),(35.4,49)):
                event(time,'contact','stone',amp=.8,rate=.27,start=start,pan=.1,dur=2.2)
            event(30,'material','chain',amp=.4,rate=.22,start=0,dur=12.5,cutoff=1200)
            event(31,'material','stone',amp=.75,rate=.37,start=30,dur=12,cutoff=900)
        script=template.replace('@WORK@',WORK.as_posix()).replace('@DURATION@',str(duration))
        script=script.replace('@SOURCES@',json.dumps(paths)).replace('@EVENTS@','\n'.join(events))
        job=WORK/(cue+'.scd');job.write_text(script)
        run([SC/'sclang.exe','-D',job],WORK/(cue+'-sclang.log'))
        raw=WORK/(cue+'-raw.wav')
        # SC 3.14.1 on this machine crashes on destruction of even a minimal
        # Limiter UGen. Render unclipped float instead, then apply a measured
        # constant delivery gain. This is mastering, not a synthesis fallback.
        run([SC/'scsynth.exe','-N',WORK/'score.osc','_',raw,'48000','WAV','float','-D','0','-o','2','-i','0','-m','262144'],WORK/(cue+'-scsynth.log'))
        decoded=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(raw),'-f','f32le','-'],
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        samples=np.frombuffer(decoded.stdout,dtype='<f4').reshape(-1,2).astype(float)
        if cue=='abyss-bed':
            samples=samples[48000:-48000];n=2*48000;fade=np.linspace(0,1,n)[:,None]
            samples=np.concatenate((samples[-n:]*(1-fade)+samples[:n]*fade,samples[n:-n]))
        peak=float(abs(samples).max());assert peak>.0001 and np.isfinite(samples).all()
        # Fixed ceiling preserves internal dynamics, with conservative mix headroom.
        samples*=({'abyss-bed':.12,'monument-move':.5}.get(cue,.66)/peak)
        output=DEST/(cue+'.wav')
        with wave.open(str(output),'wb') as f:
            f.setparams((2,2,48000,0,'NONE','not compressed'));f.writeframes((samples*32767).astype('<i2').tobytes())
        report[cue]=dict(seconds=len(samples)/48000,peak=float(abs(samples).max()),rms=float(np.sqrt(np.mean(samples*samples))),events=len(events))
    (WORK/'analysis.json').write_text(json.dumps(report,indent=2))
    (DEST/'encounter-sources.json').write_text(json.dumps(records,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

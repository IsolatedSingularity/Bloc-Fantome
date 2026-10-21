from pathlib import Path
import subprocess,numpy as np,json
root=Path('.qa/pass1-complete/audio');report={}
for file in (root/'sources').glob('*.wav'):
 p=subprocess.run(['ffmpeg','-v','error','-i',str(file),'-ar','16000','-ac','1','-f','f32le','-'],stdout=subprocess.PIPE,check=True)
 a=np.frombuffer(p.stdout,'<f4');windows=[]
 for i in range(0,len(a)-16000,16000):
  x=a[i:i+16000];f=np.fft.rfftfreq(len(x),1/16000);power=abs(np.fft.rfft(x))**2
  windows.append(dict(t=i/16000,rms=round(float(np.sqrt(np.mean(x*x))),4),low=round(float(power[(f>30)&(f<180)].sum()/max(1e-10,power.sum())),3)))
 report[file.stem]=dict(duration=len(a)/16000,peak=float(abs(a).max()),windows=windows)
 print(file.stem,len(a)/16000,sorted(windows,key=lambda x:x['rms'],reverse=True)[:8])
(root/'source-analysis.json').write_text(json.dumps(report,indent=2))

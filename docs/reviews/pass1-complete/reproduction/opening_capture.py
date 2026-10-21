"""Deterministic native GPU capture, separate from unprofiled frame timing."""
import os,sys,pathlib,json,time,subprocess,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame,blocFantome as b
from unittest.mock import patch
from ui.opening_audio import OPENING_CHANNELS
OUT=ROOT/'.qa/pass1-complete/opening1080';OUT.mkdir(exist_ok=True)
sys.argv.append('--opening-windowed')
b.APP_CONFIG_FILE=str(OUT/'config.json')
with patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'):
 app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
 app.assetManager.loadAllAssets();app._createInitialFloor();app._applyWindowSize(1920,1080)
 app._openOpeningScene();s=app.openingScene
 assert s.gpu is not None
 # Hidden window is still a native WGL render, explicitly distinct from OS input QA.
 from pygame._sdl2 import Window
 app._displayWindow.hide()
 s.resize((1920,1080))
 proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080','-framerate','20','-i','-','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p',str(OUT/'source-opening-silent.mp4')],stdin=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 events=[];frames=[]
 piano_path=str(app._openingPiano.current_path)
 try:
  for frame in range(32*20):
   t=frame/20
   if frame==100:s.place();events.append(dict(t=t,event='place'))
   if frame==200:s.activate('door');events.append(dict(t=t,event='door / approach'))
   if frame==550:s.target_angle+=35;events.append(dict(t=t,event='orbit'))
   s.update(.05);s.render(app.screen)
   capture=s.gpu.capture(s.size)
   assert capture.get_size()==(1920,1080),capture.get_size()
   if frame in (80,180,260,360,460,520,600):pygame.image.save(capture,OUT/f'native-{t:05.2f}.png')
   proc.stdin.write(pygame.image.tostring(capture,'RGB'));pygame.event.pump()
 finally:proc.stdin.close();assert proc.wait(timeout=60)==0
 # No encoding/readback in the following sustained rendering interval.
 for i in range(360):
  s.update(1/60);started=time.perf_counter();s.render(app.screen);s.gpu.gl.glFinish()
  frames.append((time.perf_counter()-started)*1000)
 gl=s.gpu.gl
 # Exercise both native context recreations and render the restored scene.
 for windowed in (True,False):app._setOpeningDisplay(windowed);s.render(app.screen)
 s.activate('heart');s.update(.1)
 channels={name:dict(busy=pygame.mixer.Channel(index).get_busy(),gain=pygame.mixer.Channel(index).get_volume()) for name,index in OPENING_CHANNELS.items()}
 s.update(44);app._closeOpeningScene()
 report=dict(native_backend='Windows/WGL',size=[1920,1080],video_fps=20,audio='Dummy mixer; video is silent, not loopback evidence',events=events,frames_ms=frames,
  p50=sorted(frames)[180],p95=sorted(frames)[341],p99=sorted(frames)[356],max=max(frames),over50=sum(v>50 for v in frames),over100=sum(v>100 for v in frames),
  context_recreations=2,channels=channels,closed_channels=not any(pygame.mixer.Channel(i).get_busy() for i in OPENING_CHANNELS.values()),
  piano_path=piano_path,source_sha256=hashlib.sha256((ROOT/'Code/ui/opening_scene.py').read_bytes()).hexdigest())
 (OUT/'report.json').write_text(json.dumps(report,indent=2));app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()

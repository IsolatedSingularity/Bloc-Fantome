import sys,os,time,faulthandler,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Code'))
faulthandler.enable()
os.environ['SDL_VIDEODRIVER']='windows';pass
from blocFantome import BlocFantome,pygame
app=BlocFantome();original=app._handleEvents;done=None;step=0
app._saveAppConfig=lambda:None

def events():
 global done,step
 original()
 s=app.openingScene
 if s:
  if s.ready and step==0:
   s.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=s.renderer.worldToScreen(*s.TARGET)));step=1;print('PLACED',flush=True)
  elif s.complete and s.phase=='shrine' and step==1:
   s.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=s.renderer.project((.5,-1,4.7))[:2]));step=2;print('DOOR',flush=True)
  elif s.phase=='sanctuary' and step==2:
   s.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=s.project_sanctuary((1,-25,35))[:2]));step=3;print('HEART',s.awakened_at,flush=True)
  elif s.awakened_at is not None and s.elapsed-s.awakened_at>2 and step==3:
   pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=s.return_rect.center));step=4;print('RETURN',flush=True)
 elif step==4:
  if done is None:done=time.perf_counter();print('RESTORED',app.screen.get_size(),flush=True)
  elif time.perf_counter()-done>3:app.running=False
app._handleEvents=events
original_splash=app._showSplashScreen
def splash_check(splash=None):
 print('SPLASH SIZES',splash.artwork_rect.size,pygame.display.get_window_size(),app.screen.get_size(),flush=True)
 assert all(abs(a-b)<=1 for a,b in zip(splash.artwork_rect.size,pygame.display.get_window_size()))
 splash.present()
 pygame.image.save(app.screen,ROOT/'.qa/sanctuary-295/splash-native.png')
 print('SPLASH FIT',pygame.display.get_window_size(),flush=True)
 return original_splash(splash)
app._showSplashScreen=splash_check
app.run();print('COMPLETE',step,flush=True)
assert step==4


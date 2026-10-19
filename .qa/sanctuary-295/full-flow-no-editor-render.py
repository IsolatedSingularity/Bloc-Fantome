import sys,os,time,faulthandler,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Code'))
faulthandler.enable()
os.environ['SDL_VIDEODRIVER']='windows';sys.argv.append('--opening-windowed')
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
   s.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=s.renderer.project((1,-19,13))[:2]));step=3;print('ALTAR',s.awakened_at,flush=True)
  elif s.awakened_at is not None and s.elapsed-s.awakened_at>2 and step==3:
   pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=s.return_rect.center));step=4;print('RETURN',flush=True)
 elif step==4:
  if done is None:done=time.perf_counter();print('RESTORED',app.screen.get_size(),flush=True)
  elif time.perf_counter()-done>3:app.running=False
app._handleEvents=events
original_render=app._render
def isolated_render():
 if step==4 and app.openingScene is None:
  app.screen.fill((20,30,40));pygame.display.flip()
 else:original_render()
app._render=isolated_render
app.run();print('COMPLETE',step,flush=True)
assert step==4

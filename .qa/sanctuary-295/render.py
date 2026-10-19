import os,sys,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
import pygame,numpy as np
from ui.opening_scene import OpeningScene
from ui.presentation_renderer import PresentationRenderer
pygame.init();pygame.mixer.set_num_channels(32)
pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
screen=pygame.display.set_mode((1920,1080),pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN)
s=OpeningScene(screen.get_size(),None,effects_volume=0);s.gpu=PresentationRenderer()
def capture(name):
 s.render(screen);pygame.image.save(s.gpu.capture(s.size),ROOT/f'.qa/sanctuary-295/{name}.png');pygame.display.flip()
s.update(4.5);capture('shrine-ready')
print('ghost',s.renderer.worldToScreen(*s.TARGET),s.target_at(s.renderer.worldToScreen(*s.TARGET)))
s.place();s.update(4.8);capture('shrine-door')
print('door',s.renderer.project((.5,-1,4.7)),s.target_at(s.renderer.project((.5,-1,4.7))[:2]))
s.activate('door')
last=0
for t in (0,2.2,3.5,5,7.6,9,10.4):
 s.update(t-last);last=t;capture('cinematic-'+str(t))
capture('sanctuary')
print('altar',s.project_sanctuary((1,-19,13)),s.target_at(s.project_sanctuary((1,-19,13))[:2]))
print('cross',s.target_at(s.project_sanctuary((1,-25,35))[:2]))
for a in (90,180,225,315):
 s.renderer.angle=s.target_angle=a;s.update(.1);capture('orbit-'+str(a))
s.renderer.angle=s.target_angle=s.ARRIVAL_ANGLE;s.activate('altar');s.update(2);capture('awakened')
timings=[]
for size in ((1200,800),(1920,1080)):
 screen=pygame.display.set_mode(size,pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN)
 s.gpu=PresentationRenderer();s.resize(size)
 values=[]
 for i in range(70):
  start=time.perf_counter();s.target_angle+=.5;s.pointer=(size[0]//2,size[1]//2);s.update(1/60);s.render(screen);s.gpu.gl.glFinish();pygame.display.flip()
  if i>9:values.append((time.perf_counter()-start)*1000)
 timings.append(dict(size=size,p50_ms=float(np.percentile(values,50)),p95_ms=float(np.percentile(values,95)),max_ms=max(values)))
report=dict(timings=timings,gl_error=s.gpu.gl.glGetError(),renderer=s.gpu.gl.glGetString(0x1F01).decode())
(ROOT/'.qa/sanctuary-295/render-profile.json').write_text(json.dumps(report,indent=2));print(report)
s.close();pygame.quit()

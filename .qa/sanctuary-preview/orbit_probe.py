"""Hidden-window GPU feasibility probe; no app integration or dependency install."""
import os,sys,ctypes as C,math,time,json
from pathlib import Path
import numpy as np
from PIL import Image
from architecture import sanctuary,ROOT,B
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
pygame.init()
pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
pygame.display.set_mode((1920,1080),pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN,vsync=0)
gl=C.WinDLL('opengl32.dll')
def bind(name,restype,args):
 f=getattr(gl,name);f.restype=restype;f.argtypes=args;return f
U=C.c_uint;I=C.c_int;F=C.c_float;D=C.c_double;P=C.c_void_p
for name,args in {
 'glViewport':[I,I,I,I],'glEnable':[U],'glDisable':[U],'glClearColor':[F,F,F,F],
 'glClear':[U],'glMatrixMode':[U],'glLoadIdentity':[], 'glOrtho':[D,D,D,D,D,D],
 'glRotatef':[F,F,F,F],'glTranslatef':[F,F,F],'glVertexPointer':[I,U,I,P],
 'glTexCoordPointer':[I,U,I,P],'glColorPointer':[I,U,I,P],
 'glEnableClientState':[U],'glDrawArrays':[U,I,I],'glFinish':[],
 'glTexParameteri':[U,U,I],'glTexImage2D':[U,I,I,I,I,I,U,U,P],
 'glBlendFunc':[U,U],'glDepthMask':[C.c_ubyte],'glReadPixels':[I,I,I,I,U,U,P],
 'glPixelStorei':[U,I]}.items():bind(name,None,args)
bind('glGetString',C.c_char_p,[U]);bind('glGetError',U,[])
# Existing full-resolution texture sources, one atlas and no generated replacement art.
paths=ROOT/'Assets/Texture Hub/blocks'
textures=['quartz_block_bottom.png','quartz_pillar.png','quartz_pillar_top.png',
          'quartz_bricks.png','chiseled_quartz_block.png','polished_andesite.png',
          'light_blue_stained_glass.png','yellow_stained_glass.png','glowstone.png']
atlas=Image.new('RGBA',(64*len(textures),64))
for n,name in enumerate(textures):
 im=Image.open(paths/name).convert('RGBA').resize((64,64),Image.Resampling.NEAREST)
 if 'stained_glass' in name:
  arr=np.array(im);arr[:,:,3]=np.maximum(75,arr[:,:,3]//2);im=Image.fromarray(arr)
 atlas.paste(im,(n*64,0))
pixels=np.ascontiguousarray(np.array(atlas))
gl.glEnable(0x0DE1);gl.glTexParameteri(0x0DE1,0x2801,0x2600);gl.glTexParameteri(0x0DE1,0x2800,0x2600)
gl.glTexParameteri(0x0DE1,0x2802,0x812F);gl.glTexParameteri(0x0DE1,0x2803,0x812F)
gl.glTexImage2D(0x0DE1,0,0x1908,pixels.shape[1],pixels.shape[0],0,0x1908,0x1401,pixels.ctypes.data)
gl.glEnable(0x0B71);gl.glEnable(0x0BE2);gl.glBlendFunc(0x0302,0x0303)
gl.glClearColor(.016,.034,.055,1)
faces=[((1,0,0),[(1,0,0),(1,1,0),(1,1,1),(1,0,1)]),
       ((-1,0,0),[(0,1,0),(0,0,0),(0,0,1),(0,1,1)]),
       ((0,1,0),[(1,1,0),(0,1,0),(0,1,1),(1,1,1)]),
       ((0,-1,0),[(0,0,0),(1,0,0),(1,0,1),(0,0,1)]),
       ((0,0,1),[(0,0,1),(1,0,1),(1,1,1),(0,1,1)]),
       ((0,0,-1),[(0,1,0),(1,1,0),(1,0,0),(0,0,0)])]
cells=sanctuary();opaque=[];glass=[]
trans={B.LIGHT_BLUE_STAINED_GLASS,B.YELLOW_STAINED_GLASS}
palette={'foundation':(.23,.29,.37),'base':(.76,.79,.79),'floor':(.88,.88,.84),
         'aisle':(.65,.74,.79),'stone':(1,.98,.93),'glass':(.75,.88,1),
         'amber':(1,.89,.66),'glow':(1,1,.9)}
for (x,y,z),(block,tint) in cells.items():
 for normal,corners in faces:
  other=cells.get((x+normal[0],y+normal[1],z+normal[2]))
  if other and (other[0] not in trans or block==other[0]):continue
  ti={B.SMOOTH_QUARTZ:0,B.QUARTZ_PILLAR:2 if normal[2] else 1,B.QUARTZ_BRICKS:3,
      B.CHISELED_QUARTZ:4,B.POLISHED_ANDESITE:5,B.LIGHT_BLUE_STAINED_GLASS:6,
      B.YELLOW_STAINED_GLASS:7,B.GLOWSTONE:8}[block]
  shade=1 if block in trans or block==B.GLOWSTONE else .77+.23*max(0,normal[2]-.3*normal[0]-.5*normal[1])
  face=[]
  for corner,(u,v) in zip(corners,[(0,1),(1,1),(1,0),(0,0)]):
   pos=(x+corner[0]-.5,z+corner[2]-25,-(y+corner[1]+3))
   uv=((ti*64+.5+u*63)/(64*len(textures)),(.5+v*63)/64)
   face.append((*pos,*uv,*(c*shade for c in palette[tint]),1))
  (glass if block in trans else opaque).append(face)
opaque=np.asarray(opaque,dtype='float32');glass=np.asarray(glass,dtype='float32')
for state in (0x8074,0x8078,0x8076):gl.glEnableClientState(state)
def draw(data):
 data=np.ascontiguousarray(data.reshape(-1,9));stride=36
 gl.glVertexPointer(3,0x1406,stride,data.ctypes.data)
 gl.glTexCoordPointer(2,0x1406,stride,data.ctypes.data+12)
 gl.glColorPointer(4,0x1406,stride,data.ctypes.data+20)
 gl.glDrawArrays(0x0007,0,len(data))
def frame(angle,size=(1920,1080),capture=None):
 w,h=size;gl.glViewport(0,0,w,h)
 gl.glClear(0x4000|0x0100);gl.glMatrixMode(0x1701);gl.glLoadIdentity()
 half=39;gl.glOrtho(-half*w/h,half*w/h,-half,half,-200,200)
 gl.glMatrixMode(0x1700);gl.glLoadIdentity();gl.glRotatef(25,1,0,0);gl.glRotatef(angle,0,1,0)
 gl.glDepthMask(1);draw(opaque)
 # Glass sorted back to front for each camera angle; no depth writes.
 a=math.radians(angle);p=math.radians(25)
 centers=glass[:,:,:3].mean(axis=1)
 depths=(-math.sin(a)*centers[:,0]+math.cos(a)*centers[:,2])*math.cos(p)+centers[:,1]*math.sin(p)
 gl.glDepthMask(0);draw(glass[np.argsort(depths)]);gl.glDepthMask(1)
 gl.glFinish()
 if capture:
  out=np.empty((h,w,3),dtype=np.uint8);gl.glPixelStorei(0x0D05,1)
  gl.glReadPixels(0,0,w,h,0x1907,0x1401,out.ctypes.data)
  Image.fromarray(out[::-1]).save(capture)
for angle in (-35,0,45,135):frame(angle,capture=ROOT/f'.qa/sanctuary-preview/orbit-{angle}.png')
timings=[]
for size in ((1200,800),(1920,1080)):
 for a in range(12):frame(a*7,size)
 values=[]
 for a in range(120):
  t=time.perf_counter();frame(a*3,size);values.append((time.perf_counter()-t)*1000)
 timings.append(dict(size=size,p50_ms=float(np.percentile(values,50)),p95_ms=float(np.percentile(values,95)),max_ms=max(values)))
report=dict(renderer=gl.glGetString(0x1F01).decode(),version=gl.glGetString(0x1F02).decode(),blocks=len(cells),opaque_faces=len(opaque),glass_faces=len(glass),timings=timings,gl_error=gl.glGetError(),scope='Hidden-window scene render only; no app UI, picking, particles, audio, fullscreen switching or presentation timing included.')
(ROOT/'.qa/sanctuary-preview/orbit-feasibility.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
pygame.quit()

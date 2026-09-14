import os,sys,time
os.environ['SDL_VIDEODRIVER']='dummy';sys.path.insert(0,'Code')
import pygame
from engine.sky_layers import SkyLayers
pygame.display.init();pygame.display.set_mode((1,1));s=pygame.Surface((1920,1080));layers=SkyLayers()
for dim in ('overworld','nether','end'):
 t=[]
 for i in range(100):
  start=time.perf_counter();layers.render(s,dim,0,18);t.append((time.perf_counter()-start)*1000)
 print(dim,sum(len(x[3]) for x in layers.forms[dim]),'faces',sorted(t)[94],'ms')

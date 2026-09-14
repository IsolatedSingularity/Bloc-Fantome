import os,sys,json,gzip,math
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,'Code')
import pygame
from tools.bake_world_map_sprites import Baker
from blocFantome import BlocFantome
source=Path('Code/world_map_regions/end_city.json.gz')
d=json.loads(gzip.decompress(source.read_bytes()))
bb=d['structures']['endcity:-73,-15']['BB'];ox,oy=d['origin']
x0,y0,z0=bb[0]-18,bb[2]-18,40
x1,y1,z1=bb[3]+18,bb[5]+18,bb[4]+3
rows=[[x+ox-x0,y+oy-y0,z-z0,p] for x,y,z,p in d['blocks'] if x0<=x+ox<=x1 and y0<=y+oy<=y1 and z0<=z<=z1]
data=dict(data_version=2567,minecraft_version='Java 1.16.1',seed=d['seed'],dimension='end',origin=[x0,y0,z0],size=[x1-x0+1,y1-y0+1,z1-z0+1],capture_kind='natural_structure',presentation='Complete captured End City with its source terrain; bounded surrounding island cutaway.',palette=d['palette'],palette_biomes=d['palette_biomes'],blocks=rows,chunks=d['chunks'],source=str(source),structure_bounds=bb)
root=Path('Code/biome_captures')
(root/'tutorial_end_city.json.gz').write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
pygame.display.init();pygame.display.set_mode((1,1));baker=Baker()
for view in range(4):
 baker.view_rotation=view
 atlas=pygame.Surface((2048,math.ceil(len(d['palette'])/16)*208),pygame.SRCALPHA)
 for p,state in enumerate(d['palette']):
  if state['Name']=='minecraft:air':continue
  baker.biome_id=d['palette_biomes'][p]
  atlas.blit(baker.bake(state),((p%16)*128,(p//16)*208))
 pygame.image.save(atlas,str(root/'atlases'/f'_tutorial_end_city_{view}.png'))
print('City source blocks:',len(rows),'bounds:',data['size'])

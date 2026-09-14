import os,sys,json,gzip
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';sys.path.insert(0,'Code')
import pygame
from tools.bake_world_map_sprites import Baker
pygame.display.init();pygame.display.set_mode((1,1));b=Baker()
d=json.loads(gzip.decompress(Path('Code/biome_captures/tutorial_end_city.json.gz').read_bytes()))
for name in ('end_rod','dragon_wall_head','brewing_stand'):
 state=next(s for s in d['palette'] if s['Name']=='minecraft:'+name)
 image=b.bake(state)
 pygame.image.save(image.subsurface((0,96,128,112)),f'Code/biome_captures/materials/{name}.png')
 print(name,image.get_bounding_rect())

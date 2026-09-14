import sys,json,gzip
from pathlib import Path
sys.path.insert(0,'Code')
from tools.export_scene_assets import bake,write_world,Baker,pygame
pygame.display.init();pygame.display.set_mode((1,1));baker=Baker();cache={}
for name,item in json.loads(Path('Code/biome_captures/scenes.json').read_text()).items():
 path=Path('Code/biome_captures')/item['file'];data=bake(json.loads(gzip.decompress(path.read_bytes())),name,baker,cache)
 path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
 write_world(data,name,item['world'],item['title'])
 print('Baked world',name,flush=True)

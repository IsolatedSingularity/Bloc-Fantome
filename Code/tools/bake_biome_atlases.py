"""Bake every captured palette at four view angles; no runtime model parsing."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
from pathlib import Path
import gzip
import json
import math
import sys
import pygame
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.bake_world_map_sprites import Baker
from engine.capture_materials import MATERIALS
from blocFantome import BlocFantome

def main():
    root=Path(__file__).resolve().parents[1]/'biome_captures'
    (root/'atlases').mkdir(exist_ok=True);(root/'materials').mkdir(exist_ok=True)
    pygame.display.init();pygame.display.set_mode((1,1));baker=Baker();cache={}
    for path in sorted(root.glob('*.json.gz')):
        data=json.loads(gzip.decompress(path.read_bytes()));name='_tutorial_end_city' if path.name=='tutorial_end_city.json.gz' else next(k for k,v in json.loads((root/'manifest.json').read_text()).items() if v['file']==path.name)
        if '--nether-end' in sys.argv and data['dimension'] not in ('nether','end'):continue
        mapped=[]
        for state in data['palette']:
            block=BlocFantome._resolveJavaBlockType(state['Name'])
            mapped.append(block.name if block is not None else 'AIR')
        assert all(mapped[p]!='AIR' for x,y,z,p in data['blocks']),name
        data['editable_palette']=mapped
        path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
        for view in range(4):
            baker.view_rotation=view
            atlas=pygame.Surface((16*128,math.ceil(len(data['palette'])/16)*208),pygame.SRCALPHA)
            for p,state in enumerate(data['palette']):
                if state['Name'].endswith(':air'):continue
                baker.biome_id=data['palette_biomes'][p]
                key=(json.dumps(state,sort_keys=True),baker.biome_id,view)
                if key not in cache:cache[key]=baker.bake(state)
                sprite=cache[key]
                atlas.blit(sprite,((p%16)*128,(p//16)*208))
                if view==0 and mapped[p] in MATERIALS:
                    dest=root/'materials'/(mapped[p].lower()+'.png')
                    if not dest.exists():pygame.image.save(sprite.subsurface((0,96,128,112)),dest)
            pygame.image.save(atlas,root/'atlases'/f'{name}_{view}.png')
        print(name,len(data['palette']),flush=True)

if __name__=='__main__':main()

"""Export actual Java chunks and bake source-model previews for the biome library."""
from pathlib import Path
import gzip
import json
import os
import sys
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
import pygame
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.export_world_map_regions import export
from tools.bake_world_map_sprites import Baker, ANCHOR

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'.qa/biome-capture-281'
OUTPUT=ROOT/'Code/biome_captures'

def preview(data,baker,target):
    palette=data['palette'];sprites={}
    def opaque(state):
        name=state['Name'].split(':')[1]
        return not any(s in name for s in ('leaves','grass','fern','vine','flower','roots','sprouts','fungus','mushroom','water','glass','fire','sapling','lily','coral','lantern','fence')) or name=='grass_block'
    occupied={(x,z,y) for x,z,y,p in data['blocks'] if opaque(palette[p])}
    visible=[r for r in data['blocks'] if any((r[0]+dx,r[1]+dz,r[2]+dy) not in occupied for dx,dz,dy in ((1,0,0),(0,1,0),(0,0,1)))]
    if not visible:
        surface=pygame.Surface((520,360),pygame.SRCALPHA);pygame.image.save(surface,target);return
    positions=[((x-z)*32,(x+z)*16-y*38) for x,z,y,p in visible]
    lx,hx=min(x for x,y in positions)-64,max(x for x,y in positions)+64
    ly,hy=min(y for x,y in positions)-64,max(y for x,y in positions)+96
    scale=min(500/(hx-lx),338/(hy-ly)); ox=260-(hx+lx)*scale/2; oy=180-(hy+ly)*scale/2
    surface=pygame.Surface((520,360),pygame.SRCALPHA)
    for x,z,y,p in sorted(visible,key=lambda r:sum(r[:3])):
        if p not in sprites:
            baker.biome_id=data['palette_biomes'][p]
            sprite=baker.bake(palette[p])
            sprites[p]=pygame.transform.smoothscale(sprite,(max(1,round(sprite.get_width()*scale)),max(1,round(sprite.get_height()*scale))))
        surface.blit(sprites[p],(round(((x-z)*32-ANCHOR[0])*scale+ox),round(((x+z)*16-y*38-ANCHOR[1])*scale+oy)))
    pygame.image.save(surface,target)

def main():
    pygame.display.init();pygame.display.set_mode((1,1));baker=Baker()
    rows=json.loads((WORK/'locations.json').read_text()); manifest=json.loads((OUTPUT/'manifest.json').read_text()) if (OUTPUT/'manifest.json').exists() else {}
    for row in rows:
        if '--nether-end' in sys.argv and row['dimension'] not in ('nether','end'):continue
        if not row.get('location'): continue
        name=row['id']; path=OUTPUT/f"{row['dimension']}_{name}.json.gz"
        if path.exists() and '--refresh' not in sys.argv: data=json.loads(gzip.decompress(path.read_bytes()))
        else:
            spec=(row['dimension'],name,name.replace('_',' ').title(),*row['origin'],48,48)
            data=export(WORK/row.get('source_world','world'),OUTPUT,spec,editable=True)
            data['biome_id']=row['raw_id'];data['capture_kind']=row.get('capture_kind','natural')
            data['locate_response']=row['response']
            path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
        preview(data,baker,OUTPUT/f'{name}.png')
        manifest[name]={'file':path.name,'preview':name+'.png','kind':data['capture_kind'],'origin':data['origin'],'size':data['size']}
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2))

if __name__=='__main__':main()

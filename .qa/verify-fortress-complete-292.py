import sys,json,gzip
from pathlib import Path
import numpy as np
sys.path.insert(0,'Code')
from engine.anvil import _read_region_chunk,_palette_indices
root=Path('Code/biome_captures');name='nether__scene_nether_fortress_biomes_1161.json.gz'
data=json.loads(gzip.decompress((root/name).read_bytes()))
ox,oz=data['origin'];width,depth=data['size'][:2]
materials={'minecraft:nether_bricks','minecraft:nether_brick_fence','minecraft:nether_brick_stairs','minecraft:nether_wart','minecraft:chest','minecraft:spawner'}
palette=[json.dumps(s,sort_keys=True) for s in data['palette']]
actual={(x+ox,z+oz,y,palette[p]) for x,z,y,p in data['blocks'] if data['palette'][p]['Name'] in materials}
expected=set();source=Path('.qa/natural-292/world/DIM-1/region')
for cx in range(ox//16,(ox+width)//16):
    for cz in range(oz//16,(oz+depth)//16):
        chunk=_read_region_chunk(source/f'r.{cx//32}.{cz//32}.mca',cx,cz)
        for section in chunk['Level']['Sections']:
            states=section.get('Palette',[])
            ids={i for i,s in enumerate(states) if s['Name'] in materials}
            if not ids:continue
            decoded=np.fromiter(_palette_indices(len(states),section.get('BlockStates',[])),dtype=np.uint16,count=4096)
            for i in np.flatnonzero(np.isin(decoded,list(ids))):
                y=int(i)//256+section['Y']*16;z=(int(i)//16)%16+cz*16;x=int(i)%16+cx*16
                expected.add((x,z,y,json.dumps(states[int(decoded[i])],sort_keys=True)))
assert actual==expected,(len(expected-actual),len(actual-expected))
result=dict(capture=name,source_structure_cells=len(expected),retained_structure_cells=len(actual),complete=True,wastes_fraction=data['biomes']['8']/sum(data['biomes'].values()))
Path('.qa/revision-292-fortress-completeness.json').write_text(json.dumps(result,indent=2));print(result,flush=True)

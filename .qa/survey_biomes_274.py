import sys, json
from pathlib import Path
from collections import Counter
sys.path.insert(0, 'Code')
from engine.anvil import _read_region_chunk
world=Path('.qa/worldmap-vanilla/reference-world')
result=[]
for dim in ('', 'DIM-1'):
    for path in (world/dim/'region').glob('*.mca'):
        if path.stat().st_size < 8192: continue
        _,rx,rz,_=path.name.split('.')
        with path.open('rb') as f: header=f.read(4096)
        for i in range(1024):
            if header[i*4:i*4+3]==b'\0\0\0': continue
            cx,cz=int(rx)*32+i%32,int(rz)*32+i//32
            root=_read_region_chunk(path,cx,cz)
            if not root or root['Level']['Status']!='full': continue
            level=root['Level']
            counts=Counter(level.get('Biomes',[])[256:272])
            starts={k:v for k,v in level.get('Structures',{}).get('Starts',{}).items() if v.get('id')!='INVALID'}
            result.append(dict(dim=dim,x=cx*16,z=cz*16,biomes=dict(counts),structures=starts))
Path('.qa/biomes-274.json').write_text(json.dumps(result))
for biome in (2,6,14,30,44,170,171,172,173):
    rows=[r for r in result if r['biomes'].get(biome,0)>=12]
    print(biome,len(rows),[(r['x'],r['z']) for r in rows[::max(1,len(rows)//12)]][:12],flush=True)

import json,gzip
from pathlib import Path
from collections import Counter
work=Path('.qa/biome-capture-281');rows=json.loads((work/'locations.json').read_text())
for biome,key,target in [('warped_forest','warped','warped_nylium'),('crimson_forest','crimson','crimson_nylium'),('soul_sand_valley','valley','soul_sand'),('basalt_deltas','deltas','basalt'),('nether_wastes','fortress','netherrack')]:
 d=json.loads(gzip.decompress(Path('Code/world_map_regions/nether_'+key+'.json.gz').read_bytes()))
 coords={(x,z) for x,z,y,p in d['blocks'] if d['palette'][p]['Name']=='minecraft:'+target and 30<=y<95}
 candidates=[]
 for x in range(0,d['size'][0]-47,16):
  for z in range(0,d['size'][1]-47,16):
   count=sum((a,b) in coords for a in range(x,x+48) for b in range(z,z+48))
   candidates.append((count,x,z))
 count,x,z=max(candidates)
 row=next(r for r in rows if r['id']==biome)
 row['origin']=[d['origin'][0]+x,d['origin'][1]+z]
 row['source_world']='../worldmap-vanilla/reference-world'
 row['response']+='; visually selected a denser surface sample in the existing seed-1 source world.'
 print(biome,count,row['origin'])
(work/'locations.json').write_text(json.dumps(rows,indent=2))

import sys,json,gzip,hashlib
from pathlib import Path
sys.path.insert(0,'Code')
from engine.anvil import _read_region_chunk,_iter_chunk_blocks
p=Path('Code/biome_captures/tutorial_end_city.json.gz');d=json.loads(gzip.decompress(p.read_bytes()))
x0,z0,y0=d['origin'];w,depth,height=d['size'];lookup={json.dumps(s,sort_keys=True):i for i,s in enumerate(d['palette'])}
rows=[];chunks=[]
folder=Path('.qa/worldmap-vanilla/reference-world/DIM1/region')
for cz in range(z0//16,(z0+depth-1)//16+1):
 for cx in range(x0//16,(x0+w-1)//16+1):
  region=folder/f'r.{cx//32}.{cz//32}.mca'
  root=_read_region_chunk(region,cx,cz)
  assert root and root['DataVersion']==2567
  chunks.append([cx,cz])
  for b in _iter_chunk_blocks(root,cx,cz):
   if not(x0<=b.x<x0+w and z0<=b.z<z0+depth and y0<=b.y<y0+height):continue
   state={'Name':b.name}
   if b.properties:state['Properties']=b.properties
   key=json.dumps(state,sort_keys=True)
   assert key in lookup,key
   rows.append([b.x-x0,b.z-z0,b.y-y0,lookup[key]])
d['blocks']=rows;d['chunks']=chunks;d['source']='.qa/worldmap-vanilla/reference-world';d['presentation']='All original blocks in a bounded Java 1.16.1 region containing the complete End City and ship.'
p.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
report={'blocks':len(rows),'source_chunks':chunks,'origin':d['origin'],'size':d['size'],'source_regions':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in {folder/f'r.{x//32}.{z//32}.mca' for x,z in chunks}},'capture_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
Path('.qa/tutorial-city-source-291.json').write_text(json.dumps(report,indent=2))
print(len(rows),'source cells verified')

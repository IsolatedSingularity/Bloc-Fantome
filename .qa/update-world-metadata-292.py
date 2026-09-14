from pathlib import Path
# Update generated metadata atomically so a live reader never sees a partial gzip.
import gzip,json,os
for p in Path('Code/worlds').glob('*.json.gz'):
 d=json.loads(gzip.decompress(p.read_bytes()));meta=d.get('scene',{})
 if not meta.get('source_capture'):continue
 if meta['id']=='end_city_1161':
  for r in d['blocks']:
   if r['type'] not in {'END_STONE','CHORUS_PLANT','CHORUS_FLOWER'}:r['role']='structure'
 meta['structure_blocks']=sum(r.get('role')=='structure' for r in d['blocks'])
 meta['underwater']=meta['id']=='ocean_monument_1161'
 payload=gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0)
 tmp=p.with_suffix('.tmp');tmp.write_bytes(payload);os.replace(tmp,p)
 print('Updated',p.name,flush=True)

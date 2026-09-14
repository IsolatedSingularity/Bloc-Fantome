import sys,gzip,json
from pathlib import Path
sys.path.insert(0,'Code')
import blocFantome as app
missing={}
for path in Path('Code/biome_captures').glob('*.json.gz'):
 d=json.loads(gzip.decompress(path.read_bytes()))
 for x,y,z,p in d['blocks']:
  name=d['palette'][p]['Name']
  if app.BlocFantome._resolveJavaBlockType(name) is None:missing[name]=missing.get(name,0)+1
print(json.dumps(missing,indent=2))
Path('.qa/biome-unmapped-281.json').write_text(json.dumps(missing,indent=2))

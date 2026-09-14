import json
from pathlib import Path
p=Path('.qa/biome-capture-281/locations.json');rows=json.loads(p.read_text());r=next(r for r in rows if r['id']=='the_void')
r['source_world']='../void-capture-281/world';r['capture_kind']='void_preset';r['origin']=[-16,-16];r['response']='Minecraft Java 1.16.1 Void superflat preset with its generated start platform.'
p.write_text(json.dumps(rows,indent=2))

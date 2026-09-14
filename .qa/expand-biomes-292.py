import sys,json,gzip
from pathlib import Path
sys.path.insert(0,'Code')
from ui.biomes import CURATED_IDS
from tools.capture_scene_regions import VanillaServer
from tools.export_world_map_regions import export

root=Path('.qa/biome-capture-281')
rows={r['id']:r for r in json.loads((root/'locations.json').read_text())}
output=Path('Code/biome_captures'); manifest=json.loads((output/'manifest.json').read_text())
plan=[]
for name in CURATED_IDS:
    row=rows[name]; old=manifest[name]; x,z=old['origin'][:2]
    size=256 if name=='the_end' else 128 if name in ('end_highlands','small_end_islands') else 96
    origin=[-128,-128] if name=='the_end' else [(v+24-size//2)//16*16 for v in (x,z)]
    world=(root/row.get('source_world','world')).resolve()
    plan.append(dict(id=name,dimension=row['dimension'],origin=origin,size=size,world=str(world)))
Path('.qa/biome-plan-292.json').write_text(json.dumps(plan,indent=2))
if '--generate' in sys.argv:
    for world in sorted({r['world'] for r in plan}):
        source=Path(world)
        with VanillaServer(source.parent,source.name,25593) as server:
            for row in (r for r in plan if r['world']==world):
                server.generate(row['dimension'],row['origin'],(row['size'],row['size']))
                print('Generated',row['id'],row['origin'],row['size'],flush=True)
else:
    for row in plan:
        name=row['id']
        data=export(Path(row['world']),output,(row['dimension'],name,name.replace('_',' ').title(),*row['origin'],row['size'],row['size']),editable=True,retain_water='ocean' in name)
        data['capture_kind']=manifest[name]['kind'];data['biome_id']=rows[name]['raw_id']
        data['source_world']=row['world'];data['locate_response']=rows[name]['response']
        path=output/manifest[name]['file']
        path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
        manifest[name].update(origin=data['origin'],size=data['size'])
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2))

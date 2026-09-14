import sys,json,gzip
from pathlib import Path
sys.path.insert(0,'Code')
from tools.export_world_map_regions import export
out=Path('Code/biome_captures'); manifest={}
for row in json.loads(Path('.qa/natural-292/world-plan.json').read_text()):
    name='_scene_'+row['id']
    data=export(Path(row['source_world']),out,(row['dimension'],name,row['name'],*row['origin'],*row['size']),
        editable=True,landmark_ids=row['landmarks'],retain_water=row['id']=='ocean_monument_1161',geology_depth=4,fortress_cutaway=row.get('fortress_cutaway',False))
    data.update(capture_kind='natural_structure',source_world=row['source_world'],landmark_ids=row['landmarks'])
    path=out/f"{row['dimension']}_{name}.json.gz"
    path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
    manifest[name]=dict(file=path.name,world=row['id'],title=row['name'])
    (out/'scenes.json').write_text(json.dumps(manifest,indent=2))

from pathlib import Path
import json,sys
sys.path.insert(0,'Code')
from tools.verify_world_map_regions import verify
root=Path('Code/biome_captures');manifest=json.loads((root/'manifest.json').read_text());report=[]
for row in json.loads(Path('.qa/biome-plan-292.json').read_text()):
 report+=verify(Path(row['world']),root,paths=[root/manifest[row['id']]['file']])
manifest=json.loads((root/'scenes.json').read_text())
report+=verify(Path('.qa/natural-292/world'),root,paths=[root/r['file'] for r in manifest.values()])
report+=verify(Path('.qa/worldmap-vanilla/reference-world'),root,paths=[root/'tutorial_end_city.json.gz'])
Path('.qa/revision-292-source-verification.json').write_text(json.dumps(report,indent=2))
print('VERIFIED TOTAL',sum(r['verified_cells'] for r in report),flush=True)

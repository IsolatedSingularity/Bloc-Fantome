import sys,json
from pathlib import Path
sys.path.insert(0,'Code')
from tools.verify_world_map_regions import verify
root=Path('.qa/biome-capture-281')
rows=json.loads((root/'locations.json').read_text())
worlds={r['id']:root/r.get('source_world','world') for r in rows}
report=verify(root/'world',Path('Code/biome_captures'),worlds)
Path('.qa/biome-source-verification-281.json').write_text(json.dumps(report,indent=2))
print('Verified',len(report),'biomes;',sum(r['verified_cells'] for r in report),'source cells')

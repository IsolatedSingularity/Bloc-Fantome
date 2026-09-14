import json,gzip
from pathlib import Path
for p in ('Code/world_map_regions/end_city.json.gz','Code/biome_captures/manifest.json'):
 d=json.loads(gzip.decompress(Path(p).read_bytes())) if p.endswith('.gz') else json.loads(Path(p).read_text())
 if 'manifest' in p:print('END',[(k,v) for k,v in d.items() if k in ('end_highlands','the_end')])
 else:print('REGION',list(d),len(d['blocks']),{k:v for k,v in d.items() if k not in ('blocks','palette','decoration_blocks','entities')});print('palette',d['palette'][:2])
metrics=json.loads(Path('.qa/tour-291-visual/performance.json').read_text())
print('PERF',sorted(metrics,key=lambda r:r['max_loading_frame_ms'],reverse=True)[:8])

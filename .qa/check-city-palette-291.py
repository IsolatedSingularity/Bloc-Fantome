import sys,gzip,json,collections
from pathlib import Path
sys.path.insert(0,'Code')
from blocFantome import BlocFantome
p=json.loads(gzip.decompress(Path('Code/biome_captures/tutorial_end_city.json.gz').read_bytes()))
print(collections.Counter(p['palette'][r[3]]['Name'] for r in p['blocks'] if BlocFantome._resolveJavaBlockType(p['palette'][r[3]]['Name']) is None))

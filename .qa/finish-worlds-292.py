import sys,json
from pathlib import Path
sys.path.insert(0,'Code')
from tools.capture_scene_regions import VanillaServer
out=Path('.qa/natural-292')
with VanillaServer(out) as server:
    for row in json.loads((out/'world-plan.json').read_text()):
        server.generate(row['dimension'],row['origin'],row['size'])
        print('Ready',row['id'],flush=True)

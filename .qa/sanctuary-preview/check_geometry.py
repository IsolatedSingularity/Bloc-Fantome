import sys,json
from collections import deque
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from architecture import sanctuary,ROOT,B
cells=sanctuary();solid={p for p,(b,t) in cells.items() if b not in (B.LIGHT_BLUE_STAINED_GLASS,B.YELLOW_STAINED_GLASS)}
steps=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))
seen={next(iter(solid))};todo=deque(seen)
while todo:
 x,y,z=todo.popleft()
 for dx,dy,dz in steps:
  p=x+dx,y+dy,z+dz
  if p in solid and p not in seen:seen.add(p);todo.append(p)
report=dict(total_cells=len(cells),solid_cells=len(solid),connected_solid_cells=len(seen),disconnected_count=len(solid-seen),bounds=[list(map(min,zip(*cells))),list(map(max,zip(*cells)))])
(ROOT/'.qa/sanctuary-preview/geometry-check.json').write_text(json.dumps(report,indent=2))
print(report)
if solid-seen:print(sorted(solid-seen)[:20])

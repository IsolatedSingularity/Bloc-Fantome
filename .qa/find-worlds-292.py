import sys,json
from pathlib import Path
sys.path.insert(0,'Code')
from tools.capture_scene_regions import VanillaServer
from engine.anvil import _read_region_chunk
out=Path('.qa/natural-292'); candidates=[]; seen=set()
with VanillaServer(out) as server:
    for x in range(-12000,12001,2000):
        for z in range(-12000,12001,2000):
            loc,trace=server.locate('overworld','village',x,z)
            if loc is None or tuple(loc) in seen:continue
            seen.add(tuple(loc))
            for kind in ('desert_pyramid','pillager_outpost'):
                extra,evidence=server.locate('overworld',kind,*loc)
                if extra and max(abs(a-b) for a,b in zip(loc,extra))<=240:
                    candidates.append(dict(location=loc,extra=extra,kind=kind,evidence=[trace,evidence]))
    candidates.sort(key=lambda r:sum(abs(a-b) for a,b in zip(r['location'],r['extra'])))
    for row in candidates[:30]:
        x,z=row['location'];server.generate('overworld',(x,z),(16,16))
        root=_read_region_chunk(out/'world/region'/f'r.{x//512}.{z//512}.mca',x//16,z//16)
        starts=root['Level'].get('Structures',{}).get('Starts',{})
        row['starts']=starts
        village=next((s for s in starts.values() if s.get('id')=='minecraft:village'),{})
        row['village']=village
        print(row['location'],row['extra'],row['kind'],str(village.get('Children',[])[:1])[:250],flush=True)
        (out/'pairs.json').write_text(json.dumps(candidates,indent=2))

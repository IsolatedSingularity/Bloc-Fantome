import sys,json
from pathlib import Path
sys.path.insert(0,'Code')
from tools.capture_scene_regions import VanillaServer
out=Path('.qa/natural-292'); result=[]
with VanillaServer(out) as server:
    for biome in ('desert','plains','taiga','savanna','snowy_tundra','nether_wastes'):
        dim='nether' if biome=='nether_wastes' else 'overworld'
        for x,z in ((0,0),(4000,0),(-4000,0),(0,4000),(0,-4000)):
            loc,evidence=server.locate(dim,'minecraft:'+biome,x,z,True)
            if loc is None: continue
            kind='minecraft:fortress' if dim=='nether' else 'minecraft:village'
            village,trace=server.locate(dim,kind,*loc)
            if village is None:continue
            row=dict(biome=biome,biome_location=loc,location=village,evidence=[evidence,trace])
            if dim=='overworld':
                extra='minecraft:desert_pyramid' if biome=='desert' else 'minecraft:pillager_outpost'
                point,trace=server.locate(dim,extra,*village)
                row.update(extra=extra,extra_location=point)
                row['evidence'].append(trace)
            result.append(row)
            (out/'survey.json').write_text(json.dumps(result,indent=2))
            print(row,flush=True)

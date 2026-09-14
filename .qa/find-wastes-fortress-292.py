import sys,json,math
from pathlib import Path
sys.path.insert(0,'Code')
from tools.capture_scene_regions import VanillaServer
from engine.anvil import _read_region_chunk
out=Path('.qa/natural-292');results=[];seen=set()
def chunk(x,z):
    return _read_region_chunk(out/'world/DIM-1/region'/f'r.{x//512}.{z//512}.mca',x//16,z//16)
with VanillaServer(out) as server:
    for x,z in [(x,z) for x in range(-16000,16001,4000) for z in range(-16000,16001,4000)]:
        biome,_=server.locate('nether','minecraft:nether_wastes',x,z,True)
        if not biome:continue
        loc,trace=server.locate('nether','fortress',*biome)
        if not loc or tuple(loc) in seen:continue
        seen.add(tuple(loc));server.generate('nether',loc,(16,16))
        starts=chunk(*loc)['Level']['Structures']['Starts']
        fort=next((s for s in starts.values() if s.get('id')=='minecraft:fortress'),None)
        if not fort:continue
        b=fort['BB']
        if max(b[3]-b[0],b[5]-b[2])<180 or max(b[3]-b[0],b[5]-b[2])>360:continue
        points=[((b[0]+b[3])//2,(b[2]+b[5])//2),(b[0],b[2]),(b[3],b[5]),(b[0],b[5]),(b[3],b[2])]
        counts=[]
        for px,pz in points:
            server.generate('nether',(px//16*16,pz//16*16),(16,16))
            values=chunk(px,pz)['Level']['Biomes'][224:304]
            counts.append(sum(v==8 for v in values)/len(values))
            if counts[-1]<.9:break
        row=dict(location=loc,bounds=b,wastes=counts,evidence=trace)
        results.append(row);(out/'fortress-wastes-survey.json').write_text(json.dumps(results,indent=2))
        print(row,flush=True)
        if len(counts)==5 and min(counts)>=.9:
            origin=[b[0]//16*16-16,b[2]//16*16-16]
            size=[math.ceil((b[3]+17-origin[0])/16)*16,math.ceil((b[5]+17-origin[1])/16)*16]
            server.generate('nether',origin,size)
            row.update(origin=origin,size=size)
            (out/'fortress-wastes-selected.json').write_text(json.dumps(row,indent=2));break

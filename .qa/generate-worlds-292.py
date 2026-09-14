import sys,json,math
from pathlib import Path
sys.path.insert(0,'Code')
from tools.capture_scene_regions import VanillaServer
from engine.anvil import _read_region_chunk
out=Path('.qa/natural-292'); pairs=json.loads((out/'pairs.json').read_text());plan=[]
def start_at(server,dim,loc,kind):
    x,z=loc;server.generate(dim,(x//16*16,z//16*16),(16,16))
    directory=out/'world'/({'nether':'DIM-1','end':'DIM1'}.get(dim,''))/'region'
    chunk=_read_region_chunk(directory/f'r.{x//512}.{z//512}.mca',x//16,z//16)
    start=next(s for s in chunk['Level']['Structures']['Starts'].values() if s.get('id')=='minecraft:'+kind)
    return start,chunk['Level'].get('Biomes',[])
def add(key,name,dimension,starts):
    boxes=[s['BB'] for s in starts]
    x0=min(b[0] for b in boxes)-32;z0=min(b[2] for b in boxes)-32
    x1=max(b[3] for b in boxes)+33;z1=max(b[5] for b in boxes)+33
    x0=x0//16*16;z0=z0//16*16
    width=max(192,math.ceil((x1-x0)/16)*16);depth=max(192,math.ceil((z1-z0)/16)*16)
    row=dict(id=key,name=name,dimension=dimension,origin=[x0,z0],size=[width,depth],
        landmarks=sorted({s['id'] for s in starts}),bounds=boxes,source_world=str((out/'world').resolve()))
    plan.append(row);(out/'world-plan.json').write_text(json.dumps(plan,indent=2))
    print('Selected',key,row['origin'],row['size'],flush=True)

with VanillaServer(out) as server:
    for variant,loc in [('desert',[816,10848]),('plains',[6368,5312]),('taiga',[1376,-12672]),('savanna',[10352,5120])]:
        pair=next(r for r in pairs if r['location']==loc)
        village,_=start_at(server,'overworld',loc,'village')
        extra,_=start_at(server,'overworld',pair['extra'],pair['kind'])
        assert '/'+variant+'/' in village['Children'][0]['pool_element']['location'],variant
        add('village_'+variant+'_1161',variant.title()+' World','overworld',[village,extra])
    snowy=[]
    for loc in ([-1760,-320],[-5536,-848],[-1712,512],[-1824,-4880]):
        village,_=start_at(server,'overworld',loc,'village')
        if '/snowy/' not in village['Children'][0]['pool_element']['location']:continue
        igloo,trace=server.locate('overworld','igloo',*loc)
        snowy.append((max(abs(a-b) for a,b in zip(loc,igloo)),loc,village,igloo))
    distance,loc,village,igloo=min(snowy,key=lambda r:r[0])
    structures=[village]
    if distance<=300:structures.append(start_at(server,'overworld',igloo,'igloo')[0])
    add('village_snowy_1161','Snowbound World','overworld',structures)
    # Select a complete fortress from a wastes start, rather than stitching biomes.
    fortress=[]
    for loc in ([192,0],[3520,-224],[-4544,-528],[-752,3792],[-192,-4720]):
        start,biomes=start_at(server,'nether',loc,'fortress')
        fortress.append((sum(b==8 for b in biomes),start))
    add('nether_fortress_biomes_1161','Nether Fortress','nether',[max(fortress,key=lambda r:r[0])[1]])
    seen=set();found={}
    for x in (-1600,0,1600,3200,-3200):
        for z in (-1600,0,1600,3200,-3200):
            loc,_=server.locate('nether','bastion_remnant',x,z)
            if not loc or tuple(loc) in seen:continue
            seen.add(tuple(loc));start,_=start_at(server,'nether',loc,'bastion_remnant')
            encoded=json.dumps(start)
            variant=next((v for v in ('treasure','bridge','hoglin_stable','units') if '/'+v+'/' in encoded),None)
            if variant and variant not in found:
                found[variant]=start
                key='housing_units' if variant=='units' else variant
                add('bastion_'+key+'_1161',key.replace('_',' ').title()+' Bastion','nether',[start])
            if len(found)==4:break
        if len(found)==4:break
    assert len(found)==4,found.keys()
    monument,_=start_at(server,'overworld',[-880,-848],'monument')
    add('ocean_monument_1161','Deep Ocean','overworld',[monument])
    for row in plan:
        server.generate(row['dimension'],row['origin'],row['size'])
        print('Ready',row['id'],flush=True)

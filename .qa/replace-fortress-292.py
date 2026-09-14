import sys,json,gzip,os,shutil
from pathlib import Path
sys.path.insert(0,'Code')
from tools.export_world_map_regions import export
from tools.export_scene_assets import bake,write_world,Baker,pygame
from tools.verify_world_map_regions import verify
base=Path('Code/biome_captures');work=Path('.qa/natural-292')
selection=json.loads((work/'fortress-wastes-selected.json').read_text())
scene_id='nether_fortress_biomes_1161';key='_scene_'+scene_id
data=export(work/'world',base,('nether',key,'Nether Fortress',*selection['origin'],*selection['size']),editable=True,landmark_ids=['minecraft:fortress'],geology_depth=4,fortress_cutaway=True)
data.update(capture_kind='natural_structure',source_world=str(work/'world'),landmark_ids=['minecraft:fortress'])
pygame.display.init();pygame.display.set_mode((1,1));baker=Baker()
data=bake(data,key,baker,{})
manifest=json.loads((base/'scenes.json').read_text());path=base/manifest[key]['file']
def atomic(path,data):
    temporary=path.with_suffix('.tmp');temporary.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0));os.replace(temporary,path)
atomic(path,data);write_world(data,key,scene_id,'Nether Fortress')
manifest=json.loads((base/'scenes.json').read_text())
bb=selection['bounds'];ox,oz=data['origin']
x0=bb[0]-ox-8;y0=bb[2]-oz-8;x1=bb[3]-ox+8;y1=bb[5]-oz+8
tour=dict(data,blocks=[[x-x0,y-y0,z,p] for x,y,z,p in data['blocks'] if x0<=x<=x1 and y0<=y<=y1],origin=[ox+x0,oz+y0],size=[x1-x0+1,y1-y0+1])
tour_key='_scene_tour_fortress';tour_path=base/manifest[tour_key]['file']
tour['id']=tour_key
atomic(tour_path,tour)
for view in range(4):shutil.copyfile(base/'atlases'/f'{key}_{view}.png',base/'atlases'/f'{tour_key}_{view}.png')
from tools.export_biome_captures import preview
preview(tour,baker,base/f'{tour_key}.png')
manifest[tour_key]['palette_count']=len(tour['palette'])
(base/'scenes.json').write_text(json.dumps(manifest,indent=2))
plan=json.loads((work/'world-plan.json').read_text())
for row in plan:
    if row['id']==scene_id:row.update(origin=selection['origin'],size=selection['size'],fortress_cutaway=True)
(work/'world-plan.json').write_text(json.dumps(plan,indent=2))
report_path=Path('.qa/revision-292-source-verification.json');report=json.loads(report_path.read_text())
verified=verify(work/'world',base,paths=[path,tour_path]);names={r['file'] for r in verified}
report=[r for r in report if r['file'] not in names]+verified
report_path.write_text(json.dumps(report,indent=2))
print('Replaced fortress:',len(data['blocks']),'world cells;',len(tour['blocks']),'tour cells;',data['origin'],data['size'],flush=True)

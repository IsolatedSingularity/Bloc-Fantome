import json,gzip,shutil,sys
from pathlib import Path
sys.path.insert(0,'Code')
from tools.export_scene_assets import bake,write_world,Baker,pygame
root=Path('Code/biome_captures');manifest=json.loads((root/'scenes.json').read_text());pygame.display.init();pygame.display.set_mode((1,1));baker=Baker()
for name,parent,landmark in [('outpost','village_taiga_1161','minecraft:pillager_outpost'),('fortress','nether_fortress_biomes_1161','minecraft:fortress'),('bastion','bastion_treasure_1161','minecraft:bastion_remnant')]:
 src='_scene_'+parent;data=json.loads(gzip.decompress((root/manifest[src]['file']).read_bytes()))
 bb=next(s['BB'] for s in data['structures'].values() if s.get('id')==landmark)
 ox,oz=data['origin'];x0=max(0,bb[0]-ox-8);y0=max(0,bb[2]-oz-8);x1=min(data['size'][0]-1,bb[3]-ox+8);y1=min(data['size'][1]-1,bb[5]-oz+8)
 data['blocks']=[[x-x0,y-y0,z,p] for x,y,z,p in data['blocks'] if x0<=x<=x1 and y0<=y<=y1]
 data['origin']=[ox+x0,oz+y0];data['size']=[x1-x0+1,y1-y0+1];data['landmark_ids']=[landmark]
 target='_scene_tour_'+name;file=target+'.json.gz';data['id']=target
 for view in range(4):shutil.copyfile(root/'atlases'/f'{src}_{view}.png',root/'atlases'/f'{target}_{view}.png')
 from tools.export_biome_captures import preview
 preview(data,baker,root/f'{target}.png')
 (root/file).write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
 manifest[target]=dict(file=file,title=name,kind='tutorial')
 print('Tutorial capture',target,len(data['blocks']),flush=True)
(root/'scenes.json').write_text(json.dumps(manifest,indent=2))
# Replace two legacy assembled habitats with already verified natural captures.
for source,world,title in [('_tutorial_end_city','end_city_1161','End City'),('basalt_deltas','basalt_deltas_1161','Basalt Deltas')]:
 file='tutorial_end_city.json.gz' if source.startswith('_tutorial') else json.loads((root/'manifest.json').read_text())[source]['file']
 data=json.loads(gzip.decompress((root/file).read_bytes()))
 if len(data['origin'])==3:
  print('End origin',data['origin'],data.keys(),flush=True)
  continue
 data.setdefault('landmark_ids',[]);data.setdefault('structures',{});data.setdefault('seed',1)
 write_world(data,source,world,title)

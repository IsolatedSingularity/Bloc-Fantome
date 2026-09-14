"""Bake auditable source captures and editable gallery files, without live parsing."""
import gzip
import json
import math
import os
from pathlib import Path
import sys
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from blocFantome import BlocFantome
from tools.bake_world_map_sprites import Baker, save_atlas
from tools.export_biome_captures import preview
from engine.capture_materials import MATERIALS

ROOT=Path(__file__).resolve().parents[1]


def bake(data, name, baker, cache):
    """Retain source states, model geometry and tint in all four orientations."""
    output=ROOT/'biome_captures'
    mapped=[]
    for state in data['palette']:
        block=BlocFantome._resolveJavaBlockType(state['Name'])
        mapped.append(block.name if block is not None else 'AIR')
    used={r[3] for r in data['blocks']}
    missing=[data['palette'][p] for p in used if mapped[p]=='AIR']
    if missing:raise ValueError(f'{name}: unsupported source states {missing}')
    data['editable_palette']=mapped
    for view in range(4):
        baker.view_rotation=view
        atlas=pygame.Surface((2048,math.ceil(len(mapped)/16)*208),pygame.SRCALPHA)
        for p,state in enumerate(data['palette']):
            if p not in used:continue
            baker.biome_id=data['palette_biomes'][p]
            key=(json.dumps(state,sort_keys=True),baker.biome_id,view)
            if key not in cache:cache[key]=baker.bake(state)
            sprite=cache[key]
            atlas.blit(sprite,((p%16)*128,(p//16)*208))
            if view==0 and mapped[p] in MATERIALS:
                target=output/'materials'/(mapped[p].lower()+'.png')
                if not target.exists():pygame.image.save(sprite.subsurface((0,96,128,112)),target)
        save_atlas(atlas,output/'atlases'/f'{name}_{view}.png')
    baker.view_rotation=0
    preview_data=data
    if 'ocean' in name:
        preview_data=dict(data,blocks=[r for r in data['blocks']
            if data['palette'][r[3]]['Name'] not in ('minecraft:water','minecraft:bubble_column')])
    preview(preview_data,baker,output/f'{name}.png')
    if len(cache)>5000:cache.clear()
    return data


def write_world(data,capture_id,scene_id,title):
    natural={'grass_block','dirt','coarse_dirt','podzol','sand','red_sand','gravel',
        'stone','sandstone','netherrack','basalt','blackstone','soul_sand','soul_soil',
        'lava','water','bedrock','end_stone'}
    bounds=[s['BB'] for s in data['structures'].values() if s.get('id') in data['landmark_ids']]
    fortress=data['landmark_ids']==['minecraft:fortress']
    fortress_materials={'nether_bricks','nether_brick_fence','nether_brick_stairs','nether_wart','chest','spawner','soul_sand','lava'}
    ox,oz=data['origin'][:2];rows=[]
    for x,y,z,p in data['blocks']:
        state=data['palette'][p];name=state['Name'].split(':')[-1]
        row=dict(x=x,y=y,z=z,type=data['editable_palette'][p],sourceCapture=capture_id,sourcePalette=p)
        material = name in fortress_materials if fortress else name not in natural
        if material and any(b[0]<=x+ox<=b[3] and b[2]<=y+oz<=b[5]
                and (b[1]<=z<=b[4] or (fortress and name=='nether_bricks')) for b in bounds):row['role']='structure'
        if name in ('water','lava'):
            level=int(state.get('Properties',{}).get('level','0'))
            row.update(liquidLevel=8 if level==0 or level>=8 else 8-level,liquidSource=level==0,liquidFalling=level>=8)
        rows.append(row)
    scene=dict(kind='world',id=scene_id,name=title,version='Java 1.16.1',seed=data['seed'],
        origin=data['origin'],source_capture=capture_id,accuracy=data['presentation'],
        provider='Official Java world capture',default_terrain_view='all',fit_context=True,
        structure_blocks=sum(r.get('role')=='structure' for r in rows),
        underwater=scene_id=='ocean_monument_1161',water_cutaway=scene_id=='ocean_monument_1161')
    payload=dict(version=5,dimension=data['dimension'],bounds=dict(width=data['size'][0],depth=data['size'][1],height=256,min_y=0),scene=scene,blocks=rows)
    path=ROOT/'worlds'/f'{scene_id}.json.gz'
    temporary=path.with_suffix('.tmp')
    temporary.write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0))
    os.replace(temporary,path)
    manifest_path=ROOT/'biome_captures/scenes.json'
    manifest=json.loads(manifest_path.read_text())
    if capture_id in manifest:
        manifest[capture_id].update(scene=scene,palette_count=len(data['palette']))
        manifest_path.write_text(json.dumps(manifest,indent=2))
    import shutil
    shutil.copyfile(ROOT/'biome_captures'/f'{capture_id}.png',ROOT/'world_previews'/f'{scene_id}.png')


if __name__=='__main__':
    pygame.display.init();pygame.display.set_mode((1,1));baker=Baker();cache={}
    from ui.biomes import CURATED_IDS
    manifest=json.loads((ROOT/'biome_captures/manifest.json').read_text())
    for name in CURATED_IDS:
        path=ROOT/'biome_captures'/manifest[name]['file']
        data=bake(json.loads(gzip.decompress(path.read_bytes())),name,baker,cache)
        path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
        # Gallery uses the pre-existing preview filename.
        import shutil
        if manifest[name]['preview']!=name+'.png':shutil.copyfile(ROOT/'biome_captures'/f'{name}.png',ROOT/'biome_captures'/manifest[name]['preview'])
        print('Baked',name,len(data['blocks']),flush=True)

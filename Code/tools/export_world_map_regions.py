"""Export read-only selector surfaces from official Java 1.16.1 chunks.

Run after generating the documented seed/regions with the local vanilla server.
Terrain and structures retain their source states through documented cutaways.
The approved active portal is stored separately as authored decoration.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
from engine.anvil import _read_region_chunk, _palette_indices

REGIONS = (
    ("nether", "bastion", "Hoglin Stable", -912, -256, 240, 240),
    ("nether", "fortress", "Nether Fortress", 224, -240, 240, 240),
    ("nether", "warped", "Warped Forest", -416, 0, 160, 160),
    ("nether", "crimson", "Crimson Forest", -416, 400, 160, 160),
    ("nether", "valley", "Soul Sand Valley", -160, 240, 160, 160),
    ("nether", "deltas", "Basalt Deltas", -944, -288, 128, 128),
    ("end", "central", "Central Island", -128, -128, 256, 256),
    ("end", "city", "Outer Islands", -1664, -512, 768, 768),
    ("overworld", "plains", "Plains and River", -208, 160, 240, 240),
    ("overworld", "taiga", "Snowy Taiga", -2080, 128, 160, 160),
    ("overworld", "swamp", "Swamp", -256, -592, 192, 192),
    ("overworld", "flowers", "Flower Forest", -416, 560, 128, 128),
    ("overworld", "mushroom", "Mushroom Fields", -3328, 1376, 512, 512),
    ("overworld", "desert", "Desert", 1456, 2032, 160, 160),
    ("ocean", "monument", "Ocean Monument", -1008, -976, 240, 240),
    ("ocean", "shipwreck", "Sunken Shipwreck", -416, 64, 240, 240),
    ("ocean", "reef", "Coral Reef", -832, -1408, 96, 96),
)


def complete_end_islands(records, palette, width, depth, origin, starts):
    """Omit whole distant islands intersecting the survey edge, never trim one."""
    land = {(x,z) for x,z,y,pid in records if palette[pid]['Name']=='minecraft:end_stone'}
    excluded = set()
    while land:
        seed = land.pop()
        component, queue = {seed}, deque([seed])
        while queue:
            x,z = queue.popleft()
            for neighbor in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
                if neighbor in land:
                    land.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        if any(x in (0,width-1) or z in (0,depth-1) for x,z in component):
            for start in starts.values():
                if start.get('id') != 'minecraft:endcity':
                    continue
                x0,y0,z0,x1,y1,z1 = start['BB']
                if any(x0<=x+origin[0]<=x1 and z0<=z+origin[1]<=z1 for x,z in component):
                    raise ValueError('End City island reaches the capture edge; generate more chunks')
            excluded.update(component)
    return [r for r in records if (r[0],r[1]) not in excluded]


def export(world: Path, output: Path, spec: tuple, *, editable=False,
           landmark_ids=(), retain_water=False, geology_depth=12, fortress_cutaway=False) -> dict:
    dimension, key, title, ox, oz, width, depth = spec
    region_dir = world / {"nether": "DIM-1", "end": "DIM1"}.get(dimension, "") / "region"
    volume = np.zeros((width, depth, 256), dtype=np.uint16)
    biome_columns = np.zeros((width, depth), dtype=np.uint16)
    palette = [{"Name": "minecraft:air"}]
    lookup = {json.dumps(palette[0], sort_keys=True): 0}
    starts, entities, biome_counts, chunk_evidence = {}, [], Counter(), []
    for cz in range(oz // 16, (oz + depth) // 16):
        for cx in range(ox // 16, (ox + width) // 16):
            path = region_dir / f"r.{cx // 32}.{cz // 32}.mca"
            root = _read_region_chunk(path, cx, cz)
            if not root or root.get("DataVersion") != 2567:
                raise ValueError(f"Missing Java 1.16.1 chunk: {cx}, {cz}")
            level = root["Level"]
            bx, bz = cx * 16 - ox, cz * 16 - oz
            biome_columns[bx:bx+16,bz:bz+16] = np.asarray(level['Biomes'][256:272]).reshape(4,4).T.repeat(4,axis=0).repeat(4,axis=1)
            if level["Status"] != "full":
                raise ValueError(f"Incomplete chunk {cx}, {cz}: {level['Status']}")
            chunk_evidence.append([cx, cz, hashlib.sha256(json.dumps(root, sort_keys=True, default=list).encode()).hexdigest()])
            biome_counts.update(level.get("Biomes", []))
            entities.extend(level.get("Entities", []))
            for name, start in level.get("Structures", {}).get("Starts", {}).items():
                if start.get("id") != "INVALID":
                    starts[f"{name}:{cx},{cz}"] = start
            for section in level.get("Sections", []):
                sy = section["Y"]
                if sy < 0 or sy >= 16 or "Palette" not in section:
                    continue
                indices = []
                for state in section["Palette"]:
                    if state["Name"] in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
                        indices.append(0)
                        continue
                    encoded = json.dumps(state, sort_keys=True)
                    if encoded not in lookup:
                        lookup[encoded] = len(palette)
                        palette.append(state)
                    indices.append(lookup[encoded])
                decoded = np.fromiter(_palette_indices(len(indices), section.get("BlockStates", [])), dtype=np.uint16, count=4096)
                values = np.asarray(indices, dtype=np.uint16)[decoded].reshape(16, 16, 16).transpose(2, 1, 0)
                x, z = cx * 16 - ox, cz * 16 - oz
                volume[x:x+16, z:z+16, sy*16:sy*16+16] = values

    source_count = int(np.count_nonzero(volume))
    source_volume = volume.copy() if landmark_ids or retain_water else None
    landmarks = [s for s in starts.values() if s.get('id') in landmark_ids]
    for start in landmarks:
        x0, y0, z0, x1, y1, z1 = start['BB']
        if not (ox <= x0 <= x1 < ox+width and oz <= z0 <= z1 < oz+depth):
            raise ValueError(f"Incomplete {start['id']} at capture edge: {start['BB']}")
    presentation = "unaltered terrain and structures"
    if dimension in ("overworld", "ocean"):
        # A source terrain section: omit deep caves and solid geology, never
        # create a replacement floor or move a naturally generated feature.
        ground_names = {"grass_block", "dirt", "coarse_dirt", "podzol", "mycelium",
                        "stone", "sand", "red_sand", "gravel", "clay", "sandstone"}
        ground_ids = np.asarray([p["Name"].split(":")[1] in ground_names for p in palette])
        ground = ground_ids[volume]
        floor = 255 - np.argmax(ground[:, :, ::-1], axis=2)
        floor[~ground.any(axis=2)] = 0
        volume[np.arange(256)[None,None,:] < np.maximum(0,floor-geology_depth)[:,:,None]] = 0
        water_ids = np.asarray([p["Name"] == "minecraft:water" for p in palette])
        water = water_ids[volume]
        if dimension == "ocean" or (editable and 'ocean' in key):
            volume[water] = 0
            presentation = "water cutaway; source seabed section with 12-block geology"
        else:
            # Keep the water surface, removing invisible stacked fluid cells.
            covered = np.roll(water, -1, axis=2)
            covered[:, :, -1] = False
            if not editable:
                volume[water & covered] = 0
            presentation = "source surface section with 12-block geology"
    if dimension == "nether":
        original_volume = volume.copy() if editable else None
        # Expose the first substantial cavern above the lava sea. The previous
        # highest-air rule retained entire higher cave floors as foreground walls.
        air = volume[:, :, 32:104] == 0
        openings = np.ones((width, depth, 65), dtype=bool)
        for offset in range(8):
            openings &= air[:, :, offset:offset+65]
        ceiling = 32 + np.argmax(openings, axis=2)
        ceiling[~openings.any(axis=2)] = 64
        natural = {"air", "netherrack", "gravel", "soul_sand", "soul_soil", "basalt", "blackstone", "lava", "bedrock", "nether_quartz_ore", "nether_gold_ore", "ancient_debris"}
        natural_ids = np.asarray([p["Name"].split(":")[1] in natural for p in palette])
        ys = np.arange(256)[None, None, :]
        remove = (natural_ids[volume] & ((ys >= ceiling[:, :, None]) | (ys < ceiling[:, :, None]-13))) | (ys > ceiling[:, :, None]+24)
        structure_material = np.asarray([p["Name"].split(":")[1] not in natural or 'blackstone' in p["Name"] for p in palette])
        for start in starts.values():
            if start.get('id') not in ('minecraft:bastion_remnant','minecraft:fortress'):
                continue
            x0, y0, z0, x1, y1, z1 = start["BB"]
            area=(slice(max(0,x0-ox),min(width,x1-ox+1)),slice(max(0,z0-oz),min(depth,z1-oz+1)),slice(y0,y1+1))
            remove[area] |= natural_ids[volume[area]] & ~structure_material[volume[area]]
            remove[area] &= ~structure_material[volume[area]]
            if start['id'] == 'minecraft:fortress':
                # Vanilla CorridorNetherWartsRoom places soul sand at local
                # Y4; CorridorExit places its lava well at local (6,5,6).
                for piece in start['Children']:
                    px0,py0,pz0,px1,py1,pz1 = piece['BB']
                    if piece['id'] == 'minecraft:necsr':
                        bed = (slice(max(0,px0-ox),min(width,px1-ox+1)),
                               slice(max(0,pz0-oz),min(depth,pz1-oz+1)),py0+4)
                        soul = np.asarray([p['Name']=='minecraft:soul_sand' for p in palette])
                        remove[bed] &= ~soul[volume[bed]]
                    elif piece['id'] == 'minecraft:nece':
                        wx,wz = (px0+px1)//2-ox,(pz0+pz1)//2-oz
                        if 0<=wx<width and 0<=wz<depth:
                            remove[wx,wz,py0:py0+6] = False
        volume[remove] = 0
        # The bottom is a documented horizontal section through actual blocks.
        volume[:, :, :16] = 0
        # Lava is an opaque surface, not a stack of shortened fluid cubes.
        lava = np.asarray([p['Name']=='minecraft:lava' for p in palette])[volume]
        covered = np.roll(lava, -1, axis=2)
        covered[:, :, -1] = False
        volume[lava & covered] = 0
        presentation = "first open cavern and structure-footprint cutaway; 12-block source geology; structure materials retained"

        if editable and not fortress_cutaway:
            # Small biome slices must expose the biome's actual surface layer,
            # rather than an unrelated lava sea beneath an elevated forest.
            volume=original_volume
            targets={'warped_forest':{'warped_nylium'},'crimson_forest':{'crimson_nylium'},
                     'soul_sand_valley':{'soul_sand','soul_soil'},
                     'basalt_deltas':{'basalt','blackstone'}}.get(key,{'netherrack','gravel'})
            target_ids=np.asarray([p['Name'].split(':')[1] in targets for p in palette])
            ground=target_ids[volume]
            ground[:,:,:30]=False;ground[:,:,108:]=False
            # Only exposed floors, never a solid cave roof.
            air_above=np.roll(volume==0,-1,axis=2)
            if 'forest' in key:
                air_above|=np.asarray([p['Name'].split(':')[1] in {'warped_roots','crimson_roots','nether_sprouts'} for p in palette])[np.roll(volume,-1,axis=2)]
            ground &= air_above
            floors=255-np.argmax(ground[:,:,::-1],axis=2)
            valid=ground.any(axis=2)
            median=int(np.median(floors[valid])) if valid.any() else 50
            floors[~valid]=median
            heights=np.arange(256)[None,None,:]
            bottom=max(16,int(np.percentile(floors[valid],10))-12) if valid.any() else 20
            volume[heights.repeat(width,axis=0).repeat(depth,axis=1)<bottom]=0
            natural_ids=np.asarray([p['Name'].split(':')[1] in natural for p in palette])
            volume[natural_ids[volume] & (heights>floors[:,:,None])]=0
            volume[heights>np.minimum(120,floors+30)[:,:,None]]=0
            presentation='source biome-floor cutaway; 12-block geology; original vegetation and block states'

    if editable and dimension=='end':
        end_stone=np.asarray([p['Name']=='minecraft:end_stone' for p in palette])[volume]
        floors=255-np.argmax(end_stone[:,:,::-1],axis=2)
        if end_stone.any():
            bottom=max(0,int(np.percentile(floors[end_stone.any(axis=2)],10))-12)
            volume[:,:,:bottom]=0
            presentation='horizontal source terrain section; upper geology and original End features'

    # An editable landmark keeps every source cell throughout its bounding box,
    # including buried foundations and interior states. Never clip a building
    # to the terrain cutaway chosen for its surrounding geology.
    for start in landmarks:
        x0,y0,z0,x1,y1,z1=start['BB']
        area=(slice(x0-ox,x1-ox+1),slice(z0-oz,z1-oz+1),slice(y0,y1+1))
        if fortress_cutaway:
            # Source-checked NetherFortressGenerator materials, including the
            # chest placed through StructurePiece. Expose the actual cavern
            # while retaining every fortress cell, including supports below BB.
            fortress_names={'nether_bricks','nether_brick_fence','nether_brick_stairs',
                            'nether_wart','spawner','chest'}
            structure_ids=np.asarray([p['Name'].split(':')[1] in fortress_names for p in palette])
            keep=structure_ids[source_volume]
            volume[keep]=source_volume[keep]
            interior_ids=np.asarray([p['Name'].split(':')[1] in {'lava','soul_sand'} for p in palette])
            interior=interior_ids[source_volume[area]]
            volume[area][interior]=source_volume[area][interior]
        else:
            volume[area]=source_volume[area]
    if retain_water:
        water_ids=np.asarray([p['Name']=='minecraft:water' for p in palette])
        water=water_ids[source_volume]
        volume[water]=source_volume[water]
    if landmarks:
        presentation += ('; complete fortress materials and supports retained from source'
                         if fortress_cutaway else '; complete landmark bounding boxes retained')
    if retain_water:
        presentation = presentation.replace('water cutaway; ', '') + '; original water retained'
    presentation = presentation.replace('12-block', f'{geology_depth}-block') if dimension in ('overworld','ocean') else presentation

    # Keep all faces next to air or a non-solid model. This is a static selector,
    # so buried solid interiors need no runtime storage. Preserve original state.
    solid_names = {"netherrack", "end_stone", "basalt", "blackstone", "soul_sand", "soul_soil",
                   "obsidian", "bedrock", "gravel", "lava", "nether_bricks", "purpur_block",
                   "purpur_pillar", "end_stone_bricks", "polished_blackstone_bricks",
                   "cracked_polished_blackstone_bricks", "polished_blackstone", "nether_wart_block",
                   "warped_wart_block", "crimson_nylium", "warped_nylium", "magma_block"}
    solid_names.update({"grass_block", "dirt", "coarse_dirt", "podzol", "mycelium", "stone",
                        "sand", "red_sand", "clay", "sandstone", "granite", "andesite", "diorite",
                        "coal_ore", "iron_ore", "gold_ore", "cobblestone", "mossy_cobblestone",
                        "prismarine", "prismarine_bricks", "dark_prismarine", "sea_lantern"})
    solid_ids = np.asarray([p["Name"].split(":")[1] in solid_names for p in palette])
    solid = solid_ids[volume]
    buried = solid.copy()
    for axis in range(3):
        for shift in (-1, 1):
            neighbor = np.roll(solid, shift, axis=axis)
            edge = [slice(None)] * 3
            edge[axis] = 0 if shift == 1 else -1
            neighbor[tuple(edge)] = False
            buried &= neighbor
    if not editable:
        volume[buried] = 0
    coords = np.argwhere(volume != 0)
    records = np.column_stack((coords, volume[tuple(coords.T)])).tolist()
    if dimension == 'end' and key == 'city':
        records = complete_end_islands(records,palette,width,depth,(ox,oz),starts)
        presentation = 'complete source islands; whole distant boundary-crossing islands omitted'
    palette_biomes = [None] * len(palette)
    if dimension in ('overworld','ocean'):
        # Preserve vanilla palette states; a parallel biome ID chooses each
        # state's source colormap tint without modifying its block properties.
        tinted = {'grass_block','grass','fern','large_fern','tall_grass','vine','water',
                  'sugar_cane','oak_leaves','jungle_leaves','acacia_leaves','dark_oak_leaves'}
        tint_ids = {i for i,p in enumerate(palette) if p['Name'].split(':')[1] in tinted}
        variants = {}
        for record in records:
            x,z,y,pid = record
            if pid in tint_ids:
                biome = int(biome_columns[x,z])
                if (pid,biome) not in variants:
                    variants[pid,biome] = len(palette)
                    palette.append(palette[pid])
                    palette_biomes.append(biome)
                record[3] = variants[pid,biome]
    decoration_blocks = []
    decoration_anchor = None
    if dimension == 'nether' and key == 'warped':
        # Explicitly separate the approved decorative active portal from the
        # source cells. The reference world itself is never edited to place it.
        ground = [(x,z,y) for x,z,y,pid in records if palette[pid]['Name']=='minecraft:warped_nylium']
        heights = {(x,z):y for x,z,y in ground}
        flat = [(x,z,y) for x,z,y in ground if x+3<width
                and all(heights.get((x+dx,z))==y for dx in range(4))
                and not volume[x:x+4,z,y+1:y+6].any()]
        candidates = sorted(flat or ground, key=lambda p:(p[0]-width*.5)**2+(p[1]-depth*.5)**2)[:200]
        cells = np.asarray(records)
        us,vs,ds = cells[:,0]-cells[:,1], cells[:,0]+cells[:,1]-2*cells[:,2], cells[:,:3].sum(axis=1)
        def portal_visibility(point):
            x,z,y = point
            u,v,d = x+1.5-z, x+1.5+z-2*(y+3), x+1.5+z+y+3
            occluders = np.count_nonzero((abs(us-u)<3)&(abs(vs-v)<6)&(ds>d+3))
            return occluders, (x-width*.5)**2+(z-depth*.5)**2
        x,z,y = min(candidates, key=portal_visibility)
        base = y+1
        for state in ({'Name':'minecraft:obsidian'}, {'Name':'minecraft:nether_portal','Properties':{'axis':'x'}}):
            palette.append(state)
            palette_biomes.append(None)
        for dx in range(4):
            for dy in range(5):
                frame = dx in (0,3) or dy in (0,4)
                decoration_blocks.append([x+dx,z,base+dy,len(palette)-(2 if frame else 1)])
        decoration_anchor = [x+7,z-3,base+7]
    payload = {
        "format": 1, "minecraft_version": "Java 1.16.1", "data_version": 2567,
        "seed": 1, "dimension": dimension, "key": key, "title": title,
        "origin": [ox, oz], "size": [width, depth, 256],
        "presentation": presentation,
        "source_block_count": source_count, "biomes": dict(biome_counts),
        "surface_biomes": dict(Counter(map(int, biome_columns.flat))),
        "structures": starts, "entities": entities, "chunks": chunk_evidence,
        "palette": palette, "palette_biomes": palette_biomes, "blocks": records,
        "decoration_blocks": decoration_blocks, "decoration_anchor": decoration_anchor,
    }
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"{dimension}_{key}.json.gz"
    temporary = target.with_suffix('.pending')
    temporary.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":")).encode(), mtime=0))
    temporary.replace(target)
    print(key, len(records), "surface blocks;", len(palette), "states;", target.stat().st_size, "bytes", flush=True)
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("--output", type=Path, default=CODE / "world_map_regions")
    parser.add_argument("--region", choices=[r[1] for r in REGIONS])
    args = parser.parse_args()
    for spec in REGIONS:
        if args.region is None or args.region == spec[1]:
            export(args.world, args.output, spec)

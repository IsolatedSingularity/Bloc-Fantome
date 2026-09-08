"""Export read-only selector surfaces from official Java 1.16.1 chunks.

Run after generating the documented seed/regions with the local vanilla server.
No terrain generator, template assembly, or material substitution lives here.
Only the Nether roof cutaway and invisible solid interiors are removed.
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
    ("nether", "warped", "Warped Forest", -384, 0, 240, 240),
    ("nether", "crimson", "Crimson Forest", -464, 288, 240, 240),
    ("nether", "valley", "Soul Valley and Deltas", -240, 128, 240, 240),
    ("end", "central", "Central Island", -128, -128, 256, 256),
    ("end", "city", "Outer Islands", -1664, -512, 768, 768),
    ("overworld", "plains", "Plains and River", -304, -32, 240, 240),
    ("overworld", "taiga", "Taiga Village", -288, -400, 256, 256),
    ("overworld", "flowers", "Flower Forest", -544, 416, 240, 240),
    ("overworld", "mushroom", "Mushroom Fields", -3072, 1376, 384, 384),
    ("overworld", "desert", "Desert", 1488, 1872, 240, 240),
    ("ocean", "monument", "Ocean Monument", -1008, -976, 240, 240),
    ("ocean", "shipwreck", "Sunken Shipwreck", -416, 64, 240, 240),
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


def export(world: Path, output: Path, spec: tuple) -> dict:
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
        volume[np.arange(256)[None,None,:] < np.maximum(0,floor-12)[:,:,None]] = 0
        water_ids = np.asarray([p["Name"] == "minecraft:water" for p in palette])
        water = water_ids[volume]
        if dimension == "ocean":
            volume[water] = 0
            presentation = "water cutaway; source seabed section with 12-block geology"
        else:
            # Keep the water surface, removing invisible stacked fluid cells.
            covered = np.roll(water, -1, axis=2)
            covered[:, :, -1] = False
            volume[water & covered] = 0
            presentation = "source surface section with 12-block geology"
    if dimension == "nether":
        # Remove the roof down to the highest air opening below the survey
        # ceiling. Protect structure materials, not all rock inside their BB.
        survey_ceiling = 80 if key == "fortress" else 110
        air = volume[:, :, 32:survey_ceiling+1] == 0
        ceiling = survey_ceiling - np.argmax(air[:, :, ::-1], axis=2)
        ceiling[~air.any(axis=2)] = 31
        remove = np.arange(256)[None, None, :] > ceiling[:, :, None]
        natural = {"air", "netherrack", "gravel", "soul_sand", "soul_soil", "basalt", "lava", "bedrock", "nether_quartz_ore", "nether_gold_ore", "ancient_debris"}
        structure_material = np.asarray([p["Name"].split(":")[1] not in natural for p in palette])
        for start in starts.values():
            if start.get('id') not in ('minecraft:bastion_remnant','minecraft:fortress'):
                continue
            x0, y0, z0, x1, y1, z1 = start["BB"]
            area=(slice(max(0,x0-ox),min(width,x1-ox+1)),slice(max(0,z0-oz),min(depth,z1-oz+1)),slice(y0,y1+1))
            remove[area] &= ~structure_material[volume[area]]
        volume[remove] = 0
        # The bottom is a documented horizontal section through actual blocks.
        volume[:, :, :16] = 0
        presentation = f"roof cutaway above first air below Y{survey_ceiling}; bottom cut at Y16"

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
    payload = {
        "format": 1, "minecraft_version": "Java 1.16.1", "data_version": 2567,
        "seed": 1, "dimension": dimension, "key": key, "title": title,
        "origin": [ox, oz], "size": [width, depth, 256],
        "presentation": presentation,
        "source_block_count": source_count, "biomes": dict(biome_counts),
        "structures": starts, "entities": entities, "chunks": chunk_evidence,
        "palette": palette, "palette_biomes": palette_biomes, "blocks": records,
    }
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"{dimension}_{key}.json.gz"
    target.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":")).encode(), mtime=0))
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

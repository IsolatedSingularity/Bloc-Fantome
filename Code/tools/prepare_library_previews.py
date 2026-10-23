"""Derive representative Library views without rewriting canonical captures.

Swamp selects the most Swamp-dominant 32x32 source window, penalizing village
materials. End retains complete connected islands away from capture edges.
Palette indices, states, biome tints and every selected cell remain original.
"""
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pygame
from engine.capture_records import load_capture_file
from engine.biome_capture import source_sprite

ROOT = Path(__file__).resolve().parents[1] / 'biome_captures'


def derive(name, data):
    cells = list(data['blocks']); width, depth, height = data['size']
    if name == 'swamp':
        top = {}
        structures = set()
        for x, y, z, p in cells:
            biome = data['palette_biomes'][p]
            if biome is not None and (x, y) not in top or biome is not None and z > top[x, y][0]:
                top[x, y] = (z, biome)
            if any(word in data['palette'][p]['Name'] for word in ('planks', 'cobblestone', 'path', 'stairs', 'farmland', 'pumpkin', 'fence', 'torch')):
                structures.add((x, y))
        scores = np.zeros((width, depth), dtype=int)
        for (x, y), (_, biome) in top.items():scores[x, y] = 1 if biome == 6 else -2
        for x, y in structures:scores[x, y] -= 100
        extent = 32
        summed = np.pad(scores, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        windows = summed[extent:, extent:] - summed[:-extent, extent:] - summed[extent:, :-extent] + summed[:-extent, :-extent]
        x0, y0 = map(int, np.unravel_index(windows.argmax(), windows.shape))
        chosen = {(x, y) for x in range(x0, x0+extent) for y in range(y0, y0+extent)}
        counts = Counter(top[p][1] for p in chosen if p in top)
        detail = dict(window=[x0, y0, extent, extent], surface_biomes=dict(counts),
                      swamp_fraction=counts[6]/sum(counts.values()))
    else:
        remaining = {(x, y) for x, y, z, p in cells}
        chosen = set(); components = []
        while remaining:
            seed = remaining.pop(); group = {seed}; queue = [seed]
            while queue:
                x, y = queue.pop()
                for neighbor in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if neighbor in remaining:
                        remaining.remove(neighbor); group.add(neighbor); queue.append(neighbor)
            complete = all(0 < x < width-1 and 0 < y < depth-1 for x, y in group)
            components.append(dict(columns=len(group), complete=complete))
            if complete:chosen.update(group)
        detail = dict(components=components)
    kept = [r for r in cells if tuple(r[:2]) in chosen]
    x0=min(r[0] for r in kept); y0=min(r[1] for r in kept)
    x1=max(r[0] for r in kept); y1=max(r[1] for r in kept)
    derived = dict(data)
    derived['blocks'] = [(x-x0,y-y0,z,p) for x,y,z,p in kept]
    derived['size'] = [x1-x0+1,y1-y0+1,height]
    derived['origin'] = [data['origin'][0]+x0,data['origin'][1]+y0]
    derived['presentation'] = 'Library source subset; canonical capture preserved'
    derived['structures'] = {}; derived['decoration_blocks'] = []
    return derived, detail


def preview(name, data, target):
    # Use the same baked source-model atlas as the opened scene.
    cells=data['blocks']; occupied={tuple(r[:3]) for r in cells}
    visible=[r for r in cells if any((r[0]+dx,r[1]+dy,r[2]+dz) not in occupied
                                   for dx,dy,dz in ((1,0,0),(0,1,0),(0,0,1)))]
    points=[((x-y)*32,(x+y)*16-z*38) for x,y,z,p in visible]
    left=min(x for x,y in points)-64; right=max(x for x,y in points)+64
    top=min(y for x,y in points)-64; bottom=max(y for x,y in points)+96
    scale=min(960/(right-left),620/(bottom-top))
    surface=pygame.Surface((1000,660),pygame.SRCALPHA); sprites={}
    # Atlas anchors match the canonical export (64, 160).
    from tools.bake_world_map_sprites import ANCHOR
    for x,y,z,p in sorted(visible,key=lambda r:sum(r[:3])):
        if p not in sprites:
            raw=source_sprite(name,p,0)
            sprites[p]=pygame.transform.scale(raw,(max(1,round(raw.get_width()*scale)),max(1,round(raw.get_height()*scale))))
        surface.blit(sprites[p],(round(20+((x-y)*32-ANCHOR[0]-left)*scale),
                                 round(20+((x+y)*16-z*38-ANCHOR[1]-top)*scale)))
    pygame.image.save(surface,str(target))


def main():
    pygame.display.init(); pygame.display.set_mode((1,1))
    dest=ROOT/'derived'; dest.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/'manifest.json').read_text()); provenance={}
    for name in ('swamp','small_end_islands'):
        path=ROOT/manifest[name]['file']; data=load_capture_file(path)
        result,detail=derive(name,data)
        result['derived_from']=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**detail)
        output=dest/(name+'.json.gz')
        output.write_bytes(gzip.compress(json.dumps(result,separators=(',',':')).encode(),mtime=0))
        preview(name,result,dest/(name+'.png'))
        provenance[name]=dict(result['derived_from'],file=output.name,source_file=path.name,
                              cells=len(result['blocks']),preview=name+'.png')
    (dest/'manifest.json').write_text(json.dumps(provenance,indent=2))
    print(json.dumps(provenance,indent=2))
    pygame.quit()


if __name__=='__main__':main()

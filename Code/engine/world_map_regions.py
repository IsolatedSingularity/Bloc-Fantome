"""Immutable vanilla chunk captures for the read-only dimension selectors."""
from functools import lru_cache
import gzip
import json
from pathlib import Path

from runtime_paths import BUNDLED_DATA_DIR

REGION_ROOT = Path(BUNDLED_DATA_DIR) / "world_map_regions"
NETHER_HEIGHT_SCALE = 32 / 38
REGIONS = {
    "overworld": (("plains", "Plains and River"), ("taiga", "Snowy Taiga"), ("swamp", "Swamp"),
                  ("flowers", "Flower Forest"), ("mushroom", "Mushroom Fields"),
                  ("desert", "Desert")),
    "nether": (("bastion", "Hoglin Stable"), ("fortress", "Fortress"),
               ("warped", "Warped Forest"), ("crimson", "Crimson Forest"),
               ("valley", "Soul Sand Valley"), ("deltas", "Basalt Deltas")),
    "end": (("central", "Central Island"), ("city", "Outer Islands")),
    "ocean": (("monument", "Ocean Monument"), ("shipwreck", "Sunken Shipwreck"), ("reef", "Coral Reef")),
}

LANDMARKS = {
    'plains': ('Grassy Meadow', 'Riverbank'), 'taiga': ('Snowy Pines', 'Frosted Trail'),
    'swamp': ('Ruined Portal', 'Lily Pond'), 'flowers': ('Flower Meadow', 'Birch Grove'),
    'mushroom': ('Red Mushrooms', 'Brown Mushrooms'), 'desert': ('Sand Dunes', 'Cactus Ridge'),
    'bastion': ('Hoglin Stable', 'Bastion Rampart'), 'fortress': ('Fortress', 'Nether Bridge'),
    'warped': ('Nether Portal', 'Warped Grove'), 'crimson': ('Crimson Grove', 'Shroomlights'),
    'valley': ('Soul Sands', 'Valley Ridge'), 'deltas': ('Basalt Spires', 'Lava Basin'),
    'central': ('Obsidian Pillars', 'Exit Fountain'), 'city': ('End City', 'End Ship'),
    'monument': ('Ocean Monument', 'Kelp Garden'), 'shipwreck': ('Sunken Ship', 'Seagrass Bed'),
    'reef': ('Coral Garden', 'Sea Pickles'),
}


@lru_cache(maxsize=1)
def load_region(dimension, key):
    if key not in dict(REGIONS.get(dimension, ())):
        raise ValueError(f"Unknown selector region {dimension}/{key}")
    path = REGION_ROOT / f"{dimension}_{key}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("minecraft_version") != "Java 1.16.1" or data.get("data_version") != 2567:
        raise ValueError("Selector capture must be Minecraft Java 1.16.1")
    return data


def build_region_hub(world, dimension, key):
    from engine.world_map import MapScene
    data = load_region(dimension, key)
    width, depth, height = data["size"]
    world.resize(width, depth, height, preserve=False)
    world.setDimension("overworld" if dimension == "ocean" else dimension)
    ox, oz = data["origin"]
    # Region sprites retain every source palette state without forcing them
    # through the editable block catalog's material fallbacks.
    anchors = []
    feature = {"bastion": "bastion_remnant", "fortress": "fortress", "city": "endcity",
               "swamp": "ruined_portal", "monument": "monument", "shipwreck": "shipwreck"}.get(key)
    structures = [start for name,start in data["structures"].items() if name.split(":")[0] == feature]
    focus = None
    for start in structures:
        x0,y0,z0,x1,y1,z1 = start["BB"]
        focus = ((x0-ox, z0-oz, y0), (x1-ox, z1-oz, y1))
        ax0,ay0,az0,ax1,ay1,az1=start['Children'][0]['BB']
        if key=='city':
            ax0,ay0,az0,ax1,ay1,az1=max((piece for piece in start['Children'] if piece.get('Template')!='ship'),key=lambda piece:piece['BB'][4])['BB']
        anchors.append(((ax0+ax1)/2-ox,(az0+az1)/2-oz,ay1+4))
    if key == "central":
        focus = ((64,64,45),(192,192,110))
    elif focus is None:
        span = 150 if key == 'mushroom' else min(60, width//3)
        focus = ((width//2-span,depth//2-span,50),(width//2+span,depth//2+span,90))
    if key == 'mushroom':
        land = [(x,z,y) for x,z,y,pid in data['blocks'] if data['palette'][pid]['Name']=='minecraft:mycelium']
        focus = ((min(p[0] for p in land)-12,min(p[1] for p in land)-12,55),
                 (max(p[0] for p in land)+12,max(p[1] for p in land)+12,90))
    elif key == 'swamp':
        focus = ((8,8,55),(width-8,depth-8,95))
    elif key == 'reef':
        floor = [y for x,z,y,pid in data['blocks'] if data['palette'][pid]['Name']=='minecraft:sand']
        center_y = sorted(floor)[len(floor)//2]+6
        focus = ((8,8,center_y-10),(width-8,depth-8,center_y+10))
    elif key == 'valley':
        soil = [y for x,z,y,pid in data['blocks'] if 24<=x<=88 and 96<=z<=160 and y>=40
                and data['palette'][pid]['Name'] in ('minecraft:soul_sand','minecraft:soul_soil')]
        center_y = sorted(soil)[len(soil)//2]+4
        focus = ((24,96,center_y-8),(88,160,center_y+12))
    elif key == 'flowers':
        focus = ((64,16,58),(128,80,86))
    if dimension == "nether":
        # Match the less exaggerated vertical projection of the block atlas.
        focus = tuple((x,z,y*NETHER_HEIGHT_SCALE) for x,z,y in focus)
        anchors = [(x,z,y*NETHER_HEIGHT_SCALE) for x,z,y in anchors]
    if key == "city":
        ship = next(piece for start in structures for piece in start["Children"] if piece.get("Template") == "ship")
        x0,y0,z0,x1,y1,z1 = ship["BB"]
        anchors.append(((x0+x1)/2-ox,(z0+z1)/2-oz,y1+4))
    if dimension == "ocean":
        (x0,z0,y0),(x1,z1,y1) = focus
        focus = ((x0-24,z0-24,y0),(x1+24,z1+24,y1+8))
    elif key == 'desert':
        (x0,z0,y0),(x1,z1,y1) = focus
        focus = ((x0-36,z0-36,y0),(x1+36,z1+36,y1+8))
    # Every survey has two non-playable landmarks. Prefer captured feature
    # blocks; fallback anchors sit on actual nearby surface columns.
    material_pairs = {
        'mushroom': ('red_mushroom_block', 'brown_mushroom_block'),
        'reef': ('tube_coral_block', 'sea_pickle'),
        'swamp': ('vine', 'lily_pad'), 'taiga': ('snow', 'spruce_leaves'),
        'flowers': ('poppy', 'birch_log'),
        'desert': ('sand', 'cactus'), 'warped': ('warped_nylium', 'warped_wart_block'),
        'crimson': ('nether_wart_block', 'shroomlight'),
        'valley': ('soul_sand', 'soul_soil'), 'deltas': ('basalt', 'lava'),
        'monument': ('prismarine', 'kelp'), 'shipwreck': ('oak_planks', 'seagrass'),
    }
    scale = NETHER_HEIGHT_SCALE if dimension == 'nether' else 1.0
    (fx0,fz0,_),(fx1,fz1,_) = focus
    cx,cz = (fx0+fx1)/2,(fz0+fz1)/2
    if key == 'plains':
        focus = ((cx-60,cz-60,50),(cx+60,cz+60,100))
    top = {}
    for x,z,y,pid in data['blocks']:
        if y > top.get((x,z), -1): top[x,z] = y
    for index in range(len(anchors), 2):
        tx,tz = cx + (index*2-1)*24, cz - (index*2-1)*16
        material = material_pairs.get(key, ('',''))[index]
        candidates = [(x,z,y) for x,z,y,pid in data['blocks']
                      if material and data['palette'][pid]['Name']=='minecraft:'+material]
        if not candidates:
            candidates = [(x,z,y) for (x,z),y in top.items()]
        x,z,y = min(candidates,key=lambda p:(p[0]-tx)**2+(p[1]-tz)**2)
        anchors.append((x,z,(y+4)*scale))
    if data.get('decoration_anchor'):
        x,z,y = data['decoration_anchor']
        anchors[0] = (x,z,y*scale)
    return MapScene(
        dimension, data["title"], "Minecraft Java 1.16.1 / Seed 1",
        (), tuple(anchors[:2]), LANDMARKS[key],
        focus, tuple(data["structures"]), (), (), region_key=key, route_indices=(0,1),
    )

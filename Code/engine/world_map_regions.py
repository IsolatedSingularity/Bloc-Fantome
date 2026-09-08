"""Immutable vanilla chunk captures for the read-only dimension selectors."""
from functools import lru_cache
import gzip
import json
from pathlib import Path

from runtime_paths import BUNDLED_DATA_DIR

REGION_ROOT = Path(BUNDLED_DATA_DIR) / "world_map_regions"
REGIONS = {
    "overworld": (("plains", "Plains and River"), ("taiga", "Taiga Village"),
                  ("flowers", "Flower Forest"), ("mushroom", "Mushroom Fields"),
                  ("desert", "Desert Coast")),
    "nether": (("bastion", "Hoglin Stable"), ("fortress", "Fortress"),
               ("warped", "Warped Forest"), ("crimson", "Crimson Forest"),
               ("valley", "Valley and Deltas")),
    "end": (("central", "Central Island"), ("city", "Outer Islands")),
    "ocean": (("monument", "Ocean Monument"), ("shipwreck", "Sunken Shipwreck")),
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
               "taiga": "village", "monument": "monument", "shipwreck": "shipwreck",
               "desert": "desert_pyramid"}.get(key)
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
        focus = ((width//2-60,depth//2-60,50),(width//2+60,depth//2+60,90))
    if dimension == "nether":
        # Match the less exaggerated vertical projection of the block atlas.
        focus = tuple((x,z,y*0.6) for x,z,y in focus)
        anchors = [(x,z,y*0.6) for x,z,y in anchors]
    route_indices = (1,) if key == "fortress" else (0,) if key == "bastion" else ()
    if key == "city":
        route_indices = (0, 1)
        ship = next(piece for start in structures for piece in start["Children"] if piece.get("Template") == "ship")
        x0,y0,z0,x1,y1,z1 = ship["BB"]
        anchors.append(((x0+x1)/2-ox,(z0+z1)/2-oz,y1+4))
    if dimension == "overworld":
        route_indices = (0,) if key == "taiga" else (1,) if key == "desert" else ()
    if dimension == "ocean":
        route_indices = (0,) if key == "monument" else (1,)
        (x0,z0,y0),(x1,z1,y1) = focus
        focus = ((x0-24,z0-24,y0),(x1+24,z1+24,y1+8))
    elif key == 'desert':
        (x0,z0,y0),(x1,z1,y1) = focus
        focus = ((x0-36,z0-36,y0),(x1+36,z1+36,y1+8))
    if not route_indices:
        anchors = []
    labels = {"nether": ("Bastion Gate", "Fortress", "Soul Valley", "Warped Route"),
              "end": ("End City", "End Ship", "Outer Isle", "Void Route"),
              "overworld": ("Village", "Temple", "Forest", "Mushrooms"),
              "ocean": ("Monument", "Shipwreck", "Ocean Ruins", "Deep Water")}
    return MapScene(
        dimension, data["title"], "Minecraft Java 1.16.1 / Seed 1",
        (() if dimension == 'ocean' else tuple(anchors[:2])),
        (tuple(anchors[:2]) if dimension == 'ocean' else ()), labels[dimension],
        focus, tuple(data["structures"]), (), (), region_key=key, route_indices=route_indices,
    )

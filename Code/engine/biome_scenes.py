"""Editable cells from actual Java 1.16.1 captures (see biome_capture)."""
from functools import lru_cache
from engine.biome_capture import capture
SIZE=48

@lru_cache(maxsize=6)
def biome_scene(biome_id):
    data=capture(biome_id)
    names=data['editable_palette']
    return tuple((x,y,z,names[p]) for x,y,z,p in data['blocks'])

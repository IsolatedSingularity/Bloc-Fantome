"""Prepare independent map data and surfaces without touching the display."""
from copy import copy
import pygame


def prepare_map(dimension, catalog, renderer, size, decode=None, tracks=(), prepared=None):
    from time import perf_counter
    timeline = [('start', perf_counter())]
    from engine.world import World
    from engine.world_map import build_hub
    from ui.source_map import SourceMap
    if prepared is None:
        world = World(1, 1, 1, catalog=catalog)
        scene = build_hub(world, dimension)
        bounds = (world.width, world.depth, world.height, world.min_y)
        timeline.append(('hub', perf_counter()))
        source = SourceMap(dimension, scene.region_key) if scene.region_key else None
        music = None
    else:
        scene, bounds, source, music = prepared
    timeline.append(('source', perf_counter()))
    if source:
        camera = copy(renderer)
        source.frame_overview(camera, size)
        source.render(pygame.Surface(size, pygame.SRCALPHA), camera, cooperative=True)
    timeline.append(('render', perf_counter()))
    if music is None:music = {path: decode(path) for path in tracks} if decode else {}
    timeline.append(('music', perf_counter()))
    if source:source.preparation_timeline = timeline
    return scene, bounds, source, music

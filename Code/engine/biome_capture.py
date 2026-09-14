"""Version-locked biome captures, preserving source palette states through edits."""
from functools import lru_cache
from pathlib import Path
import gzip
import json
import pygame
from runtime_paths import BUNDLED_DATA_DIR
from engine.capture_records import load_capture_file

ROOT=Path(BUNDLED_DATA_DIR)/'biome_captures'

@lru_cache(maxsize=1)
def manifest():return json.loads((ROOT/'manifest.json').read_text())

@lru_cache(maxsize=1)
def scene_manifest():
    path=ROOT/'scenes.json'
    return json.loads(path.read_text()) if path.exists() else {}

@lru_cache(maxsize=2)
def capture(name):
    row={'file':'tutorial_end_city.json.gz'} if name=='_tutorial_end_city' else (scene_manifest() if name.startswith('_scene_') else manifest())[name]
    data=load_capture_file(ROOT/row['file'])
    if data['data_version']!=2567:raise ValueError('Biome capture must be Java 1.16.1')
    return data

@lru_cache(maxsize=4)
def atlas(name,rotation):
    if name!='_tutorial_end_city' and name not in manifest() and name not in scene_manifest():return None
    path=ROOT/'atlases'/f'{name}_{rotation%4}.png'
    return pygame.image.load(str(path)).convert_alpha() if path.exists() else None

@lru_cache(maxsize=512)
def source_sprite(name,index,rotation):
    image=atlas(name,rotation)
    if image is None or index<0:return None
    row=(scene_manifest() if name.startswith('_scene_') else manifest()).get(name,{})
    count=row.get('palette_count')
    if count is None:count=len(capture(name)['palette'])
    if index>=count:return None
    return image.subsurface(((index%16)*128,(index//16)*208,128,208)).copy()

@lru_cache(maxsize=80)
def default_sprite(name):
    path=ROOT/'materials'/f'{name.lower()}.png'
    return pygame.image.load(str(path)).convert_alpha() if path.exists() else None

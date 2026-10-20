"""Read-only prepared lesson data shipped with this exact application build."""
import gzip
import hashlib
import json
import pickle
import sys
from functools import lru_cache
from pathlib import Path
from dataclasses import replace
from runtime_paths import BUNDLED_DATA_DIR

ROOT=Path(BUNDLED_DATA_DIR)/'tutorial_prepared'
SOURCES=('blocFantome.py','engine/world.py','engine/world_snapshot.py',
         'engine/tutorial_runtime.py','engine/tutorial_lessons.py',
         'engine/block_state.py','domain/blocks.py','engine/biome_capture.py',
         'engine/build_io.py','engine/capture_materials.py')


@lru_cache(maxsize=1)
def fingerprint():
    root=Path(__file__).resolve().parents[1]
    digest=hashlib.sha256()
    for name in SOURCES:digest.update((root/name).read_bytes())
    for path in sorted((root/'biome_captures').glob('*.json*')):
        digest.update(path.name.encode());digest.update(path.read_bytes())
    return digest.hexdigest()


def load_lesson(key,catalog):
    manifest=ROOT/'manifest.json'
    if not manifest.is_file():return None
    index=json.loads(manifest.read_text())
    if index.get('schema')!=1:return None
    if not getattr(sys,'frozen',False) and index.get('code')!=fingerprint():return None
    row=index['lessons'].get(key)
    if row is None:return None
    packed=(ROOT/row['file']).read_bytes()
    if hashlib.sha256(packed).hexdigest()!=row['sha256']:
        raise ValueError('Damaged prepared tutorial: '+key)
    # Only our bundled, digest-checked data is read here, never a user save or
    # downloaded path. Each load creates an independent, one-use state holder.
    snapshot,state=pickle.loads(gzip.decompress(packed))
    from engine.world import World
    prepared=World(snapshot.width,snapshot.depth,snapshot.height,catalog=catalog)
    prepared.__dict__.update(state)
    return replace(snapshot,_prepared=[prepared])

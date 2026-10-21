"""Disposable lesson accelerators derived from tracked source data.

Pickle is only used for application-owned build output, never user saves. Its
digest checks integrity, not authenticity of arbitrary downloaded data. Missing,
stale or damaged caches fall back to exact scene preparation; builds fail closed.
"""
from dataclasses import replace
from functools import lru_cache
import gzip
import hashlib
import json
import logging
from pathlib import Path
import pickle
import sys
from runtime_paths import BUNDLED_DATA_DIR

ROOT=Path(BUNDLED_DATA_DIR)/'tutorial_prepared'
SCHEMA=2
SOURCES=('blocFantome.py','engine/world.py','engine/world_snapshot.py',
         'engine/tutorial_runtime.py','engine/tutorial_lessons.py','engine/tutorial_scenes.py',
         'engine/tutorial_prepared.py','engine/draw_order.py','engine/block_state.py','domain/blocks.py',
         'domain/block_catalog.py','domain/world_catalog.py','domain/structures.py',
         'engine/biome_capture.py','engine/capture_records.py','engine/build_io.py',
         'engine/capture_materials.py','engine/scene_cache.py','engine/native_acceleration.py')


def fingerprint_at(root):
    """Hash code and source records read by the exact lesson builders."""
    root=Path(root);paths={root/name for name in SOURCES}
    for pattern in ('biome_captures/*.json*','biome_captures/runtime/*.gz',
                    'worlds/*.json*','saves/*.json*'):
        paths.update(root.glob(pattern))
    digest=hashlib.sha256()
    for path in sorted(paths):
        if path.name.startswith('_autosave'):continue
        name=path.relative_to(root).as_posix().encode();payload=path.read_bytes()
        digest.update(len(name).to_bytes(4,'little'));digest.update(name)
        digest.update(len(payload).to_bytes(8,'little'));digest.update(payload)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def fingerprint():return fingerprint_at(Path(__file__).resolve().parents[1])


def new_index():
    return {'schema':SCHEMA,'python':list(sys.version_info[:2]),'code':fingerprint(),'lessons':{}}


def read_index(root):
    index=json.loads((Path(root)/'manifest.json').read_text(encoding='utf-8'))
    if (index.get('schema')!=SCHEMA or index.get('python')!=list(sys.version_info[:2])
            or not isinstance(index.get('lessons'),dict)):
        raise ValueError('Incompatible prepared lesson schema or Python version')
    if not getattr(sys,'frozen',False) and index.get('code')!=fingerprint():
        raise ValueError('Stale prepared lessons; run Code/tools/bake_tutorial.py')
    return index


def read_payload(root,row):
    name=row['file']
    if not isinstance(name,str) or Path(name).name!=name or not name.endswith('.prepared'):
        raise ValueError('Prepared lesson path must be a local .prepared filename')
    packed=(Path(root)/name).read_bytes()
    if hashlib.sha256(packed).hexdigest()!=row['sha256']:
        raise ValueError('Damaged prepared tutorial: '+name)
    return packed


def validate_bundle(root=None,required=None):
    root=ROOT if root is None else root
    index=read_index(root)
    if required is not None and set(index['lessons'])!=set(required):
        raise ValueError('Release requires every prepared large tutorial lesson')
    for row in index['lessons'].values():read_payload(root,row)
    return index


def encode_lesson(snapshot):
    state=dict(snapshot._prepared[0].__dict__)
    state.pop('catalog');state.pop('_retiredState',None)
    return gzip.compress(pickle.dumps((replace(snapshot,_prepared=None),state),protocol=5),
                         compresslevel=1,mtime=0)


def load_lesson(key,catalog):
    if not (ROOT/'manifest.json').is_file():return None
    try:
        index=read_index(ROOT);row=index['lessons'].get(key)
        if row is None:return None
        snapshot,state=pickle.loads(gzip.decompress(read_payload(ROOT,row)))
        from engine.world import World
        from engine.world_snapshot import WorldSnapshot
        if not isinstance(snapshot,WorldSnapshot) or not isinstance(state,dict):
            raise ValueError('Invalid prepared lesson payload')
        if len(snapshot.blocks)!=row['cells']:raise ValueError('Prepared lesson cell count mismatch')
        prepared=World(snapshot.width,snapshot.depth,snapshot.height,catalog=catalog)
        prepared.__dict__.update(state)
        return replace(snapshot,_prepared=[prepared])
    except (OSError,ValueError,KeyError,TypeError,EOFError,pickle.UnpicklingError,AttributeError) as error:
        logging.getLogger(__name__).warning('Prepared tutorial %s skipped: %s',key,error)
        return None

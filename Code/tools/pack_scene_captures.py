"""Prepack exact source records for runtime; retain original JSON for auditing."""
from array import array
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import zlib


def pack_capture(path):
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    destination = path.parent / 'runtime'
    destination.mkdir(exist_ok=True)
    metadata_path = destination / path.name
    cells_path = destination / (path.name.removesuffix('.json.gz') + '.cells.gz')
    if metadata_path.exists() and cells_path.exists():
        try:
            metadata = json.loads(gzip.decompress(metadata_path.read_bytes()))
            payload=gzip.decompress(cells_path.read_bytes())
            if (metadata.get('_source_sha256') == digest
                    and metadata.get('_cells_sha256') == hashlib.sha256(payload).hexdigest()
                    and len(payload)==metadata.get('_record_count',-1)*8):
                return False
        except (OSError,ValueError,EOFError,TypeError,zlib.error):pass
    data = json.loads(gzip.decompress(original))
    records = data.pop('blocks')
    packed = array('H', (value for row in records for value in row))
    if packed.itemsize != 2:
        raise RuntimeError('Source capture packing requires 16-bit unsigned shorts')
    if sys.byteorder != 'little':
        packed.byteswap()
    payload=packed.tobytes()
    data.update(_source_sha256=digest, _record_count=len(records),_cells_sha256=hashlib.sha256(payload).hexdigest())
    for target, payload in ((cells_path, payload),
                            (metadata_path, json.dumps(data,separators=(',',':')).encode())):
        temporary = target.with_suffix('.tmp')
        temporary.write_bytes(gzip.compress(payload,mtime=0))
        os.replace(temporary,target)
    return True


def pack_all(root):
    return sum(pack_capture(path) for path in sorted(Path(root).glob('*.json.gz')))


if __name__ == '__main__':
    print('Packed',pack_all(Path(__file__).resolve().parents[1]/'biome_captures'),'source captures')

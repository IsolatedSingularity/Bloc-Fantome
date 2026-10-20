"""Compact read-only source cells without millions of intermediate JSON lists."""
from collections.abc import Sequence
import gzip
import hashlib
import json
import struct
import logging
import zlib


class CaptureRecords(Sequence):
    def __init__(self, payload):
        if len(payload) % 8:
            raise ValueError('Incomplete source capture record')
        self.payload = payload

    def __len__(self):
        return len(self.payload) // 8

    def __iter__(self):
        return struct.iter_unpack('<4H', self.payload)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self))) ]
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        return struct.unpack_from('<4H', self.payload, index * 8)


def load_capture_file(path):
    original = path.read_bytes()
    packed = path.parent / 'runtime' / path.name
    if packed.exists():
        try:
            metadata = json.loads(gzip.decompress(packed.read_bytes()))
            if metadata.pop('_source_sha256', None) == hashlib.sha256(original).hexdigest():
                cells = packed.with_name(path.name.removesuffix('.json.gz') + '.cells.gz')
                payload = gzip.decompress(cells.read_bytes())
                if hashlib.sha256(payload).hexdigest() != metadata.pop('_cells_sha256',None):
                    raise ValueError('Packed capture cell digest mismatch')
                records = CaptureRecords(payload)
                if len(records) != metadata.pop('_record_count'):
                    raise ValueError('Packed capture cell count mismatch')
                metadata['blocks'] = records
                return metadata
        except (OSError,ValueError,EOFError,KeyError,TypeError,zlib.error) as error:
            logging.getLogger(__name__).warning('Derived capture %s skipped: %s',path.name,error)
    # Source development remains usable before packing or after changing a capture.
    return json.loads(gzip.decompress(original))

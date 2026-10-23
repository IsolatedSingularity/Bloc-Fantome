"""Local native build receipts. Hashes detect stale output, not untrusted code."""
import hashlib
import json
from pathlib import Path
import platform
import struct


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_hashes(code):
    code = Path(code)
    crate = code / 'native/depth_sort'
    paths = [code / 'build_native.py', crate / 'Cargo.toml', crate / 'Cargo.lock']
    paths.extend(sorted((crate / 'src').rglob('*.rs')))
    return {p.relative_to(code).as_posix(): digest(p) for p in paths}


def write_receipt(library, code):
    library = Path(library)
    record = dict(schema=1, binary_sha256=digest(library), sources=source_hashes(code),
                  machine=platform.machine().lower(), bits=struct.calcsize('P') * 8)
    from engine.settings_io import write_json_atomic
    write_json_atomic(library.with_suffix('.json'), record)


def verified(library, code=None):
    try:
        library = Path(library)
        record = json.loads(library.with_suffix('.json').read_text(encoding='utf-8'))
        return (isinstance(record, dict) and record.get('schema') == 1
                and record.get('machine') == platform.machine().lower()
                and record.get('bits') == struct.calcsize('P') * 8
                and record.get('binary_sha256') == digest(library)
                and bool(record.get('sources'))
                and (code is None or record['sources'] == source_hashes(code)))
    except (OSError, ValueError, TypeError):
        return False

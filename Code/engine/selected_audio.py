"""Release-media contract, independent of Pygame initialization."""
import hashlib
import json
from pathlib import Path


def validate_selected_audio(sound_root, manifest):
    records = json.loads(Path(manifest).read_text(encoding='utf-8'))
    roles = {row['role'] for row in records if row['role']}
    if roles != {'boot', 'shutdown', 'world_map', 'save', 'error', 'button', 'close'}:
        raise ValueError('Selected audio manifest must define all seven roles')
    for row in records:
        path = Path(sound_root) / 'ui/selected' / row['file']
        if not path.is_file():raise FileNotFoundError(f'Required selected audio missing: {path}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError(f'Selected original audio hash mismatch: {path}')
    return records


def validate_presentation_audio(sound_root, manifest):
    records=json.loads(Path(manifest).read_text(encoding='utf-8'))['files']
    expected={*(f'voice{i:02d}' for i in range(1,12)),'contact','fall','reflection'}
    if {row['name'] for row in records}!=expected:
        raise ValueError('Incomplete Pass B recorded presentation manifest')
    for row in records:
        path=Path(sound_root)/'opening/pass-b'/row['file']
        if not path.is_file():raise FileNotFoundError(f'Required Pass B audio missing: {path}')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError(f'Pass B audio hash mismatch: {path}')
    return records

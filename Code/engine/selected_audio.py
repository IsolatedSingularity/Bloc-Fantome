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

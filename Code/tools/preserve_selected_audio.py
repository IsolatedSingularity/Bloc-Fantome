"""Inventory and preserve the owner's selected originals without transcoding."""
import hashlib
import json
from pathlib import Path
import shutil
import wave
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ROLES = {'bootUp': 'boot', 'shutDown': 'shutdown', 'worldMap': 'world_map',
         'save': 'save', 'error': 'error', 'pressButton': 'button', 'close': 'close'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT / 'Sounds'
    destination = ROOT / 'Assets/Sound Hub/ui/selected'
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(source.rglob('*.wav')):
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and digest(target) != digest(path):
            raise ValueError(f'Refusing to replace a different preserved original: {target}')
        if not target.exists():shutil.copy2(path, target)
        assert digest(target) == digest(path)
        with wave.open(str(path), 'rb') as wav:
            channels, width, rate, frames, codec, _ = wav.getparams()
            raw = wav.readframes(frames)
        if width != 2:raise ValueError(f'Inspect unsupported PCM width: {path}')
        samples = np.frombuffer(raw, dtype='<i2').astype(float) / 32768
        records.append(dict(source=path.relative_to(ROOT).as_posix(),
            file=relative.as_posix(), runtime=target.relative_to(ROOT).as_posix(),
            role=ROLES.get(path.stem), codec=f'WAV PCM signed {width*8}-bit little-endian',
            channels=channels, sample_rate=rate, frames=frames, duration_seconds=frames/rate,
            bytes=path.stat().st_size, sha256=digest(path), peak=float(abs(samples).max()),
            rms=float(np.sqrt(np.mean(samples*samples))),
            author='Owner private licensing records', source_url=None,
            permission='Owner-cleared local development and compiled releases; standalone source redistribution not asserted'))
    assert {r['role'] for r in records if r['role']} == set(ROLES.values())
    manifest = ROOT / 'docs/design/selected-audio.json'
    manifest.write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8')
    backup = ROOT / '.qa/pass-b/selected-audio-originals.zip'
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        with zipfile.ZipFile(backup, 'w', zipfile.ZIP_DEFLATED) as archive:
            for row in records:archive.write(ROOT/row['source'], row['source'])
            archive.write(manifest, manifest.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(backup) as archive:
        assert archive.testzip() is None
        for row in records:
            assert hashlib.sha256(archive.read(row['source'])).hexdigest() == row['sha256']
    (backup.parent/'audio-backup.json').write_text(json.dumps(dict(
        archive=str(backup), sha256=digest(backup), files=len(records), verified=True,
        off_device_copy_verified=False), indent=2)+'\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':main()

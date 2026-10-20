"""Archive tracked derived QA evidence; keep all originals in the working tree.

Create and independently extract a ZIP, then compare every SHA-256. This tool
does not change Git tracking. The manifest is also the explicit removal list.
Source worlds, research, audio sources, scripts and receipts are excluded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PROTECTED = ('.qa/natural-292/', '.qa/biome-capture-281/',
             '.qa/void-capture-281/', '.qa/worldmap-vanilla/')
DERIVED = {'.png', '.gif', '.bfc', '.prof', '.xml', '.mp4'}


def selected(path):
    return (path.startswith('.qa/') and not path.startswith(PROTECTED)
            and Path(path).suffix in DERIVED)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def archive(destination):
    destination = destination.resolve()
    if not destination.is_relative_to(ROOT / '.qa'):
        raise ValueError('Archive destination must be inside workspace .qa')
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / 'manifest.json'
    archive_path = destination / 'generated-evidence.zip'
    if archive_path.exists() or manifest_path.exists():
        raise FileExistsError('Preserve the existing archive; use a fresh destination')
    names = subprocess.check_output(['git', 'ls-files', '-z', '.qa'], cwd=ROOT).decode().split('\0')
    rows = [{'path': name, 'bytes': (ROOT / name).stat().st_size,
             'sha256': sha(ROOT / name)} for name in names if selected(name)]
    index = {'baseline': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
             'files': rows, 'count': len(rows), 'bytes': sum(row['bytes'] for row in rows)}
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_STORED, allowZip64=True) as output:
        for row in rows:
            output.write(ROOT / row['path'], row['path'])
        output.writestr('MANIFEST.json', json.dumps(index, indent=2))
    index['archive_sha256'] = sha(archive_path)
    index['archive_bytes'] = archive_path.stat().st_size
    # A separate reader and actual files, rather than ZipFile.testzip alone.
    extracted = destination / 'verified-extraction'
    with zipfile.ZipFile(archive_path) as source:
        source.extractall(extracted)
    for row in rows:
        candidate = extracted / row['path']
        if candidate.stat().st_size != row['bytes'] or sha(candidate) != row['sha256']:
            raise ValueError('Archive verification failed: ' + row['path'])
    index['verified_extraction'] = True
    manifest_path.write_text(json.dumps(index, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in index.items() if k != 'files'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    archive(parser.parse_args().destination)

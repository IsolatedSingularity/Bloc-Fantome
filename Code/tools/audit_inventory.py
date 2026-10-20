"""Read-only inventory and preservation receipts for the engineering review.

Outputs stay local. No files are removed and no user configuration is loaded by
the application. Run from any directory with the tested Python interpreter.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / '.qa/engineering-audit'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def preservation():
    installed_root=Path(os.environ['LOCALAPPDATA'])/'Programs/Bloc Fantôme'
    roots = [ROOT, ROOT / 'Code', ROOT / 'saves', ROOT / 'Code/saves',
             Path(os.environ['APPDATA']) / 'BlocFantome',
             Path(os.environ['LOCALAPPDATA']) / 'BlocFantome',
             installed_root,installed_root/'saves']
    paths = set()
    for base in roots:
        if not base.is_dir():
            continue
        paths.update(p for p in base.glob('.*config*.json') if p.is_file())
        paths.update(p for p in base.glob('config.json') if p.is_file())
        if base.name in ('saves', 'BlocFantome'):
            paths.update(p for p in base.rglob('*') if p.is_file())
    paths.update(ROOT.glob('*.exe'))
    paths.update((ROOT / 'Code/build/installer').glob('*.exe'))
    installed = installed_root/'BlocFantome.exe'
    if installed.is_file():
        paths.add(installed)
    return {str(p): {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(paths)}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = subprocess.check_output(['git', 'ls-tree', '-r', '-l', 'HEAD'], cwd=ROOT).decode().splitlines()
    groups = {}
    files = []
    for row in rows:
        info, name = row.split('\t', 1)
        size = int(info.split()[-1])
        group = '/'.join(name.split('/')[:2]) if name.startswith('.qa/') else name.split('/')[0]
        total = groups.setdefault(group, {'files': 0, 'bytes': 0})
        total['files'] += 1
        total['bytes'] += size
        files.append({'path': name, 'bytes': size})
    (OUTPUT / 'tracked-inventory.json').write_text(json.dumps({'groups': groups, 'files': files}, indent=2))
    receipt = OUTPUT / 'preservation-before.json'
    if not receipt.exists():
        receipt.write_text(json.dumps(preservation(), indent=2))
    print(json.dumps(dict(sorted(groups.items(), key=lambda x: -x[1]['bytes']))))


if __name__ == '__main__':
    main()

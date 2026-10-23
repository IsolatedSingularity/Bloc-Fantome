"""Recover Java 1.21.1 textures and indexed sounds without overwriting assets.

Only this release layout is validated. Install and launch it once with the Java
launcher first. Private opening, font, skybox and custom audio inputs are separate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import tempfile
import zipfile

SUPPORTED_VERSIONS = {(1, 21, 1)}
MIN_VERSION = (1, 21, 1)


def get_minecraft_dir():
    system = platform.system()
    if system == 'Windows':
        root = Path(os.environ.get('APPDATA', Path.home())) / '.minecraft'
    elif system == 'Darwin':
        root = Path.home() / 'Library/Application Support/minecraft'
    else:
        root = Path.home() / '.minecraft'
    return root if root.is_dir() else None


def parse_version(value):
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', value):
        return None
    parts = tuple(map(int, value.split('.')))
    return parts if len(parts) == 3 else (*parts, 0)


def find_best_version(versions_dir):
    candidates = []
    for folder in Path(versions_dir).iterdir() if Path(versions_dir).is_dir() else ():
        version = parse_version(folder.name)
        jar = folder / (folder.name + '.jar')
        if version in SUPPORTED_VERSIONS and jar.is_file():
            candidates.append((version, jar, folder.name))
    if not candidates:
        return None
    _, jar, name = max(candidates)
    return jar, name


def _safe_relative(value):
    path = PurePosixPath(value)
    if (not value or '\\' in value or ':' in value or path.is_absolute()
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Unsafe asset path: ' + value)
    return path


def _checked_bytes(path, record):
    data = Path(path).read_bytes()
    expected = record.get('hash', record.get('sha1'))
    if (not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{40}', expected)
            or len(data) != record.get('size') or hashlib.sha1(data).hexdigest() != expected):
        raise ValueError('Missing or damaged Java asset: ' + str(path))
    return data


def _stage(jar_path, stage, minecraft_dir):
    from PIL import Image
    metadata = json.loads(jar_path.with_suffix('.json').read_text(encoding='utf-8'))
    if (parse_version(jar_path.stem) not in SUPPORTED_VERSIONS
            or metadata.get('id') != jar_path.stem or metadata.get('type') != 'release'):
        raise ValueError('Unsupported Java release; validated release is 1.21.1')
    index_record = metadata['assetIndex']
    index_id = str(index_record['id'])
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', index_id):
        raise ValueError('Invalid asset index identifier')
    index = json.loads(_checked_bytes(minecraft_dir / 'assets/indexes' / (index_id + '.json'), index_record))
    entries = {}
    counts = {'textures': 0, 'sounds': 0}

    def put(relative, data):
        relative = _safe_relative(relative).as_posix()
        folded = relative.casefold()
        if folded in entries:
            raise ValueError('Asset destination collision: ' + relative)
        entries[folded] = relative
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    with zipfile.ZipFile(jar_path) as jar:
        for item in jar.infolist():
            prefix = 'assets/minecraft/textures/'
            if not item.filename.startswith(prefix) or item.is_dir():
                continue
            relative = _safe_relative(item.filename[len(prefix):])
            if not str(relative).endswith(('.png', '.png.mcmeta')):
                continue
            parts = list(relative.parts)
            if parts[0] in ('block', 'item'):
                parts[0] += 's'
            data = jar.read(item)
            put('Texture Hub/' + '/'.join(parts), data)
            if str(relative).endswith('.png'):
                with Image.open(stage / 'Texture Hub' / Path(*parts)) as image:
                    image.verify()
                counts['textures'] += 1
            else:
                json.loads(data)
    for name, record in index['objects'].items():
        prefix = 'minecraft/sounds/'
        if not name.startswith(prefix) or not name.endswith('.ogg'):
            continue
        relative = _safe_relative(name[len(prefix):]).as_posix()
        digest = record['hash']
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{40}', digest):
            raise ValueError('Invalid object hash')
        data = _checked_bytes(minecraft_dir / 'assets/objects' / digest[:2] / digest, record)
        if not data.startswith(b'OggS'):
            raise ValueError('Invalid Ogg asset: ' + name)
        put('Sound Hub/' + relative, data)
        counts['sounds'] += 1
    if not all(counts.values()):
        raise ValueError('Incomplete extraction: textures and indexed sounds are both required')
    return counts


def _promote(stage, assets_dir):
    """Validate every destination before installing; roll back new files on error."""
    assets_dir = assets_dir.resolve()
    files = sorted(p for p in stage.rglob('*') if p.is_file())
    pending = []
    for source in files:
        target = assets_dir / source.relative_to(stage)
        if not target.resolve().is_relative_to(assets_dir):
            raise ValueError('Asset destination escapes output directory')
        if target.exists():
            if not target.is_file() or target.read_bytes() != source.read_bytes():
                raise ValueError('Existing asset differs; preserve it and use a fresh output directory: ' + str(target))
        else:
            pending.append((source, target))
    written = []
    try:
        for source, target in pending:
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation also protects against a file appearing after validation.
            with target.open('xb') as output:
                written.append(target)
                with source.open('rb') as input_stream:
                    shutil.copyfileobj(input_stream, output)
                output.flush()
                os.fsync(output.fileno())
    except BaseException:
        for target in reversed(written):
            target.unlink()
        raise


def extract_assets(jar_path, assets_dir, minecraft_dir=None):
    jar_path, assets_dir = Path(jar_path), Path(assets_dir)
    minecraft_dir = Path(minecraft_dir) if minecraft_dir else jar_path.parents[2]
    try:
        assets_dir.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.asset-stage-', dir=assets_dir.parent) as temporary:
            stage = Path(temporary)
            counts = _stage(jar_path, stage, minecraft_dir)
            _promote(stage, assets_dir)
        print(f"Validated Java 1.21.1: {counts['textures']} textures, {counts['sounds']} indexed sounds")
        return True
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(f'Asset setup failed without replacing existing files: {error}')
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--minecraft-dir', type=Path)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'Assets')
    args = parser.parse_args()
    minecraft = args.minecraft_dir or get_minecraft_dir()
    result = find_best_version(minecraft / 'versions') if minecraft else None
    if not result:
        print('Install and launch Minecraft Java 1.21.1 before extracting assets.')
        return 1
    return 0 if extract_assets(result[0], args.output_dir, minecraft) else 1


if __name__ == '__main__':
    raise SystemExit(main())

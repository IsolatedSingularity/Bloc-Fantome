"""Redistributable synthetic Java layout; no game or private media needed."""
import hashlib
import io
import json
import zipfile
from pathlib import Path
from PIL import Image
import pytest
import setup_assets as setup


@pytest.fixture
def java(tmp_path):
    mc = tmp_path / 'minecraft'
    version = mc / 'versions/1.21.1'
    version.mkdir(parents=True)
    jar = version / '1.21.1.jar'
    png = io.BytesIO(); Image.new('RGBA', (16, 16), (40, 80, 20, 255)).save(png, format='PNG')
    with zipfile.ZipFile(jar, 'w') as archive:
        archive.writestr('assets/minecraft/textures/block/stone.png', png.getvalue())
        archive.writestr('assets/minecraft/textures/entity/chest/normal.png', png.getvalue())
        archive.writestr('assets/minecraft/textures/block/stone.png.mcmeta', '{"animation":{}}')
    sound = b'OggS synthetic indexed sound fixture'
    digest = hashlib.sha1(sound).hexdigest()
    obj = mc / 'assets/objects' / digest[:2] / digest
    obj.parent.mkdir(parents=True); obj.write_bytes(sound)
    index = mc / 'assets/indexes/17.json'; index.parent.mkdir(parents=True)
    index.write_text(json.dumps({'objects': {'minecraft/sounds/block/test.ogg': {'hash': digest, 'size': len(sound)}}}))
    jar.with_suffix('.json').write_text(json.dumps({'id': '1.21.1', 'type': 'release', 'assetIndex': {
        'id':'17', 'sha1':hashlib.sha1(index.read_bytes()).hexdigest(), 'size':index.stat().st_size}}))
    return mc, jar, obj


def test_hashed_sounds_and_nested_textures(java, tmp_path):
    mc, jar, obj = java; dest = tmp_path / 'Assets'
    assert setup.extract_assets(jar, dest)
    assert (dest / 'Sound Hub/block/test.ogg').read_bytes() == obj.read_bytes()
    assert (dest / 'Texture Hub/entity/chest/normal.png').is_file()
    assert (dest / 'Texture Hub/blocks/stone.png.mcmeta').is_file()


@pytest.mark.parametrize('damage', ['missing', 'hash', 'index'])
def test_incomplete_source_never_touches_existing(java, tmp_path, damage):
    mc, jar, obj = java; dest = tmp_path / 'Assets'; dest.mkdir()
    original = dest / 'owner.wav'; original.write_bytes(b'preserve')
    if damage == 'missing':obj.unlink()
    elif damage == 'hash':obj.write_bytes(b'bad')
    else:(mc / 'assets/indexes/17.json').write_text('{}')
    assert not setup.extract_assets(jar, dest)
    assert list(dest.iterdir()) == [original]


def test_existing_collision_and_case_collision_are_rejected(java, tmp_path):
    mc, jar, obj = java; dest = tmp_path / 'Assets'
    original = dest / 'Texture Hub/blocks/stone.png'; original.parent.mkdir(parents=True)
    original.write_bytes(b'owner texture')
    assert not setup.extract_assets(jar, dest)
    assert original.read_bytes() == b'owner texture'
    with zipfile.ZipFile(jar, 'a') as archive:
        archive.writestr('assets/minecraft/textures/block/STONE.png', b'collision')
    assert not setup.extract_assets(jar, tmp_path / 'fresh')


@pytest.mark.parametrize('version', ['1.21.1-forge', '1.21.1-pre1', '24w10a', '2.0', '1.20.6'])
def test_only_validated_release_selected(tmp_path, version):
    folder = tmp_path / version; folder.mkdir(); (folder / (version + '.jar')).touch()
    assert setup.find_best_version(tmp_path) is None


def test_unsafe_index_path_is_rejected(java, tmp_path):
    mc, jar, obj = java
    index = mc / 'assets/indexes/17.json'
    data=json.loads(index.read_text());data['objects']['minecraft/sounds/../escape.ogg']=next(iter(data['objects'].values()))
    index.write_text(json.dumps(data))
    metadata=json.loads(jar.with_suffix('.json').read_text())
    metadata['assetIndex'].update(sha1=hashlib.sha1(index.read_bytes()).hexdigest(),size=index.stat().st_size)
    jar.with_suffix('.json').write_text(json.dumps(metadata))
    assert not setup.extract_assets(jar, tmp_path / 'Assets')

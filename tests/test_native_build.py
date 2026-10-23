"""Optional acceleration must be tied to the exact sources and binary."""
import json
import platform
from pathlib import Path
from types import SimpleNamespace
import pytest
import build_native as native


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    platform.machine()  # Resolve Windows platform probing before mocking Cargo.
    manifest = tmp_path / 'native/depth_sort/Cargo.toml'
    manifest.parent.mkdir(parents=True)
    manifest.write_text('[package]\nname="test"')
    (manifest.parent / 'Cargo.lock').write_text('version=4')
    (manifest.parent / 'src').mkdir()
    (manifest.parent / 'src/lib.rs').write_text('source')
    (tmp_path / 'build_native.py').write_text('builder')
    output = tmp_path / 'native/bin/bloc_fantome_native.dll'
    output.parent.mkdir(parents=True)
    output.write_bytes(b'old binary')
    monkeypatch.setattr(native, 'SCRIPT_DIR', tmp_path)
    monkeypatch.setattr(native, 'MANIFEST', manifest)
    monkeypatch.setattr(native, 'OUTPUT', output)
    return tmp_path, output


def test_absent_cargo_rejects_unverified_dll(checkout, monkeypatch):
    monkeypatch.setattr(native.shutil, 'which', lambda _: None)
    assert native.build() is False
    with pytest.raises(RuntimeError):native.build(required=True)


def test_success_receipt_and_cargo_absent_validation(checkout, monkeypatch):
    root, output = checkout
    compiled = root / 'build/native-target/release/bloc_fantome_native.dll'
    compiled.parent.mkdir(parents=True); compiled.write_bytes(b'new binary')
    monkeypatch.setattr(native.shutil, 'which', lambda _: 'cargo')
    monkeypatch.setattr(native.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=0))
    assert native.build()
    monkeypatch.setattr(native.shutil, 'which', lambda _: None)
    assert native.build()
    (root / 'native/depth_sort/src/lib.rs').write_text('changed')
    assert native.build() is False


def test_failed_build_preserves_binary_and_reports_fallback(checkout, monkeypatch):
    root, output = checkout
    monkeypatch.setattr(native.shutil, 'which', lambda _: 'cargo')
    monkeypatch.setattr(native.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1))
    assert native.build() is False
    assert output.read_bytes() == b'old binary'


def test_runtime_rejects_damaged_receipt_or_dll(checkout):
    from engine.native_provenance import write_receipt, verified
    root, output = checkout
    write_receipt(output, root)
    assert verified(output, root)
    output.write_bytes(b'corrupt')
    assert not verified(output, root)
    output.with_suffix('.json').write_text('[]')
    assert not verified(output, root)

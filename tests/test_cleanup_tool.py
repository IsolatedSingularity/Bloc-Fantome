"""Dry-run and tracked-file protection for the explicitly bounded cleanup tool."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest


def test_cleanup_handles_source_only_checkout_and_preserves_tracked_files(tmp_path):
    shell=shutil.which('pwsh') or shutil.which('powershell')
    if not shell:pytest.skip('PowerShell maintenance tool requires a Windows/PowerShell runner')
    root=Path(__file__).resolve().parents[1]
    script=tmp_path/'Code/tools/clean_generated.ps1';script.parent.mkdir(parents=True)
    (tmp_path/'tests').mkdir()
    shutil.copyfile(root/'Code/tools/clean_generated.ps1',script)
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    def run(*args):
        subprocess.run([shell,'-NoProfile','-File',str(script),*args],cwd=tmp_path,
                       check=True,capture_output=True,text=True)
    run() # No build directory or installers exist.
    fixture=tmp_path/'.qa/pytest-owned';fixture.mkdir()
    retained=fixture/'retained.txt';retained.write_text('tracked fixture')
    subprocess.run(['git','-C',str(tmp_path),'add','--',str(retained)],check=True)
    disposable=tmp_path/'Code/__pycache__';disposable.mkdir()
    bytecode=disposable/'fixture.pyc';bytecode.write_bytes(b'generated')
    run()
    assert bytecode.is_file() and retained.is_file()
    plan=json.loads((tmp_path/'.qa/architecture/cleanup-plan.json').read_text(encoding='utf-8-sig'))
    assert not plan['Applied'] and plan['Files']==1
    run('-Apply')
    assert not bytecode.exists() and retained.read_text()=='tracked fixture'

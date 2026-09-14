import hashlib,json
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
root=Path.cwd();archive=CArchiveReader(str(root/'BlocFantome.exe'))
entries={name.replace('\\','/'):name for name in archive.toc}
checked=[]
for folder in ('Code/biome_captures','Code/world_previews','Code/worlds','Code/world_map_regions'):
    base=root/folder
    for path in base.rglob('*'):
        if not path.is_file():continue
        suffix=base.name+'/'+path.relative_to(base).as_posix()
        entry=next((v for k,v in entries.items() if k.endswith(suffix)),None)
        assert entry,suffix
        assert archive.extract(entry)==path.read_bytes(),suffix
        checked.append(suffix)
for suffix in ('Assets/Icons/Splash_Swamp.jpg',):
    entry=next(v for k,v in entries.items() if k.endswith(suffix))
    assert archive.extract(entry)==(root/suffix).read_bytes(),suffix
    checked.append(suffix)
assert (root/'Assets/Fonts/Zekton/Zekton-Regular.otf').is_file()
assert any(k.endswith('_tkinter.pyd') for k in entries)
assert any(k.endswith('bloc_fantome_native.dll') for k in entries)
pyz=archive.open_embedded_archive(next(n for n in archive.toc if n.endswith('.pyz')))
for module in ('tkinter','tkinter.filedialog','tkinter.messagebox','tkinter.simpledialog'):
    source='tkinter/__init__.py' if module=='tkinter' else module.replace('.','/')+'.py'
    assert module in pyz.toc or source in entries,module
for module in ('engine.biome_capture','engine.capture_records','engine.tutorial_lessons','engine.tutorial_runtime','engine.world_snapshot','engine.skybox','ui.chrome','ui.library','ui.help','ui.tutorial','ui.preview_browser'):
    assert module in pyz.toc,module
assert any('pyi_tk_runtime' in k for k in entries)
result=dict(version='2.9.2',checked_files=len(checked),files=checked,exe_sha256=hashlib.sha256((root/'BlocFantome.exe').read_bytes()).hexdigest(),tkinter=True,native=True)
(root/'.qa/revision-292-archive.json').write_text(json.dumps(result,indent=2))
print('Verified',len(checked),'source and visual assets byte-for-byte, Tk dialogs and native acceleration')

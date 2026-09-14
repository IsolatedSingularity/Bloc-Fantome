import json
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
root=Path.cwd()
archive=CArchiveReader(str(root/'BlocFantome.exe'))
names={name.replace('\\','/') for name in archive.toc}
required=[f'world_map_regions/{p.name}' for p in (root/'Code/world_map_regions').iterdir()
          if p.name.endswith(('.png','.json.gz')) or p.name=='atlas.json']
required+=['Assets/Icons/Splash_Background_Warped_Forest.png']
missing=[name for name in required if not any(n.endswith(name) for n in names)]
assert not missing,missing
for path in (root/'Code/world_map_regions').iterdir():
    if path.name.endswith(('.png','.json.gz')) or path.name=='atlas.json':
        entry=next(n for n in archive.toc if n.replace('\\','/').endswith('world_map_regions/'+path.name))
        assert archive.extract(entry)==path.read_bytes(),path.name
assert any(n.endswith('_tkinter.pyd') for n in names)
pyz=archive.open_embedded_archive(next(n for n in archive.toc if n.endswith('.pyz')))
assert 'tkinter' in pyz.toc or 'tkinter/__init__.py' in names
for module in ('filedialog','messagebox','simpledialog'):
    assert 'tkinter.'+module in pyz.toc or 'tkinter/'+module+'.py' in names
assert any('pyi_tk_runtime' in n for n in names | set(pyz.toc))
result={'version':'2.9.0','required_files':required,'checked_files':len(required),
        'tkinter':True,'_tkinter.pyd':True,'pyi_tk_runtime':True}
(root/'.qa/consistency-290-archive.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))

for module in ('engine.biome_catalog','engine.tutorial_lessons','engine.tutorial_runtime','engine.sky_layers','ui.biomes','ui.tutorial'):
    assert module in pyz.toc,module
assert any(n.endswith('bloc_fantome_native.dll') for n in names)
print('All guided release modules and native DLL verified')
capture_files=list((root/'Code/biome_captures').rglob('*'))
capture_files=[p for p in capture_files if p.is_file()]
for path in capture_files:
    suffix='biome_captures/'+path.relative_to(root/'Code/biome_captures').as_posix()
    entry=next(n for n in archive.toc if n.replace('\\','/').endswith(suffix))
    assert archive.extract(entry)==path.read_bytes(),suffix
for suffix in ('Assets/Icons/Splash_Midnight_Workshop.png','References/Titles/horror.png'):
    entry=next(n for n in archive.toc if n.replace('\\','/').endswith(suffix))
    assert archive.extract(entry)==(root/suffix).read_bytes(),suffix
for module in ('engine.biome_capture','engine.capture_materials'):
    assert module in pyz.toc,module
print(f'Verified {len(capture_files)} biome files plus new splash and title byte-for-byte')



for module in ('ui.chrome', 'ui.library', 'ui.help'):
    assert module in pyz.toc, module
assert (root/'Assets/Fonts/Zekton/Zekton-Regular.otf').is_file()
print('Shared UI modules verified; external Zekton font present (included by installer Assets/Fonts rule)')



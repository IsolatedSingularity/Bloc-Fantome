from pathlib import Path
s=Path('.qa/verify_archive_290.py').read_text().replace('2.9.0','2.9.1').replace('consistency-290-archive.json','tour-291-archive.json')
s+='''
for module in ('engine.tutorial_scenes','ui.preview_browser'):
    assert module in pyz.toc,module
previews=list((root/'Code/world_previews').glob('*.png'))
assert len(previews)==15
for path in previews:
    suffix='world_previews/'+path.name
    entry=next(n for n in archive.toc if n.replace('\\\\','/').endswith(suffix))
    assert archive.extract(entry)==path.read_bytes(),suffix
print('All 15 exact world previews and new tutorial modules verified')
'''
Path('.qa/verify_archive_291.py').write_text(s)
s=Path('.qa/verify-start-menu-290.ps1').read_text(encoding='utf-8').replace('2.9.0','2.9.1').replace('start-menu-290','start-menu-291').replace('consistency-start-menu-290.json','tour-start-menu-291.json')
Path('.qa/verify-start-menu-291.ps1').write_text(s,encoding='utf-8')

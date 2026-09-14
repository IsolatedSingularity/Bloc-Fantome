from pathlib import Path
s=Path('.qa/implement-tour-291.py').read_text(encoding='utf-8-sig')
exec(s[s.index("p=Path('Code/blocFantome.py')"):])
p=Path('Code/engine/tutorial_scenes.py');s=p.read_text().replace('B.BRICK_STAIRS','B.SANDSTONE_STAIRS').replace('B.SPRUCE_SLAB','B.OAK_SLAB');p.write_text(s)
from sys import path
path.insert(0,'Code')
from engine.tutorial_lessons import TOUR
from engine.tutorial_scenes import scene_snapshot
print([(p['id'],len(scene_snapshot(p['id']).blocks)) for p in TOUR if not p['capture'] and not p['world']])

import sys
sys.path.insert(0,'Code')
from engine.biome_capture import capture
for key in ('_scene_tour_well','_scene_tour_outpost','_scene_tour_fortress','_scene_tour_bastion'):
 d=capture(key)
 print(key,d['size'],d['origin'],d.get('landmark_ids'),[(s.get('id'),s.get('BB')) for s in d.get('structures',{}).values()])

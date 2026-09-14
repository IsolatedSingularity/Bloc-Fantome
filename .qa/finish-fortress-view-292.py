import sys,json,gzip
from pathlib import Path
sys.path.insert(0,'Code')
from tools.export_scene_assets import write_world,Baker,pygame
from tools.export_biome_captures import preview
root=Path('Code/biome_captures');manifest=json.loads((root/'scenes.json').read_text())
name='_scene_nether_fortress_biomes_1161'
data=json.loads(gzip.decompress((root/manifest[name]['file']).read_bytes()))
pygame.display.init();pygame.display.set_mode((1,1));baker=Baker()
materials={'minecraft:nether_bricks','minecraft:nether_brick_fence','minecraft:nether_brick_stairs','minecraft:nether_wart','minecraft:chest','minecraft:spawner'}
shown=dict(data,blocks=[r for r in data['blocks'] if data['palette'][r[3]]['Name'] in materials])
preview(shown,baker,root/f'{name}.png')
write_world(data,name,'nether_fortress_biomes_1161','Nether Fortress')
print('Fortress preview:',len(shown['blocks']),'source structure cells; terrain remains editable and translucent by default',flush=True)

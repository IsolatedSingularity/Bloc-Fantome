from pathlib import Path
import gzip,json,sys
sys.path.insert(0,'Code')
import blocFantome as app
missing={}
for p in sorted(Path('Code/biome_captures').glob('*.json.gz')):
 d=json.loads(gzip.decompress(p.read_bytes()))
 for row in d['blocks']:
  name=d['palette'][row[3]]['Name']
  if app.BlocFantome._resolveJavaBlockType(name) is None or name=='minecraft:grass':missing[name]=True
names=sorted(n.split(':')[1].upper() if n!='minecraft:grass' else 'SHORT_GRASS' for n in missing)
p=Path('Code/domain/blocks.py');s=p.read_text();mark='    # Java capture materials (stable appended identifiers).\n'
if mark not in s:
 s=s.replace('\n\nclass Facing(Enum):','\n'+mark+'\n'.join(f'    {n} = {600+i}' for i,n in enumerate(names))+'\n\n\nclass Facing(Enum):');p.write_text(s)
solid={'BLUE_ICE','BUBBLE_CORAL_BLOCK','HORN_CORAL_BLOCK','CHISELED_SANDSTONE','COARSE_DIRT','GRASS_PATH','INFESTED_STONE','LOOM','NETHER_QUARTZ_ORE','SNOW_BLOCK','BEE_NEST'}
text='"""Source-model materials added for faithful editable Java biome captures."""\nMATERIALS = '+repr({n:(600+i,n not in solid) for i,n in enumerate(names)})+'\n'
Path('Code/engine/capture_materials.py').write_text(text)
print(len(names),'capture materials')

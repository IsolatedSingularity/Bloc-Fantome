from pathlib import Path
p=Path('Code/tools/bake_builder_splash.py');s=p.read_text().replace("put(21,19,1,'crafting_table');put(22,19,1,'chest'","put(21,23,1,'crafting_table');put(22,23,1,'chest'").replace('sprites={};scale=.79','sprites={};scale=.64').replace('round(450+','round(365+')
s=s.replace("if all((x+dx,z+dz,y+dy) in cells for dx,dz,dy in ((1,0,0),(0,1,0),(0,0,1))):continue", "if all((x+dx,z+dz,y+dy) in cells and cells[x+dx,z+dz,y+dy]['Name'].split(':')[1] not in ('grass','poppy','dandelion','water','glass','oak_leaves','oak_fence','lantern') for dx,dz,dy in ((1,0,0),(0,1,0),(0,0,1))):continue")
p.write_text(s)

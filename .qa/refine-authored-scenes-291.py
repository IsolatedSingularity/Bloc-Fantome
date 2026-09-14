from pathlib import Path
p=Path('Code/engine/tutorial_scenes.py');s=p.read_text();a=s.index("    elif key=='skies':");b=s.index("    elif key=='liquids':",a)
s=s[:a]+'''    elif key=='skies':
        # A complete domed observatory: load-bearing drum, windows, balcony
        # and glazed hemisphere. Every roof ring rests on the course below.
        for x in range(11,36):
            for y in range(11,36):
                radius=(x-23)**2+(y-23)**2
                if radius<=121:s.box(x,y,3,x,y,7,B.STONE_BRICKS)
                if 49<=radius<=81:
                    for z in range(8,19):
                        window=(abs(x-23)<2 or abs(y-23)<2) and 11<=z<=15
                        s.put(x,y,z,B.GLASS if window else B.QUARTZ_BLOCK)
                if radius<=81:s.put(x,y,8,B.OAK_PLANKS)
                for h in range(9):
                    shell=radius+h*h
                    if 49<=shell<=81:
                        s.put(x,y,19+h,B.QUARTZ_BLOCK if x==23 or y==23 else B.GLASS)
        s.box(22,30,9,24,32,12,B.AIR)
        for j in range(4):
            for x in range(21,26):s.put(x,35-j,5+j,B.STONE_BRICK_STAIRS,Facing.NORTH)
        s.put(23,23,10,B.SEA_LANTERN);s.tree(8,14);s.tree(38,36)
'''+s[b:]
a=s.index("    elif key=='worldmap':")
s=s[:a]+s[a:]
# Connect the archive gallery with a staircase and rail, leaving its front open for inspection.
s=s.replace("s.box(21,24,7,27,27,8,B.OAK_PLANKS);s.put(24,25,9,B.LANTERN)", "s.box(21,24,7,27,27,8,B.OAK_PLANKS);s.put(24,25,9,B.LANTERN)\n        for x in range(11,36):s.put(x,18,15,B.OAK_FENCE)\n        for j in range(8):\n            for x in (32,33):s.put(x,25-j,7+j,B.OAK_STAIRS,Facing.NORTH)")
p.write_text(s)

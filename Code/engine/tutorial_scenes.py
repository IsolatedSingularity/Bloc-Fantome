"""Original editable teaching builds. Canonical chapters load actual game data."""
from functools import lru_cache
from math import sin, cos
from domain.blocks import BlockType as B, BlockProperties, Facing
from engine.world_snapshot import WorldSnapshot


class Builder:
    def __init__(self):
        self.cells={}; self.props={}; self.water={}

    def put(self,x,y,z,block, facing=None):
        if block==B.AIR:
            self.cells.pop((x,y,z),None); self.props.pop((x,y,z),None); return
        self.cells[x,y,z]=block
        if facing is not None:self.props[x,y,z]=BlockProperties(facing=facing)
        if block==B.WATER:self.water[x,y,z]=8

    def box(self,x0,y0,z0,x1,y1,z1,block):
        for x in range(x0,x1+1):
            for y in range(y0,y1+1):
                for z in range(z0,z1+1):self.put(x,y,z,block)

    def ground(self, river=False, terraces=False):
        for x in range(3,45):
            for y in range(3,45):
                if abs(x-23)/22+abs(y-23)/22>1.63+0.06*sin(x):continue
                top=4+int(1.3*sin(x*.18)*cos(y*.14))
                if terraces:top=4+y//12
                stream=river and abs(y-(24+3*sin(x*.15)))<3
                if stream:top=2
                for z in range(top+1):
                    block=B.STONE if z<top-1 else B.DIRT if z<top else B.GRASS
                    self.put(x,y,z,B.GRAVEL if stream and z==top else block)
                if stream:self.put(x,y,3,B.WATER)

    def pad(self,x,y,w,d,z=6,block=B.COBBLESTONE):
        self.box(x,y,2,x+w-1,y+d-1,z,block)

    def tree(self,x,y,z=5):
        self.box(x,y,z,x,y,z+7,B.OAK_LOG)
        for h,r in ((5,3),(6,3),(7,2),(8,1)):
            for dx in range(-r,r+1):
                for dy in range(-r,r+1):
                    if abs(dx)+abs(dy)<=r+1:self.put(x+dx,y+dy,z+h,B.OAK_LEAVES)

    def house(self,x,y,w=11,d=10,z=6, roof=B.SPRUCE_STAIRS):
        self.pad(x-1,y-1,w+2,d+2,z)
        self.box(x,y,z+1,x+w-1,y+d-1,z+1,B.OAK_PLANKS)
        for xx in range(x,x+w):
            for yy in range(y,y+d):
                if xx not in (x,x+w-1) and yy not in (y,y+d-1):continue
                for h in range(2,7):
                    corner=xx in (x,x+w-1) and yy in (y,y+d-1)
                    window=(xx-x)%4==2 or (yy-y)%4==2
                    self.put(xx,yy,z+h,B.OAK_LOG if corner else B.GLASS if window and h in (3,4) else B.OAK_PLANKS)
        self.box(x+w//2,y+d-1,z+2,x+w//2+1,y+d-1,z+4,B.AIR)
        for xx in range(x-1,x+w+1):
            rise=min(xx-(x-1),x+w-xx)
            for yy in range(y-1,y+d+1):
                self.put(xx,yy,z+7+rise,roof,Facing.EAST if xx<x+w//2 else Facing.WEST)
            for yy in (y,y+d-1):
                for h in range(7,7+rise):self.put(xx,yy,z+h,B.OAK_PLANKS)
        self.box(x+2,y+2,z+7,x+3,y+3,z+14,B.BRICKS)
        self.put(x+1,y+d,z+4,B.LANTERN);self.put(x+w-2,y+d,z+4,B.LANTERN)
        self.box(x+2,y+2,z+2,x+4,y+2,z+3,B.BOOKSHELF)

    def arch(self,x,y,z,width=9,height=9,depth=3):
        for xx in range(width):
            clearance=height-2-int(abs(xx-(width-1)/2)*.65)
            for yy in range(depth):
                for h in range(height+1):
                    if xx in (0,width-1) or h>=clearance:self.put(x+xx,y+yy,z+h,B.STONE_BRICKS)

    def tower(self,x,y,z=6,size=9,height=19):
        self.pad(x-1,y-1,size+2,size+2,z)
        for h in range(1,height+1):
            for dx in range(size):
                for dy in range(size):
                    if dx not in (0,size-1) and dy not in (0,size-1):continue
                    window=h%6 in (3,4) and (dx==size//2 or dy==size//2)
                    self.put(x+dx,y+dy,z+h,B.GLASS if window else B.COBBLESTONE if h%6==0 else B.STONE_BRICKS)
        self.box(x-1,y-1,z+height+1,x+size,y+size,z+height+1,B.STONE_BRICKS)
        for dx in range(-1,size+1):
            for dy in range(-1,size+1):
                if (dx in (-1,size) or dy in (-1,size)) and (dx+dy)%2==0:self.put(x+dx,y+dy,z+height+2,B.STONE_BRICKS)
        for h in range(1,14):self.put(x+size+1,y+h//2,z+h//2,B.STONE_BRICK_STAIRS,Facing.SOUTH)
        self.put(x+size//2,y+size//2,z+height+2,B.LANTERN)


@lru_cache(maxsize=20)
def scene_snapshot(key):
    s=Builder();s.ground(river=key in ('welcome','history','liquids'),terraces=key in ('fill','selection','saving'))
    if key=='welcome':
        s.house(13,8,13,11);s.house(31,10,7,8)
        s.box(8,23,5,15,29,5,B.OAK_PLANKS)
        for x in (8,15):s.box(x,23,2,x,29,4,B.OAK_LOG)
        s.tree(8,12);s.tree(36,35);s.tree(12,36)
    elif key=='blocks':
        for x,y,roof in ((9,9,B.SPRUCE_STAIRS),(27,9,B.SANDSTONE_STAIRS),(9,28,B.OAK_STAIRS),(27,28,B.STONE_BRICK_STAIRS)):s.house(x,y,9,8,roof=roof)
        s.pad(21,20,5,8,6,B.STONE_BRICKS);s.put(23,23,7,B.LANTERN)
    elif key=='camera':
        s.tower(18,17,height=24);s.house(29,13,8,10);s.tree(9,13);s.tree(12,36)
        s.box(15,27,18,29,30,18,B.OAK_PLANKS)
        for x in range(15,30):s.put(x,30,19,B.OAK_FENCE)
    elif key=='fill':
        for i in range(3):
            y=9+i*10;z=5+i*2;s.pad(9,y,30,8,z,B.STONE_BRICKS)
            s.box(11,y+1,z+1,35,y+5,z+1,B.DIRT)
            for x in range(12,36,2):
                for yy in (y+2,y+4):s.put(x,yy,z+2,B.POPPY if i%2 else B.DANDELION)
            for j in range(3):s.put(23,y+7+j,z-1+j,B.STONE_BRICK_STAIRS,Facing.NORTH)
        s.house(6,5,7,7);s.tree(39,38,7)
    elif key=='history':
        for x in (16,24):s.arch(x,17,2,width=8,height=8,depth=13)
        s.box(16,16,11,31,31,11,B.STONE_BRICKS)
        for x in (16,31):
            for y in range(16,32):s.put(x,y,12,B.STONE_BRICK_SLAB)
        for y in range(10,17):s.box(19,y,5,28,y,5+(y-10),B.COBBLESTONE)
        s.house(7,7,8,8);s.tree(37,12);s.tree(9,37)
    elif key=='mirror':
        s.tower(8,16,size=8,height=16);s.tower(32,16,size=8,height=16)
        s.arch(16,18,6,width=16,height=13,depth=5);s.pad(18,25,12,13,5,B.STONE_BRICKS)
        for x in (19,28):s.put(x,28,7,B.LANTERN)
        s.tree(9,36);s.tree(38,36)
    elif key=='selection':
        s.pad(7,10,32,16,6,B.STONE_BRICKS)
        for y in (10,23):
            for x in (7,18,29):s.arch(x,y,7,width=10,height=10,depth=2)
            s.box(7,y,18,38,y+3,18,B.STONE_BRICK_SLAB)
        for x in (11,22,33):s.put(x,16,7,B.LANTERN)
        s.tree(12,36,7);s.tree(36,36,7)
    elif key=='structures':
        s.house(8,9,11,10);s.house(27,10,10,9);s.house(11,29,9,8)
        s.pad(27,29,9,8,6,B.STONE_BRICKS)
        for x in (27,35):
            for y in (29,36):s.box(x,y,7,x,y,11,B.OAK_LOG)
        s.box(26,28,12,36,37,12,B.OAK_SLAB);s.box(29,31,7,33,34,7,B.WATER);s.tree(38,25)
    elif key=='skies':
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
    elif key=='liquids':
        s.house(10,8,12,11)
        for x in range(24,38):
            level=5+(37-x)//4;s.box(x,11,2,x,15,level,B.STONE_BRICKS);s.put(x,13,level+1,B.WATER)
        for dy,dz in ((-4,0),(-3,3),(0,4),(3,3),(4,0),(3,-3),(0,-4),(-3,-3)):
            s.box(23,20+dy,9+dz,25,20+dy,9+dz,B.SPRUCE_PLANKS)
        s.box(24,16,9,24,24,9,B.OAK_LOG);s.box(24,20,5,24,20,13,B.OAK_LOG)
        s.tree(8,35);s.tree(37,35)
    elif key=='lighting':
        s.pad(10,10,27,26,6,B.STONE_BRICKS)
        for y in (11,16):s.box(11,y,7,35,y,17,B.BOOKSHELF)
        for x in (11,19,27,35):
            for y in (11,19,32):s.box(x,y,7,x,y,19,B.OAK_LOG);s.put(x+1,y,15,B.LANTERN)
        s.box(11,11,14,35,17,14,B.OAK_PLANKS);s.box(11,11,20,35,14,20,B.OAK_SLAB)
        s.box(21,24,7,27,27,8,B.OAK_PLANKS);s.put(24,25,9,B.LANTERN)
        for x in range(11,36):s.put(x,18,15,B.OAK_FENCE)
        for j in range(8):
            for x in (32,33):s.put(x,25-j,7+j,B.OAK_STAIRS,Facing.NORTH)
    elif key=='worldmap':
        s.house(10,9,13,12);s.tower(29,11,size=7,height=13);s.pad(11,28,26,8,6,B.COBBLESTONE)
        for x in (13,22,31):s.box(x,28,7,x,28,12,B.OAK_LOG);s.box(x-2,28,13,x+2,28,13,B.OAK_PLANKS)
        s.tree(8,36);s.tree(39,34)
    elif key=='horror':
        s.pad(12,10,24,28,6,B.MOSSY_STONE_BRICKS)
        for x in (12,32):
            for y in (11,20,29):s.box(x,y,7,x+2,y+2,21,B.STONE_BRICKS)
        s.arch(12,11,7,width=23,height=18,depth=2)
        for y in (19,24,29):s.box(16,y,7,21,y,8,B.SPRUCE_STAIRS)
        s.box(24,14,7,26,34,7,B.RED_WOOL);s.put(25,16,8,B.SOUL_LANTERN)
    else:
        s.house(14,11,15,13,z=8);s.house(30,26,8,10,z=7)
        for x,y in ((8,9),(38,11),(10,36),(38,36)):s.tree(x,y,7)
    return WorldSnapshot(48,48,64,blocks=s.cells,properties=s.props,liquid_levels=s.water,
        liquid_sources=frozenset(s.water),scene_metadata={'kind':'tutorial','name':key,'authored':True})

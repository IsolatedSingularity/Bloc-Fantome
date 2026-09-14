"""Bake the miniature midnight workshop splash from licensed Minecraft models."""
import math
import os
from pathlib import Path
import random
import sys
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
import pygame
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.bake_world_map_sprites import Baker,ANCHOR

def main():
    pygame.display.init();pygame.display.set_mode((1,1));baker=Baker();baker.biome_id=1
    cells={};rng=random.Random(281)
    def put(x,z,y,name,**props):
        if name.endswith('_log'):props.setdefault('axis','y')
        if name=='grass_block':props.setdefault('snowy','false')
        cells[x,z,y]={'Name':'minecraft:'+name,**({'Properties':props} if props else {})}
    for x in range(32):
        for z in range(28):
            r=((x-15)/17)**2+((z-13)/15)**2
            if r>1:continue
            bottom=-int((1-r)*6)
            for y in range(bottom,1):put(x,z,y,'grass_block' if y==0 else 'dirt' if y>-3 else 'stone')
            if 19<x<28 and 13<z<22:put(x,z,0,'water',level='0')
            elif rng.random()<.07:put(x,z,1,rng.choice(('poppy','dandelion','grass')))
    for x in range(9,21):
        for z in range(7,17):
            put(x,z,1,'oak_planks')
            for y in range(2,7):
                if x in (9,20) or z in (7,16):
                    name='oak_log' if x in (9,20) and z in (7,16) else 'oak_planks'
                    if y in (3,4) and (x in (12,13,17,18) or z in (10,11,13,14)):name='glass'
                    put(x,z,y,name)
    for x in range(8,22):
        for z in range(6,18):
            y=7+min(z-6,17-z)//2
            put(x,z,y,'dark_oak_planks')
    for y in range(7,13):put(11,9,y,'bricks')
    # A winding path, orchard and a tiny workshop table.
    for z in range(17,27):
        for x in range(12+(z//4)%2,15+(z//4)%2):
            if (x,z,0) in cells:put(x,z,0,'grass_path')
    for tx,tz in ((5,9),(24,6),(5,20)):
        for y in range(1,7):put(tx,tz,y,'oak_log')
        for dx in range(-2,3):
            for dz in range(-2,3):
                for y in range(5,8):
                    if abs(dx)+abs(dz)+(y-5)<6:put(tx+dx,tz+dz,y,'oak_leaves',persistent='true',distance='1')
    put(21,23,1,'crafting_table');put(22,23,1,'chest',facing='south',type='single',waterlogged='false')
    for x,z in ((10,18),(17,21),(24,12)):
        for y in range(1,3):put(x,z,y,'oak_fence')
        put(x,z,3,'lantern',hanging='false',waterlogged='false')
    # One small unnatural seam under the otherwise welcoming island.
    for x in range(12,16):
        for y in range(-5,-2):put(x,26,y,'obsidian')
    put(13,27,-3,'crying_obsidian');put(15,27,-3,'crying_obsidian')
    surface=pygame.Surface((1920,1080))
    for y in range(1080):
        t=y/1080;pygame.draw.line(surface,(round(10+13*t),round(12+12*t),round(26+17*t)),(0,y),(1919,y))
    for i in range(130):
        x,y=rng.randrange(1920),rng.randrange(950)
        pygame.draw.circle(surface,(77,83,113),(x,y),1 if i%7 else 2)
    pygame.draw.ellipse(surface,(12,14,25),(400,890,1100,105))
    sprites={};scale=.64
    for (x,z,y),state in sorted(cells.items(),key=lambda row:sum(row[0])):
        if all((x+dx,z+dz,y+dy) in cells and cells[x+dx,z+dz,y+dy]['Name'].split(':')[1] not in ('grass','poppy','dandelion','water','glass','oak_leaves','oak_fence','lantern') for dx,dz,dy in ((1,0,0),(0,1,0),(0,0,1))):continue
        key=str(state)
        if key not in sprites:
            sprite=baker.bake(state)
            sprites[key]=pygame.transform.smoothscale(sprite,(round(sprite.get_width()*scale),round(sprite.get_height()*scale)))
        surface.blit(sprites[key],(round(950+((x-z)*32-ANCHOR[0])*scale),round(365+((x+z)*16-y*38-ANCHOR[1])*scale)))
    target=Path(__file__).resolve().parents[2]/'Assets/Icons/Splash_Midnight_Workshop.png'
    pygame.image.save(surface,target);print(target)

if __name__=='__main__':main()

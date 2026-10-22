"""Reproject opaque cube faces at enlarged display size, retaining source texels.

Only registered simple cubes use this path. Models, transparent sprites, captured
Java atlases and small/normal views keep their existing rasterization. Exterior
coverage is sampled separately from RGB: no blanket texture smoothing.
"""
from weakref import WeakKeyDictionary
import numpy as np
import pygame

_recipes = WeakKeyDictionary()


def register(sprite, textures):
    if all(t is not None and np.all(pygame.surfarray.array_alpha(t)==255) for t in textures):
        _recipes[sprite]=(textures,None)


def inherit_lighting(source, target, brightness, level, color):
    recipe=_recipes.get(source)
    if recipe is not None:_recipes[target]=(recipe[0],(brightness,level,color))


def enlarged(sprite, size, tile_ratio):
    recipe=_recipes.get(sprite)
    if recipe is None:return None
    textures,light=recipe
    w,h=size;th=h*tile_ratio;bh=h-th
    x,y=np.meshgrid(np.arange(w)+.5,np.arange(h)+.5,indexing='ij')
    top_y=np.abs(x-w/2)*th/w
    bottom_top=th-top_y
    is_top=y<bottom_top
    is_left=(x<w/2)&~is_top
    # Original face orientation and 0.70/0.85 lighting are preserved.
    coordinates=((x/w+y/th-.5,-x/w+y/th+.5,is_top,1.),
        (x/(w/2),(y-(th/2+x*th/w))/bh,is_left,.70),
        ((x-w/2)/(w/2),(y-(th-(x-w/2)*th/w))/bh,~is_top&~is_left,.85))
    rgb=np.zeros((w,h,3),dtype=np.uint8)
    for texture,(u,v,mask,shade) in zip(textures,coordinates):
        pixels=pygame.surfarray.array3d(texture)
        tx=np.clip(np.floor(u*texture.get_width()).astype(int),0,texture.get_width()-1)
        ty=np.clip(np.floor(v*texture.get_height()).astype(int),0,texture.get_height()-1)
        rgb[mask]=(pixels[tx[mask],ty[mask]]*shade).astype(np.uint8)
    # Four coverage samples affect silhouette alpha only, never interior texels.
    coverage=np.zeros((w,h),dtype=np.uint16)
    for dx,dy in ((-.25,-.25),(.25,-.25),(-.25,.25),(.25,.25)):
        edge=np.abs(x+dx-w/2)*th/w
        coverage+=((y+dy>=edge)&(y+dy<=h-edge)).astype(np.uint16)
    result=pygame.Surface(size,pygame.SRCALPHA)
    pygame.surfarray.blit_array(result,rgb)
    alpha=pygame.surfarray.pixels_alpha(result);alpha[:]=coverage*255//4;del alpha
    # Keep definition lines one output pixel wide rather than magnifying them.
    points=((w//2,0),(w-1,round(th/2)),(w//2,h-1),(0,round(h-th/2)))
    for a,b in ((points[0],points[1]),(points[0],(0,round(th/2))),
                (points[2],points[3]),(points[2],(w-1,round(h-th/2)))):
        pygame.draw.aaline(result,(50,50,50),a,b)
    if light:
        from engine.lighting import shade_sprite
        result=shade_sprite(result,*light)
    return result

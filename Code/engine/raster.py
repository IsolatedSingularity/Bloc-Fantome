"""Array sampling of the original scalar raster equations, without smoothing."""
from functools import lru_cache
import numpy as np
import pygame


def paint(surface, texture, x, y, tx, ty, shade=1.0):
    colors=pygame.surfarray.array3d(texture)[tx,ty]
    alpha=pygame.surfarray.array_alpha(texture)[tx,ty]
    clip=surface.get_clip()
    valid=(alpha>0)&(x>=clip.left)&(x<clip.right)&(y>=clip.top)&(y<clip.bottom)
    rgb=pygame.surfarray.pixels3d(surface)
    rgb[x[valid],y[valid]]=(colors[valid]*shade).astype(np.uint8)
    del rgb
    if surface.get_masks()[3]:
        target_alpha=pygame.surfarray.pixels_alpha(surface)
        target_alpha[x[valid],y[valid]]=alpha[valid]
        del target_alpha


@lru_cache(maxsize=8)
def cube_coordinates(width,tile_height,block_height):
    hw,hh=width//2,tile_height//2
    height=tile_height+block_height
    x,y=np.indices((width,height))
    span=(hw*np.where(y<=hh,y/hh,(tile_height-y)/hh)).astype(int)
    mask=(y<tile_height)&(span>0)&(x>=hw-span)&(x<hw+span)
    px,py=x[mask],y[mask]
    u=((px-hw)/hw+(py-hh)/hh)*.5+.5
    v=(-(px-hw)/hw+(py-hh)/hh)*.5+.5
    top=(px,py,np.clip((u*(hw-1)).astype(int),0,hw-1),np.clip((v*(hw-1)).astype(int),0,hw-1))
    sides=[]
    for right in (False,True):
        rx=x-hw if right else x
        top_y=tile_height-1-(rx/hw*hh).astype(int) if right else hh+(rx/hw*hh).astype(int)
        mask=(x>=hw if right else x<hw)&(y>=np.maximum(0,top_y))&(y<np.minimum(top_y+block_height,height))
        sides.append((x[mask],y[mask],np.clip((rx[mask]/hw*(hw-1)).astype(int),0,hw-1),
                      np.clip(((y[mask]-top_y[mask])/block_height*(block_height-1)).astype(int),0,block_height-1)))
    return top,*sides


def cube_faces(surface,textures,width,tile_height,block_height,transparent):
    for texture,coords,shade in zip(textures,cube_coordinates(width,tile_height,block_height),
                                     (1,.8 if transparent else .7,.9 if transparent else .85)):
        paint(surface,texture,*coords,shade)


def model_face(surface,points,texture,shade,uv_origin,uv_u,uv_v):
    p0,p1,_,p3=points
    min_x=max(0,int(min(p[0] for p in points)))
    max_x=min(surface.get_width()-1,int(max(p[0] for p in points)+1))
    min_y=max(0,int(min(p[1] for p in points)))
    max_y=min(surface.get_height()-1,int(max(p[1] for p in points)+1))
    ux,uy=p1[0]-p0[0],p1[1]-p0[1]
    vx,vy=p3[0]-p0[0],p3[1]-p0[1]
    determinant=ux*vy-uy*vx
    if abs(determinant)<.001 or max_x<min_x or max_y<min_y:return
    x,y=np.meshgrid(np.arange(min_x,max_x+1),np.arange(min_y,max_y+1),indexing='ij')
    dx,dy=x+.5-p0[0],y+.5-p0[1]
    a=(dx*vy-dy*vx)/determinant;b=(ux*dy-uy*dx)/determinant
    valid=(a>=-.001)&(a<=1.001)&(b>=-.001)&(b<=1.001)
    a,b=a[valid],b[valid]
    width,height=texture.get_size()
    tx=((uv_origin[0]+a*uv_u[0]+b*uv_v[0])*width).astype(int)%width
    ty=((uv_origin[1]+a*uv_u[1]+b*uv_v[1])*height).astype(int)%height
    paint(surface,texture,x[valid],y[valid],tx,ty,shade)

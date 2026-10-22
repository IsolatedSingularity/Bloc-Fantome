"""Generated monochrome artwork, sampled from source masks at display size."""
from pathlib import Path
from functools import lru_cache
import math
import pygame
import numpy as np

CONTROLS = ('library_worlds','library_biomes','library_structures','library_saved',
         'rain','snow','sun','clouds','lighting','sky','horror_rain','flow')
ACTIONS = ('overworld','nether','end','terrain','terrain_view','sky_previous',
           'sky_next','clear_liquids','clear_world','grow','shrink','noise')
TOOLS_A = ('fill','brush','selection','copy','paste','clip_left','clip_right',
           'fill_selection','hollow','delete','flood','replace','wand','stamp',
           'blueprint','mirror_x')
TOOLS_B = ('mirror_y','radial','measure','layers','layer_up','layer_down','minimap',
           'center','xray','interact','turn','turn_placed','half','undo','redo','tools_emblem')
DIMENSIONS = ('dimension_overworld','dimension_nether','dimension_end')
NAMES = CONTROLS + ACTIONS + TOOLS_A + TOOLS_B + DIMENSIONS
ANIMATED = CONTROLS[4:] + ('nether',)


@lru_cache(maxsize=1)
def artwork():
    masks = {}
    sheets=(('controls-mask.png',CONTROLS,4,3),('actions-mask.png',ACTIONS,4,3),
            ('library-revision-mask.png',('library_structures','library_saved'),2,1),
            ('library-landmarks-mask.png',('library_worlds','library_biomes','library_saved'),3,1),
            ('tools-a-mask.png',TOOLS_A,4,4),('tools-b-mask.png',TOOLS_B,4,4),
            ('dimensions-mask.png',('library_worlds','library_biomes')+DIMENSIONS,5,1),
            ('polish-mask.png',('dimension_overworld','dimension_end','lighting','clouds'),2,2))
    for filename,names,cols,rows in sheets:
        atlas=pygame.image.load(str(Path(__file__).with_name('art')/filename));w,h=atlas.get_size()
        for i,name in enumerate(names):
            box = pygame.Rect(i%cols*w//cols, i//cols*h//rows, w//cols, h//rows)
            if filename=='actions-mask.png':
                # The approved artwork has taller first-row silhouettes.
                # Split in its empty gutters, not through the End island tip.
                cuts=(0,round(h*.36),round(h*.66),h)
                box.y=cuts[i//cols];box.height=cuts[i//cols+1]-box.y
            elif filename in ('tools-a-mask.png','tools-b-mask.png'):
                # Cut the actual empty gutters of the preserved source sheets.
                cuts=((0,352,625,886,1254) if filename=='tools-a-mask.png'
                      else (0,339,617,911,1254))
                box.y=cuts[i//cols];box.height=cuts[i//cols+1]-box.y
            rgb = pygame.surfarray.array3d(atlas.subsurface(box))
            # Black is the mask background; reject generation compression noise.
            alpha = np.clip((rgb.mean(axis=2)-20)*255/235,0,255).astype(np.uint8)
            xs,ys = np.nonzero(alpha>32)
            bounds = pygame.Rect(int(xs.min()),int(ys.min()),int(xs.max()-xs.min()+1),int(ys.max()-ys.min()+1))
            layer = pygame.Surface(box.size,pygame.SRCALPHA);layer.fill((255,255,255,0))
            pixels = pygame.surfarray.pixels_alpha(layer);pixels[:]=alpha;del pixels
            masks[name] = layer.subsurface(bounds).copy()
    return masks


@lru_cache(maxsize=96)
def fitted(name,size):
    source=artwork()[name];ratio=min(size[0]/source.get_width(),size[1]/source.get_height())
    ratio*=.84 if name in ('sun','snow') else .94 if name=='sky' else 1
    return pygame.transform.smoothscale(source,(max(1,round(source.get_width()*ratio)),max(1,round(source.get_height()*ratio))))


def _part(source,box):
    result=pygame.Surface(source.get_size(),pygame.SRCALPHA)
    result.blit(source,box.topleft,box)
    return result


@lru_cache(maxsize=96)
def layers(name,size):
    source=fitted(name,size);w,h=source.get_size()
    if name=='rain':
        split=round(h*.65)
        return (source,_part(source,pygame.Rect(0,0,w,split)),
                *(_part(source,pygame.Rect(i*w//3,split,(i+1)*w//3-i*w//3,h-split)) for i in range(3)))
    if name=='flow':
        return (source,*(_part(source,pygame.Rect(0,i*h//3,w,(i+1)*h//3-i*h//3)) for i in range(3)))
    return (source,)


@lru_cache(maxsize=8)
def precipitation(name):
    if name=='snow':return fitted('snow',(9,9))
    rain=artwork()['rain'];w,h=rain.get_size()
    drop=rain.subsurface((0,round(h*.65),w//3,h-round(h*.65)))
    drop=drop.subsurface(drop.get_bounding_rect())
    return pygame.transform.smoothscale(drop,(4,7))


@lru_cache(maxsize=96)
def faded_particle(name,level):
    particle=precipitation(name).copy();particle.set_alpha(level*5)
    return particle


def weather_effect(surface,name,rect,phase):
    """Generated drops/flakes travel across active tiles; no off-state motion."""
    if not phase or name not in ('rain','horror_rain','snow'):return
    rect=pygame.Rect(rect);old=surface.get_clip();surface.set_clip(rect.inflate(-12,-12).clip(old))
    particle=precipitation(name)
    for i in range(8):
        life=(phase*(.32 if name=='snow' else .85)+i*.381966)%1
        x=rect.x+10+((i*.618034)%1)*(rect.width-24)
        x+=math.sin(phase+i)*5 if name=='snow' else -life*7
        y=rect.y+7+life*(rect.height-14)
        drop=faded_particle(name,round(23*math.sin(math.pi*life)))
        surface.blit(drop,(round(x),round(y)))
    surface.set_clip(old)


def _draw_frame(surface,name,rect,phase=0):
    rect=pygame.Rect(rect)
    # Reserve motion space inside the hit tile; never resample a prior frame.
    size=(max(1,round(rect.width*.88)),max(1,round(rect.height*.88)))
    parts=layers(name,size);base=parts[0];target=base.get_rect(center=rect.center)
    t=phase
    if not t or name.startswith('library_'):
        surface.blit(base,target);return
    if name=='rain':
        surface.blit(parts[1],target)
        for i,drop in enumerate(parts[2:]):
            progress=(t*.85+i/3)%1
            moving=drop.copy();moving.set_alpha(round(255*math.sin(math.pi*progress)**.5))
            surface.blit(moving,target.move(round(-progress*rect.width*.035),round((progress-.5)*rect.height*.14)))
    elif name in ('sun','snow'):
        source=fitted(name,size)
        angle=t*(12 if name=='sun' else -8)
        # Rotate from the fitted native source once while preparing the cache.
        ratio=1
        rotated=pygame.transform.rotozoom(source,angle,ratio)
        surface.blit(rotated,rotated.get_rect(center=rect.center))
    elif name=='clouds':
        surface.blit(base,target.move(round(math.sin(t*.8)*rect.width*.055),round(math.sin(t*.4)*rect.height*.018)))
    elif name in ('lighting','horror_rain'):
        cycle=t%4.8
        flash=math.exp(-((cycle-.3)/.10)**2)+.65*math.exp(-((cycle-.65)/.12)**2)
        lit=base.copy();lit.set_alpha(min(255,round(180+75*flash)))
        surface.blit(lit,target)
    elif name=='flow':
        # Keep the approved water silhouette intact. Drops fall into the pool,
        # then leave expanding, fading ripples rather than sliding strips.
        surface.blit(base,target)
        for i in range(2):
            life=(t*.65+i*.5)%1
            x=rect.centerx+round((i-.5)*rect.width*.3)
            waterline=target.top+round(target.height*.62)
            effect=pygame.Surface(rect.size,pygame.SRCALPHA)
            if life<.55:
                y=target.top+round((waterline-target.top)*life/.55)
                pygame.draw.line(effect,(255,255,255,220),(x-rect.x,y-rect.y),(x-rect.x,y-rect.y+4),2)
            else:
                spread=(life-.55)/.45
                radius=max(2,round(2+spread*rect.width*.17))
                pygame.draw.ellipse(effect,(255,255,255,round(190*(1-spread))),
                    (x-rect.x-radius,waterline-rect.y-2,2*radius,max(3,radius//2)),1)
            surface.blit(effect,rect)
    elif name=='sky':
        # A slow lunar rock, not the weather tiles' falling motion.
        source=fitted(name,size);ratio=1
        moon=pygame.transform.rotozoom(source,3*math.sin(t*.6),ratio)
        surface.blit(moon,moon.get_rect(center=rect.center))
    elif name=='nether':
        # Flame deformation grows toward the tip while its base stays planted.
        flame=pygame.Surface(base.get_size(),pygame.SRCALPHA);w,h=base.get_size()
        for y in range(h):
            bend=round((1-y/h)**1.6*(math.sin(t*5+y*.16)+.45*math.sin(t*9+y*.27))*w*.055)
            flame.blit(base,(bend,y),(0,y,w,1))
        surface.blit(flame,target)
        ember=fitted('nether',(5,7))
        for i in range(2):
            life=(t*.65+i*.5)%1
            spark=ember.copy();spark.set_alpha(round(210*math.sin(math.pi*life)))
            surface.blit(spark,(rect.centerx+round(math.sin(t+i*2)*rect.width*.18),rect.centery-round(life*rect.height*.4)))
    else:surface.blit(base,target)


@lru_cache(maxsize=32)
def animation_frames(name,size):
    """Build small native buffers once per tile size, never on each display frame."""
    period={'rain':1/.85,'snow':45.,'sun':30.,'sky':math.tau/.6,'horror_rain':4.8,
            'flow':1/.65,'nether':math.tau}.get(name,6.)
    count=96 if name in ('sun','snow') else 48
    result=[]
    for i in range(count):
        frame=pygame.Surface(size,pygame.SRCALPHA)
        _draw_frame(frame,name,frame.get_rect(),period*(i+.001)/count)
        result.append(frame)
    return period,tuple(result)


def draw(surface,name,rect,phase=0):
    rect=pygame.Rect(rect)
    if not phase or name not in ANIMATED:
        _draw_frame(surface,name,rect,0);return
    period,frames=animation_frames(name,rect.size)
    surface.blit(frames[int((phase%period)/period*len(frames))],rect)

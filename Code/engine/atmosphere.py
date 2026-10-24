"""Bounded editor atmosphere. World rasterization remains the source of occlusion.

Fog depth is rotated x+y (horizontal camera distance), not screen y: a tall
foreground tower stays clear. A quarter-size alpha stencil follows the existing
global painter order, including cutouts and transparent faces. Banks animate at
12 Hz independently of world traversal. Rain contacts use actual exposed tops.
"""
from collections import OrderedDict
import math
import random
import weakref

import numpy as np
import pygame


def rain_material(name):
    name = name.upper()
    if 'WATER' in name:return 'water'
    if any(s in name for s in ('LEAVES','MOSS','GRASS','VINE')):return 'foliage'
    if any(s in name for s in ('WOOD','PLANK','LOG','BAMBOO')):return 'wood'
    if any(s in name for s in ('GLASS','IRON','COPPER','GOLD','ANVIL')):return 'glass_metal'
    if any(s in name for s in ('BRICK','QUARTZ','CONCRETE','PRISMARINE','TERRACOTTA')):return 'masonry'
    return 'stone'


class DepthStencil:
    SCALE = 4
    # Shared only within an Atmosphere owner, capped by both entries and bytes.
    def __init__(self, size, renderer, depth_range, sprites=None):
        self.surface = pygame.Surface((math.ceil(size[0]/4),math.ceil(size[1]/4)))
        self.surface.fill('white')
        self.renderer = renderer
        self.depth_range = depth_range
        self.sprites = sprites if sprites is not None else OrderedDict()
        self.blits = []

    def add(self, sprite, position, depth):
        low,high = self.depth_range
        # Twelve bounded depth groups. Color carries distance; alpha is original.
        level=round(11*max(0.,min(1.,(high-depth)/max(1.,high-low))))
        key=(sprite,level)
        mask=self.sprites.get(key)
        if mask is None:
            size=(max(1,math.ceil(sprite.get_width()/4)),max(1,math.ceil(sprite.get_height()/4)))
            mask=pygame.transform.smoothscale(sprite,size)
            mask.fill((0,0,0,255),special_flags=pygame.BLEND_RGBA_MULT)
            value=round(level*255/11)
            mask.fill((value,value,value,0),special_flags=pygame.BLEND_RGBA_ADD)
            # smoothscale preserves the surface-wide alpha separately.
            mask.set_alpha(sprite.get_alpha())
            if len(self.sprites)>=384:self.sprites.popitem(last=False)
            self.sprites[key]=mask
            # Include source references in the cap, not just reduced masks.
            retained=sum((s.get_width()*s.get_height()+m.get_width()*m.get_height())*4
                         for (s,_),m in self.sprites.items())
            while retained>4*1024**2 and len(self.sprites)>1:
                (s,_),m=self.sprites.popitem(last=False)
                retained-=(s.get_width()*s.get_height()+m.get_width()*m.get_height())*4
        self.blits.append((mask,(round(position[0]/4),round(position[1]/4))))
        if len(self.blits)>=512:self.flush()

    def flush(self):
        if self.blits:
            self.surface.blits(self.blits,doreturn=False)
            self.blits.clear()


class Atmosphere:
    MAX_DROPS = 1250
    MAX_CONTACTS = 512

    def __init__(self, seed=330):
        self.rng=random.Random(seed)
        self.elapsed=0.
        self.intensity=1.
        self.target=1.
        self.next_change=31.
        self.wind=.1
        self.wind_target=.1
        self.rain_level=0.
        self.reduced=False
        self.drops=[]
        self.contacts=[]
        self.just_landed=[]
        self.size=(0,0)
        self.rain_layer=None
        self.rain_sprites=OrderedDict()
        self.depths=OrderedDict()
        self.depth_sprites=OrderedDict()
        self.fog_low=None
        self.fog_frame=None
        self.fog_key=None
        self.fog_distance=None
        self.distance_key=None
        self.sky_color=(150,177,197)
        self.camera=None
        self.contact_timer=0.
        self.visibility_depth=None
        self.visibility_offset=(0,0)

    def start_rain(self,size):
        self.size=tuple(size)
        count=min(self.MAX_DROPS,max(360,round(size[0]*size[1]/1350)))
        self.drops=[]
        for i in range(count):
            depth=0 if i<count*.32 else 1 if i<count*.93 else 2
            self.drops.append(dict(x=self.rng.uniform(0,size[0]),y=self.rng.uniform(0,size[1]),
                              speed=self.rng.uniform(.86,1.16)*(300,640,980)[depth],
                              length=self.rng.uniform(.8,1.2)*(9,20,32)[depth],depth=depth,
                              angle=.1,color=(70,100,140,220)))
        self.contacts.clear();self.camera=None

    def stop_rain(self):
        self.drops.clear();self.contacts.clear();self.rain_layer=None
        self.just_landed.clear();self.rain_sprites.clear()
        self.rain_level=0.;self.contact_timer=0.;self.camera=None

    def update(self,dt_ms,raining,reduced=False):
        dt=max(0.,min(.25,dt_ms/1000.))
        self.elapsed+=dt;self.reduced=bool(reduced)
        if self.elapsed>=self.next_change:
            self.target=self.rng.uniform(.58,1.4)
            self.wind_target=self.rng.uniform(-.2,.3)
            self.next_change=self.elapsed+self.rng.uniform(23,63)
        self.intensity+=(self.target-self.intensity)*(1-math.exp(-dt/9))
        self.wind+=(self.wind_target-self.wind)*(1-math.exp(-dt/5))
        self.rain_level+=((1. if raining else 0.)-self.rain_level)*(1-math.exp(-dt/1.2))
        self.just_landed.clear()
        if not raining:return
        w,h=self.size
        gust=0 if reduced else .06*math.sin(self.elapsed*.37)*math.sin(self.elapsed*.113)
        for drop in self.drops:
            velocity=drop['speed']*(.72 if reduced else 1.)
            drop['y']+=velocity*dt
            drop['x']+=velocity*(self.wind+gust)*dt
            drop['angle']=self.wind+gust
            if drop['y']>h+40:
                drop['y']-=h+80;drop['x']=self.rng.uniform(-30,w+30)
            drop['x']=(drop['x']+40)%(w+80)-40
        for contact in self.contacts:
            previous=contact['age'];contact['age']+=dt
            if previous<0<=contact['age']:self.just_landed.append(contact)
        self.contacts[:]=[c for c in self.contacts if c['age']<c['duration']]
        self.contact_timer+=dt

    def camera_motion(self,renderer,size):
        current=(renderer.offsetX,renderer.offsetY,renderer.viewRotation,renderer.zoomLevel)
        if self.camera and self.camera[2:]==current[2:]:
            dx,dy=current[0]-self.camera[0],current[1]-self.camera[1]
            if dx or dy:
                for p in self.drops:
                    factor=(.15,.5,.85)[p['depth']]
                    p['x']+=dx*factor;p['y']+=dy*factor
        if self.size!=tuple(size):
            old=self.size
            if old[0] and old[1]:
                for p in self.drops:p['x']*=size[0]/old[0];p['y']*=size[1]/old[1]
            self.size=tuple(size);self.rain_layer=None
        self.camera=current

    def add_contact(self,position,material,uv=(.5,.5)):
        if len(self.contacts)>=self.MAX_CONTACTS:return
        # A short incoming streak and its crown share this exact world contact.
        self.contacts.append(dict(position=position,uv=uv,material=material,age=-self.rng.uniform(.25,1.65),
                                  duration=.75 if material=='water' else .42,
                                  phase=self.rng.uniform(0,math.tau)))

    def render_rain(self,target,renderer,*,distant=False):
        if not self.drops:return
        size=target.get_size()
        self.camera_motion(renderer,size)
        blits=[]
        zoom=max(.65,min(1.35,math.sqrt(renderer.zoomLevel)))
        opacity=self.rain_level*(.7+.3*self.intensity)
        angle=self.drops[0]['angle']
        pose=(round(zoom*16),round(angle*20),round(opacity*16))
        alphas=tuple(round(a*opacity) for a in (90,160,185))
        for p in self.drops:
            depth=p['depth']
            # Far/middle curtains are behind architecture. The middle rain in
            # front of geometry consists of world-anchored, terminating drops.
            if (depth<2)!=distant:continue
            x,y=p['x'],p['y']
            if p.get('pose')!=pose:
                p['glyph']=self.streak(p['length']*zoom,angle,depth,alphas[depth]);p['pose']=pose
            glyph,dx=p['glyph']
            blits.append((glyph,(round(x)-dx,round(y)-2)))
        if not distant:
            for c in self.contacts:
                sx,sy=self.project_contact(c,renderer)
                age=c['age'];material=c['material']
                if not self.contact_visible(c,renderer,sx,sy):continue
                if age<0:
                    height=-age*650*zoom
                    length=max(3,round(18*zoom/3)*3)
                    angle=round(self.wind*20)/20
                    glyph,dx=self.streak(length,angle,1,round(220*self.rain_level))
                    # The bright head reaches the top face at age zero; the tail
                    # extends upward, never through the roof before impact.
                    blits.append((glyph,(round(sx-angle*(height+length))-dx,
                                         round(sy-height-length)-2)))
                    continue
                progress=age/c['duration'];alpha=round(235*(1-progress)*self.rain_level)
                radius=max(2,(3+progress*10)*zoom)
                # Cache complete tiny splash glyphs; batch them directly onto the
                # viewport instead of clearing/blending two full-screen layers.
                key=('splash',material=='water',round(progress*24),round(zoom*8),round(alpha/16))
                glyph=self.rain_sprites.get(key)
                if glyph is not None:
                    blits.append((glyph,(round(sx)-32,round(sy)-24)));continue
                layer=pygame.Surface((64,40),pygame.SRCALPHA)
                draw_x,draw_y=32,24
                if material=='water':
                    rect=pygame.Rect(draw_x-radius*1.5,draw_y-radius*.55,radius*3,radius*1.1)
                    pygame.draw.ellipse(layer,(24,57,83,alpha),rect.inflate(2,2),2)
                    pygame.draw.ellipse(layer,(170,220,244,alpha),rect,1)
                else:
                    # Tiny contact crown, then ballistic droplets. No hovering rings on stone.
                    height=math.sin(progress*math.pi)*9*zoom
                    for dx in (-1,0,1):
                        px=draw_x+dx*radius;py=draw_y-height*(1 if dx else 1.3)
                        pygame.draw.line(layer,(31,65,91,alpha),(px,py),(px,py+3),3)
                        pygame.draw.line(layer,(198,232,251,alpha),(px,py),(px,py+2),1)
                    if progress<.3:
                        pygame.draw.ellipse(layer,(162,209,235,alpha),
                                            (draw_x-radius,draw_y-1,max(3,radius*2),3),1)
                self.cache_glyph(key,layer)
                blits.append((layer,(round(sx)-32,round(sy)-24)))
        target.blits(blits,doreturn=False)

    def cache_glyph(self,key,surface):
        if len(self.rain_sprites)>=384:self.rain_sprites.popitem(last=False)
        self.rain_sprites[key]=surface

    def streak(self,length,angle,depth,alpha):
        length=max(3,round(length/3)*3);angle=round(angle*20)/20
        alpha=max(0,min(255,round(alpha/16)*16))
        key=('streak',length,angle,depth,alpha)
        glyph=self.rain_sprites.get(key)
        shift=round(length*angle);dx=max(2,2-shift)
        if glyph is None:
            glyph=pygame.Surface((abs(shift)+5,length+5),pygame.SRCALPHA)
            start=(dx,2);end=(dx+shift,length+2)
            pygame.draw.line(glyph,(36,62,88,alpha),start,end,1 if depth==0 else 3)
            pygame.draw.line(glyph,(163,204,231,alpha),start,end,1)
            if depth==2:
                pygame.draw.line(glyph,(204,230,248,round(alpha*.8)),(end[0],end[1]-length//4),end,2)
            self.cache_glyph(key,glyph)
        return glyph,dx

    @staticmethod
    def project_contact(contact,renderer):
        x,y,z=contact['position']
        sx,sy=renderer.worldToScreen(x,y,z)
        u,v=contact['uv']
        u,v=renderer._rotateCoords(u-.5,v-.5)
        return (sx+(u-v)*renderer._tileWHalf,
                sy+renderer._tileHHalf+(u+v)*renderer._tileHHalf)

    def contact_visible(self,contact,renderer,sx,sy):
        depth=self.visibility_depth
        if depth is None:return True
        px=round((sx-self.visibility_offset[0])/4)
        py=round((sy-self.visibility_offset[1])/4)
        if not (0<=px<depth.surface.get_width() and 0<=py<depth.surface.get_height()):return False
        low,high=depth.depth_range
        x,y,_=contact['position']
        expected=255*max(0,min(1,(high-sum(renderer._rotateCoords(x,y)))/max(1,high-low)))
        # Allow one quantization bin and one edge pixel; reject hidden rear tops.
        return depth.surface.get_at((px,py)).r>=expected-30

    def begin_depth(self,source,renderer,depth_range,clip=None,previous=None):
        key=id(source)
        entry=self.depths.get(key)
        if entry is not None and entry[0]() is source:return entry[1]
        d=DepthStencil(source.get_size(),renderer,depth_range,self.depth_sprites)
        if previous is not None:
            old=self.depth_for(previous)
            if old and old.surface.get_size()==d.surface.get_size():d.surface.blit(old.surface,(0,0))
        if clip:
            rect=pygame.Rect(clip.x//4,clip.y//4,math.ceil(clip.width/4)+1,math.ceil(clip.height/4)+1)
            d.surface.set_clip(rect);d.surface.fill('white',rect)
        if len(self.depths)>=5:self.depths.popitem(last=False)
        self.depths[key]=(weakref.ref(source),d)
        self.fog_key=None
        self.distance_key=None
        return d

    def depth_for(self,source):
        entry=self.depths.get(id(source))
        return entry[1] if entry is not None and entry[0]() is source else None

    def clear_depth(self):
        self.depths.clear();self.depth_sprites.clear();self.fog_key=None
        self.visibility_depth=None
        self.fog_distance=None;self.distance_key=None

    def render_fog(self,target,source,offset,color,strength):
        depth=self.depth_for(source)
        if depth is None:return
        size=target.get_size();low_size=(max(1,size[0]//6),max(1,size[1]//6))
        tick=int(self.elapsed*(3 if self.reduced else 12))
        key=(size,id(source),tuple(round(v) for v in offset),tuple(color),round(strength,2),tick)
        if key!=self.fog_key:
            if self.fog_low is None or self.fog_low.get_size()!=low_size:
                self.fog_low=pygame.Surface(low_size,pygame.SRCALPHA)
                self.fog_frame=pygame.Surface(size,pygame.SRCALPHA)
            # Three evolving banks, independent speeds and opening widths.
            x=np.linspace(0,1,low_size[0],dtype=np.float32)[:,None]
            y=np.linspace(0,1,low_size[1],dtype=np.float32)[None,:]
            t=self.elapsed*(.16 if self.reduced else 1.)
            density=np.zeros(low_size,dtype=np.float32)
            for i,(center,speed) in enumerate(((.27,.012),(.48,-.008),(.66,.005))):
                phase=x*(8+i*3)+t*speed*5+i*2
                ridge=center+.065*np.sin(phase)+.028*np.sin(phase*2.13-t*.019)
                thickness=.055+.025*(1+np.sin(phase*.73+t*.031))
                openings=np.clip(.38+.36*np.sin(phase*.57+t*.027+i)+.28*np.cos(phase*1.37-t*.014),.07,1)
                density+=np.exp(-((y-ridge)/thickness)**2)*openings*(.7-i*.1)
            # Sample the painter stencil in viewport coordinates, preserving sky holes.
            distance_key=(size,id(source),tuple(round(v) for v in offset))
            if self.distance_key!=distance_key:
                canvas=pygame.Surface((math.ceil(size[0]/4),math.ceil(size[1]/4)))
                canvas.fill('white');canvas.blit(depth.surface,(round(offset[0]/4),round(offset[1]/4)))
                sampled=pygame.transform.smoothscale(canvas,low_size)
                self.fog_distance=pygame.surfarray.array3d(sampled)[:,:,0].astype(np.float32)/255
                self.distance_key=distance_key
            distance=self.fog_distance
            alpha=np.clip((density*165+10)*distance**1.7*strength,0,190).astype(np.uint8)
            self.fog_low.fill((*color,0))
            pygame.surfarray.pixels_alpha(self.fog_low)[:]=alpha
            pygame.transform.smoothscale(self.fog_low,size,self.fog_frame)
            self.fog_key=key
        target.blit(self.fog_frame,(0,0))

    def release(self):
        self.stop_rain();self.clear_depth()
        self.fog_low=None;self.fog_frame=None

    def metrics(self):
        surfaces=[self.rain_layer,self.fog_low,self.fog_frame]
        surfaces += [d.surface for _,d in self.depths.values()]+list(self.depth_sprites.values())+list(self.rain_sprites.values())
        retained_sources={sprite for sprite,_ in self.depth_sprites}
        return dict(particles=len(self.drops),contacts=len(self.contacts),depth_masks=len(self.depths),
                    surface_bytes=sum(s.get_width()*s.get_height()*s.get_bytesize() for s in surfaces if s is not None),
                    retained_source_bytes=sum(s.get_width()*s.get_height()*s.get_bytesize() for s in retained_sources),
                    intensity=round(self.intensity,4))

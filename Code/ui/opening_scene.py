"""Two reversible, independently rendered monument scenes."""
import json
import math
import os

import pygame

from domain.blocks import BlockType as B
from ui.presentation_renderer import Camera, make_mesh, PALETTE, FACES
from ui.opening_geometry import sanctuary, distant_arches
from ui.opening_audio import OpeningAudio
import numpy as np
from runtime_paths import BASE_DIR, SOUNDS_DIR
from ui.fonts import load_ui_font


CONFIG_PATH = os.path.join(BASE_DIR, '.opening_config.json')
MUSIC_PATH = os.path.join(SOUNDS_DIR, 'opening', 'panoir-you-have-time.ogg')


def skip_on_launch():
    try:
        with open(CONFIG_PATH, encoding='utf-8') as handle:
            data=json.load(handle)
            return bool(data.get('skipOnLaunch', False)) if isinstance(data,dict) else False
    except (OSError, ValueError, TypeError):
        return False


def save_skip(value):
    with open(CONFIG_PATH + '.tmp', 'w', encoding='utf-8') as handle:
        json.dump({'skipOnLaunch': bool(value)}, handle)
    os.replace(CONFIG_PATH + '.tmp', CONFIG_PATH)


def ramp(value, start, duration):
    return max(0.0, min(1.0, (value-start)/duration))


class OpeningScene:
    """Presentation data never enters the live world, camera or undo history."""
    TARGET = (0,3,2)
    READY_AT = 4.4
    REVEAL_DURATION = 4.6
    RISE_START = 2.2
    RISE_END = 7.6
    RISE_DURATION = 10.4
    SANCTUARY_OFFSET = np.array((-44.0,-36.0,0.0))
    ARRIVAL_ANGLE = 160.0

    def __init__(self,size,assets,*,skip=False,effects_volume=1):
        self.assets=assets
        self.elapsed=0.0
        self.placed_at=None
        self.skip=skip
        self.closed=False
        self.phase='shrine'
        self.phase_at=0.0
        self.awakened_at=None
        self.pointer=(-1,-1)
        self.hover=None
        self.feedback={}
        self.last_turn=(-100.0,0)
        self.demonstrated=False
        self.dragging=False
        self.zoom=self.target_zoom=1.0
        self.controls_at=self.READY_AT
        self.renderer=Camera(size)
        self.target_angle=135.0
        self.font=load_ui_font(20)
        self.small_font=load_ui_font(16)
        self.gpu=None
        self.audio=OpeningAudio(effects_volume)
        self.floor = []
        for x in range(-5, 6):
            for y in range(-5, 6):
                if abs(x)+abs(y)>8:
                    continue
                self.floor.append((x,y,-1,B.POLISHED_ANDESITE,'base'))
                material = B.SMOOTH_QUARTZ if (x+y)%2 else B.SMOOTH_STONE
                self.floor.append((x,y,0,material,'light' if (x+y)%2 else 'dark'))
        # A processional stair leads to an open lantern shrine. The two split
        # porticoes settle onto their plinths to frame the light over the landing.
        self.pedestals = [(x,y,z,B.QUARTZ_BRICKS,'stone')
                          for x in (-2,2) for y in (-2,-1) for z in (1,2)]
        self.pedestals += [(x,y,z,B.SMOOTH_QUARTZ,'stone')
                           for y,height in ((2,1),(1,2),(0,3),(-1,3),(-2,3))
                           for x in (-1,0,1) for z in range(1,height+1)]
        self.pedestals += [(0,3,1,B.CHISELED_QUARTZ,'stone')]
        left = [(x,y,z,B.QUARTZ_PILLAR,'stone')
                for x in (-3,) for y in (-2,-1) for z in range(2,5)]
        left += [(x,y,5,B.SMOOTH_QUARTZ,'stone') for x in (-3,-2,-1) for y in (-2,-1)]
        right = [(x,y,z,B.QUARTZ_PILLAR,'stone')
                 for x in (3,) for y in (-2,-1) for z in range(2,5)]
        right += [(x,y,5,B.SMOOTH_QUARTZ,'stone') for x in (2,3) for y in (-2,-1)]
        self.sections = (tuple(left), tuple(right))
        self.vein = [(0,-1,11,B.GLOWSTONE,'glow'), (0,-1,12,B.GLOWSTONE,'glow'),
                     (-1,-1,13,B.GLOWSTONE,'glow'), (0,-1,13,B.GLOWSTONE,'glow'),
                     (0,-2,13,B.GLOWSTONE,'glow'), (1,-2,14,B.GLOWSTONE,'glow'),
                     (0,-2,14,B.GLOWSTONE,'glow'), (-1,-2,14,B.GLOWSTONE,'glow')]
        self.vein=[(x,y,z+2,b,t) for x,y,z,b,t in self.vein]
        self.sanctuary_cells=sanctuary()
        self.distant_cells=distant_arches()
        self.meshes={
            'fixed':make_mesh(self._dict(self.floor+self.pedestals)),
            'vein':make_mesh(self._dict(self.vein)),
            'left':make_mesh(self._dict(self.sections[0])),
            'right':make_mesh(self._dict(self.sections[1])),
            'placed':make_mesh({self.TARGET:(B.CHISELED_QUARTZ,'stone')}),
            'light':make_mesh({(0,-2,4):(B.GLOWSTONE,'glow')}),
            'sanctuary':make_mesh(self.sanctuary_cells),
            'distant':make_mesh(self.distant_cells),
        }
        self.resize(size)

    @staticmethod
    def _dict(cells):
        return {(x,y,z):(block,tint) for x,y,z,block,tint in cells}

    @staticmethod
    def smooth(t):
        t=max(0,min(1,t))
        return t*t*(3-2*t)

    @property
    def ready(self):
        return self.phase=='shrine' and self.elapsed>=self.READY_AT and self.placed_at is None

    @property
    def complete(self):
        return self.placed_at is not None and self.elapsed-self.placed_at>=self.REVEAL_DURATION

    @property
    def orbit_enabled(self):
        return self.complete and self.phase!='approach'

    def section_offsets(self):
        t=0 if self.placed_at is None else self.elapsed-self.placed_at
        return ((self.smooth(ramp(t,1.35,1.5)),0,self.smooth(ramp(t,.15,1))),
                (-self.smooth(ramp(t,2,1.5)),0,self.smooth(ramp(t,.8,1))))

    def cells(self):
        cells=list(self.floor)+self.pedestals+self.vein
        for section,(dx,dy,dz) in zip(self.sections,self.section_offsets()):
            cells.extend((x+dx,y+dy,z+dz,b,t) for x,y,z,b,t in section)
        if self.placed_at is not None:
            cells.append((*self.TARGET,B.CHISELED_QUARTZ,'stone'))
            if self.elapsed-self.placed_at>=3.5:cells.append((0,-2,4,B.GLOWSTONE,'glow'))
        return cells

    def resize(self,size):
        self.size=tuple(size);w,h=size
        self.renderer.size=self.size
        self.overlay=pygame.Surface(size,pygame.SRCALPHA)
        self.controls=pygame.Surface(size,pygame.SRCALPHA)
        self.close_rect=pygame.Rect(w-56,20,36,36)
        self.turn_rects=(pygame.Rect(w//2-184,h-72,42,40),pygame.Rect(w//2+142,h-72,42,40))
        self.slider_rect=pygame.Rect(w//2-118,h-59,236,14)
        self.return_rect=pygame.Rect(w//2-65,h-125,130,36)
        self.halo=self._halo(max(32,round(h*.14)),(238,188,104))
        self.blue_halo=self._halo(max(32,round(h*.22)),(73,142,174))
        self.rise_fog=pygame.Surface(size,pygame.SRCALPHA)
        for y in range(round(h*.44),h):
            alpha=round(220*max(0,(y/h-.44)/.56)**1.3)
            pygame.draw.line(self.rise_fog,(5,16,25,alpha),(0,y),(w,y))

    @staticmethod
    def _halo(radius,color):
        surface=pygame.Surface((radius*2,radius*2),pygame.SRCALPHA)
        for r in range(radius,0,-2):
            pygame.draw.circle(surface,(*color,round(34*(1-r/radius)**2)),(radius,radius),r)
        return surface

    def update(self,seconds):
        dt=max(0,seconds);previous=self.elapsed;self.elapsed+=dt
        old_angle=self.renderer.angle
        if self.size[1]-155<=self.pointer[1]<=self.size[1] or self.dragging:
            self.controls_at=self.elapsed
        if self.placed_at is not None and previous-self.placed_at<self.REVEAL_DURATION<=self.elapsed-self.placed_at:
            self.controls_at=self.elapsed
        if self.awakened_at is not None and previous-self.awakened_at<=1.2<self.elapsed-self.awakened_at:
            self.controls_at=self.elapsed
        if self.placed_at is not None:
            for cue in (.15,.8,1.35,2.0):
                if previous-self.placed_at<cue<=self.elapsed-self.placed_at:self.audio.play('move',self.elapsed)
        if self.placed_at is not None and previous-self.placed_at<3.5<=self.elapsed-self.placed_at:
            self.audio.play('settle',self.elapsed)
        if self.phase=='approach':
            before=previous-self.phase_at;t=self.elapsed-self.phase_at
            if before<self.RISE_START<=t:self.audio.play('rise',self.elapsed)
            if before<4.4<=t:self.audio.play('move',self.elapsed)
            if before<self.RISE_END<=t:self.audio.play('settle',self.elapsed)
            if t>=self.RISE_DURATION-1e-9:
                self.phase='sanctuary'
                self.controls_at=self.elapsed
                self.renderer.angle=self.target_angle=self.ARRIVAL_ANGLE
        # Exponential damping is independent of frame rate, with no snap at 360.
        self.renderer.angle+=(self.target_angle-self.renderer.angle)*(1-math.exp(-dt*7))
        if self.phase=='shrine':
            self.renderer.center=np.array((.5,.5,4.0))
            self.renderer.half=max(10.5,10.5*1.35/(self.size[0]/self.size[1]))
        elif self.phase=='approach':
            t=self.elapsed-self.phase_at
            wide=self.smooth(ramp(t,0,self.RISE_START))
            arrive=self.smooth(ramp(t,4.8,self.RISE_DURATION-4.8))
            start=np.array((.5,.5,4));middle=np.array((-18.,-18.,7.))
            finish=self.SANCTUARY_OFFSET+(.5,-3,20)
            self.renderer.center=(start+(middle-start)*wide)*(1-arrive)+finish*arrive
            self.renderer.half=(10.5+15.5*wide+12*arrive)*max(1,1.35/(self.size[0]/self.size[1]))
            self.renderer.angle=self.depart_angle+(135-self.depart_angle)*wide+(self.ARRIVAL_ANGLE-135)*arrive
        else:
            self.renderer.center=self.SANCTUARY_OFFSET+(.5,-3,20)
            self.renderer.half=38*max(1,1.35/(self.size[0]/self.size[1]))
        self.zoom+=(self.target_zoom-self.zoom)*(1-math.exp(-dt*10))
        self.renderer.half*=self.zoom
        self.audio.update_orbit((self.renderer.angle-old_angle)/dt if dt and self.orbit_enabled else 0,dt)
        # Less than three display pixels, zero-mean, decaying at the landing.
        tremor=0.0
        if self.phase=='approach':
            t=self.elapsed-self.phase_at
            rise=ramp(t,self.RISE_START,self.RISE_END-self.RISE_START)
            tremor=2.2*math.sin(math.pi*rise)**2
            if t>self.RISE_END:tremor+=1.8*math.exp(-(t-self.RISE_END)*5)
        elif self.phase=='sanctuary':
            t=self.elapsed-self.phase_at-self.RISE_DURATION
            tremor=1.8*math.exp(-max(0,t)*5)
        elif self.placed_at is not None:
            t=self.elapsed-self.placed_at
            tremor=.65*max(0,1-abs(t-2)/2)
        self.renderer.shake=(tremor*math.sin(self.elapsed*43),tremor*.65*math.sin(self.elapsed*57))
        new_hover=self.target_at(self.pointer)
        if new_hover!=self.hover and new_hover is not None:self.audio.play('hover',self.elapsed)
        self.hover=new_hover

    def place(self):
        if not self.ready:return False
        self.placed_at=self.elapsed
        self.audio.play('place',self.elapsed)
        self.audio.play('rise',self.elapsed)
        return True

    def turn(self,direction):
        if not self.orbit_enabled:return
        self.target_angle+=direction*45
        self.last_turn=(self.elapsed,direction)
        self.demonstrated=True
        self.controls_at=self.elapsed

    def targets(self):
        if self.ready:return {'ghost':(self.TARGET,tuple(v+1 for v in self.TARGET))}
        if self.phase=='shrine' and self.complete:
            return {'door':((-.4,-1.3,3.5),(1.4,-.65,5.9))}
        if self.phase=='sanctuary':
            local={'heart':((-2,-27,31),(4,-24,39)),
                    'altar':((-2,-22,10),(4,-18,14)),
                    'pier':((10,0,7),(12,2,35)),
                    'pier_left':((-10,0,7),(-8,2,35))}
            return {name:(np.asarray(lo)+self.SANCTUARY_OFFSET,np.asarray(hi)+self.SANCTUARY_OFFSET)
                    for name,(lo,hi) in local.items()}
        return {}

    def project_sanctuary(self,point):
        return self.renderer.project(np.asarray(point)+self.SANCTUARY_OFFSET)

    def target_at(self,pos):
        hits=[]
        for name,(lo,hi) in self.targets().items():
            distance=self.renderer.hit(pos,lo,hi)
            if distance is not None:hits.append((distance,name))
        if not hits:return None
        distance,name=min(hits)
        # Interactive volumes can be seen through glass but never through stone.
        # Vectorized slab testing keeps hover cost bounded even in the large nave.
        cells=self.sanctuary_cells if self.phase=='sanctuary' else self._dict(self.cells())
        if self.phase=='sanctuary':
            if not hasattr(self,'_opaque_positions'):
                from ui.presentation_renderer import TRANSPARENT
                self._opaque_positions=np.array([p for p,(b,t) in cells.items() if b not in TRANSPARENT],dtype=float)+self.SANCTUARY_OFFSET
            positions=self._opaque_positions
        else:positions=np.array(list(cells),dtype=float)
        lo,hi=self.targets()[name]
        # The target itself is allowed to occlude its own selection volume.
        outside=np.any((positions+1<=np.asarray(lo))|(positions>=np.asarray(hi)),axis=1)
        positions=positions[outside]
        origin,direction=self.renderer.ray(pos)
        parallel=np.abs(direction)<1e-10
        safe=np.where(parallel,1,direction)
        a=(positions-origin)/safe;b=(positions+1-origin)/safe
        near=np.where(parallel,-np.inf,np.minimum(a,b)).max(axis=1)
        far=np.where(parallel,np.inf,np.maximum(a,b)).min(axis=1)
        valid=~np.any(parallel & ((origin<positions)|(origin>positions+1)),axis=1)
        if np.any(valid & (far>=np.maximum(0,near)) & (near<distance-.02)):return None
        return name

    def ghost_hit(self,pos):
        return self.ready and self.target_at(pos)=='ghost'

    def activate(self,name):
        if name=='ghost':self.place()
        elif name=='door' and self.phase=='shrine' and self.complete:
            self.phase='approach';self.phase_at=self.elapsed
            self.depart_angle=135+(self.renderer.angle-135+180)%360-180
            # Approach the approved front-quarter composition by the short arc.
            self.target_angle=self.renderer.angle+(135-self.renderer.angle+180)%360-180
            self.zoom=self.target_zoom=1.0
        elif self.phase=='sanctuary' and name in self.targets():
            self.feedback[name]=self.elapsed
            self.audio.play('touch',self.elapsed)
            if name in ('heart','altar') and self.awakened_at is None:
                self.awakened_at=self.elapsed

    def _slide(self,x):
        fraction=max(0,min(1,(x-self.slider_rect.left)/self.slider_rect.width))
        desired=135+(fraction-.5)*360
        self.controls_at=self.elapsed
        self.target_angle=desired
        self.demonstrated=True

    @property
    def controls_alpha(self):
        return round(255*(1-ramp(self.elapsed-self.controls_at,3,.4)))

    def handle_event(self,event):
        if hasattr(event,'pos'):self.pointer=event.pos
        if hasattr(event,'pos') and self.size[1]-155<=event.pos[1]<=self.size[1]:
            self.controls_at=self.elapsed
        if event.type==pygame.WINDOWFOCUSLOST:self.dragging=False
        if event.type==pygame.MOUSEWHEEL:
            if self.phase!='approach' and self.elapsed>=self.READY_AT:
                delta=getattr(event,'precise_y',event.y)
                if getattr(event,'flipped',False):delta=-delta
                self.target_zoom=max(.55,min(1.5,self.target_zoom*math.exp(-max(-20,min(20,delta))*.12)))
                self.controls_at=self.elapsed
            return
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:self.closed=True
            elif event.key in (pygame.K_q,pygame.K_e):self.turn(-1 if event.key==pygame.K_q else 1)
            return
        if event.type==pygame.MOUSEBUTTONUP and event.button==1:self.dragging=False
        if event.type==pygame.MOUSEMOTION and self.dragging:self._slide(event.pos[0])
        if event.type!=pygame.MOUSEBUTTONDOWN or event.button!=1:return
        if self.close_rect.collidepoint(event.pos):self.closed=True;return
        if self.awakened_at is not None and self.elapsed-self.awakened_at>1.2 and self.return_rect.collidepoint(event.pos):
            self.closed=True;return
        if self.orbit_enabled:
            for rect,direction in zip(self.turn_rects,(-1,1)):
                if rect.collidepoint(event.pos):self.turn(direction);return
            if self.slider_rect.inflate(12,20).collidepoint(event.pos):
                self.dragging=True;self._slide(event.pos[0]);return
        name=self.target_at(event.pos)
        if name:self.activate(name)

    def _outline(self,surface,lo,hi,color,width=1):
        corners=[(x,y,z) for z in (lo[2],hi[2]) for y in (lo[1],hi[1]) for x in (lo[0],hi[0])]
        points=self.renderer.project(corners)[:,:2]
        for a,b in ((0,1),(0,2),(1,3),(2,3),(4,5),(4,6),(5,7),(6,7),(0,4),(1,5),(2,6),(3,7)):
            pygame.draw.line(surface,color,points[a],points[b],width)

    def _draw_overlay(self):
        surface=self.overlay;surface.fill((0,0,0,0));w,h=self.size
        if self.phase=='approach':
            t=self.elapsed-self.phase_at
            self.rise_fog.set_alpha(round(230*(1-ramp(t,self.RISE_END-1,2.5))))
            surface.blit(self.rise_fog,(0,0))
        for i in range(34):
            x=(i*137.7+math.sin(i*9.7)*w*.18+math.sin(self.elapsed*.17+i)*13)%w
            y=(i*73+self.elapsed*(2+i%3))%(h*.89)
            alpha=35+round(22*(1+math.sin(self.elapsed*.4+i)))
            pygame.draw.circle(surface,(133,180,190,alpha),(round(x),round(y)),1 if i%5 else 2)
        if self.phase=='shrine':
            light=self.renderer.project((.5,-.5,11.5))[:2]
            surface.blit(self.halo,self.halo.get_rect(center=light))
            if self.complete:
                center=self.renderer.project((.5,-1,4.7))[:2]
                surface.blit(self.halo,self.halo.get_rect(center=center))
        elif self.phase=='sanctuary':
            center=self.project_sanctuary((1,-25,35))[:2]
            halo=self.halo if self.awakened_at is not None else self.blue_halo
            surface.blit(halo,halo.get_rect(center=center))
            if self.awakened_at is not None:
                altar=self.project_sanctuary((1,-19,13))[:2]
                surface.blit(self.halo,self.halo.get_rect(center=altar))
                t=self.elapsed-self.awakened_at
                for i in range(22):
                    a=i*2.4;t0=(t*.25+i*.037)%1
                    point=(center[0]+math.sin(a)*t0*w*.18,center[1]+math.cos(a)*t0*h*.22-t0*45)
                    pygame.draw.circle(surface,(249,216,157,round(160*(1-t0))),point,2)
        targets=self.targets()
        for name,(lo,hi) in targets.items():
            active=self.hover==name
            if name=='ghost':
                alpha=220 if active else round(120+35*math.sin(self.elapsed*2))
                # Face tint plus exact cube edges makes the placement silhouette clear.
                points=self.renderer.project([(x,y,z) for x,y,z in
                    ((lo[0],lo[1],hi[2]),(hi[0],lo[1],hi[2]),(hi[0],hi[1],hi[2]),(lo[0],hi[1],hi[2]))])[:,:2]
                pygame.draw.polygon(surface,(196,220,218,65 if active else 28),points)
                self._outline(surface,lo,hi,(221,236,222,alpha),2 if active else 1)
            elif active:
                self._outline(surface,lo,hi,(213,231,228,115),1)
            elif name=='door':
                self._outline(surface,lo,hi,(245,222,168,round(60+25*math.sin(self.elapsed*1.7))),1)
            since=self.elapsed-self.feedback.get(name,-100)
            if 0<=since<1.2:
                center=self.renderer.project((np.asarray(lo)+hi)/2)[:2]
                pygame.draw.circle(surface,(236,224,188,round(180*(1-since/1.2))),center,round(8+since*34),1)
        darkness=round(255*(1-ramp(self.elapsed,.25,3.4)))
        if darkness:pygame.draw.rect(surface,(0,0,0,darkness),surface.get_rect())
        cx,cy=self.close_rect.center
        color=(238,237,221,230) if self.close_rect.collidepoint(self.pointer) else (126,151,165,170)
        pygame.draw.line(surface,color,(cx-5,cy-5),(cx+5,cy+5),2)
        pygame.draw.line(surface,color,(cx+5,cy-5),(cx-5,cy+5),2)
        surface=self.controls;surface.fill((0,0,0,0))
        if self.orbit_enabled:
            for rect,label,direction in zip(self.turn_rects,('Q','E'),(-1,1)):
                idle=(not self.demonstrated and direction==1 and (self.elapsed-self.placed_at)%6<.7)
                pressed=(self.last_turn[1]==direction and self.elapsed-self.last_turn[0]<.22) or idle
                hover=rect.collidepoint(self.pointer)
                face=rect.move(0,3 if pressed else 0)
                pygame.draw.rect(surface,(93,126,142,48 if pressed else 24),face,border_radius=7)
                pygame.draw.rect(surface,(181,205,211,150 if hover or pressed else 75),face,1,border_radius=7)
                text=self.font.render(label,True,(217,228,226));surface.blit(text,text.get_rect(center=face.center))
                # Complete arrowheads with two wings, independent of the arc tangent.
                y=rect.y-12;x=rect.centerx
                pygame.draw.line(surface,(155,185,193,160),(x-8,y),(x+8,y),1)
                tip=x+direction*8
                pygame.draw.lines(surface,(155,185,193,180),False,[(tip-direction*5,y-4),(tip,y),(tip-direction*5,y+4)],1)
                if idle:
                    age=(self.elapsed-self.placed_at)%6
                    pygame.draw.circle(surface,(168,208,220,round(90*(1-age/.7))),face.center,round(23+age*12),1)
            track=self.slider_rect
            pygame.draw.line(surface,(145,174,187,85),track.midleft,track.midright,2)
            fraction=((self.renderer.angle-135+180)%360)/360
            knob=(round(track.left+fraction*track.width),track.centery)
            pygame.draw.circle(surface,(187,210,218,200),knob,4)
        prompt=None
        if self.ready:prompt='Place the missing stone.'
        elif self.phase=='sanctuary' and self.awakened_at is None and self.elapsed-self.phase_at>7:prompt='Touch the light.'
        if prompt:
            text=self.small_font.render(prompt,True,(175,197,202))
            surface.blit(text,text.get_rect(center=(w//2,h-101)))
        if self.awakened_at is not None and self.elapsed-self.awakened_at>1.2:
            hover=self.return_rect.collidepoint(self.pointer)
            text=self.font.render('Return  ›',True,(246,229,190) if hover else (202,215,216))
            surface.blit(text,text.get_rect(center=self.return_rect.center))
        surface.set_alpha(self.controls_alpha)
        self.overlay.blit(surface,(0,0))
        surface=self.overlay
        if self.elapsed<3.85:
            surface.fill((0,0,0,round(255*(1-self.smooth(ramp(self.elapsed,.35,3.5))))))
        return surface

    def _visible_meshes(self):
        if self.phase=='shrine':
            result=[(self.meshes['fixed'],(0,0,0)),(self.meshes['vein'],(0,0,0))]
            result.extend((self.meshes[n],o) for n,o in zip(('left','right'),self.section_offsets()))
            if self.placed_at is not None:result.append((self.meshes['placed'],(0,0,0)))
            if self.complete:result.append((self.meshes['light'],(0,0,0)))
            return result
        t=self.elapsed-self.phase_at
        rise=self.smooth(ramp(t,self.RISE_START,self.RISE_END-self.RISE_START))
        retract=self.smooth(ramp(t,4.4,3.2))
        result=[]
        if self.phase=='approach':
            result=[(self.meshes['fixed'],(0,0,-retract*75)),
                    (self.meshes['vein'],(0,0,retract*100))]
            result.extend((self.meshes[n],(o[0],0,o[2]-retract*75))
                          for n,o in zip(('left','right'),self.section_offsets()))
            result.extend((self.meshes[n],(0,0,-retract*75)) for n in ('placed','light'))
        result.extend(((self.meshes['distant'],self.SANCTUARY_OFFSET+(0,0,-(1-rise)*95)),
                       (self.meshes['sanctuary'],self.SANCTUARY_OFFSET+(0,0,-(1-rise)*85))))
        return result

    def render(self,screen):
        # SDL2 resizes an OpenGL window without resizing Pygame's placeholder
        # display Surface. Query the actual drawable window, not that Surface.
        size=pygame.display.get_window_size() if self.gpu else screen.get_size()
        if size!=self.size:self.resize(size)
        meshes=self._visible_meshes()
        if self.gpu:
            self.gpu.begin(self.renderer,self.elapsed)
            if self.phase=='approach':self.gpu.clip_below(-12)
            for mesh,offset in meshes:self.gpu.mesh(mesh,self.renderer,offset)
            self.gpu.clear_clip()
            self.gpu.overlay(self._draw_overlay())
        else:
            # Software inspection/fallback uses the same faces and camera. It is
            # deliberately uncached at screen resolution and never scales text.
            screen.fill((5,15,25))
            faces=[]
            for mesh,offset in meshes:
                for data in mesh:
                    if not len(data):continue
                    points=data[:,:,:3][:,:,[0,2,1]].copy();points[:,:,1]*=-1;points+=offset
                    if self.phase=='approach':
                        visible=points[:,:,2].max(axis=1)>=-12
                        data=data[visible];points=points[visible]
                    projected=self.renderer.project(points)
                    for face,verts in zip(data,projected):faces.append((verts[:,2].mean(),verts[:,:2],tuple((face[0,5:8]*255).astype(int))))
            for _,points,color in sorted(faces,key=lambda f:f[0]):pygame.draw.polygon(screen,color,points)
            screen.blit(self._draw_overlay(),(0,0))

    def close(self):
        self.audio.close()
        if self.gpu:self.gpu.close();self.gpu=None

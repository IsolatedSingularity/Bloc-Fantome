"""Two reversible, independently rendered monument scenes."""
import json
import math
import os

import pygame

from domain.blocks import BlockType as B
from ui.presentation_renderer import Camera, make_mesh, PALETTE, FACES
from ui.opening_geometry import sanctuary, distant_arches
from ui.opening_audio import OpeningAudio
from ui.opening_environment import AbyssGround, foundations, flowers
from ui.opening_encounter import OpeningEncounter, DURATION as ENCOUNTER_DURATION, ARCHITECTURE_SCALE, architecture_mesh
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
    RISE_START = 3.0
    RISE_END = 13.0
    RISE_DURATION = 16.0
    SANCTUARY_OFFSET = np.array((-70.0,-58.0,0.0))
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
        self.encounter=None
        self.orbit_keys=set()
        self.ground=AbyssGround()
        self.flowers=flowers()
        self.flowers[:,:,:3]*=ARCHITECTURE_SCALE
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
        self.vein.extend((x,y,z,B.GLOWSTONE,'glow') for x,y,z in
                         ((-2,-2,15),(-1,-3,16),(0,-3,17),(1,-2,17),(1,-1,16)))
        self.sanctuary_cells=sanctuary()
        self.distant_cells=distant_arches()
        self.encounter=OpeningEncounter(self.sanctuary_cells)
        self.meshes={
            'fixed':make_mesh(self._dict(self.floor+self.pedestals)),
            'vein':make_mesh(self._dict(self.vein)),
            'left':make_mesh(self._dict(self.sections[0])),
            'right':make_mesh(self._dict(self.sections[1])),
            'placed':make_mesh({self.TARGET:(B.CHISELED_QUARTZ,'stone')}),
            'light':make_mesh({(0,-2,4):(B.GLOWSTONE,'glow')}),
            'sanctuary':architecture_mesh(self.sanctuary_cells),
            'distant':architecture_mesh(self.distant_cells),
            'foundations':foundations(),
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
        return self.complete and self.phase not in ('approach','encounter')

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
        angular_speed=0.
        if self.orbit_enabled and self.orbit_keys:
            direction=int(pygame.K_e in self.orbit_keys)-int(pygame.K_q in self.orbit_keys)
            angular_speed=direction*38
            self.target_angle+=angular_speed*dt
            self.last_turn=(self.elapsed,direction);self.controls_at=self.elapsed
        if self.phase=='encounter':
            t=self.elapsed-self.awakened_at
            if t>=ENCOUNTER_DURATION:self.closed=True
            self.audio.update_encounter(t,dt)
        if self.size[1]-155<=self.pointer[1]<=self.size[1] or self.dragging:
            self.controls_at=self.elapsed
        if self.placed_at is not None and previous-self.placed_at<self.REVEAL_DURATION<=self.elapsed-self.placed_at:
            self.controls_at=self.elapsed
        if self.awakened_at is not None and previous-self.awakened_at<=1.2<self.elapsed-self.awakened_at:
            self.controls_at=self.elapsed
        if self.placed_at is not None and previous-self.placed_at<.15<=self.elapsed-self.placed_at:
            self.audio.play('move',self.elapsed)
        if self.placed_at is not None and previous-self.placed_at<3.5<=self.elapsed-self.placed_at:
            self.audio.play('settle',self.elapsed)
        if self.phase=='approach':
            before=previous-self.phase_at;t=self.elapsed-self.phase_at
            if before<self.RISE_START<=t:self.audio.play('rise',self.elapsed)
            if before<self.RISE_END<=t:self.audio.play('settle',self.elapsed)
            if t>=self.RISE_DURATION-1e-9:
                self.phase='sanctuary'
                self.controls_at=self.elapsed
                self.renderer.angle=self.target_angle=self.ARRIVAL_ANGLE
        # Exponential damping is independent of frame rate, with no snap at 360.
        self.renderer.angle+=(self.target_angle-self.renderer.angle)*(1-math.exp(-dt*7))
        self.renderer.angle+=angular_speed*(dt*math.exp(-dt*7)-(1-math.exp(-dt*7))/7)
        if self.phase=='shrine':
            self.renderer.center=np.array((.5,.5,6.0))
            self.renderer.half=max(12.4,12.4*1.35/(self.size[0]/self.size[1]))
        elif self.phase=='approach':
            t=self.elapsed-self.phase_at
            wide=self.smooth(ramp(t,0,4.2))
            arrive=self.smooth(ramp(t,.6,11.4))
            start,start_half=self.depart_camera
            finish=self.SANCTUARY_OFFSET+(.5,-3,25)
            self.renderer.center=start+(finish-start)*arrive
            self.renderer.half=start_half+(41*max(1,1.35/(self.size[0]/self.size[1]))-start_half)*wide
            self.renderer.angle=self.depart_angle+(135-self.depart_angle)*wide+(self.ARRIVAL_ANGLE-135)*arrive
        elif self.phase=='sanctuary':
            self.renderer.center=self.SANCTUARY_OFFSET+(.5,-3,25)
            self.renderer.half=41*max(1,1.35/(self.size[0]/self.size[1]))
        else:
            # Preserve the player's composition at the click, then ease into the
            # established encounter shot. No cut or zoom snap from an arbitrary orbit.
            u=self.smooth(ramp(self.elapsed-self.awakened_at,0,2.8))
            center,half,angle=self.encounter_camera
            self.renderer.center=center+(self.SANCTUARY_OFFSET+(.5,6,43)-center)*u
            self.renderer.half=half+(55*max(1,1.35/(self.size[0]/self.size[1]))-half)*u
            turn=(self.ARRIVAL_ANGLE-angle+180)%360-180
            self.renderer.angle=self.target_angle=angle+turn*u
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
        return True

    def turn(self,direction):
        if not self.orbit_enabled:return
        self.target_angle+=direction*3
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
            return {name:(np.asarray(lo)*ARCHITECTURE_SCALE+self.SANCTUARY_OFFSET,np.asarray(hi)*ARCHITECTURE_SCALE+self.SANCTUARY_OFFSET)
                    for name,(lo,hi) in local.items()}
        return {}

    def project_sanctuary(self,point):
        return self.renderer.project(np.asarray(point)*ARCHITECTURE_SCALE+self.SANCTUARY_OFFSET)

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
                self._opaque_positions=np.array([p for p,(b,t) in cells.items() if b not in TRANSPARENT],dtype=float)*ARCHITECTURE_SCALE+self.SANCTUARY_OFFSET
            positions=self._opaque_positions
        else:positions=np.array(list(cells),dtype=float)
        cell_size=ARCHITECTURE_SCALE if self.phase=='sanctuary' else 1
        lo,hi=self.targets()[name]
        # The target itself is allowed to occlude its own selection volume.
        outside=np.any((positions+cell_size<=np.asarray(lo))|(positions>=np.asarray(hi)),axis=1)
        positions=positions[outside]
        origin,direction=self.renderer.ray(pos)
        parallel=np.abs(direction)<1e-10
        safe=np.where(parallel,1,direction)
        a=(positions-origin)/safe;b=(positions+cell_size-origin)/safe
        near=np.where(parallel,-np.inf,np.minimum(a,b)).max(axis=1)
        far=np.where(parallel,np.inf,np.maximum(a,b)).min(axis=1)
        valid=~np.any(parallel & ((origin<positions)|(origin>positions+cell_size)),axis=1)
        if np.any(valid & (far>=np.maximum(0,near)) & (near<distance-.02)):return None
        return name

    def ghost_hit(self,pos):
        return self.ready and self.target_at(pos)=='ghost'

    def activate(self,name):
        if name=='ghost':self.place()
        elif name=='door' and self.phase=='shrine' and self.complete:
            self.depart_camera=(self.renderer.center.copy(),self.renderer.half)
            self.phase='approach';self.phase_at=self.elapsed
            self.depart_angle=135+(self.renderer.angle-135+180)%360-180
            # Approach the approved front-quarter composition by the short arc.
            self.target_angle=self.renderer.angle+(135-self.renderer.angle+180)%360-180
            self.zoom=self.target_zoom=1.0
        elif self.phase=='sanctuary' and name in self.targets():
            self.feedback[name]=self.elapsed
            self.audio.play('touch',self.elapsed)
            if name=='heart' and self.awakened_at is None:
                self.encounter_camera=(self.renderer.center.copy(),self.renderer.half,self.renderer.angle)
                self.awakened_at=self.elapsed
                self.phase='encounter';self.orbit_keys.clear()
                self.zoom=self.target_zoom=1.
                if pygame.mixer.get_init():pygame.mixer.Channel(30).stop()
                self.audio.start_encounter()

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
        if event.type==pygame.WINDOWFOCUSLOST:
            self.orbit_keys.clear();self.dragging=False
        if self.phase=='encounter':return
        if event.type==pygame.KEYUP and event.key in (pygame.K_q,pygame.K_e):
            self.orbit_keys.discard(event.key);return
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
            elif event.key in (pygame.K_q,pygame.K_e) and self.orbit_enabled:
                self.orbit_keys.add(event.key);self.demonstrated=True
            return
        if event.type==pygame.MOUSEBUTTONUP and event.button==1:self.dragging=False
        if event.type==pygame.MOUSEMOTION and self.dragging:self._slide(event.pos[0])
        if event.type!=pygame.MOUSEBUTTONDOWN or event.button!=1:return
        if self.orbit_enabled:
            for rect,direction in zip(self.turn_rects,(-1,1)):
                if rect.collidepoint(event.pos):self.turn(direction);return
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
        if self.phase=='encounter':
            t=self.elapsed-self.awakened_at
            alpha=round(255*ramp(t,40.2,2.3))
            if alpha:surface.fill((0,0,0,alpha))
            return surface
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
        surface=self.controls;surface.fill((0,0,0,0))
        if self.orbit_enabled:
            for rect,label,direction in zip(self.turn_rects,('Q','E'),(-1,1)):
                idle=not self.demonstrated and (self.elapsed-self.placed_at)%5<.8
                held=(pygame.K_q if direction<0 else pygame.K_e) in self.orbit_keys
                pulse=.5+.5*math.sin(self.elapsed*3+direction)
                face=rect.move(0,2 if held else round(pulse*2) if idle else 0)
                pygame.draw.rect(surface,(172,192,197,95 if held else 40),face,1,border_radius=5)
                text=self.small_font.render(label,True,(162,178,180))
                surface.blit(text,text.get_rect(center=face.center))
        surface.set_alpha(self.controls_alpha)
        self.overlay.blit(surface,(0,0))
        surface=self.overlay
        if self.elapsed<3.85:
            surface.fill((0,0,0,round(255*(1-self.smooth(ramp(self.elapsed,.35,3.5))))))
        return surface

    def _visible_meshes(self):
        result=[(self.meshes[n],(0,0,0)) for n in ('foundations','fixed','vein')]
        result.extend((self.meshes[n],o) for n,o in zip(('left','right'),self.section_offsets()))
        if self.placed_at is not None:result.append((self.meshes['placed'],(0,0,0)))
        if self.complete:result.append((self.meshes['light'],(0,0,0)))
        if self.phase=='shrine':return result
        t=self.elapsed-self.phase_at
        rise=self.smooth(ramp(t,self.RISE_START,self.RISE_END-self.RISE_START))
        if self.phase=='encounter':
            t=self.elapsed-self.awakened_at
            destruction=self.encounter.masonry(t)
            if destruction is not None:
                result=[self.encounter.surroundings(mesh,np.asarray(offset)-self.SANCTUARY_OFFSET,t,34,6) for mesh,offset in result]
                result=[(mesh,self.SANCTUARY_OFFSET+offset) for mesh,offset in result]
                result.extend((mesh,self.SANCTUARY_OFFSET+offset) for mesh,offset in destruction)
                mesh,offset=self.encounter.surroundings(self.meshes['distant'],(0,0,0),t,33,6)
                result.append((mesh,self.SANCTUARY_OFFSET+offset))
                return result
        result.extend(((self.meshes['distant'],self.SANCTUARY_OFFSET+(0,0,-(1-rise)*95)),
                       (self.meshes['sanctuary'],self.SANCTUARY_OFFSET+(0,0,-(1-rise)*85))))
        return result

    def _encounter_overlay_gpu(self):
        # No interface text exists during this phase. Draw its sparse motes
        # directly instead of uploading an 8 MB transparent FHD image per frame.
        gpu=self.gpu;gpu.screen_space(self.size);gpu.gl.glDisable(0x0DE1)
        w,h=self.size;data=np.zeros((34,4,9),dtype='float32')
        for i in range(34):
            x=(i*137.7+math.sin(i*9.7)*w*.18+math.sin(self.elapsed*.17+i)*13)%w
            y=(i*73+self.elapsed*(2+i%3))%(h*.89)
            r=1 if i%5 else 2
            data[i,:,:3]=((x-r,y-r,0),(x+r,y-r,0),(x+r,y+r,0),(x-r,y+r,0))
            data[i,:,5:8]=np.array((133,180,190))/255
            data[i,:,8]=(35+22*(1+math.sin(self.elapsed*.4+i)))/255
        gpu.draw(data)
        alpha=ramp(self.elapsed-self.awakened_at,40.2,2.3)
        if alpha:gpu.flat(((0,0,0),(w,0,0),(w,h,0),(0,h,0)),((0,0,0,alpha),)*4)

    def render(self,screen):
        # SDL2 resizes an OpenGL window without resizing Pygame's placeholder
        # display Surface. Query the actual drawable window, not that Surface.
        size=pygame.display.get_window_size() if self.gpu else screen.get_size()
        if size!=self.size:self.resize(size)
        meshes=self._visible_meshes()
        if self.gpu:
            self.gpu.begin(self.renderer,self.elapsed)
            swallow=ramp(self.elapsed-self.awakened_at,32,9) if self.awakened_at is not None else 0
            self.gpu.gl.glDisable(0x0DE1)
            self.gpu.draw(self.ground.mesh(self.elapsed,swallow),0x0004)
            self.gpu.gl.glEnable(0x0DE1);self.gpu.gl.glBindTexture(0x0DE1,self.gpu.ids[0])
            if self.phase=='approach':self.gpu.clip_below(-19)
            for mesh,offset in meshes:self.gpu.mesh(mesh,self.renderer,offset)
            self.gpu.clear_clip()
            if self.phase in ('sanctuary','encounter'):
                if self.phase=='sanctuary' or self.elapsed-self.awakened_at<33:
                    dx,dy,dz=self.SANCTUARY_OFFSET
                    self.gpu.gl.glTranslatef(dx,dz,-dy);self.gpu.gl.glDisable(0x0DE1)
                    self.gpu.draw(self.flowers);self.gpu.gl.glTranslatef(-dx,-dz,dy)
                if self.phase=='encounter':self.encounter.rig.draw(self.gpu,self.elapsed-self.awakened_at,self.SANCTUARY_OFFSET)
            if self.phase=='encounter':self._encounter_overlay_gpu()
            else:self.gpu.overlay(self._draw_overlay())
        else:
            # Software inspection/fallback uses the same faces and camera. It is
            # deliberately uncached at screen resolution and never scales text.
            screen.fill((5,15,25))
            faces=[]
            swallow=ramp(self.elapsed-self.awakened_at,32,9) if self.awakened_at is not None else 0
            meshes=[((self.ground.mesh(self.elapsed,swallow,coarse=True),),(0,0,0))]+meshes
            if self.phase=='encounter':
                creature,_=self.encounter.rig.geometry(self.elapsed-self.awakened_at)
                meshes.append(((creature.reshape(-1,3,9),),self.SANCTUARY_OFFSET))
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
        if self.gpu:
            if self.encounter:self.encounter.close(self.gpu)
            self.gpu.close();self.gpu=None

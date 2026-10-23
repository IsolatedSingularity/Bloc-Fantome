"""World tile material and independent motion from the preserved original masks.

Small buffers only. No full-screen blur, source-mask edits or phase-shared bounce.
"""
import math
from functools import lru_cache
import pygame
import numpy as np
from ui import chrome
from ui.generated_icons import fitted, layers


def material(screen,rect,color,level,focused=False):
    tint=tuple(round(a+(b*.52-a)*level) for a,b in zip(chrome.CONTROL,color))
    chrome.rounded(screen,(*tint,120+round(28*level)),rect,12)
    # A shallow, cached highlight follows the face; text never shares its alpha.
    screen.blit(gloss(rect.size),rect)
    if focused:chrome.outline(screen,(*chrome.FOCUS,210),rect.inflate(-1,-1),12)


@lru_cache(maxsize=24)
def gloss(size):
    layer=pygame.Surface(size,pygame.SRCALPHA);w,h=size
    for y in range(2,min(22,h-2)):
        pygame.draw.line(layer,(214,233,255,round(15*(1-y/22)**2)),(7,y),(w-8,y))
    pygame.draw.line(layer,(226,241,255,65),(13,1),(w-14,1))
    return layer


def _blit(screen,source,center,alpha=255,dx=0,dy=0):
    copy=source.copy();copy.set_alpha(max(0,min(255,round(alpha))))
    screen.blit(copy,copy.get_rect(center=(round(center[0]+dx),round(center[1]+dy))))


@lru_cache(maxsize=32)
def pieces(name,size):
    source=fitted(name,size);w,h=source.get_size()
    if name=='clouds':
        # The two masks are disconnected across the original occlusion gutter.
        components=pygame.mask.from_surface(source,30).connected_components(8)
        parts=[]
        for component in components:
            # Keep the original coverage at the contour, not mask stair steps.
            layer=component.to_surface(setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
            layer.blit(source,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
            parts.append(layer)
        return tuple(parts)
    return (source,)


def icon(screen,name,rect,seconds,level=1.,reduced=False,celestial=0.):
    """State transitions finish in 200ms; active paths have independent clocks."""
    rect=pygame.Rect(rect);size=(round(rect.width*.88),round(rect.height*.88))
    base=fitted(name,size);center=rect.center;t=0 if reduced else seconds
    active=level>0 and not reduced
    alpha=160+95*level
    if name=='rain':
        source,cloud,*drops=layers(name,size)
        # Passing rear cloud, then a grounded front bank, with staggered contact.
        _blit(screen,cloud,center,alpha*.42,(-2+t*.35%4) if active else -2,-2)
        _blit(screen,cloud,center,alpha,1 if active else 0,0)
        for i,drop in enumerate(drops):
            life=(t*(.79+i*.07)+i*.37)%1 if active else .5
            fade=min(1,life*6,(1-life)*7) if active else 1
            _blit(screen,drop,center,alpha*fade,-life*(2+i%2),round((life-.5)*rect.height*.22))
            if active and life>.87:
                q=(life-.87)/.13;x=rect.x+rect.width*(.25+i*.25);y=rect.bottom-3
                pygame.draw.line(screen,(170,200,220),(round(x-q*3),y),(round(x+q*3),y),1)
    elif name=='snow':
        # Three independently advected flakes; bounded tumble, never a spinner.
        for i,(scale,speed,offset) in enumerate(((.58,.13,.12),(.34,.19,.62),(.26,.11,.87))):
            flake=fitted('snow',(round(size[0]*scale),round(size[1]*scale)))
            life=(t*speed+offset)%1 if active else offset
            dx=(i-1)*rect.width*.25+(life-.5)**2*(8 if i%2 else -9)
            dy=(life-.5)*rect.height*.52
            angle=(life-.5)*36*(1 if i%2 else -1) if active else 0
            flake=pygame.transform.rotozoom(flake,angle,1)
            fade=min(1,life*8,(1-life)*8) if active else 1
            _blit(screen,flake,center,alpha*fade,dx,dy)
    elif name=='sun':
        night=celestial%720>=360
        body=fitted('sky' if night else 'sun',size)
        q=(celestial%360)/360 if active else .5
        _blit(screen,body,center,alpha,math.sin((q-.5)*math.pi)*4,-math.sin(q*math.pi)*3*level)
        # A low horizon shadow responds to the same celestial position.
        if level:pygame.draw.line(screen,(115,147,171),(rect.x+8,rect.bottom-1),(rect.right-8,rect.bottom-1))
    elif name=='clouds':
        parts=pieces(name,size)
        for i,part in enumerate(sorted(parts,key=lambda p:p.get_bounding_rect().centery)):
            # Different speeds and opposing occlusion, with soft wrapped edges.
            travel=(t*(.09+i*.035)+i*.39)%1 if active else .5
            dx=(travel-.5)*8;fade=.72+.28*(1-abs(travel-.5)*2)
            _blit(screen,part,center,alpha*(fade if i==0 else 1),dx,-i*.5)
    elif name=='lighting':
        # Move illumination across the original cube faces, keeping its shape.
        lit=base.copy();w,h=lit.get_size();pixels=pygame.surfarray.pixels_alpha(lit)
        x=np.arange(w)[:,None]/max(1,w-1);y=np.arange(h)[None,:]/max(1,h-1)
        source=.5+.3*math.cos(t*.71) if active else .5
        face=(.57+.43*np.clip(1-abs(x-source)*1.5,0,1))*level+(1-level)*.62
        shadow=np.where(y>.88,.58+.24*(1-source),1.)
        pixels[:]=(pixels*face*shadow).astype('uint8');del pixels
        _blit(screen,lit,center)
    elif name=='sky':
        # Crescent stays anchored. Stars emerge separately with depth.
        w,h=base.get_size();moon=base.copy();stars=base.copy()
        cut=round(w*.62);moon.fill((0,0,0,0),(cut,0,w-cut,h));stars.fill((0,0,0,0),(0,0,cut,h))
        _blit(screen,moon,center,alpha)
        reveal=.65+.35*(.5-.5*math.cos(t*.83)) if active else 1
        _blit(screen,stars,center,alpha*reveal,0,-2*level*reveal)
    elif name=='horror_rain':
        # Low-amplitude gust disturbances at unequal intervals, never a flash.
        cycle=t%7.3;gust=math.exp(-((cycle-1.2)/.24)**2)-.7*math.exp(-((cycle-4.8)/.38)**2) if active else 0
        _blit(screen,base,center,alpha,-1.6*gust,0)
        for i in range(3):
            life=(t*(.7+i*.17)+i*.43)%1 if active else .6
            if active and (i!=1 or cycle<2.3):
                x=rect.x+rect.width*(.24+i*.25)-life*(2+gust*2);y=rect.centery+life*rect.height*.38
                pygame.draw.line(screen,(172,142,162),(round(x),round(y)),(round(x-1),round(y+3)),1)
    elif name=='flow':
        # Current brightness propagates along the actual three ribbon masks.
        water=base.copy();w,h=water.get_size();pixels=pygame.surfarray.pixels_alpha(water)
        x=np.arange(w)[:,None]/max(1,w-1);y=np.arange(h)[None,:]/max(1,h-1)
        phase=(x-t*.38+y*.42)%1
        current=.62+.38*np.exp(-((phase-.48)/.19)**2) if active else .9
        pixels[:]=(pixels*current*(alpha/255)).astype('uint8');del pixels
        _blit(screen,water,center)
    else:_blit(screen,base,center,alpha)


@lru_cache(maxsize=12)
def end_icon(size):
    """Locally authored simplified End silhouette: one island, three pillars."""
    w,h=size;s=pygame.Surface((w*3,h*3),pygame.SRCALPHA)
    def p(x,y):return round(x*w*3),round(y*h*3)
    white=(242,247,252)
    pygame.draw.polygon(s,white,[p(*q) for q in ((.08,.67),(.48,.48),(.92,.66),(.67,.8),(.51,.96),(.3,.81))])
    for x,top,bottom in ((.29,.36,.69),(.51,.12,.72),(.72,.4,.67)):
        pygame.draw.polygon(s,white,[p(x-.045,top),p(x+.045,top-.025),p(x+.045,bottom),p(x-.045,bottom+.025)])
        pygame.draw.line(s,(0,0,0,0),p(x+.045,top+.05),p(x+.045,bottom),max(1,round(w*.09)))
    return pygame.transform.smoothscale(s,size)

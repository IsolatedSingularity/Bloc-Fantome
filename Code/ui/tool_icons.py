"""Small original line silhouettes, drawn at their final display resolution."""
import pygame
import math
from collections import OrderedDict


def _basic(surface, action, rect, color):
    x,y=rect.center; r=min(rect.width,rect.height)//3
    stroke=max(2,rect.width//16)
    line=lambda points:pygame.draw.lines(surface,color,False,points,stroke)
    if action in ('rain','snow','clouds','horror_rain'):
        pygame.draw.arc(surface,color,(x-r,y-r,r*2,r+4),0,3.14,stroke)
        line([(x-r,y),(x+r,y)])
        for dx in (() if action=='clouds' else (-r,0,r)):
            line([(x+dx,y+3),(x+dx-2,y+7)])
            if action=='snow':line([(x+dx-3,y+5),(x+dx+2,y+5)])
    elif action in ('sun','lighting','sky'):
        pygame.draw.circle(surface,color,(x,y),max(2,r//2),stroke)
        for dx,dy in ((1,0),(-1,0),(0,stroke),(0,-1)):
            line([(x+dx*(r-1),y+dy*(r-1)),(x+dx*(r+3),y+dy*(r+3))])
    elif action in ('grow','shrink','noise','terrain','terrain_view'):
        pygame.draw.polygon(surface,(88,130,102),[(x-r,y),(x,y-r//2),(x+r,y),(x,y+r//2)])
        pygame.draw.polygon(surface,(104,88,69),[(x-r,y),(x,y+r//2),(x+r,y),(x+r,y+5),(x,y+r//2+5),(x-r,y+5)])
        if action=='noise':
            line([(x-r,y),(x-3,y-5),(x+1,y-2),(x+5,y-7),(x+r,y)])
        else:
            line([(x-4,y-8),(x+4,y-8)])
            if action=='grow':line([(x,y-12),(x,y-4)])
    elif action=='flow':
        for dy in (-4,3):line([(x-r,y+dy),(x-3,y+dy-3),(x+3,y+dy+3),(x+r,y+dy)])
    elif action=='brush':
        line([(x-r,y+r),(x+2,y-2)])
        pygame.draw.polygon(surface,color,[(x,y-4),(x+4,y-8),(x+8,y-4),(x+4,y)],stroke)
    elif action in ('fill','flood','replace'):
        pygame.draw.polygon(surface,color,[(x-r,y-r),(x+r,y-r),(x+r-3,y+r),(x-r+3,y+r)],stroke)
        line([(x-r+2,y),(x+r-2,y)])
        if action=='replace':line([(x-r,y+r+3),(x+r,y+r+3),(x+r-3,y+r)])
    elif action in ('clip_left','clip_right','turn','turn_placed','half'):
        pygame.draw.arc(surface,color,(x-r,y-r,r*2,r*2),.3,5,stroke)
        dx=-r if action=='clip_left' else r
        pygame.draw.polygon(surface,color,[(x+dx,y-r),(x+dx-4,y-r+4),(x+dx+3,y-r+5)])
    elif action in ('copy','paste','stamp','blueprint'):
        pygame.draw.rect(surface,color,(x-r,y-r,r+4,r+5),stroke)
        pygame.draw.rect(surface,color,(x-2,y-2,r+3,r+4),stroke)
    elif action in ('selection','fill_selection','hollow','delete','wand'):
        pygame.draw.rect(surface,color,(x-r,y-r,r*2,r*2),stroke)
        if action in ('fill_selection','wand'):line([(x-r,y+r),(x+r,y-r)])
        if action=='delete':line([(x-r,y-r),(x+r,y+r)])
    elif action in ('mirror_x','mirror_y','radial','layers','layer_up','layer_down'):
        line([(x-r,y-r),(x-r,y+r)]);line([(x+r,y-r),(x+r,y+r)])
        line([(x,y-r-2),(x,y+r+2)])
    elif action in ('measure','grid','center','xray','minimap'):
        pygame.draw.rect(surface,color,(x-r,y-r,r*2,r*2),stroke)
        line([(x-r,y),(x+r,y)]);line([(x,y-r),(x,y+r)])
    else:
        line([(x-r,y+r),(x+r,y-r)])
        pygame.draw.polygon(surface,color,[(x+r-5,y-r),(x+r,y-r-4),(x+r+4,y-r),(x+r,y-r+5)],stroke)


_cache=OrderedDict()
_cache_bytes=0


def draw(surface,action,rect,color,phase=0):
    """Original scalable silhouettes; only these small icon buffers are sampled."""
    global _cache_bytes
    rect=pygame.Rect(rect);tick=round(phase*20)%160 if phase else 0
    key=(action,rect.size,tuple(color),tick)
    tile=_cache.get(key)
    if tile is None:
        tile=pygame.Surface((rect.width*3,rect.height*3),pygame.SRCALPHA)
        _paint(tile,action,color,tick/20)
        tile=pygame.transform.smoothscale(tile,rect.size)
        cost=rect.width*rect.height*4
        while _cache and _cache_bytes+cost>8*1024*1024:
            _,old=_cache.popitem(last=False);_cache_bytes-=old.get_width()*old.get_height()*4
        _cache[key]=tile;_cache_bytes+=cost
    else:_cache.move_to_end(key)
    surface.blit(tile,rect)


def _paint(s,action,c,t):
    w,h=s.get_size();u=min(w,h)/100;ox=(w-100*u)/2;oy=(h-100*u)/2
    def pt(x,y):return round(ox+x*u),round(oy+y*u)
    def line(points,color=c,width=3):pygame.draw.lines(s,color,False,[pt(*p) for p in points],max(1,round(width*u)))
    def poly(points,color=c):pygame.draw.polygon(s,color,[pt(*p) for p in points])
    def circle(x,y,r,color=c,width=0):pygame.draw.circle(s,color,pt(x,y),round(r*u),round(width*u))
    if action in ('rain','clouds','horror_rain'):
        drift=math.sin(t)*4 if action=='clouds' else 0
        for x,y,r in ((34,40,13),(50,32,18),(68,41,12)):circle(x+drift,y,r)
        poly([(22+drift,41),(79+drift,41),(73+drift,52),(28+drift,52)])
        if action!='clouds':
            for i,x in enumerate((31,50,69)):
                y=61+((t*18+i*3)%12 if t else 0)
                if action=='horror_rain':poly([(x,y-5),(x-4,y+4),(x+4,y+4)])
                else:line([(x,y),(x-4,y+9)],width=4)
    elif action=='snow':
        for i in range(6):
            a=i*math.pi/3;end=(50+29*math.cos(a),50+29*math.sin(a))
            line([(50,50),end]);x,y=50+20*math.cos(a),50+20*math.sin(a)
            for sign in (-1,1):line([(x,y),(x+10*math.cos(a+sign*.7),y+10*math.sin(a+sign*.7))])
        if t:circle(50+34*math.cos(t),50+34*math.sin(t),2)
    elif action=='sun':
        circle(50,50,15,width=3)
        for i in range(8):
            a=i*math.pi/4+t*.3
            line([(50+23*math.cos(a),50+23*math.sin(a)),(50+31*math.cos(a),50+31*math.sin(a))])
    elif action=='lighting':
        poly([(52,17),(29,53),(47,53),(40,84),(74,43),(54,43),(66,17)])
        if t and math.sin(t*4)>.2:
            line([(20,32),(12,26)]);line([(79,65),(88,71)])
    elif action=='sky':
        # Crescent with transparent cut-out, plus a separate star.
        circle(43,49,27);circle(54,40,25,(0,0,0,0))
        poly([(75,21),(78,29),(87,32),(78,35),(75,44),(72,35),(64,32),(72,29)])
    elif action=='flow':
        for y in (34,50,66):line([(x,y+4*math.sin(x*.12-t*2)) for x in range(18,83,4)],width=3)
    elif action in ('grow','shrink','noise','terrain','terrain_view'):
        for i,j in ((0,0),(1,0),(0,1),(1,1)):
            x=50+(i-j)*18;y=43+(i+j)*9
            height=13+((i*9+j*5)%13 if action=='noise' else 0)
            poly([(x-18,y-height),(x,y-height-9),(x+18,y-height),(x,y-height+9)],(111,168,118))
            poly([(x-18,y-height),(x,y-height+9),(x,y+12),(x-18,y+3)],(111,83,61))
            poly([(x,y-height+9),(x+18,y-height),(x+18,y+3),(x,y+12)],(77,65,56))
            line([(x-16,y-height),(x,y-height-8),(x+16,y-height)],(161,196,133),1)
        if action in ('grow','shrink'):
            line([(43,15),(57,15)],(221,238,250),3)
            if action=='grow':line([(50,8),(50,22)],(221,238,250),3)
    elif action=='library_worlds':
        circle(50,49,31,(91,145,181));line([(23,35),(36,30),(47,39),(39,50),(53,57),(48,75)],(168,205,146),7)
        line([(63,25),(70,41),(62,53),(75,63)],(168,205,146),6)
        pygame.draw.ellipse(s,c,(*pt(35,18),round(30*u),round(62*u)),max(1,round(u)))
    elif action=='library_biomes':
        poly([(12,76),(50,58),(88,76),(50,91)],(84,122,105))
        for x,y,sz in ((32,56,24),(66,58,20),(51,39,29)):
            line([(x,y),(x,y+22)],(159,123,85),4)
            poly([(x,y-sz),(x-sz*.55,y+7),(x+sz*.55,y+7)],(102,167,139))
    elif action=='library_structures':
        for x in (23,62):
            poly([(x,32),(x+15,26),(x+15,76),(x,83)],(139,166,192))
            poly([(x+15,26),(x+23,31),(x+23,80),(x+15,76)],(90,117,149))
        poly([(23,32),(38,26),(77,26),(85,31),(68,40),(39,40)],(191,206,219))
        line([(27,50),(35,47)],(215,224,230),2)
    elif action=='library_saved':
        for x,y in ((32,21),(24,29)):
            poly([(x,y),(x+31,y),(x+44,y+13),(x+44,y+53),(x,y+53)],(98,136,170))
            line([(x+31,y),(x+31,y+13),(x+44,y+13)],(190,214,232),2)
        line([(34,50),(57,50)],(219,229,239),3);line([(34,61),(52,61)],(219,229,239),3)
    else:_basic(s,action,s.get_rect(),c)

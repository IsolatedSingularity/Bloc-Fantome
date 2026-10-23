"""Native-size satin navy chrome. World textures never enter UI surfaces."""
import pygame
import pygame.gfxdraw
from collections import OrderedDict
from functools import lru_cache

TEXT = (230, 236, 245)
MUTED = (153, 170, 192)
ACCENT = (173, 203, 235)
SURFACE = (16, 24, 39)
CONTROL = (30, 43, 62)
HOVER = (47, 65, 87)
SELECTED = (41, 61, 84)
FOCUS = (174, 208, 215)
ERROR = (245, 174, 150)
RADIUS = 12
GAP = 8
MARGIN = 24


_rounded_cache = OrderedDict()
_rounded_bytes = 0


def rounded(screen, color, rect, radius=RADIUS):
    """Native-sized fills with antialiased corners and a 12 MiB cache."""
    global _rounded_bytes
    rect = pygame.Rect(rect)
    if rect.width <= 0 or rect.height <= 0:return
    rgba = tuple(color) if len(color)==4 else (*color,255)
    radius = max(0,min(int(radius),rect.width//2,rect.height//2))
    key = (rect.size,rgba,radius)
    layer = _rounded_cache.get(key)
    if layer is None:
        layer=pygame.Surface(rect.size,pygame.SRCALPHA)
        layer.fill((*rgba[:3],0))
        w,h=rect.size;r=radius
        if not r:
            layer.fill(rgba)
        pygame.draw.rect(layer,rgba,(r,0,w-2*r,h))
        pygame.draw.rect(layer,rgba,(0,r,w,h-2*r))
        # Supersample only four tiny corner buffers. Text and the panel body
        # stay at their native final size; no full-screen supersampling.
        corner=pygame.Surface((max(1,r*6),max(1,r*6)),pygame.SRCALPHA)
        pygame.draw.circle(corner,(255,255,255,255),(r*3,r*3),r*3)
        circle=pygame.transform.smoothscale(corner,(r*2,r*2))
        coverage=pygame.surfarray.array_alpha(circle).astype('uint16')*rgba[3]//255
        alpha=pygame.surfarray.pixels_alpha(layer)
        for dest,area in (((0,0),(0,0,r,r)),((w-r,0),(r,0,r,r)),
                          ((0,h-r),(0,r,r,r)),((w-r,h-r),(r,r,r,r))):
            # Filter only coverage, never RGB against transparent black. This
            # prevents dark corner patches from double-multiplied edge colors.
            dx,dy=dest;sx,sy,_,_=area
            alpha[dx:dx+r,dy:dy+r]=coverage[sx:sx+r,sy:sy+r]
        del alpha
        cost=w*h*4
        while _rounded_cache and _rounded_bytes+cost>12*1024*1024:
            _,old=_rounded_cache.popitem(last=False);_rounded_bytes-=old.get_width()*old.get_height()*4
        if cost<=12*1024*1024:
            _rounded_cache[key]=layer;_rounded_bytes+=cost
    else:_rounded_cache.move_to_end(key)
    screen.blit(layer,rect)


def panel(screen, rect, assets=None, accent=None, alpha=246, *, major=False):
    rect=pygame.Rect(rect)
    # Cached fills retain readable navy; only a small top highlight is translucent.
    alpha=max(215,alpha)
    rounded(screen,(*SURFACE,alpha),rect,0 if major else RADIUS)
    if rect.width>24 and rect.height>20:
        outline(screen, (57,75,94,100), rect, 0 if major else RADIUS)


def _outline(size, color, radius, width):
    """Subtract concentric coverage masks for a consistent antialiased stroke."""
    global _rounded_bytes
    key=('stroke',size,color,radius,width)
    if key in _rounded_cache:
        _rounded_cache.move_to_end(key)
        return _rounded_cache[key]
    outer=pygame.Surface(size,pygame.SRCALPHA)
    inner=pygame.Surface(size,pygame.SRCALPHA)
    rounded(outer,(255,255,255),outer.get_rect(),radius)
    rounded(inner,(255,255,255),inner.get_rect().inflate(-2*width,-2*width),max(0,radius-width))
    coverage=pygame.surfarray.array_alpha(outer).astype('int32')-pygame.surfarray.array_alpha(inner)
    layer=pygame.Surface(size,pygame.SRCALPHA);layer.fill(color)
    alpha=pygame.surfarray.pixels_alpha(layer)
    alpha[:]=coverage.clip(0,255)*(color[3] if len(color)==4 else 255)//255
    del alpha
    cost=size[0]*size[1]*4
    while _rounded_cache and _rounded_bytes+cost>12*1024*1024:
        _,old=_rounded_cache.popitem(last=False);_rounded_bytes-=old.get_width()*old.get_height()*4
    if cost<=12*1024*1024:
        _rounded_cache[key]=layer;_rounded_bytes+=cost
    return layer


def outline(screen, color, rect, radius=7, width=1):
    rect=pygame.Rect(rect)
    if rect.width>2*width and rect.height>2*width:
        screen.blit(_outline(rect.size,tuple(color),radius,width),rect)


def ellipsize(text, font, width):
    text = str(text)
    if font.size(text)[0] <= width: return text
    while text and font.size(text + '…')[0] > width: text = text[:-1]
    return text + '…' if text else ''


def button(screen, rect, text, font, hovered=False, selected=False,
           enabled=True, focused=False, quiet=False):
    rect = pygame.Rect(rect)
    if not quiet or hovered or selected:
        rounded(screen, HOVER if hovered and enabled else SELECTED if selected else CONTROL, rect, 7)
    if selected:
        outline(screen, ACCENT, rect.inflate(-4,-4), 5)
    if focused:
        outline(screen, FOCUS, rect.inflate(4, 4), 9, 2)
    color = ACCENT if selected else TEXT if enabled else MUTED
    if text=='Close':
        # A restrained, rounded X with the same optical weight at every size.
        size=max(12,min(18,round(font.get_height()*.65)))
        glyph=_close_glyph(size,color)
        screen.blit(glyph,glyph.get_rect(center=rect.center))
        return
    label = font.render(ellipsize(text, font, max(0, rect.width-16)), True, color)
    old = screen.get_clip(); screen.set_clip(rect.clip(old))
    screen.blit(label, label.get_rect(center=rect.center)); screen.set_clip(old)


@lru_cache(maxsize=16)
def _close_glyph(size,color):
    scale=3;image=pygame.Surface((size*scale,size*scale),pygame.SRCALPHA)
    lo=scale;hi=(size-1)*scale-scale
    for start,end in (((lo,lo),(hi,hi)),((lo,hi),(hi,lo))):
        pygame.draw.line(image,color,start,end,2*scale)
        for point in (start,end):pygame.draw.circle(image,color,point,scale)
    return pygame.transform.smoothscale(image,(size,size))


def close_size(font):
    return max(32,font.get_height()+10)


def icon_button(screen, rect, label, font, hovered=False, focused=False):
    """Quiet dark utility control with the same stroke and focus geometry."""
    rect=pygame.Rect(rect)
    rounded(screen, CONTROL if hovered else SURFACE, rect, 7)
    outline(screen, ACCENT if hovered else (57,75,94), rect, 7)
    if focused:outline(screen, FOCUS, rect.inflate(4,4), 9, 2)
    glyph=font.render(label,True,TEXT if hovered or focused else MUTED)
    ink=glyph.get_bounding_rect()
    screen.blit(glyph,(rect.centerx-ink.width//2-ink.x,rect.centery-ink.height//2-ink.y))


def wrapped_height(text,font,width):
    lines=0
    for paragraph in str(text).split('\n'):
        line='';lines+=1
        for word in paragraph.split():
            trial=(line+' '+word).strip()
            if line and font.size(trial)[0]>width:
                lines+=1;line=word
            else:line=trial
    return lines*font.get_linesize()+max(0,lines-1)*3


def button_surface(texture, size):
    """Compatibility for old cached controls; deliberately ignore the atlas."""
    result = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(result, CONTROL, result.get_rect(), border_radius=4)
    return result


def wrapped(screen, text, font, rect, color=TEXT):
    """Wrap at final glyph size, including paragraphs and long tokens."""
    rect = pygame.Rect(rect)
    old = screen.get_clip(); screen.set_clip(rect.clip(old)); y = rect.top
    try:
        for paragraph in str(text).split('\n'):
            line = ''
            for word in paragraph.split():
                trial = (line+' '+word).strip()
                if line and font.size(trial)[0] > rect.width:
                    if y+font.get_height() > rect.bottom: return y
                    screen.blit(font.render(ellipsize(line,font,rect.width),True,color),(rect.x,y))
                    y += font.get_linesize()+3; line = word
                else: line = trial
            if line and y+font.get_height() <= rect.bottom:
                screen.blit(font.render(ellipsize(line,font,rect.width),True,color),(rect.x,y))
            y += font.get_linesize()+3
        return y
    finally: screen.set_clip(old)


def speaker(screen, rect, muted=False):
    x,y=rect.center
    pygame.draw.rect(screen,MUTED,(x-8,y-3,5,7))
    pygame.draw.polygon(screen,MUTED,((x-3,y-3),(x+3,y-7),(x+3,y+7),(x-3,y+4)))
    if muted:pygame.draw.line(screen,ERROR,(x-8,y-8),(x+9,y+8),2)
    else:pygame.draw.lines(screen,MUTED,False,((x+6,y-5),(x+9,y),(x+6,y+5)),2)


def heading(screen, rect, text, assets, font):
    wrapped(screen,text,font,pygame.Rect(rect).inflate(-8,0))

"""Native-size matte chrome. World textures never enter UI surfaces."""
import pygame
import pygame.gfxdraw
from collections import OrderedDict

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
    radius = max(1,min(int(radius),rect.width//2,rect.height//2))
    key = (rect.size,rgba,radius)
    layer = _rounded_cache.get(key)
    if layer is None:
        layer=pygame.Surface(rect.size,pygame.SRCALPHA)
        w,h=rect.size;r=radius
        pygame.draw.rect(layer,rgba,(r,0,w-2*r,h))
        pygame.draw.rect(layer,rgba,(0,r,w,h-2*r))
        # Supersample only four tiny corner buffers. Text and the panel body
        # stay at their native final size; no full-screen supersampling.
        corner=pygame.Surface((r*6,r*6),pygame.SRCALPHA)
        pygame.draw.circle(corner,rgba,(r*3,r*3),r*3)
        circle=pygame.transform.smoothscale(corner,(r*2,r*2))
        for dest,area in (((0,0),(0,0,r,r)),((w-r,0),(r,0,r,r)),
                          ((0,h-r),(0,r,r,r)),((w-r,h-r),(r,r,r,r))):
            layer.blit(circle,dest,area)
        cost=w*h*4
        while _rounded_cache and _rounded_bytes+cost>12*1024*1024:
            _,old=_rounded_cache.popitem(last=False);_rounded_bytes-=old.get_width()*old.get_height()*4
        if cost<=12*1024*1024:
            _rounded_cache[key]=layer;_rounded_bytes+=cost
    else:_rounded_cache.move_to_end(key)
    screen.blit(layer,rect)


def panel(screen, rect, assets=None, accent=None, alpha=234):
    rounded(screen,(*SURFACE,alpha),rect)


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
        pygame.draw.line(screen, ACCENT, (rect.left+10, rect.bottom-3), (rect.right-10, rect.bottom-3), 2)
    if focused:
        pygame.draw.rect(screen, FOCUS, rect.inflate(4, 4), 2, border_radius=6)
    color = ACCENT if selected else TEXT if enabled else MUTED
    label = font.render(ellipsize(text, font, max(0, rect.width-16)), True, color)
    old = screen.get_clip(); screen.set_clip(rect.clip(old))
    screen.blit(label, label.get_rect(center=rect.center)); screen.set_clip(old)


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

"""Native caches for the generated flat white artwork; no procedural replacement art."""
from functools import lru_cache
import math
import pygame
from ui.generated_icons import artwork, fitted

NAMES={'dimension_overworld','dimension_end','lighting','clouds'}


@lru_cache(maxsize=8)
def source_parts(name):
    source=artwork()[name]
    mask=pygame.mask.from_surface(source,16)
    components=mask.connected_components(max(4,source.get_width()*source.get_height()//300))
    parts=[]
    for component in components:
        bounds=component.get_bounding_rects()[0]
        layer=component.to_surface(setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
        layer.blit(source,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        parts.append((bounds,layer))
    return source.get_size(),tuple(parts)


@lru_cache(maxsize=40)
def frames(name,size):
    if name.startswith('dimension_'):
        frame=pygame.Surface(size,pygame.SRCALPHA)
        base=fitted(name,(round(size[0]*.88),round(size[1]*.88)))
        frame.blit(base,base.get_rect(center=frame.get_rect().center))
        return (frame,)
    (sw,sh),parts=source_parts(name)
    ratio=min(size[0]/sw,size[1]/sh)*.88
    fitted_size=(max(1,round(sw*ratio)),max(1,round(sh*ratio)))
    prepared=[(bounds,pygame.transform.smoothscale(layer,fitted_size)) for bounds,layer in parts]
    result=[]
    for i in range(48):
        phase=i/48*math.tau;drift=math.sin(phase)
        frame=pygame.Surface(size,pygame.SRCALPHA)
        for bounds,source in prepared:
            layer=source.copy();dx=0;alpha=255
            if name=='clouds':
                back=bounds.centery<sh*.46
                dx=round(math.sin(phase+(0 if back else 1.1))*size[0]*(.05 if back else .035))
            elif bounds.height>sh*.3 and bounds.centery>sh*.5:
                alpha=round(205+50*drift*(1 if bounds.centerx<sw*.5 else -1))
            elif bounds.centery>sh*.85:
                dx=round(drift*size[0]*.035);alpha=round(160+35*drift)
            elif bounds.bottom<sh*.27:
                dx=round(drift*size[0]*.03)
            layer.set_alpha(alpha)
            frame.blit(layer,layer.get_rect(center=(size[0]//2+dx,size[1]//2)))
        result.append(frame)
    return tuple(result)


def draw(surface,name,rect,phase=0):
    rect=pygame.Rect(rect)
    if not phase:
        base=fitted(name,(max(1,round(rect.width*.88)),max(1,round(rect.height*.88))))
        surface.blit(base,base.get_rect(center=rect.center));return
    sequence=frames(name,rect.size)
    surface.blit(sequence[int((phase%6)/6*len(sequence))],rect)

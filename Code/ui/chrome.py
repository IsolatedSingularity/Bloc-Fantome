"""Native-size matte chrome. World textures never enter UI surfaces."""
import pygame

TEXT = (235, 237, 230)
MUTED = (163, 178, 178)
ACCENT = (208, 194, 153)
SURFACE = (19, 28, 31)
CONTROL = (32, 43, 46)
HOVER = (50, 64, 66)
SELECTED = (43, 54, 56)
FOCUS = (174, 208, 215)
ERROR = (245, 174, 150)
RADIUS = 7
GAP = 8
MARGIN = 24


def panel(screen, rect, assets=None, accent=None, alpha=246):
    rect = pygame.Rect(rect)
    if rect.width <= 0 or rect.height <= 0: return
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (*SURFACE, alpha), layer.get_rect(), border_radius=RADIUS)
    screen.blit(layer, rect)


def ellipsize(text, font, width):
    text = str(text)
    if font.size(text)[0] <= width: return text
    while text and font.size(text + '…')[0] > width: text = text[:-1]
    return text + '…' if text else ''


def button(screen, rect, text, font, hovered=False, selected=False,
           enabled=True, focused=False, quiet=False):
    rect = pygame.Rect(rect)
    if not quiet or hovered or selected:
        pygame.draw.rect(screen, HOVER if hovered and enabled else SELECTED if selected else CONTROL,
                         rect, border_radius=4)
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

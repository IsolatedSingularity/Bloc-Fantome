"""Shared Minecraft panel and button geometry, rendered at native resolution."""
import pygame

TEXT = (238, 238, 230)
MUTED = (184, 184, 174)
ACCENT = (177, 205, 142)


def button_surface(texture, size):
    """Keep the two-pixel texture edges intact on short and square controls."""
    width, height = size
    result = pygame.Surface(size, pygame.SRCALPHA)
    sw, sh = texture.get_size()
    border = min(2, sw // 3, sh // 3, width // 3, height // 3)
    if not border:
        return pygame.transform.scale(texture, size)
    xs, ys = (0, border, sw-border, sw), (0, border, sh-border, sh)
    dx, dy = (0, border, width-border, width), (0, border, height-border, height)
    for row in range(3):
        for col in range(3):
            source = texture.subsurface((xs[col], ys[row], xs[col+1]-xs[col], ys[row+1]-ys[row]))
            result.blit(pygame.transform.scale(source, (dx[col+1]-dx[col], dy[row+1]-dy[row])), (dx[col], dy[row]))
    return result


def panel(screen, rect, assets=None, accent=None):
    rect = pygame.Rect(rect)
    texture = getattr(assets, 'backgroundTile', None)
    cache = getattr(assets, '_chromePanels', {}) if assets else {}
    key = (rect.size, id(texture))
    surface = cache.get(key)
    if surface is None:
        surface = pygame.Surface(rect.size)
        surface.fill((43, 43, 43))
        if texture:
            tile = texture.copy()
            tile.fill((75, 75, 75), special_flags=pygame.BLEND_RGB_MULT)
            for y in range(0, rect.height, tile.get_height()):
                for x in range(0, rect.width, tile.get_width()):
                    surface.blit(tile, (x, y))
        if assets:
            if len(cache) >= 24: cache.clear()
            cache[key] = surface
            assets._chromePanels = cache
    screen.blit(surface, rect)
    pygame.draw.rect(screen, (15, 15, 15), rect, 2)
    inner = rect.inflate(-4, -4)
    pygame.draw.line(screen, (153, 153, 153), inner.topleft, (inner.right-1, inner.top), 2)
    pygame.draw.line(screen, (153, 153, 153), inner.topleft, (inner.left, inner.bottom-1), 2)
    pygame.draw.line(screen, (30, 30, 30), (inner.left, inner.bottom-1), (inner.right-1, inner.bottom-1), 2)
    pygame.draw.line(screen, (30, 30, 30), (inner.right-1, inner.top), (inner.right-1, inner.bottom-1), 2)
    if accent:
        pygame.draw.line(screen, accent, (rect.left+10, rect.top+7), (rect.right-11, rect.top+7), 2)


def wrapped(screen, text, font, rect, color=TEXT):
    """Wrap native-size text within a measured area."""
    rect = pygame.Rect(rect)
    y = rect.top
    line = ''
    for word in text.split():
        trial = (line+' '+word).strip()
        if line and font.size(trial)[0] > rect.width:
            if y+font.get_height() > rect.bottom: return y
            screen.blit(font.render(line, True, color), (rect.x, y))
            y += font.get_linesize()+3
            line = word
        else:
            line = trial
    if line and y+font.get_height() <= rect.bottom:
        screen.blit(font.render(line, True, color), (rect.x, y))
        y += font.get_linesize()+3
    return y


def speaker(screen, rect, muted=False):
    """A pixel speaker icon independent of the font's symbol coverage."""
    x,y=rect.center
    color=(180,180,180)
    pygame.draw.rect(screen,color,(x-8,y-3,5,7))
    pygame.draw.polygon(screen,color,((x-3,y-3),(x+3,y-7),(x+3,y+7),(x-3,y+4)))
    if muted:pygame.draw.line(screen,(225,100,90),(x-8,y-8),(x+9,y+8),2)
    else:
        pygame.draw.lines(screen,color,False,((x+6,y-5),(x+9,y),(x+6,y+5)),2)


def heading(screen,rect,text,assets,font):
    """Use the editor's raised section artwork and native heading font everywhere."""
    assets.drawButton(screen,pygame.Rect(rect),text,font,False,False,letterSpacing=1)

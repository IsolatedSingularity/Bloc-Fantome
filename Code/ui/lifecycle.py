"""Quiet lifecycle motion, measured in elapsed time rather than frames."""
import math
from pathlib import Path
import random
import pygame
from ui.fonts import load_ui_font


def jump_height(seconds, index):
    """Rise, hang, land and settle completely before the next block moves."""
    t = (seconds % 2.7) - index * .9
    if not 0 < t < .76:
        return 0.0
    if t < .28:
        return 13 * (1 - (1 - t / .28) ** 3)
    if t < .38:
        return 13.0
    if t < .64:
        return 13 * (1 - ((t - .38) / .26) ** 2)
    return -1.2 * math.sin(math.pi * (t - .64) / .12)


def assembly(screen, center, seconds, reduced=False, closing=False, opacity=1):
    for i in range(3):
        # Outro runs once, right to left, at a slower and lower amplitude.
        lift=0 if reduced else round(jump_height(min(seconds*.97,2.69),2-i)*.65 if closing else jump_height(seconds,i))
        x=center[0]+(i-1)*18;y=center[1]-lift
        color=tuple(round(v*opacity) for v in (177,204,205))
        pygame.draw.polygon(screen,color,((x-6,y),(x,y-3),(x+6,y),(x,y+3)))
        pygame.draw.lines(screen,color,False,((x-6,y+1),(x-6,y+6),(x,y+9),(x+6,y+6),(x+6,y+1)),1)
        pygame.draw.line(screen,color,(x,y+3),(x,y+9),1)


FAREWELLS = (
    'Leave a little light on.',
    'The moon will keep watch.',
    'Your next idea can wait until morning.',
    'A quiet pause between worlds.',
    'Even blocks need a little rest.',
    'See you beyond the next clearing.',
    'The fireflies have it from here.',
    'Until the next small adventure.',
)


def night_art_path():
    return Path(__file__).with_name('art') / 'goodbye-night.png'


def cover_rect(source_size, target_size):
    """Cover, protecting the moon and both characters in the right-hand clearing."""
    sw, sh = source_size
    w, h = target_size
    scale = max(w / sw, h / sh)
    width, height = math.ceil(sw * scale), math.ceil(sh * scale)
    # Focal point balances moon (61%, 19%) and figures (69-77%, 63-80%).
    x = max(w-width, min(0, round(w*.70-width*.70)))
    y = max(h-height, min(0, round(h*.47-height*.47)))
    return pygame.Rect(x, y, width, height)


class GoodbyeScreen:
    duration_ms = 3000
    fade_ms = 350

    def __init__(self, screen, reduced=False, phrase=None):
        self.screen = screen
        self.reduced = reduced
        self.phrase = phrase or random.choice(FAREWELLS)
        self.artwork = pygame.image.load(str(night_art_path())).convert()
        self._size = None
        self._prepare()

    def _prepare(self):
        w, h = self.screen.get_size()
        self._size = (w, h)
        self.crop = cover_rect(self.artwork.get_size(), self._size)
        self.background = pygame.Surface(self._size)
        self.background.blit(pygame.transform.smoothscale(self.artwork, self.crop.size), self.crop)
        # Soft lower veil, with no strip or bezel.
        veil = pygame.Surface(self._size, pygame.SRCALPHA)
        for y in range(h):
            alpha = round(100 * max(0, (y/h-.62)/.38) ** 1.4)
            pygame.draw.line(veil, (4,12,23,alpha), (0,y), (w,y))
        self.background.blit(veil, (0,0))
        self.title = load_ui_font(max(44,min(68,round(h*.070)))).render('Goodbye', True, (236,240,242))
        self.message = load_ui_font(max(15,min(21,round(h*.022)))).render(self.phrase, True, (211,226,233))
        self.shade = pygame.Surface(self._size)
        self.shade.fill((4,12,23))

    @staticmethod
    def skip_requested(events):
        return any(e.type in (pygame.QUIT,pygame.MOUSEBUTTONDOWN,pygame.KEYDOWN) for e in events)

    def render(self, elapsed):
        if self.screen.get_size() != self._size:
            self._prepare()
        screen = self.screen
        w, h = self._size
        screen.set_clip(None)
        screen.blit(self.background, (0,0))
        arrival = min(1, max(0, elapsed / 400))
        lift = 0 if self.reduced else round(5 * (1-arrival) ** 3)
        center = (w//2, round(h*.78)+lift)
        message_y=center[1]+self.title.get_height()//2+self.message.get_height()//2+10
        for text,y in ((self.title,center[1]),(self.message,message_y)):
            screen.blit(text,text.get_rect(center=(center[0],y)))
        assembly(screen,(center[0],center[1]-self.title.get_height()//2-25),
                 elapsed/1000,self.reduced,closing=True)
        if not self.reduced:
            fade = min(1,.55+.45*arrival,max(0,(self.duration_ms-elapsed)/self.fade_ms))
            self.shade.set_alpha(round(255*(1-fade)))
            screen.blit(self.shade,(0,0))

"""Quiet lifecycle motion, measured in elapsed time rather than frames."""
import math
from pathlib import Path
import random
import pygame
from ui.fonts import load_ui_font


def block_pose(seconds, index):
    """Ballistic lift/contact, followed by a finite damped spring response.

    Height and velocity meet at the apex. Contact transfers downward velocity
    into compression; the exponential envelope dissipates it before the next
    block starts. The sequence repeats only after all three have rested.
    """
    t = seconds % 3.6 - index * 1.02
    if not 0 < t < .94:
        return 0., 1., 0.
    if t < .33:
        q=t/.33
        return 15*(2*q-q*q), 1., -.035*q
    if t < .41:
        return 15., 1., -.035
    if t < .66:
        q=(t-.41)/.25
        return 15*(1-q*q), 1., -.035*(1-q)
    age=t-.66
    response=math.exp(-18*age)*math.sin(39*age)
    # Smoothly truncate the imperceptible tail, including its derivative.
    tail=min(1.,max(0.,(.94-t)/.07));tail=tail*tail*(3-2*tail)
    return -1.6*response*tail, 1-.18*response*tail, .065*response*tail


def jump_height(seconds, index):
    return block_pose(seconds,index)[0]


def assembly(screen, center, seconds, reduced=False, closing=False, opacity=1):
    # Retiming only the decoration leaves loading, audio and outro deadlines alone.
    seconds *= 1.06
    for i in range(3):
        # Outro runs once, right to left, settling before the closing fade.
        lift,stretch,angle=(0.,1.,0.) if reduced else block_pose(min(seconds*1.14,3.59),2-i) if closing else block_pose(seconds,i)
        if closing:lift*=.65;stretch=1+(stretch-1)*.65;angle*=.65
        x=center[0]+(i-1)*18;y=center[1]-lift
        color=tuple(round(v*opacity) for v in (177,204,205))
        def point(px,py):
            px*=1.239/stretch;py=(py-9)*1.239*stretch
            return round(x+px*math.cos(angle)-py*math.sin(angle)),round(y+10.62+px*math.sin(angle)+py*math.cos(angle))
        pygame.draw.polygon(screen,color,[point(*p) for p in ((-6,0),(0,-3),(6,0),(0,3))])
        pygame.draw.lines(screen,color,False,[point(*p) for p in ((-6,1),(-6,6),(0,9),(6,6),(6,1))],1)
        pygame.draw.line(screen,color,point(0,3),point(0,9),1)


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

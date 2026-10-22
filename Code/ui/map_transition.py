"""Brief input-safe map cover/reveal using the accepted editor chrome."""
import pygame
from ui import chrome
from ui.fonts import load_ui_font


class MapTransition:
    def __init__(self, screen, reduced_motion=False):
        self.started = pygame.time.get_ticks()
        self.reduced_motion = reduced_motion
        self.ready = False
        self.background = screen.copy()
        self.font = load_ui_font(24)
        self.small = load_ui_font(14)
        self.layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

    @property
    def covered(self):
        return pygame.time.get_ticks()-self.started >= (0 if self.reduced_motion else 120)

    def reveal(self):
        self.ready=True;self.started=pygame.time.get_ticks()

    @property
    def finished(self):
        return self.ready and pygame.time.get_ticks()-self.started >= (0 if self.reduced_motion else 180)

    def render(self, screen):
        age=pygame.time.get_ticks()-self.started
        if not self.ready:screen.blit(self.background,(0,0))
        u=max(0,min(1,age/(180 if self.ready else 120)))
        alpha=(1-u if self.ready else u*u*(3-2*u))
        if self.reduced_motion:alpha=0 if self.ready else 1
        if self.layer.get_size()!=screen.get_size():self.layer=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
        self.layer.fill((*chrome.SURFACE,round(alpha*255)))
        if not self.ready:
            text=self.font.render('World Map',True,chrome.TEXT);text.set_alpha(round(alpha*255))
            self.layer.blit(text,text.get_rect(center=screen.get_rect().center))
            hint=self.small.render('Esc to cancel',True,chrome.MUTED);hint.set_alpha(round(alpha*255))
            self.layer.blit(hint,hint.get_rect(center=(screen.get_width()//2,screen.get_height()//2+32)))
        screen.blit(self.layer,(0,0))

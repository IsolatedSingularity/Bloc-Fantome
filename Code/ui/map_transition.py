"""A reversible, real-time cartographic fold over the preserved editor."""
import math
import pygame
from ui import chrome
from ui.fonts import load_ui_font


class MapTransition:
    def __init__(self, screen, reduced_motion=False):
        self.started = pygame.time.get_ticks()
        self.ready = False
        self.future = None
        self.reduced_motion = reduced_motion
        self.background = screen.copy()
        self.font = load_ui_font(24)
        self.small = load_ui_font(14)
        self.paper = pygame.Surface(screen.get_size())
        self.paper.fill((20, 33, 43))
        w, h = screen.get_size()
        # Fixed contours, not a pulsing spinner. Fold edges establish map space.
        for ring in range(9):
            points = []
            for step in range(101):
                angle = step * math.tau / 100
                radius = 35 + ring * 29 + 8 * math.sin(angle * 3 + ring * .3)
                points.append((w*.5 + math.cos(angle)*radius*1.7,
                               h*.5 + math.sin(angle)*radius))
            pygame.draw.lines(self.paper, (38, 60, 70), True, points, 1)
        for x in (w//4, w//2, 3*w//4):
            pygame.draw.line(self.paper, (47, 65, 75), (x, 0), (x, h))
        # Quiet marginal cartography, drawn once; reveal timing stays unchanged.
        ink=(94,119,131)
        cx,cy=56,h-75
        pygame.draw.lines(self.paper,ink,False,((cx-9,cy+8),(cx,cy-18),(cx+9,cy+8),(cx,cy+2),(cx-9,cy+8)),1)
        self.paper.blit(self.small.render('N',True,ink),(cx-5,cy-40))
        pygame.draw.line(self.paper,ink,(w-148,h-50),(w-48,h-50))
        for x in range(w-148,w-47,25):pygame.draw.line(self.paper,ink,(x,h-54),(x,h-46))
        for dx,dy in ((-29,8),(-9,-12),(16,-3),(32,-21)):
            pygame.draw.circle(self.paper,ink,(w-93+dx,65+dy),2)
        pygame.draw.lines(self.paper,(46,68,81),False,((w-122,73),(w-102,53),(w-77,62),(w-61,44)),1)
        title = self.font.render('World Map', True, chrome.TEXT)
        hint = self.small.render('Esc to cancel', True, chrome.MUTED)
        self.paper.blit(title, title.get_rect(center=(w//2, h//2-12)))
        self.paper.blit(hint, hint.get_rect(center=(w//2, h//2+22)))

    @property
    def covered(self):
        return pygame.time.get_ticks()-self.started >= (0 if self.reduced_motion else 220)

    def reveal(self):
        self.ready = True
        self.started = pygame.time.get_ticks()

    @property
    def finished(self):
        return self.ready and pygame.time.get_ticks()-self.started >= (0 if self.reduced_motion else 320)

    def render(self, screen):
        w, h = screen.get_size()
        age = pygame.time.get_ticks()-self.started
        u = min(1., age/(320 if self.ready else 220))
        u = u*u*(3-2*u)
        if self.reduced_motion:
            u = 1.
        if not self.ready:
            screen.blit(self.background, (0, 0))
            rect = pygame.Rect(0, 0, max(1, round(w*u)), h)
            rect.center = screen.get_rect().center
            screen.blit(self.paper, rect, rect)
            pygame.draw.line(screen, chrome.ACCENT, rect.topleft, rect.bottomleft, 1)
            pygame.draw.line(screen, chrome.ACCENT, rect.topright, rect.bottomright, 1)
        else:
            # Reveal the already prepared map outward from the central fold.
            edge = round(w*(1-u)/2)
            if edge:
                screen.blit(self.paper, (0, 0), (0, 0, edge, h))
                screen.blit(self.paper, (w-edge, 0), (w-edge, 0, edge, h))
                pygame.draw.line(screen, chrome.ACCENT, (edge, 0), (edge, h), 1)
                pygame.draw.line(screen, chrome.ACCENT, (w-edge, 0), (w-edge, h), 1)

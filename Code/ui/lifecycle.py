"""Small original assembling/disassembling forms, independent from loading work."""
import pygame
from ui.fonts import load_ui_font


def assembly(screen, center, seconds, reduced=False, closing=False, opacity=1):
    for i in range(3):
        progress=1 if reduced else min(1,max(0,((seconds%3.2)-i*.22)/.65))
        if closing and not reduced:progress=1-min(1,max(0,(seconds-i*.16)/1.35))
        lift=0 if reduced else round((1-progress)*12)
        x=center[0]+(i-1)*16;y=center[1]-lift
        color=tuple(round(v*opacity*(.35+.65*progress)) for v in (177,204,205))
        pygame.draw.polygon(screen,color,((x-6,y),(x,y-3),(x+6,y),(x,y+3)))
        pygame.draw.lines(screen,color,False,((x-6,y+1),(x-6,y+6),(x,y+9),(x+6,y+6),(x+6,y+1)),1)
        pygame.draw.line(screen,color,(x,y+3),(x,y+9),1)


class GoodbyeScreen:
    duration_ms=1800
    fade_ms=300

    def __init__(self, screen, reduced=False):
        self.screen=screen;self.reduced=reduced
        self.title=load_ui_font(30).render('Goodbye',True,(226,234,242))
        self.brand=load_ui_font(15).render('Bloc Fantôme',True,(150,174,192))
        self.hint=load_ui_font(13).render('Esc or click to close now',True,(135,153,174))

    @staticmethod
    def skip_requested(events):
        return any(e.type in (pygame.QUIT,pygame.MOUSEBUTTONDOWN) or
                   (e.type==pygame.KEYDOWN and e.key in (pygame.K_ESCAPE,pygame.K_RETURN,pygame.K_SPACE)) for e in events)

    def render(self, elapsed):
        screen=self.screen;w,h=screen.get_size();screen.fill((10,18,31))
        fade=1 if self.reduced else min(1,elapsed/160,max(0,(self.duration_ms-elapsed)/self.fade_ms))
        for text,y in ((self.title,h//2),(self.brand,h//2+38),(self.hint,h-36)):
            text.set_alpha(round(255*fade));screen.blit(text,text.get_rect(center=(w//2,y)))
        assembly(screen,(w//2,h//2-56),elapsed/1000,self.reduced,closing=True,opacity=fade)

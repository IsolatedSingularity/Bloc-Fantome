"""A reversible, real-time cartographic fold over the preserved editor."""
import math
import pygame
from ui import chrome
from ui.fonts import load_ui_font


class MapTransition:
    def __init__(self, screen, reduced_motion=False, *, closing=False):
        self.started = pygame.time.get_ticks()
        self.ready = False
        self.future = None
        self.reduced_motion = reduced_motion
        self.background = screen.copy()
        self.font = load_ui_font(24)
        self.small = load_ui_font(14)
        self.closing = closing
        self.paper = self._paper(screen.get_size())

    def _paper(self,size):
        w,h=size
        paper=pygame.Surface(size);paper.fill((20,33,43))
        faint=(31,48,59);ink=(70,94,108);light=(133,158,174)
        # Two asymmetric contour fields leave the central survey mark quiet.
        for cx,cy,stretch,phase in ((w*.12,h*.33,1.45,.6),(w*.88,h*.72,1.65,2.4)):
            for ring in range(13):
                points=[]
                for step in range(181):
                    angle=step*math.tau/180
                    r=32+ring*18+12*math.sin(angle*3+phase)+6*math.sin(angle*5+ring*.12)
                    points.append((cx+math.cos(angle)*r*stretch,cy+math.sin(angle)*r))
                pygame.draw.aalines(paper,faint,True,points)
        margin=max(24,round(min(w,h)*.065))
        frame=pygame.Rect(margin,margin,w-2*margin,h-2*margin)
        pygame.draw.rect(paper,(43,63,77),frame,1)
        for x in (frame.left,frame.right):
            for y in (frame.top,frame.bottom):
                sx=1 if x==frame.left else -1;sy=1 if y==frame.top else -1
                pygame.draw.lines(paper,ink,False,((x,y+sy*24),(x,y),(x+sx*24,y)))
        cx,cy=w//2,round(h*.43);radius=round(min(w,h)*.14)
        pygame.draw.circle(paper,ink,(cx,cy),radius,1)
        pygame.draw.circle(paper,(43,63,77),(cx,cy),radius+8,1)
        for i in range(64):
            angle=i*math.tau/64-math.pi/2
            outer=radius+8;inner=outer-(8 if i%8==0 else 3)
            pygame.draw.aaline(paper,ink,(cx+math.cos(angle)*inner,cy+math.sin(angle)*inner),
                               (cx+math.cos(angle)*outer,cy+math.sin(angle)*outer))
        # Slightly turned compass rose, not a continuously spinning loader.
        for i in range(8):
            angle=i*math.tau/8-math.pi/2-.08
            tip=(cx+math.cos(angle)*radius*.82,cy+math.sin(angle)*radius*.82)
            a=(cx+math.cos(angle+.5)*radius*.17,cy+math.sin(angle+.5)*radius*.17)
            b=(cx+math.cos(angle-.5)*radius*.17,cy+math.sin(angle-.5)*radius*.17)
            pygame.draw.polygon(paper,light if i%2==0 else ink,((cx,cy),a,tip))
            pygame.draw.aalines(paper,ink,True,((cx,cy),b,tip))
        for label,dx,dy in (('N',0,-1),('E',1,0),('S',0,1),('W',-1,0)):
            text=self.small.render(label,True,light)
            paper.blit(text,text.get_rect(center=(cx+dx*(radius+28),cy+dy*(radius+28))))
        title=self.font.render('World Map',True,chrome.TEXT)
        paper.blit(title,title.get_rect(center=(cx,cy+radius+74)))
        if not self.closing:
            hint=self.small.render('Esc to cancel',True,chrome.MUTED)
            paper.blit(hint,hint.get_rect(center=(cx,cy+radius+110)))
        # Survey scale in the lower margin, balanced with the central fold.
        for x in range(cx-60,cx+61,20):pygame.draw.line(paper,ink,(x,h-margin-21),(x,h-margin-15))
        pygame.draw.line(paper,ink,(cx-60,h-margin-18),(cx+60,h-margin-18))
        return paper

    @property
    def covered(self):
        return pygame.time.get_ticks()-self.started >= (0 if self.reduced_motion else (320 if self.closing else 220))

    def reveal(self):
        self.ready = True
        self.started = pygame.time.get_ticks()

    @property
    def finished(self):
        return self.ready and pygame.time.get_ticks()-self.started >= (0 if self.reduced_motion else (220 if self.closing else 320))

    def render(self, screen):
        w, h = screen.get_size()
        if self.paper.get_size()!=(w,h):
            self.paper=self._paper((w,h))
            # Resize only the captured scene; text is rerasterized natively above.
            self.background=pygame.transform.scale(self.background,(w,h))
        age = pygame.time.get_ticks()-self.started
        duration=(220 if self.closing else 320) if self.ready else (320 if self.closing else 220)
        u=min(1.,max(0.,age/duration));u=u*u*(3-2*u)
        if self.reduced_motion:u=1.
        if not self.ready:screen.blit(self.background,(0,0))
        # Exit is the temporal reverse: cover from margins, then fold inward.
        center_panel = self.ready if self.closing else not self.ready
        amount=(1-u if self.ready else u)
        if center_panel:
            width=round(w*amount)
            if width:
                rect=pygame.Rect((w-width)//2,0,width,h)
                screen.blit(self.paper,rect,rect)
                pygame.draw.line(screen,chrome.ACCENT,rect.topleft,rect.bottomleft)
                pygame.draw.line(screen,chrome.ACCENT,rect.topright,rect.bottomright)
        else:
            edge=round(w*amount/2)
            if edge:
                screen.blit(self.paper,(0,0),(0,0,edge,h))
                screen.blit(self.paper,(w-edge,0),(w-edge,0,edge,h))
                pygame.draw.line(screen,chrome.ACCENT,(edge,0),(edge,h))
                pygame.draw.line(screen,chrome.ACCENT,(w-edge,0),(w-edge,h))

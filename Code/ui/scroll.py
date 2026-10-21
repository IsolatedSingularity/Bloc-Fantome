"""Shared precise-wheel motion with bounded, time-based deceleration."""
import math
import pygame


class SmoothScroll:
    def __init__(self):
        self.position=0.0
        self.target=0.0
        self.last=pygame.time.get_ticks()/1000

    def reset(self, position=0):
        self.position=self.target=float(position)
        self.last=pygame.time.get_ticks()/1000

    def wheel(self,event,maximum,step=60):
        delta=float(getattr(event,'precise_y',event.y))
        self.target=max(0,min(maximum,self.target-delta*step))

    def update(self,maximum,reduced=False):
        now=pygame.time.get_ticks()/1000
        dt=max(0,min(.1,now-self.last));self.last=now
        return self.advance(maximum,dt,reduced)

    def advance(self,maximum,dt,reduced=False):
        self.target=max(0,min(maximum,self.target))
        self.position=max(0,min(maximum,self.position))
        self.position=self.target if reduced else self.position+(self.target-self.position)*(1-math.exp(-18*dt))
        if abs(self.target-self.position)<.1:self.position=self.target
        return round(self.position)


def for_field(owner,field):
    name='_smooth_'+field
    scroll=getattr(owner,name,None)
    if scroll is None:
        scroll=SmoothScroll();scroll.reset(getattr(owner,field,0));setattr(owner,name,scroll)
    return scroll


def update_field(owner,field,maximum,reduced=False):
    scroll=for_field(owner,field)
    value=scroll.update(maximum,reduced)
    setattr(owner,field,value)
    return value

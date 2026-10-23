"""SDL-owned native dragging/resizing with a quiet client-area title strip.

No mouse-position drag loop and no renderer replacement. Unsupported drivers
retain their native frame. Keep the C callback alive as long as the SDL window.
"""
import ctypes
import os
from pathlib import Path
import pygame
from ui.fonts import load_ui_font

HEIGHT = 28
BUTTON = 42
_live = []


def hit_region(x, y, width, height, fullscreen=False):
    """SDL_HitTestResult: normal, draggable, then clockwise resize corners."""
    if fullscreen:return 0
    left=x<6;right=x>=width-6;top=y<6;bottom=y>=height-6
    if top:return 2 if left else 4 if right else 3
    if bottom:return 8 if left else 6 if right else 7
    if left:return 9
    if right:return 5
    return 1 if y<HEIGHT and x<width-3*BUTTON else 0


class WindowChrome:
    def __init__(self):
        self.enabled=False;self.fullscreen=False;self.focus=None;self.pressed=None
        self.width,self.height=pygame.display.get_window_size()
        self.font=load_ui_font(12)
        if pygame.display.get_driver()!='windows' or os.environ.get('BLOC_NATIVE_FRAME')=='1':return
        try:
            from pygame._sdl2.video import Window
            self.window=Window.from_display_module()
            dll=Path(pygame.__file__).parent/'SDL2.dll'
            self.sdl=ctypes.CDLL(str(dll))
            self.sdl.SDL_GetWindowFromID.argtypes=[ctypes.c_uint32]
            self.sdl.SDL_GetWindowFromID.restype=ctypes.c_void_p
            self.pointer=self.sdl.SDL_GetWindowFromID(self.window.id)
            class Point(ctypes.Structure):
                _fields_=[('x',ctypes.c_int),('y',ctypes.c_int)]
            callback=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.POINTER(Point),ctypes.c_void_p)
            self.callback=callback(lambda window,p,data:hit_region(p.contents.x,p.contents.y,self.width,self.height,self.fullscreen))
            self.sdl.SDL_SetWindowHitTest.argtypes=[ctypes.c_void_p,callback,ctypes.c_void_p]
            self.sdl.SDL_SetWindowHitTest.restype=ctypes.c_int
            if self.sdl.SDL_SetWindowHitTest(self.pointer,self.callback,None)!=0:return
            self.window.borderless=True
            self.enabled=True
            _live.append(self)
        except (OSError,AttributeError,pygame.error):
            if hasattr(self,'window'):self.window.borderless=False

    def sync(self,fullscreen=False):
        self.width,self.height=pygame.display.get_window_size();self.fullscreen=fullscreen
        if self.enabled:
            from pygame._sdl2.video import Window
            self.window=Window.from_display_module()
            self.pointer=self.sdl.SDL_GetWindowFromID(self.window.id)
            if self.sdl.SDL_SetWindowHitTest(self.pointer,self.callback,None)!=0:
                self.window.borderless=False;self.enabled=False;return
            self.window.borderless=True

    def rects(self):
        return [pygame.Rect(self.width-(3-i)*BUTTON,0,BUTTON,HEIGHT) for i in range(3)]

    def handle(self,event,app):
        if not self.enabled:return False
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_F10:
                self.focus=0 if self.focus is None else None;return True
            if self.focus is not None:
                if event.key==pygame.K_ESCAPE:self.focus=None
                elif event.key in (pygame.K_TAB,pygame.K_RIGHT):self.focus=(self.focus+1)%3
                elif event.key==pygame.K_LEFT:self.focus=(self.focus-1)%3
                elif event.key in (pygame.K_RETURN,pygame.K_SPACE):self.activate(self.focus,app)
                return True
        if event.type in (pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP) and event.button==1:
            hit=next((i for i,r in enumerate(self.rects()) if r.collidepoint(event.pos)),None)
            if event.type==pygame.MOUSEBUTTONDOWN:
                self.pressed=hit
                if event.pos[1]<HEIGHT:return True
            else:
                pressed=self.pressed;self.pressed=None
                if hit is not None and hit==pressed:self.activate(hit,app)
                if pressed is not None or event.pos[1]<HEIGHT:return True
        return event.type==pygame.MOUSEMOTION and event.pos[1]<HEIGHT

    def activate(self,index,app):
        self.focus=None
        if index==0:pygame.display.iconify()
        elif index==1:
            if app.openingScene is not None:app._setOpeningDisplay(not app._openingWindowed)
            else:app._toggleFullscreen()
        else:app._requestExit()

    def draw(self,screen):
        if not self.enabled:return
        self.width=screen.get_width()
        pygame.draw.rect(screen,(12,20,33),(0,0,self.width,HEIGHT))
        text=self.font.render('Bloc Fantôme',True,(163,180,201))
        screen.blit(text,(12,(HEIGHT-text.get_height())//2))
        mouse=pygame.mouse.get_pos()
        for i,r in enumerate(self.rects()):
            if r.collidepoint(mouse) or self.focus==i:
                pygame.draw.rect(screen,(81,45,57) if i==2 else (34,49,68),r)
            if self.focus==i:pygame.draw.rect(screen,(174,208,215),r.inflate(-4,-4),1)
            x,y=r.center;c=(205,216,230)
            if i==0:pygame.draw.line(screen,c,(x-5,y+3),(x+5,y+3))
            elif i==1:
                pygame.draw.rect(screen,c,(x-5,y-5,10,10),1)
                if self.fullscreen:pygame.draw.line(screen,c,(x-2,y-2),(x+4,y-2))
            else:
                pygame.draw.line(screen,c,(x-4,y-4),(x+4,y+4))
                pygame.draw.line(screen,c,(x+4,y-4),(x-4,y+4))

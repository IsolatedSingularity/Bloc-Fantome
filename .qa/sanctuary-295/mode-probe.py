import pygame,time,faulthandler
from pygame._sdl2 import Window
faulthandler.enable();pygame.init()
for size,flags in (((1200,800),pygame.RESIZABLE),((1200,800),pygame.OPENGL|pygame.DOUBLEBUF|pygame.RESIZABLE),((1200,800),pygame.RESIZABLE)):
 s=pygame.display.set_mode(size,flags)
 print('mode',flags,flush=True)
 for i in range(120):
  pygame.event.get()
  if not flags&pygame.OPENGL:s.fill((23,34,45))
  pygame.display.flip();pygame.time.wait(5)
pygame.quit();print('PASS')

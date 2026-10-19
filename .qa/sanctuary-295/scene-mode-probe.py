import pygame,sys,faulthandler
sys.path.insert(0,'Code')
from ui.opening_scene import OpeningScene
from ui.presentation_renderer import PresentationRenderer
from pygame._sdl2 import Window
faulthandler.enable();pygame.init();pygame.mixer.set_num_channels(32)
screen=pygame.display.set_mode((1200,800),pygame.RESIZABLE)
position=Window.from_display_module().position
scene=OpeningScene((1200,800),None)
screen=pygame.display.set_mode((1200,800),pygame.OPENGL|pygame.DOUBLEBUF|pygame.RESIZABLE)
Window.from_display_module().position=position
scene.gpu=PresentationRenderer()
for i in range(120):
 pygame.event.get();scene.update(.1);scene.render(screen);pygame.display.flip()
scene.close();scene=None
screen=pygame.display.set_mode((1200,800),pygame.RESIZABLE);Window.from_display_module().position=position
for i in range(120):
 pygame.event.get();screen.fill((20,30,40));pygame.display.flip();pygame.time.wait(5)
pygame.quit();print('PASS')

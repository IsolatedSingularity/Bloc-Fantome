import os,sys
os.environ['SDL_VIDEODRIVER']='dummy';sys.path.insert(0,'Code')
import pygame
from splash import SplashScreen
from runtime_paths import ICONS_DIR,FONTS_DIR,TEXTURES_DIR
pygame.init()
for w,h in [(960,640),(1200,800),(1920,1080)]:
 screen=pygame.display.set_mode((w,h));splash=SplashScreen(screen,pygame.time.Clock(),TEXTURES_DIR,FONTS_DIR,ICONS_DIR);splash.present()
 pygame.image.save(screen,f'.qa/maintenance/splash-{w}.png')
pygame.quit()

import os,sys
os.environ['SDL_VIDEODRIVER']='dummy';sys.path.insert(0,'Code')
import pygame
from splash import SplashScreen
from runtime_paths import TEXTURES_DIR,FONTS_DIR,ICONS_DIR
pygame.init()
for w,h in ((960,640),(1200,800),(1920,1080)):
 screen=pygame.display.set_mode((w,h));s=SplashScreen(screen,pygame.time.Clock(),TEXTURES_DIR,FONTS_DIR,ICONS_DIR)
 s.present();assert s.title.get_height()<=h*.30+1
 pygame.image.save(screen,f'.qa/visual-281-final/splash_{w}.png')

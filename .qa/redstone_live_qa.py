import os, sys, time, json, traceback
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'Code'))
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ.pop('SDL_VIDEODRIVER',None)
log=(root/'.qa/redstone-live.log').open('w',encoding='utf-8',buffering=1)
sys.stdout=sys.stderr=log
try:
 import pygame
 import blocFantome as m
 app=m.BlocFantome()
 app.autoSaveEnabled=False
 app.autoBackupEnabled=False
 print("DRIVER",pygame.display.get_driver(),pygame.display.get_wm_info(),flush=True)
 app._saveAppConfig=lambda:None
 assert app.assetManager.loadAllAssets()
 print("ENTERING",flush=True)
 app._toggleRedstoneLab()
 print("ENTERED",flush=True)
 pygame.display.set_caption('Bloc Fantome - Redstone QA')
 start=time.monotonic()
 while app.running and time.monotonic()-start<1200:
  app.clock.tick(60)
  app._handleEvents()
  app._update()
  app._render()
  pygame.display.flip()
 pygame.quit()
except Exception:
 traceback.print_exc()

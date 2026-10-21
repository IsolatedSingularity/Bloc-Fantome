"""Native rendering and state checks. Scripted actions, not OS input evidence."""
import os,sys,json,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
import pygame,blocFantome as b
from ui.fonts import set_text_scale,font_source
OUT=Path(__file__).resolve().parent/'native-final';OUT.mkdir(exist_ok=True)
b.DERIVED_WORLD_CACHE_DIR=str(OUT/'cache')
with patch.object(b,'APP_CONFIG_FILE',str(OUT/'config.json')),patch.object(b,'SAVES_DIR',str(OUT)),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'):
 app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
 try:
  assert app.assetManager.loadAllAssets();app.tutorialScreen.assetManager=app.assetManager
  app._createInitialFloor();app._fitWorldToViewport();app.workshop.visibility.pinned=True
  def capture(name):
   for _ in range(6):pygame.event.pump();app._update();app._render()
   pygame.image.save(app.screen,OUT/(name+'.png'))
  app._applyWindowSize(960,640);set_text_scale(1.5);app.workshop.text_scale=1.5
  app.tutorialScreen.visible=True;capture('tutorial-150');app.tutorialScreen.visible=False
  app._openWorldMap();capture('map-150');app._exitWorldMap()
  for x in range(3):app._placeBlockWithUndo(2+x,3,1,b.BlockType.COPPER_BLOCK)
  app.historyPanelOpen=True;capture('history-150');app.historyPanelOpen=False
  app.workshop.act('clear_world',app);capture('clear-confirm-150')
  app.workshop.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0),app)
  save=OUT/'roundtrip.json.gz';assert app._saveBuilding(filepath=str(save),silent=True)
  before_blocks=dict(app.world.blocks);app._placeBlockWithUndo(7,7,1,b.BlockType.DIAMOND_BLOCK)
  assert app._loadBuildingFromPath(str(save),silent=True)
  assert app.world.blocks==before_blocks
  set_text_scale(1);app.workshop.text_scale=1;app._applyWindowSize(1200,800)
  def anchor():return list(app.renderer._screenToWorldPoint(app.screen.get_width()/2,app.screen.get_height()/2,app.cameraFocusZ))
  initial=dict(zoom=app.zoomLevel,anchor=anchor());trips=[]
  for i in range(3):
   app._toggleFullscreen();capture('fullscreen' if i==0 else f'fullscreen-{i}')
   app._toggleFullscreen();capture('windowed-return' if i==0 else f'windowed-return-{i}')
   trips.append(dict(size=app.screen.get_size(),zoom=app.zoomLevel,anchor=anchor()))
  assert abs(app.zoomLevel-initial['zoom'])<.001
  assert max(abs(a-c) for a,c in zip(initial['anchor'],anchor()))<.03
  import ctypes
  report=dict(driver=pygame.display.get_driver(),dpi=ctypes.windll.user32.GetDpiForWindow(pygame.display.get_wm_info()['window']),font=str(font_source()),initial=initial,trips=trips,save_reopen_blocks=len(before_blocks),save_reopen_exact=True,input='Scripted application actions; not native keyboard acceptance')
  (OUT/'report.json').write_text(json.dumps(report,indent=2))
 finally:
  set_text_scale(1);app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()

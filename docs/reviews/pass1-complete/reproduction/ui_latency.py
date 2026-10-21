"""Source action-to-render latency; no display scanout/input-device claim."""
import os,sys,time,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame,blocFantome as b
OUT=Path(__file__).parent
with patch.object(b,'APP_CONFIG_FILE',str(OUT/'latency-config.json')),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'):
 app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
 try:
  app.assetManager.loadAllAssets();app._createInitialFloor();app._applyWindowSize(1920,1080)
  app._fitWorldToViewport();app.tooltipTimer=0;rows=[]
  for i in range(600):
   before=time.perf_counter();app.workshop.open_drawer(('build','tools','world','menu')[i%4],app)
   app.workshop.query=('copper','stairs','glass','')[i%4];app._render()
   rows.append((time.perf_counter()-before)*1000);pygame.event.pump()
  report=dict(driver=pygame.display.get_driver(),size=app.screen.get_size(),iterations=len(rows),p95=sorted(rows)[569],max=max(rows),samples_ms=rows,contract='Handler + production render + flip, scripted native window; not OS input-to-photon latency',ui_text_cache_entries=len(app.assetManager.uiTextCache))
  (OUT/'ui-latency.json').write_text(json.dumps(report,indent=2))
 finally:app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()

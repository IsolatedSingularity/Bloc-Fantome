import os,sys,time,json,cProfile,pstats
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';sys.path.insert(0,'Code')
import pygame
import blocFantome as m
app=m.BlocFantome();app.assetManager.loadAllAssets();app.autoSaveEnabled=False
app.tutorialScreen.onStepChange=app._onTutorialStepChange;app.tutorialScreen.onTutorialEnd=app._onTutorialEnd
app._preloadTutorialMusic();app._beginTutorial(advanced=False)
rows=[]
for i in range(4):
 app._handleZoom(.25,650,400)
 prof=cProfile.Profile();t=time.perf_counter();prof.enable();app.tutorialScreen.selectLesson(i);dispatch=time.perf_counter()-t
 frames=[];deadline=time.perf_counter()+90
 while time.perf_counter()<deadline:
  start=time.perf_counter();app._update();app._render();frames.append(1000*(time.perf_counter()-start))
  if app._pendingTourLoad is None and app._worldSurfaceBuild is None:break
  time.sleep(.002)
 prof.disable()
 row=dict(page=app.tutorialScreen.lesson['id'],dispatch_ms=dispatch*1000,ready_s=time.perf_counter()-t,max_frame_ms=max(frames),zoom=app.zoomLevel,offset=[app.renderer.offsetX,app.renderer.offsetY],cells=len(app.world.blocks),pending=app._pendingTourLoad is not None)
 rows.append(row);print(json.dumps(row),flush=True)
 pygame.image.save(app.screen,f'.qa/tutorial-294/{sys.argv[1]}-{i}.png')
 with open(f'.qa/tutorial-294/{sys.argv[1]}-{i}-profile.txt','w') as f:pstats.Stats(prof,stream=f).sort_stats('cumtime').print_stats(16)
Path(f'.qa/tutorial-294/{sys.argv[1]}.json').write_text(json.dumps(rows,indent=2))
app.worldLoadExecutor.shutdown(wait=True);pygame.quit()

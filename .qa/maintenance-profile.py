import os,sys,time,json,cProfile,pstats
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';sys.path.insert(0,'Code')
import pygame
from blocFantome import BlocFantome,WORLDS_DIR
from engine.world_catalog import WORLD_ENTRIES
out=Path('.qa/maintenance');out.mkdir(exist_ok=True)
app=BlocFantome();app.assetManager.loadAllAssets();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
rows=[]
for entry in (WORLD_ENTRIES[0],next(e for e in WORLD_ENTRIES if 'ocean' in e.scene_id)):
 prof=cProfile.Profile();prof.enable();t=time.perf_counter()
 dimension,bounds,metadata,snapshot,skipped=app._readBuildFile(os.path.join(WORLDS_DIR,entry.filename))
 staged=time.perf_counter()-t;t=time.perf_counter()
 app._applyStagedBuild(dimension,bounds,metadata,snapshot,entry.filename,True)
 applied=time.perf_counter()-t
 frames={}
 for name,action in [('initial',lambda:None),('rotate',lambda:app._rotateViewAndRecenter(1)),('zoom',lambda:app._handleZoom(.1,500,300)),('pan',lambda:setattr(app.renderer,'offsetX',app.renderer.offsetX+20))]:
  t=time.perf_counter();action();action_ms=(time.perf_counter()-t)*1000;samples=[]
  for _ in range(12):
   t=time.perf_counter();app._update();app._render();samples.append((time.perf_counter()-t)*1000)
  while app._worldSurfaceBuild is not None and len(samples)<1000:
   t=time.perf_counter();app._update();app._render();samples.append((time.perf_counter()-t)*1000)
  assert app._worldSurfaceBuild is None
  frames[name]={'action_ms':action_ms,'frames_ms':samples}
 prof.disable()
 with (out/(sys.argv[1]+'-'+entry.scene_id+'-profile.txt')).open('w') as f:pstats.Stats(prof,stream=f).sort_stats('cumtime').print_stats(40)
 row=dict(scene=entry.scene_id,cells=len(app.world.blocks),stage_s=staged,apply_s=applied,frames=frames);rows.append(row);print(json.dumps(row),flush=True)
 pygame.image.save(app.screen,str(out/(sys.argv[1]+'-'+entry.scene_id+'.png')))
(out/(sys.argv[1]+'-timing.json')).write_text(json.dumps(rows,indent=2))
app.worldLoadExecutor.shutdown(wait=True);pygame.quit()

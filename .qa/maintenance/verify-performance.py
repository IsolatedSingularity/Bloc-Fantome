import os,sys,time,ast,subprocess,json,types,hashlib
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';sys.path.insert(0,'Code')
import pygame
import blocFantome as module
import engine.world as wm
app=module.BlocFantome();app.assetManager.loadAllAssets();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
path=os.path.join(module.WORLDS_DIR,'nether_fortress_biomes_1161.json.gz')
d,b,m,s,k=app._readBuildFile(path);app._applyStagedBuild(d,b,m,s,path,True)
original=subprocess.check_output(['git','show','HEAD:Code/engine/world.py'],text=True)
klass=next(n for n in ast.parse(original).body if isinstance(n,ast.ClassDef) and n.name=='World')
method=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_surfaceViewsForPosition')
ns={};exec(compile(ast.Module(body=[method],type_ignores=[]),'<baseline-world>','exec'),vars(wm),ns)
optimized=app.world._surfaceViewsForPosition
app.world._surfaceViewsForPosition=types.MethodType(ns['_surfaceViewsForPosition'],app.world)
t=time.perf_counter();app.world._rebuildViewSurfaceIndex();before=time.perf_counter()-t
expected={r:set(p) for r,p in app.world.viewSurfacePositionsByView.items()}
app.world._surfaceViewsForPosition=optimized
t=time.perf_counter();app.world._rebuildViewSurfaceIndex();after=time.perf_counter()-t
assert expected==app.world.viewSurfacePositionsByView
app.worldCenteredRotation=True
views=[]
for rotation in range(4):
 if rotation:app._rotateViewAndRecenter(1)
 app._biomeViewSurfaces.clear();app._worldSurfaceCache=None;app._worldSurfaceCacheKey=None
 frames=[]
 while True:
  app.screen.fill((31,35,42));t=time.perf_counter();app._renderWorld();frames.append(1000*(time.perf_counter()-t))
  if app._worldSurfaceBuild is None:break
  assert len(frames)<1000
 pixels=pygame.image.tobytes(app.screen,'RGB')
 app._worldSurfaceCache=None;app._worldSurfaceCacheKey=None
 app.screen.fill((31,35,42));t=time.perf_counter();app._renderWorld();cached=1000*(time.perf_counter()-t)
 assert pixels==pygame.image.tobytes(app.screen,'RGB')
 views.append(dict(rotation=rotation,uncached_total_ms=sum(frames),uncached_peak_ms=max(frames),cached_ms=cached,pixel_equal=True))
 pygame.image.save(app.screen,f'.qa/maintenance/fortress-view-{rotation}.png')
report=dict(cells=len(app.world.blocks),visibility_before_s=before,visibility_after_s=after,visibility_exact=True,views=views)
Path('.qa/maintenance/isolated-performance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
app.worldLoadExecutor.shutdown(wait=True);pygame.quit()

"""Exact reference replay against the reviewed pre-optimization renderer."""
import os,sys,ast,subprocess,types,json,hashlib
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame,blocFantome as b
OUT=ROOT/'docs/reviews/owner-pass-ar/pixels';OUT.mkdir(parents=True,exist_ok=True)
source=subprocess.check_output(['git','show','c9573dcb:Code/blocFantome.py']).decode('utf-8')
cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='BlocFantome')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_renderWorld')
ns=dict(b.__dict__);exec(compile(ast.Module(body=[method],type_ignores=[]),'reviewed-renderer','exec'),ns)
with patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'),patch.object(b,'APP_CONFIG_FILE',str(OUT/'config.json')):
 app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False;app.assetManager.loadAllAssets()
 app._applyWindowSize(1200,800);current=app._renderWorld;old=types.MethodType(ns['_renderWorld'],app);rows=[]
 try:
  for scene in ('ocean_monument_1161','trial_chamber_121','village_plains_1161','ancient_city_121'):
   app._loadBuildingFromPath(str(ROOT/'Code/worlds'/f'{scene}.json.gz'),silent=True);app._fitWorldToViewport(False)
   for rotation in range(4):
    app.renderer.viewRotation=rotation;app._fitWorldToViewport(False)
    for name,fn in (('reviewed',old),('optimized',current)):
     app._biomeViewSurfaces.clear();app._invalidateViewCaches();app._worldTransitionKind=None
     fn();raw=pygame.image.tostring(app._worldSurfaceCache,'RGBA')
     if name=='reviewed':reference=raw
     else:
      equal=reference==raw;rows.append(dict(scene=scene,rotation=rotation,rgba_equal=equal,sha256=hashlib.sha256(raw).hexdigest()))
      assert equal,(scene,rotation)
    print(scene,rotation,'exact',flush=True)
  (OUT/'equivalence.json').write_text(json.dumps(rows,indent=2))
 finally:app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()

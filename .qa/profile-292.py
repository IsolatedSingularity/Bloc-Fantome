import os,sys,cProfile,pstats,time,gc
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';sys.path.insert(0,'Code')
from blocFantome import BlocFantome
app=BlocFantome();app.assetManager.loadAllAssets();app._beginTutorial(advanced=False)
for key in ('history','terrain','dimensions'):
 step=next(p for p in app.tutorialScreen.TUTORIAL_STEPS if p['id']==key)
 t=time.perf_counter();snapshot=app._stageTourScene(step);print('STAGED',key,round(time.perf_counter()-t,3),flush=True)
 prof=cProfile.Profile();prof.enable();app._applyTourScene(snapshot,step);app._render();prof.disable()
 print('APPLY',key,flush=True);pstats.Stats(prof).sort_stats('cumtime').print_stats(12)
app.worldLoadExecutor.shutdown(wait=True)

import os,sys,cProfile,pstats,time
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';sys.path.insert(0,'Code')
from blocFantome import BlocFantome
app=BlocFantome();app.assetManager.loadAllAssets();app._preloadTutorialMusic()
app._beginTutorial(advanced=False)
for key in ('biomes','dimensions','lighting'):
 i=next(i for i,p in enumerate(app.tutorialScreen.TUTORIAL_STEPS) if p['id']==key)
 app.tutorialScreen.currentStep=i;step=app.tutorialScreen.lesson;snapshot=app._stageTourScene(step)
 prof=cProfile.Profile();prof.enable();app._applyTourScene(snapshot,step);app._render();prof.disable()
 print('\nPROFILE',key,flush=True);pstats.Stats(prof).sort_stats('cumtime').print_stats(14)
app.worldLoadExecutor.shutdown(wait=True)

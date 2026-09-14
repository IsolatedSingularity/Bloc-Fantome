import os,sys,cProfile,pstats
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';sys.path.insert(0,'Code')
import pygame,blocFantome as m
app=m.BlocFantome();app.assetManager.loadAllAssets();app.tutorialScreen.visible=False
app._applyWindowSize(1920,1080);app._openBiomeScene('end_highlands');app.skyboxesEnabled=True;app.biomePanel.expanded=True
app.skyboxRenderer.update(400,'end');app.tooltipTimer=0
for _ in range(5):app._render()
p=cProfile.Profile();p.enable()
for _ in range(30):app._render()
p.disable();pstats.Stats(p).sort_stats('cumulative').print_stats(22)
app.worldLoadExecutor.shutdown(wait=True)

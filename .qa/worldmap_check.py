import os,sys,time
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,'Code')
import pygame
import blocFantome as m
app=m.BlocFantome();app.assetManager.loadAllAssets();app._openWorldMap()
out=Path('.qa/worldmap-current');out.mkdir(exist_ok=True)
for dimension,key in [('nether','bastion'),('nether','fortress'),('end','central'),('end','city')]:
 start=time.perf_counter();app._switchWorldMapHub(dimension)
 if app.worldMapScene.region_key!=key:app._handleWorldMapAction('region:'+key)
 app._render();pygame.image.save(app.screen,str(out/f'{key}.png'))
 print(key,app.zoomLevel,round(time.perf_counter()-start,2),flush=True)
app._exitWorldMap();pygame.quit()

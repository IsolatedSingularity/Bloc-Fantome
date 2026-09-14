import os,sys,time,json
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Code'))
import pygame
from blocFantome import BlocFantome
from engine.world_catalog import world_catalog
from runtime_paths import WORLDS_DIR
app=BlocFantome();assert app.assetManager.loadAllAssets()
app.tutorialScreen.visible=False
out=Path('Code/world_previews');out.mkdir(exist_ok=True)
for e in world_catalog(WORLDS_DIR):
    t=time.perf_counter()
    app._loadBuildingFromPath(str(Path(WORLDS_DIR)/e.filename),silent=True)
    app.showGrid=False;app.skyboxesEnabled=False;app.lightingEnabled=False
    app._fitWorldToViewport(notify=False)
    for _ in range(120):
        app._renderWorld()
        if app._worldSurfaceBuild is None:break
    surface=app._worldSurfaceCache
    if surface is None:
        app.screen.fill((0,0,0));app._renderWorld()
        surface=app.screen.subsurface((0,45,app._worldViewportRight(),app.screen.get_height()-125)).copy()
    box=surface.get_bounding_rect()
    if box.width and box.height:surface=surface.subsurface(box).copy()
    ratio=min(720/surface.get_width(),480/surface.get_height())
    image=pygame.transform.scale(surface,(max(1,round(surface.get_width()*ratio)),max(1,round(surface.get_height()*ratio))))
    pygame.image.save(image,str(out/(e.scene_id+'.png')))
    print(e.scene_id,len(app.world.blocks),round(time.perf_counter()-t,2),flush=True)
app.worldLoadExecutor.shutdown(wait=True);pygame.quit()

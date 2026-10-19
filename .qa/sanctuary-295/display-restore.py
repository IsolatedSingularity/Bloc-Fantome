import os,sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows'
from blocFantome import BlocFantome,BlockType,pygame
from pygame._sdl2 import Window
app=BlocFantome();assert app.assetManager.loadAllAssets()
app._createInitialFloor();app._placeBlockWithUndo(3,3,1,BlockType.DIAMOND_BLOCK)
world=dict(app.world.blocks);camera=(app.zoomLevel,app.renderer.offsetX,app.renderer.offsetY,app.renderer.viewRotation)
size=app.screen.get_size();position=app._displayWindow.position
app._openOpeningScene();assert app.openingScene.gpu
report={'fullscreen_size':app.screen.get_size(),'fullscreen_flags':app.screen.get_flags(),'caption':pygame.display.get_caption()[0]}
app.openingScene.update(4.5);app._render()
assert app.screen.get_flags() & pygame.NOFRAME
app._setOpeningDisplay(True);assert app.openingScene.gpu
assert pygame.display.get_window_size()==size
app.openingScene.update(0);app._render()
report['windowed_size']=pygame.display.get_window_size()
assert app.openingScene.size==size
app._setOpeningDisplay(False);assert app.openingScene.gpu
app._closeOpeningScene();app._handleEvents();app._render()
assert app.world.blocks==world
assert (app.zoomLevel,app.renderer.offsetX,app.renderer.offsetY,app.renderer.viewRotation)==camera
assert pygame.display.get_window_size()==size
assert app._displayWindow.position==position
assert app.undoManager.undo() is not None
assert app.world.getBlock(3,3,1)==BlockType.AIR
report['restored_size']=app.screen.get_size();report['world_camera_undo_restored']=True
(ROOT/'.qa/sanctuary-295/display-restore.json').write_text(json.dumps(report,indent=2))
app.worldLoadExecutor.shutdown(wait=True);pygame.quit();print(report)


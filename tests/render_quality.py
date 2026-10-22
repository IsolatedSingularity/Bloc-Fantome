"""Native window/fullscreen A/B at matched camera, source textures and lighting."""
import ctypes
import json
from pathlib import Path
import sys
from time import perf_counter
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Code'))
import pygame
import blocFantome as module
from engine import native_cube


def render(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    with patch.object(module,'APP_CONFIG_FILE',str(out/'isolated.json')),patch.object(module.BlocFantome,'_saveAppConfig'),patch.object(module.TutorialScreen,'_saveConfig'):
        app=module.BlocFantome();app.autoSaveEnabled=False
        rows=[]
        try:
            assert app.assetManager.loadAllAssets()
            app.world.resize(12,12,16,min_y=0,preserve=False)
            for x in range(10):
                for y in range(10):
                    height=1+(x//4 if y>4 else 0)
                    for z in range(height):app.world.setBlock(x,y,z,module.BlockType.GRASS if z==height-1 else module.BlockType.DIRT)
            for i,block in enumerate((module.BlockType.STONE,module.BlockType.BRICKS,module.BlockType.OAK_PLANKS,module.BlockType.GLASS,module.BlockType.OAK_STAIRS,module.BlockType.STONE_SLAB)):
                app.world.setBlock(2+i,2,1,block)
            app.tutorialScreen.visible=False;app.skyboxesEnabled=False;app.lightingEnabled=False
            app.workshop.visibility.pinned=True;app.showGrid=False
            def capture(name):
                app.assetManager.clearZoomCache();app._invalidateViewCaches()
                start=perf_counter();app._render();cold=(perf_counter()-start)*1000
                times=[]
                for _ in range(6):
                    start=perf_counter();app._render();times.append((perf_counter()-start)*1000)
                pygame.image.save(app.screen,str(out/(name+'.png')))
                rows.append(dict(name=name,size=app.screen.get_size(),window_size=pygame.display.get_window_size(),
                    fullscreen=app.fullscreen,flags=app.screen.get_flags(),zoom=app.zoomLevel,
                    os_dpi=ctypes.windll.user32.GetDpiForWindow(pygame.display.get_wm_info()['window']),
                    driver=pygame.display.get_driver(),cold_ms=cold,warm_ms=times))
            for fullscreen in (False,True):
                if fullscreen:app._toggleFullscreen()
                else:app._applyWindowSize(1200,800)
                for zoom in (1,2):
                    app.zoomLevel=zoom;app.renderer.setZoom(zoom)
                    cx,cy=app.renderer.worldToScreen(4.5,4.5,0)
                    app.renderer.offsetX+=app.screen.get_width()/2-cx
                    app.renderer.offsetY+=app.screen.get_height()*.48-cy
                    app.targetOffsetX=app.renderer.offsetX;app.targetOffsetY=app.renderer.offsetY
                    tag=('fullscreen' if fullscreen else 'window')+f'-zoom{zoom}'
                    with patch.object(native_cube,'enlarged',return_value=None):capture(tag+'-before')
                    capture(tag+'-after')
                if fullscreen:app._toggleFullscreen()
            # Three native-size crops distinguish nearest bitmap enlargement,
            # native projection and blanket smoothing (comparison only).
            app.zoomLevel=2
            sheet=pygame.Surface((960,460));sheet.fill((16,24,39))
            font=module.load_ui_font(16)
            for col,label in enumerate(('Previous bitmap enlargement','Native face projection','Bilinear enlargement (not shipped)')):
                sheet.blit(font.render(label,True,(230,236,245)),(col*320+8,12))
            textures=[]
            for row,block in enumerate((module.BlockType.GRASS,module.BlockType.STONE,module.BlockType.BRICKS)):
                sprite=app.assetManager.getBlockSprite(block);size=(128,140)
                variants=(pygame.transform.scale(sprite,size),native_cube.enlarged(sprite,size,32/70),pygame.transform.smoothscale(sprite,size))
                for col,image in enumerate(variants):sheet.blit(image,(col*320+96,row*140+36))
                definition=module.BLOCK_DEFINITIONS[block]
                textures.append(dict(block=block.name,source=definition.textureTop,
                                     size=app.assetManager.textures[definition.textureTop].get_size()))
            pygame.image.save(sheet,str(out/'sampling-comparison.png'))
            (out/'report.json').write_text(json.dumps(dict(rows=rows,textures=textures,
                native_cube_scope='Opaque registered editor cubes above 1x; other models and source-capture atlases unchanged'),indent=2),encoding='utf-8')
        finally:
            app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()


if __name__=='__main__':render(sys.argv[1])

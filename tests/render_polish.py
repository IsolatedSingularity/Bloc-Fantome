"""Only the requested editor UI matrix; no introductory cinematic rendering."""
from pathlib import Path
import json
import time
from unittest.mock import patch
import pygame
import blocFantome as module
from ui.fonts import set_text_scale
from ui.tool_icons import draw


def render(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    import runtime_paths
    with patch.object(module,'APP_CONFIG_FILE',str(output/'isolated.json')),patch.object(runtime_paths,'BASE_DIR',str(output)),patch.object(module.BlocFantome,'_saveAppConfig'),patch.object(module.TutorialScreen,'_saveConfig'):
        app=module.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        rows=[]
        try:
            assert app.assetManager.loadAllAssets();app._createInitialFloor()
            app.workshop.visibility.pinned=True
            assert app.skyboxesEnabled
            assert all(block==module.BlockType.GRASS for (x,y,z),block in app.world.blocks.items() if z==0)
            def capture(name):
                app.tooltipTimer=0
                deadline=time.perf_counter()+.24
                while time.perf_counter()<deadline:
                    app._update();app._render();pygame.event.pump();app.clock.tick(60)
                pygame.image.save(app.screen,str(output/(name+'.png')))
                dpi=None
                if pygame.display.get_driver()=='windows':
                    import ctypes
                    dpi=ctypes.windll.user32.GetDpiForWindow(pygame.display.get_wm_info()['window'])
                rows.append(dict(name=name,size=app.screen.get_size(),scale=app.workshop.text_scale,
                                 driver=pygame.display.get_driver(),os_dpi=dpi))
            for size in ((960,640),(1200,800),(1920,1080)):
                for scale in (1,1.25,1.5):
                    set_text_scale(scale);app.workshop.text_scale=scale;app._applyWindowSize(*size)
                    for tone,block in (('bright',module.BlockType.SMOOTH_QUARTZ),('dark',module.BlockType.OBSIDIAN)):
                        for pos in tuple(app.world.blocks):app.world.setBlock(*pos,block)
                        app.skyboxesEnabled=False;app.lightingEnabled=False;app._invalidateViewCaches();app._fitWorldToViewport()
                        tag=f'{size[0]}-{round(scale*100)}-{tone}'
                        app.workshop.page='menu';app.workshop.menu_group='File';app.workshop.menu_slots=False
                        capture('menu-'+tag)
                        app.workshop.menu_slots=True;capture('slots-'+tag)
                        app.workshop.menu_slots=False
                        for page in ('build','tools','world'):
                            app.workshop.page=page;capture(page+'-'+tag)
                        app.workshop.page='';app.settingsMenuOpen=True;capture('settings-'+tag);app.settingsMenuOpen=False
                        app._requestExit();capture('exit-'+tag);app._exitAction('stay')
                        app.tutorialScreen.visible=True;app.tutorialScreen.minimized=False
                        capture('tutorial-'+tag)
                        app.tutorialScreen.minimized=True;capture('tutorial-dock-'+tag)
                        app.tutorialScreen.visible=False;app.tutorialScreen.minimized=False
                        app.library.open(app);capture('library-home-'+tag)
                        app.library.change_view(app,'Worlds');capture('library-gallery-'+tag)
                        app.library.visible=False
                        app.workshop.page='';capture('hud-'+tag)
                    app.workshop.page='world';capture(f'world-{size[0]}-{round(scale*100)}');app.workshop.page=''
                    app.library.open(app,'Worlds');capture(f'library-{size[0]}-{round(scale*100)}');app.library.visible=False
            set_text_scale(1);app.workshop.text_scale=1;app._applyWindowSize(1200,800)
            from ui.lifecycle import GoodbyeScreen
            for size in ((960,640),(1200,800),(1920,1080)):
                for scale in (1,1.25,1.5):
                    set_text_scale(scale);app.workshop.text_scale=scale;app._applyWindowSize(*size)
                    view=GoodbyeScreen(app.screen,phrase='The fireflies have it from here.')
                    view.render(1000)
                    pygame.image.save(app.screen,str(output/f'goodbye-{size[0]}-{round(scale*100)}.png'))
            set_text_scale(1);app.workshop.text_scale=1;app._applyWindowSize(1200,800)
            app.workshop.page='menu'
            for group in ('Edit','View','More'):
                app.workshop.menu_group=group;capture('menu-'+group.lower())
            sheet=pygame.Surface((480,230));sheet.fill((16,24,39))
            font=module.load_ui_font(14)
            for row,size in enumerate((24,38,64)):
                sheet.blit(font.render(str(size)+' px',True,(230,236,245)),(10,row*76+24))
                for col,name in enumerate(('dimension_overworld','dimension_end','lighting','clouds')):
                    rect=pygame.Rect(90+col*96,row*76+6,size,size);draw(sheet,name,rect,(255,255,255),phase=1.5)
            pygame.image.save(sheet,str(output/'icons-native.png'))
            (output/'matrix.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        finally:
            app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);set_text_scale(1);pygame.quit()

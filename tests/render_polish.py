"""Only the requested editor UI matrix; no introductory cinematic rendering."""
from pathlib import Path
import json
from unittest.mock import patch
import pygame
import blocFantome as module
from ui.fonts import set_text_scale
from ui.tool_icons import draw


def render(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with patch.object(module,'APP_CONFIG_FILE',str(output/'isolated.json')),patch.object(module.BlocFantome,'_saveAppConfig'),patch.object(module.TutorialScreen,'_saveConfig'):
        app=module.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        rows=[]
        try:
            assert app.assetManager.loadAllAssets();app._createInitialFloor()
            app.workshop.visibility.pinned=True
            assert app.skyboxesEnabled
            assert all(block==module.BlockType.GRASS for (x,y,z),block in app.world.blocks.items() if z==0)
            def capture(name):
                app.tooltipTimer=0
                for _ in range(3):app._update();app._render();pygame.event.pump()
                pygame.image.save(app.screen,str(output/(name+'.png')))
                rows.append(dict(name=name,size=app.screen.get_size(),scale=app.workshop.text_scale))
            for size in ((960,640),(1200,800),(1920,1080)):
                for scale in (1,1.5):
                    set_text_scale(scale);app.workshop.text_scale=scale;app._applyWindowSize(*size)
                    for tone,block in (('bright',module.BlockType.SMOOTH_QUARTZ),('dark',module.BlockType.OBSIDIAN)):
                        for pos in tuple(app.world.blocks):app.world.setBlock(*pos,block)
                        app.skyboxesEnabled=False;app.lightingEnabled=False;app._invalidateViewCaches();app._fitWorldToViewport()
                        tag=f'{size[0]}-{round(scale*100)}-{tone}'
                        app.workshop.page='menu';app.workshop.menu_group='File';app.workshop.menu_slots=False
                        capture('menu-'+tag)
                        app.workshop.menu_slots=True;capture('slots-'+tag)
                        app.workshop.page='';app.settingsMenuOpen=True;capture('settings-'+tag);app.settingsMenuOpen=False
                        app._requestExit();capture('exit-'+tag);app._exitAction('stay')
                    app.workshop.page='world';capture(f'world-{size[0]}-{round(scale*100)}');app.workshop.page=''
                    app.library.open(app,'Worlds');capture(f'library-{size[0]}-{round(scale*100)}');app.library.visible=False
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

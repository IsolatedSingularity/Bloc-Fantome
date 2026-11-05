"""Isolated source/frozen GUI evidence. No user saves or preferences are written."""
from contextlib import ExitStack
import json
from pathlib import Path
import time
import pygame
from tools.verify_review_audio import temporary_attribute


def run(destination,module):
    import runtime_paths
    from ui.fonts import set_text_scale
    from ui.lifecycle import GoodbyeScreen
    output=Path(destination).resolve();output.mkdir(parents=True,exist_ok=True)
    rows=[]
    with ExitStack() as stack:
        for owner,name,value in ((module,'APP_CONFIG_FILE',str(output/'absent-config.json')),
                                 (runtime_paths,'BASE_DIR',str(output)),
                                 (module.BlocFantome,'_saveAppConfig',lambda self:None),
                                 (module.TutorialScreen,'_saveConfig',lambda self:None)):
            stack.enter_context(temporary_attribute(owner,name,value))
        app=module.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        try:
            assert app.skyboxesEnabled
            assert app.assetManager.loadAllAssets()
            app._generateStructurePreviews()
            app._createInitialFloor();app.workshop.visibility.pinned=True
            app.effectsMuted=app.musicMuted=app.ambientMuted=True
            def capture(name):
                for _ in range(12):
                    app._update();app._render();pygame.event.pump();app.clock.tick(60)
                if app.library.visible and app.library.tab=='Saved Builds':
                    deadline=time.perf_counter()+30
                    while time.perf_counter()<deadline:
                        app._render();pygame.event.pump()
                        if app.library._saved_future is None and all(
                            app.previewImages.get(app,e,(r.width-12,app.library.row_height-22-2*app.library.small.get_linesize())) is not None
                            for r,e in app.library.rows):break
                        time.sleep(.004)
                    else:raise AssertionError('Visible saved build previews did not settle')
                    app._render()
                pygame.image.save(app.screen,str(output/(name+'.png')))
                rows.append(dict(name=name,size=app.screen.get_size(),scale=app.workshop.text_scale))
            for size,scale in (((1200,800),1),((960,640),1.5),((1920,1080),1.25)):
                set_text_scale(scale);app.workshop.text_scale=scale;app._applyWindowSize(*size)
                tag=f'{size[0]}-{round(scale*100)}'
                capture('editor-'+tag)
                app.library.open(app);capture('library-home-'+tag);app.library.visible=False
                for tab in app.library.TABS:
                    app.library.open(app,tab)
                    for dim in (('overworld','nether','end') if tab!='Saved Builds' else ('overworld',)):
                        app.library.dimension=dim;app.library.refresh(app)
                        if app.library.entries:app.library.pending=app.library.entries[0]
                        capture(tab.lower().replace(' ','-')+'-'+dim+'-'+tag)
                    app.library.visible=False
                for page in ('world','menu'):
                    app.workshop.page=page;capture(page+'-'+tag)
                app.workshop.close_drawer(app)
                app.settingsMenuOpen=True;capture('settings-'+tag);app.settingsMenuOpen=False
            set_text_scale(1);app.workshop.text_scale=1;app._applyWindowSize(1200,800)
            app.library.open(app,'Worlds');app.library.dimension='end';app.library.refresh(app)
            entry=next(e for e in app.library.entries if e['kind']=='world')
            app.library.pending=entry;app.library.activate(app)
            deadline=time.perf_counter()+90
            while app.pendingWorldLoad is not None and time.perf_counter()<deadline:
                app._update();pygame.event.pump();time.sleep(.005)
            assert app.pendingWorldLoad is None, 'Captured structure did not finish loading'
            assert len(app.world.blocks)>1000, 'Structure gallery did not open the actual scene'
            capture('opened-end-city')
            opened=dict(key=entry['key'],blocks=len(app.world.blocks))
            app._openWorldMap()
            for size in ((960,640),(1200,800),(1920,1080)):
                app._applyWindowSize(*size);capture('map-'+str(size[0]))
            app._exitWorldMap()
            closing=GoodbyeScreen(app.screen,phrase='Leave a little light on.')
            closing.render(500);app.windowChrome.draw(app.screen)
            pygame.image.save(app.screen,str(output/'goodbye.png'))
            result=dict(version=app.version,driver=pygame.display.get_driver(),skyboxes_default_on=True,
                        opened_structure=opened,captures=rows,window_chrome=app.windowChrome.enabled)
            (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        finally:
            set_text_scale(1)
            app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True)
            pygame.quit()

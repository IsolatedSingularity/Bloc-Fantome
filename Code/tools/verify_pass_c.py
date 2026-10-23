"""Opt-in native startup measurements, isolated from owner preferences and saves."""
import json
from pathlib import Path
from time import perf_counter
import pygame
from contextlib import ExitStack
from tools.verify_review_audio import temporary_attribute


def startup(output,module):
    import runtime_paths
    from ui import opening_scene
    out=Path(output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    phases={};flips=[];original_mode=pygame.display.set_mode;original_flip=pygame.display.flip
    def flip():
        original_flip();flips.append(perf_counter())
    with ExitStack() as stack:
        for owner,key,value in ((pygame.display,'set_mode',lambda size,flags=0,*a,**k:original_mode(size,flags|pygame.HIDDEN,*a,**k)),
                                (pygame.display,'flip',flip),(runtime_paths,'BASE_DIR',str(out.parent)),
                                (runtime_paths,'SAVES_DIR',str(out.parent/'saves')),
                                (module,'SAVES_DIR',str(out.parent/'saves')),
                                (module,'APP_CONFIG_FILE',str(out.parent/'config.json')),
                                (opening_scene,'CONFIG_PATH',str(out.parent/'opening.json'))):
            stack.enter_context(temporary_attribute(owner,key,value))
        def timed(owner,name):
            original=getattr(owner,name)
            def call(*args,**kwargs):
                start=perf_counter()
                try:return original(*args,**kwargs)
                finally:phases[name]=phases.get(name,0)+(perf_counter()-start)*1000
            stack.enter_context(temporary_attribute(owner,name,call))
        for name in ('_checkTextures','_loadTextures','_createBlockSprites','_buildMipmaps','_createIconSprites','_loadSounds','_loadUITextures','_createBackground'):
            timed(module.AssetManager,name)
        for name in ('_createInitialFloor','_generateStructurePreviews','_preloadTutorialMusic','_playMenuMusic'):
            timed(module.BlocFantome,name)
        start=perf_counter();app=module.BlocFantome();construction=(perf_counter()-start)*1000
        app.autoSaveEnabled=False;app.effectsMuted=app.ambientMuted=app.musicMuted=True
        def ready():
            app._update();app._render()
            ready_at=perf_counter()
            m=app._startupMetrics;first=m['run_started']
            result=dict(version=module.APP_VERSION,driver=pygame.display.get_driver(),frozen=getattr(__import__('sys'),'frozen',False),
                        construction_ms=construction,phases_ms=phases,ready_perf_counter=ready_at,
                        startup_ms={k:(v-first)*1000 for k,v in m.items()},
                        first_editor_presented_ms=(ready_at-first)*1000,
                        frame_gaps_ms=[(b-a)*1000 for a,b in zip(flips,flips[1:])])
            out.write_text(json.dumps(result,indent=2),encoding='utf-8')
            app.running=False
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
        app._handleEvents=ready
        app.run()

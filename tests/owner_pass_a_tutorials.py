"""Native prepared-tour and persistence verification, scripted input only."""
import os,sys,time,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
import blocFantome as b
from engine.tutorial_lessons import TOUR

OUT=ROOT/'docs/reviews/owner-pass-a/tutorial'
OUT.mkdir(parents=True,exist_ok=True)
QA=ROOT/'.qa/owner-pass-a'
with patch.object(b,'APP_CONFIG_FILE',str(QA/'config.json')),patch.object(b,'SAVES_DIR',str(QA/'saves')),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'):
    app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
    app.assetManager.loadAllAssets();app._applyWindowSize(1200,800)
    app._createInitialFloor();app._fitWorldToViewport()
    report={'driver':pygame.display.get_driver(),'input':'scripted application actions','lessons':[]}
    try:
        props=b.BlockProperties(facing=b.Facing.EAST,slabPosition=b.SlabPosition.TOP)
        app._placeBlockWithUndo(4,4,1,b.BlockType.OAK_STAIRS,props)
        before=dict(app.world.blocks)
        assert app.undoManager.undo() and app.world.getBlock(4,4,1)==b.BlockType.AIR
        assert app.undoManager.redo() and app.world.blocks==before
        save=QA/'saves/owner-review-roundtrip.json.gz'
        assert app._saveBuilding(filepath=str(save),silent=True)
        app.world.setBlock(5,5,1,b.BlockType.GOLD_BLOCK)
        assert app._loadBuildingFromPath(str(save),silent=True) and app.world.blocks==before
        assert app.world.getBlockProperties(4,4,1).facing==b.Facing.EAST
        assert app.world.getBlockProperties(4,4,1).slabPosition==b.SlabPosition.TOP
        report['special_block_undo_save_reopen']=True
        app._beginTutorial(advanced=False)
        app._cancelTourLoad(navigating=True)
        for key in ('welcome','snow','structures','liquids'):
            step=next(s for s in TOUR if s['id']==key)
            app.tutorialScreen.currentStep=TOUR.index(step)
            start=time.perf_counter();snapshot=app._stageTourScene(step)
            staged=(time.perf_counter()-start)*1000
            start=time.perf_counter();app._applyTourScene(snapshot,step)
            activated=(time.perf_counter()-start)*1000
            frames=[]
            while True:
                start=time.perf_counter();pygame.event.pump();app._render()
                frames.append((time.perf_counter()-start)*1000)
                if app._worldSurfaceBuild is None:break
                assert len(frames)<1000
            if key=='snow':
                for _ in range(90):app._updateSnow(16)
                app._render()
                assert not app.snowLayers
            pygame.image.save(app.screen,OUT/f'{key}.png')
            x,y=app._cameraWorldCenter();x=max(0,min(app.world.width-1,int(x)));y=max(0,min(app.world.depth-1,int(y)))
            z=min(app.world.max_y_exclusive-1,app.world.getHighestBlock(x,y)+1)
            start=time.perf_counter();app._placeBlockWithUndo(x,y,z,b.BlockType.STONE);app._afterWorldEdit(((x,y,z),));app._render()
            edited=(time.perf_counter()-start)*1000
            assert app._worldSurfaceBuild is None
            app.renderer.offsetX+=80;app._render();assert app._worldSurfaceBuild is None
            app._rotateViewAndRecenter(1);app._render();assert app._worldSurfaceBuild is None
            report['lessons'].append(dict(lesson=key,blocks=len(app.world.blocks),stage_ms=staged,activation_ms=activated,first_complete_frames_ms=frames,edit_and_render_ms=edited))
        app.tutorialScreen.hide()
        assert app.world.blocks==before
        assert app.world.getBlockProperties(4,4,1).slabPosition==b.SlabPosition.TOP
        report['tutorial_restores_original']=True
        report['prepared_source_fingerprint']=__import__('engine.tutorial_prepared',fromlist=['fingerprint']).fingerprint()
        (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    finally:
        app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()

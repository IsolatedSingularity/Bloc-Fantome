"""Native SDL frame samples; scripted interactions, isolated user state."""
import os, sys, json, time, cProfile, pstats
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Code'))
os.environ['SDL_VIDEODRIVER'] = 'windows'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
import blocFantome as b

def main():
    out = ROOT / 'docs/reviews/owner-pass-a' / sys.argv[1]
    out.mkdir(parents=True, exist_ok=True)
    isolated = ROOT / '.qa/owner-pass-a'
    b.DERIVED_WORLD_CACHE_DIR = str(isolated / 'cache')
    results = {'driver': 'windows', 'input': 'scripted app actions', 'scenes': []}
    with patch.object(b, 'APP_CONFIG_FILE', str(isolated/'config.json')), patch.object(b, 'SAVES_DIR', str(isolated)), patch.object(b.BlocFantome, '_saveAppConfig'), patch.object(b.TutorialScreen, '_saveConfig'):
        app=b.BlocFantome(); app.autoSaveEnabled=False; app.tutorialScreen.visible=False
        app.assetManager.loadAllAssets(); app._applyWindowSize(1200,800)
        app.worldCenteredRotation=True
        def frame():
            t=time.perf_counter(); pygame.event.pump(); app._render()
            return (time.perf_counter()-t)*1000
        def settle():
            samples=[frame()]
            while app._worldSurfaceBuild is not None:
                samples.append(frame())
                if len(samples)>1000: raise RuntimeError('Surface did not complete')
            return samples
        try:
            for name in ('ancient_city_121','trial_chamber_121','village_plains_1161','ocean_monument_1161'):
                print(name, flush=True)
                start=time.perf_counter()
                assert app._loadBuildingFromPath(str(ROOT/'Code/worlds'/f'{name}.json.gz'),silent=True)
                load=(time.perf_counter()-start)*1000
                app._fitWorldToViewport(notify=False)
                row=dict(scene=name,blocks=len(app.world.blocks),load_ms=load,initial_frames=settle())
                row['stable_frames']=[frame() for _ in range(30)]
                row['edits']=[]
                for n in range(3):
                    x,y=app.world.width//2+n,app.world.depth//2
                    z=min(app.world.max_y_exclusive-1,app.world.getHighestBlock(x,y)+1)
                    start=time.perf_counter()
                    profile=cProfile.Profile() if n==0 else None
                    if profile: profile.enable()
                    app._placeBlockWithUndo(x,y,z,b.BlockType.STONE)
                    app._afterWorldEdit(((x,y,z),))
                    if profile:
                        profile.disable()
                        with (out/f'{name}-edit-profile.txt').open('w') as f:pstats.Stats(profile,stream=f).sort_stats('cumulative').print_stats(25)
                    row['edits'].append(dict(handler_ms=(time.perf_counter()-start)*1000,frames=settle()))
                row['pan']=[]
                for _ in range(3):
                    app.renderer.offsetX+=180
                    row['pan'].append(settle())
                app._handleZoom(app.zoomStep,600,400); row['zoom']=settle()
                app._rotateViewAndRecenter(1); row['rotation']=settle()
                pygame.image.save(app.screen,out/f'{name}.png')
                results['scenes'].append(row)
                (out/'frames.json').write_text(json.dumps(results,indent=2))
        finally:
            app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()

if __name__=='__main__':main()

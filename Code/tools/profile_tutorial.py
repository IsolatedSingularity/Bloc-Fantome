"""Measure exact lighting lesson preparation, bundle decode and main-thread apply."""
import argparse
import cProfile
import json
import os
from pathlib import Path
import pstats
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Code'))
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from blocFantome import BlocFantome
    from engine.tutorial_lessons import TOUR
    from engine.tutorial_prepared import load_lesson
    app=BlocFantome()
    step=next(s for s in TOUR if s['id']=='lighting')
    report={}
    try:
        start=time.perf_counter();packed=load_lesson('lighting',app.world.catalog)
        report['bundle_decode_s']=time.perf_counter()-start
        report['bundle_available']=packed is not None
        app._buildingTutorialBundle=True
        profile=cProfile.Profile();start=time.perf_counter()
        profile.enable();snapshot=app._stageTourScene(step);profile.disable()
        report['source_prepare_profiled_s']=time.perf_counter()-start
        profile.dump_stats(str(args.output/'lighting.prof'))
        with (args.output/'lighting-profile.txt').open('w') as stream:
            pstats.Stats(profile,stream=stream).sort_stats('cumtime').print_stats(25)
        timings=[]
        for _ in range(3):
            start=time.perf_counter();snapshot=app._stageTourScene(step)
            timings.append(time.perf_counter()-start)
        report['source_prepare_s']=timings
        report['cells']=len(snapshot.blocks);report['light_cells']=len(snapshot._lighting)
        app.tutorialScreen.visible=True
        start=time.perf_counter();app._applyTourScene(packed or snapshot,step)
        report['main_thread_apply_s']=time.perf_counter()-start
        report['light_map_equal']=app.lightMap==(packed or snapshot)._lighting
    finally:
        app._cancelTourLoad();app.worldLoadExecutor.shutdown(wait=True)
        import pygame
        pygame.quit()
    (args.output/'timings.json').write_text(json.dumps(report,indent=2))
    print(report,flush=True)


if __name__=='__main__':main()

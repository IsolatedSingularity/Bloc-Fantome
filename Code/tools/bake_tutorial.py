"""Prepare expensive visibility/index work once, instead of on every page visit."""
import os,sys,json,hashlib,time,gc,argparse
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Code'))
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from blocFantome import BlocFantome
from engine.tutorial_lessons import TOUR
from engine.tutorial_prepared import new_index,read_index,read_payload,encode_lesson


def bake_lessons(app,steps,target,selected=()):
    target=Path(target);target.mkdir(parents=True,exist_ok=True)
    index=new_index()
    if selected and (target/'manifest.json').exists():
        try:
            previous=read_index(target)
            for key,row in previous['lessons'].items():
                try:read_payload(target,row)
                except (OSError,ValueError,KeyError,TypeError):continue
                index['lessons'][key]=row
        except (OSError,ValueError,KeyError,TypeError):pass
    for step in steps:
        if not (step.get('capture') or step.get('world')):continue
        if selected and step['id'] not in selected:continue
        before=time.perf_counter();snapshot=app._stageTourScene(step)
        packed=encode_lesson(snapshot)
        name=step['id']+'.prepared';temporary=target/(name+'.tmp')
        temporary.write_bytes(packed);os.replace(temporary,target/name)
        index['lessons'][step['id']]={'file':name,'sha256':hashlib.sha256(packed).hexdigest(),'cells':len(snapshot.blocks)}
        print(step['id'],len(snapshot.blocks),round(len(packed)/1e6,2),'MB',round(time.perf_counter()-before,2),'s',flush=True)
        del snapshot,packed;gc.collect()
    temporary=target/'manifest.json.tmp'
    temporary.write_text(json.dumps(index,indent=2),encoding='utf-8')
    os.replace(temporary,target/'manifest.json')
    return index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lessons',nargs='*')
    parser.add_argument('--output',type=Path,default=ROOT/'Code/tutorial_prepared')
    options=parser.parse_args()
    known={step['id'] for step in TOUR if step.get('capture') or step.get('world')}
    if set(options.lessons)-known:parser.error('Unknown or non-bundled lesson')
    app=BlocFantome();app._buildingTutorialBundle=True
    try:bake_lessons(app,TOUR,options.output,options.lessons)
    finally:
        app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True)
        import pygame
        pygame.quit()

if __name__=='__main__':main()

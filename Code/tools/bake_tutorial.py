"""Prepare expensive visibility/index work once, instead of on every page visit."""
import os,sys,json,gzip,pickle,hashlib,time,gc
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Code'))
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from blocFantome import BlocFantome
from engine.tutorial_lessons import TOUR
from engine.tutorial_prepared import fingerprint


def main():
    target=ROOT/'Code/tutorial_prepared';target.mkdir(exist_ok=True)
    app=BlocFantome();app._buildingTutorialBundle=True
    index={'schema':1,'code':fingerprint(),'lessons':{}}
    selected=sys.argv[1:]
    for step in TOUR:
        if not (step.get('capture') or step.get('world')):continue
        if selected and step['id'] not in selected:continue
        before=time.perf_counter();snapshot=app._stageTourScene(step)
        state=dict(snapshot._prepared[0].__dict__);state.pop('catalog');state.pop('_retiredState',None)
        packed=gzip.compress(pickle.dumps((replace(snapshot,_prepared=None),state),protocol=5),compresslevel=1,mtime=0)
        name=step['id']+'.prepared';(target/name).write_bytes(packed)
        index['lessons'][step['id']]={'file':name,'sha256':hashlib.sha256(packed).hexdigest(),'cells':len(snapshot.blocks)}
        print(step['id'],len(snapshot.blocks),round(len(packed)/1e6,2),'MB',round(time.perf_counter()-before,2),'s',flush=True)
        del snapshot,state,packed;gc.collect()
    (target/'manifest.json').write_text(json.dumps(index,indent=2))
    app.worldLoadExecutor.shutdown()

if __name__=='__main__':main()

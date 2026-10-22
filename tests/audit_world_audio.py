"""Report effective catalog routes and missing decoded pools using local assets."""
import os
import sys
import json
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Code'))
import pygame
import blocFantome as b


def main():
    assets=b.AssetManager()
    pygame.display.set_mode((64,64),pygame.HIDDEN)
    assets._loadSounds()
    rows=[]
    for block in b.BLOCK_DEFINITIONS:
        definition=b.BLOCK_SOUNDS.get(block)
        row={'block':block.name}
        for event in ('place','break'):
            category=getattr(definition,event+'Sound',None)
            if event=='place' and assets.sounds.get(str(category)+'_place'):category+='_place'
            row[event]=category
            row[event+'_variants']=len(assets.sounds.get(category,[]))
        rows.append(row)
    result=dict(rows=rows,missing=[r for r in rows if r['block']!='AIR' and
        (not r['place_variants'] or not r['break_variants'])])
    output=Path(sys.argv[1]);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result['missing'],indent=2))
    pygame.quit()


if __name__=='__main__':main()

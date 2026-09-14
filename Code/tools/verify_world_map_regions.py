"""Compare every exported selector cell to its original vanilla chunk state."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

CODE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CODE))
from engine.anvil import _read_region_chunk


def verify(world, directory, source_worlds=None, paths=None):
    report=[]
    for path in sorted(paths if paths is not None else directory.glob('*.json.gz')):
        data=json.loads(gzip.decompress(path.read_bytes()))
        ox,oz=data['origin'][:2]
        oy=data['origin'][2] if len(data['origin'])==3 else 0
        groups=defaultdict(list)
        for x,z,y,pid in data['blocks']:
            groups[((x+ox)//16,(z+oz)//16)].append((x+ox,z+oz,y+oy,pid))
        dimension={'nether':'DIM-1','end':'DIM1'}.get(data['dimension'],'')
        verified=0
        for (cx,cz),records in groups.items():
            region=(source_worlds or {}).get(data.get('key',path.stem),world)/dimension/'region'/f'r.{cx//32}.{cz//32}.mca'
            root=_read_region_chunk(region,cx,cz)
            assert root['DataVersion']==2567
            sections={s['Y']:s for s in root['Level']['Sections'] if 'Palette' in s}
            for x,z,y,pid in records:
                section=sections[y//16]
                palette=section['Palette']
                bits=max(4,(len(palette)-1).bit_length())
                per_long=64//bits
                index=(y%16)*256+(z%16)*16+x%16
                packed=section.get('BlockStates',[])
                state_index=0 if len(palette)==1 else (packed[index//per_long] >> ((index%per_long)*bits)) & ((1<<bits)-1)
                assert palette[state_index]==data['palette'][pid],(path.name,(x,y,z),palette[state_index],data['palette'][pid])
                verified+=1
        item={'file':path.name,'verified_cells':verified,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source':'official Java 1.16.1 / seed 1','presentation':data['presentation']}
        item['authored_decoration_cells'] = len(data.get('decoration_blocks', []))
        report.append(item)
        print(item,flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('world',type=Path)
    parser.add_argument('--directory',type=Path,default=CODE/'world_map_regions')
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.world,args.directory)
    args.report.write_text(json.dumps(report,indent=2)+'\n')

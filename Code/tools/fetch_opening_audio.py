"""Fetch the selected public audition recordings, preserving originals locally."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import html,json,re,urllib.request

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'.qa/encounter/audio/sources'
SOURCES=[
 ('voice01','thanvannispen',9432),('voice02','thanvannispen',9429),
 ('voice03','thanvannispen',94585),('voice04','thanvannispen',94586),
 ('voice05','thanvannispen',125127),('voice06','thanvannispen',125128),
 ('voice07','thanvannispen',125129),('voice08','thanvannispen',125130),
 ('voice09','thanvannispen',125131),('voice10','missozzy',169811),
 ('voice11','tonsil5',416542),('whisper','LadyImperatrix',503270),
 ('stone','Pastabra',366160),('mechanism','robindouglasjohnson',698991),
 ('drain','kyles',452311),('chain','FartMuffin',571421),
]

def fetch(item):
    name,creator,number=item
    url=f'https://freesound.org/people/{creator}/sounds/{number}/'
    with urllib.request.urlopen(url,timeout=35) as response:page=response.read().decode('utf-8')
    match=re.search(r'https://cdn\.freesound\.org/previews/[^"\s<>]+-hq\.mp3',page)
    if not match:raise RuntimeError(f'No public preview: {url}')
    license_match=re.search(r'https?://creativecommons.org/(?:licenses|publicdomain)/[^"\s<>]+',page)
    if not license_match:raise RuntimeError(f'No source license found: {url}')
    target=DEST/(name+'.mp3')
    urllib.request.urlretrieve(match[0],target)
    title=re.search(r'<title>(.*?)</title>',page,re.S)
    print(name,target.stat().st_size,flush=True)
    return dict(id=name,creator=creator,url=url,preview=match[0],license=license_match[0],
                title=html.unescape(title[1].strip()) if title else str(number))

if __name__=='__main__':
    DEST.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,SOURCES))
    (DEST.parent/'sources.json').write_text(json.dumps(records,indent=2))

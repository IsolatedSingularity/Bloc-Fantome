from pathlib import Path
import json,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'.qa/tutorial-294/panoir-source.webm'
info=json.loads(source.with_suffix('.info.json').read_text(encoding='utf-8'))
dest=ROOT/'Assets/Sound Hub/opening/piano-chapters';dest.mkdir(exist_ok=True)
rows=[]
for i in (0,2,6):
 chapter=info['chapters'][i];start=chapter['start_time'];duration=chapter['end_time']-start
 target=dest/f'{i+1:02}-{chapter["title"]}.ogg'
 subprocess.run(['ffmpeg','-y','-v','error','-ss',str(start),'-i',str(source),'-t',str(duration),'-vn','-c:a','libvorbis','-q:a','6',str(target)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 rows.append(dict(chapter=chapter,output=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),editing='Whole creator-defined chapter, original dynamics and timing; no looping fragment, pitch shift or normalization.'))
report=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_url='https://www.youtube.com/watch?v=zkCR5KsJy1w',selection='Chapters one, three and seven: 258, 215 and 200 seconds. Creator boundaries retained. Owner listening acceptance pending.',chapters=rows)
(dest/'CUE_SHEET.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(Path(__file__).parent/'audio/piano-cue-sheet.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

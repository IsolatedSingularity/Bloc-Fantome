from pathlib import Path
import os,sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'Code'),str(ROOT/'tests')]
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import benchmark_large_world as bench
import blocFantome as b
OUT=Path(__file__).resolve().parent
with patch.object(b,'APP_CONFIG_FILE',str(OUT/'perf-config.json')),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'):
 bench.main(['ancient_city_121','trial_chamber_121','village_plains_1161','--viewport','1920x1080','--repetitions','5','--cache-dir',str(OUT/'performance-cache'),'--json-output',str(OUT/'performance1080.json')])

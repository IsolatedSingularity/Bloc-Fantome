from pathlib import Path
import json,hashlib,subprocess,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];QA=Path(__file__).parent;OUT=ROOT/'docs/reviews/pass1-complete'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def copy(src,dst):shutil.copy2(src,OUT/dst)
baseline=json.loads((ROOT/'.qa/pass1/preservation-before.json').read_text())
preserved=[]
for name,row in baseline.items():
 path=Path(name);actual=sha(path) if path.is_file() else None
 try:label=path.relative_to(ROOT).as_posix()
 except ValueError:label='$LOCALAPPDATA/Programs/Bloc Fantôme/'+path.name
 preserved.append(dict(path=label,before=row['sha256'],after=actual,unchanged=actual==row['sha256']))
(OUT/'verification/preservation.json').write_text(json.dumps(preserved,indent=2),encoding='utf-8')
assert all(row['unchanged'] for row in preserved),'Preservation mismatch; investigate rather than restore blindly'
changed=subprocess.check_output(['git','diff','--name-only','f63db3ab','--','Code','tests'],cwd=ROOT,text=True).splitlines()
changed+=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','Code','tests'],cwd=ROOT,text=True).splitlines()
manifest={name:sha(ROOT/name) for name in sorted(set(changed)) if (ROOT/name).is_file()}
manifest['Code/tutorial_prepared/manifest.json']=sha(ROOT/'Code/tutorial_prepared/manifest.json')
(OUT/'verification/source-manifest.json').write_text(json.dumps(manifest,indent=2))
derived=[ROOT/'Assets/Sound Hub/opening/sanctuary-rise-b4.ogg',*(ROOT/'Assets/Sound Hub/opening/piano-chapters').glob('*.ogg'),*(ROOT/'Assets/Sound Hub/ui/workshop').glob('*.ogg')]
(OUT/'verification/derived-audio.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in derived},indent=2))
for path in (QA/'native-final').glob('*.png'):copy(path,'native/final-'+path.name)
copy(QA/'native-final/report.json','native/final-checks.json')
copy(QA/'ui-latency.json','performance/ui-latency.json')
for name in ('final-suite2.xml','release-suite.xml','fallback.xml','polish.xml'):
 if (QA/name).exists():copy(QA/name,'verification/'+name)
for name in ('recovery.log','bake-release.log','build-final.log'):
 if (QA/name).exists():copy(QA/name,'verification/'+name)
copy(QA/'package-opening.png','native/packaged-opening.png')
copy(QA/'final_native.py','reproduction/final_native.py')
copy(QA/'ui_latency.py','reproduction/ui_latency.py')
copy(QA/'native_review.py','reproduction/native_review.py')
copy(QA/'capability_report.py','reproduction/capability_report.py')
copy(QA/'verification_report.py','reproduction/verification_report.py')
iterations=OUT/'native/iterations';iterations.mkdir(exist_ok=True)
for name in ('tutorial-text150.png','world-map-text150.png','build-960-text150.png'):
 copy(QA/'native-matrix'/name,'native/iterations/first-'+name)
exe=QA/'package/BlocFantome.exe'
package=dict(path=exe.relative_to(ROOT).as_posix(),bytes=exe.stat().st_size,sha256=sha(exe),assets='Workspace Assets junction; no standalone installer produced',installed='Unchanged, intentionally not promoted')
(OUT/'verification/package.json').write_text(json.dumps(package,indent=2))
print('Preserved',len(preserved),'targets; source hashes',len(manifest),'derived audio',len(derived))

from pathlib import Path
p=Path('.qa/maintenance-profile.py');s=p.read_text();s=s.replace('  frames[name]={', '''  while app._worldSurfaceBuild is not None and len(samples)<1000:
   t=time.perf_counter();app._update();app._render();samples.append((time.perf_counter()-t)*1000)
  assert app._worldSurfaceBuild is None
  frames[name]={''');p.write_text(s)

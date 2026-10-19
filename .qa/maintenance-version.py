from pathlib import Path
for name in ('Code/blocFantome.py','Code/build_exe.py','Code/installer.iss'):
 p=Path(name);p.write_text(p.read_text(encoding='utf-8').replace('2.9.2','2.9.3'),encoding='utf-8')
p=Path('CHANGELOG.md');s=p.read_text(encoding='utf-8');s=s.replace('## [2.9.2]', '''## [2.9.3] - 2026-10-18

### Fixed
- Preserve complete v5 world state in backups, retain recovery history on write failure, and report autosave failures truthfully.
- Reject corrupt, all-invalid and unsupported future builds; replace duplicate cells with the complete last valid row.
- Block editing during pending World loads, support Escape cancellation, and discard results belonging to an older canvas or mode.
- Roll back failed undo batches and retain modern block state in derived scene caches, including large canvas bounds.
- Make the structure fingerprint independent of checkout location without dropping content fields.
- Reduce repeated visibility classification and spread large initial renders over frames at unchanged final quality.
- Reserve a separate title area below the full, aspect-preserved swamp painting.

## [2.9.2]''',1);p.write_text(s,encoding='utf-8')

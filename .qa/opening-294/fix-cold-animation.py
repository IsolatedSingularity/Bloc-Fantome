from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8');needle='''        # Moving piston cells are composited at sub-cell positions every frame.
''';assert needle in s;s=s.replace(needle,'''        # Finish one animation sample while a cold surface is being assembled.
        # Water/fire frame changes must not restart its batches every tick.
        if (self._worldSurfaceBuild is not None and self._worldSurfaceBuildKey is not None
                and self._worldSurfaceBuildKey[:-1] == surfaceKey[:-1]):
            surfaceKey = self._worldSurfaceBuildKey
''' + needle,1);p.write_text(s,encoding='utf-8')

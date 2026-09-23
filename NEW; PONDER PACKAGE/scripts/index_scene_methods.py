#!/usr/bin/env python3
"""List candidate Java storyboard methods. Not a Java parser or porting tool."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
PATTERN = re.compile(r'public\s+static\s+void\s+(\w+)\s*\(\s*SceneBuilder\b', re.M)


def inventory(root: Path):
    if not root.is_dir():
        raise ValueError(f'Directory does not exist: {root}. Fetch scene sources first.')
    rows = []
    for p in sorted(root.rglob('*Scenes*.java')):
        text = p.read_text(encoding='utf-8-sig')
        for match in PATTERN.finditer(text):
            rows.append({'file': p.relative_to(root).as_posix(), 'method': match.group(1),
                         'line': 1+text.count('\n', 0, match.start())})
    return {'scope': 'Lexical method candidates; not registration count or semantic parsing',
            'count': len(rows), 'methods': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    a = p.parse_args()
    try:
        print(json.dumps(inventory(a.root), indent=2))
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

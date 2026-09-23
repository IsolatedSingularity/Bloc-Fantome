#!/usr/bin/env python3
"""Validate the extracted reference kit locally; no network calls."""
from __future__ import annotations
import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]

def verify(root: Path=ROOT):
    errors=[]
    files=[p for p in root.rglob('*') if p.is_file() and not any(x in ('__pycache__','downloads') for x in p.relative_to(root).parts)]
    for p in files:
        if p.stat().st_size>2*1024**2:errors.append(f'Unexpected large bundled file: {p.relative_to(root)}')
        if p.suffix=='.json':
            try:json.loads(p.read_text(encoding='utf-8'))
            except Exception as exc:errors.append(f'Invalid JSON {p.name}: {exc}')
        if p.suffix=='.py':
            try:ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
            except SyntaxError as exc:errors.append(str(exc))
        if p.suffix=='.md':
            text=re.sub(r'```.*?```','',p.read_text(encoding='utf-8'),flags=re.S)
            for match in re.finditer(r'\[[^\]]*\]\(([^)]+)\)',text):
                url=match.group(1)
                if urlsplit(url).scheme:continue
                file,sep,anchor=unquote(url).partition('#')
                dest=(p.parent/file).resolve() if file else p.resolve()
                if not dest.is_relative_to(root.resolve()) or not dest.is_file():
                    errors.append(f'Unresolved local link: {p.relative_to(root)} -> {url}');continue
                if sep and anchor and dest.suffix=='.md':
                    content=dest.read_text(encoding='utf-8')
                    if f'id="{anchor}"' not in content:
                        errors.append(f'Unresolved explicit anchor: {p.name} -> {url}')
    catalog=json.loads((root/'ponder/scene_catalog.json').read_text())
    if len(catalog['files'])!=47:errors.append('Scene catalogue must contain 47 files')
    if len({x['path'] for x in catalog['files']})!=47:errors.append('Duplicate scene paths')
    if sum(x['is_template'] for x in catalog['files'])!=1:errors.append('Template count mismatch')
    source=json.loads((root/'scripts/source_manifest.json').read_text())['items']
    if len({x['id'] for x in source})!=len(source):errors.append('Duplicate source IDs')
    source_paths={x.get('upstream_path') for x in source}
    if any(x['path'] not in source_paths for x in catalog['files']):errors.append('Scene missing from fetch manifest')
    if any('/resources/assets/' in x.get('upstream_path','') for x in source):errors.append('Unexpected game assets in source set')
    a=json.loads((root/'audio/manifest.json').read_text())
    if not 8<=len(a['music'])<=15:errors.append('Music count outside brief')
    if any(x['local_path'] is not None or x['bundled'] for x in a['music']):errors.append('Unexpected soundtrack payload claim')
    for p in files:
        if p.suffix.lower() in ('.mp3','.ogg','.wav','.flac','.ttf','.otf','.woff','.exe','.dll','.jar','.class'):
            errors.append(f'Unexpected media/font/executable payload: {p.name}')
    return {'ok':not errors,'errors':errors,'files_checked':len(files),
            'source_fetch_entries':len(source),'create_scene_files':len(catalog['files']),
            'music_candidates':len(a['music']),'ui_sources':len(a['items']),
            'sky_entries':len(json.loads((root/'skyboxes/manifest.json').read_text())['items']),
            'external_url_checks':'Not performed by this validator; see QA.md for research coverage'}

if __name__=='__main__':
    result=verify();print(json.dumps(result,indent=2));raise SystemExit(0 if result['ok'] else 1)

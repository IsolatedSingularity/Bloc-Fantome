#!/usr/bin/env python3
"""Optionally discover all pinned Ponder Java source, without downloading it.

Dry-run by default. --execute fetches GitHub's tree metadata and writes a new
manifest under downloads/, not into a game repo. Run fetch_references.py on the
resulting manifest to retrieve files. This is discovery, not a Java dependency
resolver. It does not install Minecraft, Catnip or a mod loader.
"""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path, PurePosixPath
from urllib.parse import quote
import sys
from fetch_references import Budget, FetchError, KIT, read_transfer, target_path
REPO='Creators-of-Create/Ponder'
PIN='89819291b726708d119b118dea01667eae0b64c9'
PREFIX='common/src/main/java/net/createmod/ponder/'
URL=f'https://api.github.com/repos/{REPO}/git/trees/{PIN}?recursive=1'


def convert_tree(tree):
    if tree.get('truncated'):
        raise FetchError('GitHub truncated the tree; refusing an incomplete full-source manifest')
    if not isinstance(tree.get('tree'), list):
        raise FetchError('Unexpected GitHub tree response')
    items=[]
    for entry in tree['tree']:
        p=entry.get('path','')
        if entry.get('type')!='blob' or not (p=='LICENSE' or (p.startswith(PREFIX) and p.endswith('.java'))):
            continue
        target_path(Path('/manifest-root'),p)
        if entry.get('mode')=='120000':
            raise FetchError('Unexpected symbolic-link source entry')
        if not isinstance(entry.get('size'),int) or entry['size']>2_000_000:
            raise FetchError('Missing or unexpectedly large source size')
        items.append({'id':'ponder-full:'+p,'group':'ponder-full','repo':REPO,'commit':PIN,
                      'upstream_path':p,'url':f'https://raw.githubusercontent.com/{REPO}/{PIN}/{quote(p)}',
                      'source_url':f'https://github.com/{REPO}/blob/{PIN}/{quote(p)}',
                      'output':'ponder-full/Ponder/'+p,'kind':'text','max_bytes':2_000_000,
                      'license':'MIT','verification':'tree_discovered_not_read'})
    if not any(i['upstream_path']=='LICENSE' for i in items) or len(items)<2:
        raise FetchError('Ponder source/license missing from tree')
    return {'schema_version':1,'scope':'Entire pinned Ponder package Java code + LICENSE; no assets/dependencies',
            'items':sorted(items,key=lambda x:x['upstream_path'])}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--output',type=Path,default=KIT/'downloads'/'ponder_full_manifest.json')
    a=p.parse_args(argv)
    print(json.dumps({'tree_url':URL,'output':str(a.output),'execute':a.execute},indent=2))
    if not a.execute:return 0
    try:
        if a.output.exists():raise FetchError('Output exists; choose a new output path')
        buf=io.BytesIO()
        read_transfer(URL,buf,8*1024**2,Budget(8*1024**2))
        manifest=convert_tree(json.loads(buf.getvalue()))
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
        print(f'{len(manifest["items"])} entries. No source files downloaded.')
        return 0
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())

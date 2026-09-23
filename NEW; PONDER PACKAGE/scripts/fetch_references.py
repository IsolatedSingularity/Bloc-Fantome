#!/usr/bin/env python3
"""Selective reference retrieval. Python 3.10+, stdlib only, dry-run by default.

Does not execute source, install mods, extract archives or touch a game repository.
Network URLs are HTTPS; localhost HTTP is exposed only to the test harness.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any, BinaryIO
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

KIT = Path(__file__).resolve().parents[1]
USER_AGENT = 'Bloc-Fantome-Reference-Kit/1.0 (selective personal reference retrieval)'


class FetchError(RuntimeError):
    """A bounded, user-readable retrieval failure."""


def target_path(root: Path, relative: str) -> Path:
    """Reject traversal, Windows drive/ADS forms, and existing symlink escapes."""
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise FetchError(f'Invalid relative output: {relative!r}')
    p = PurePosixPath(relative)
    if p.is_absolute() or any(x in ('..', '.') for x in relative.split('/')):
        raise FetchError(f'Output must stay inside destination: {relative!r}')
    if any(not x or x.endswith((' ', '.')) for x in relative.split('/')):
        raise FetchError(f'Invalid output component: {relative!r}')
    root = root.resolve()
    out = root.joinpath(*p.parts).resolve()
    if not out.is_relative_to(root) or out == root:
        raise FetchError('Output escapes the destination')
    return out


def validate_url(url: str, test_local_http: bool = False) -> None:
    u = urlsplit(url)
    local = test_local_http and u.scheme == 'http' and u.hostname in ('127.0.0.1', 'localhost')
    if not u.hostname or u.username or u.password or not (u.scheme == 'https' or local):
        raise FetchError('Expected HTTPS URL (localhost HTTP is test-only)')


class StrictRedirect(HTTPRedirectHandler):
    def __init__(self, test_local_http: bool = False):
        super().__init__()
        self.test_local_http = test_local_http

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.test_local_http)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Budget:
    def __init__(self, total: int):
        if total <= 0:
            raise FetchError('Transfer budget must be positive')
        self.total = total
        self.used = 0

    @property
    def remaining(self) -> int:
        return self.total - self.used


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)


def resolve_page_link(html: str, page_url: str, basename: str, allowed_hosts: list[str]) -> str:
    """Resolve exactly one published filename; do not guess a CDN directory."""
    parser = LinkParser()
    parser.feed(html)
    candidates = set()
    for href in parser.links:
        url = urljoin(page_url, href)
        u = urlsplit(url)
        if u.hostname not in allowed_hosts:
            continue
        if unquote(u.path.rsplit('/', 1)[-1]) == basename:
            candidates.add(url)
    if len(candidates) != 1:
        raise FetchError(f'Expected one published link for {basename!r}, found {len(candidates)}. Open {page_url}')
    return candidates.pop()


def read_transfer(url: str, sink: BinaryIO, per_file_limit: int, budget: Budget,
                  timeout: float = 30, test_local_http: bool = False) -> dict[str, Any]:
    validate_url(url, test_local_http)
    opener = build_opener(StrictRedirect(test_local_http))
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'})
    limit = min(per_file_limit, budget.remaining)
    if limit <= 0:
        raise FetchError('Transfer budget exhausted')
    with opener.open(request, timeout=timeout) as response:
        validate_url(response.geturl(), test_local_http)
        if getattr(response, 'status', 200) != 200:
            raise FetchError(f'Expected HTTP 200, got {response.status}')
        length_header = response.headers.get('Content-Length')
        length = int(length_header) if length_header is not None else None
        if length is not None and (length < 0 or length > limit):
            raise FetchError(f'Declared payload size {length} exceeds remaining/per-file budget {limit}')
        count = 0
        while True:
            chunk = response.read(min(65536, max(1, limit - count + 1)))
            if not chunk:
                break
            count += len(chunk)
            budget.used += len(chunk)
            if count > limit:
                raise FetchError('Payload exceeded transfer budget; partial file removed')
            sink.write(chunk)
        if length is not None and count != length:
            raise FetchError(f'Incomplete payload: expected {length} bytes, got {count}')
        return {'bytes': count, 'final_url': response.geturl(),
                'content_type': response.headers.get('Content-Type', '')}


def validate_payload(path: Path, kind: str) -> dict[str, Any]:
    size = path.stat().st_size
    if size == 0:
        raise FetchError('Empty payload')
    with path.open('rb') as f:
        prefix = f.read(512)
    if kind == 'text':
        text = path.read_text(encoding='utf-8-sig')
        if '\x00' in text or re.match(r'\s*(<!doctype\s+html|<html\b)', text, re.I):
            raise FetchError('Expected source text, received HTML or binary data')
        return {'utf8': True, 'lines': len(text.splitlines())}
    if kind == 'jpeg':
        if not prefix.startswith(b'\xff\xd8\xff'):
            raise FetchError('Payload does not have a JPEG signature')
        # Signature verification is not a complete decode or a seam check.
        return {'jpeg_signature': True, 'decoded': False}
    if kind == 'zip':
        with zipfile.ZipFile(path) as z:
            info = z.infolist()
            if len(info) > 20000 or sum(i.file_size for i in info) > 512 * 1024**2:
                raise FetchError('Archive inventory exceeds the uncompressed validation budget')
            for i in info:
                target_path(Path('/inventory-root'), i.filename.rstrip('/'))
                if i.flag_bits & 1:
                    raise FetchError('Encrypted ZIP member is unsupported')
                if stat.S_ISLNK(i.external_attr >> 16):
                    raise FetchError('Symbolic-link ZIP member is unsupported')
            bad = z.testzip()
            if bad:
                raise FetchError(f'ZIP CRC failure: {bad}')
            return {'zip_crc_ok': True, 'extracted': False,
                    'members': [{'name': i.filename, 'bytes': i.file_size} for i in info]}
    raise FetchError(f'Unknown validation kind: {kind}')


def fetch_one(entry: dict[str, Any], root: Path, budget: Budget,
              timeout: float = 30, test_local_http: bool = False) -> dict[str, Any]:
    if not entry.get('url') and not entry.get('resolver'):
        return {'id': entry['id'], 'status': 'manual', 'source_url': entry['source_url']}
    out = target_path(root, entry['output'])
    if out.exists():
        return {'id': entry['id'], 'status': 'existing_not_overwritten', 'path': str(out),
                'note': 'Existing bytes were not compared to upstream; use a new destination to refetch.'}
    out.parent.mkdir(parents=True, exist_ok=True)
    url = entry.get('url')
    if not url:
        resolver = entry['resolver']
        if resolver.get('type') != 'page_link':
            raise FetchError('Unsupported resolver')
        import io
        page = io.BytesIO()
        read_transfer(entry['source_url'], page, 2*1024**2, budget, timeout, test_local_http)
        url = resolve_page_link(page.getvalue().decode('utf-8'), entry['source_url'],
                                resolver['basename'], resolver['allowed_hosts'])
    temp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.fetch-', suffix='.part', dir=out.parent, delete=False) as sink:
            temp = Path(sink.name)
            transfer = read_transfer(url, sink, entry['max_bytes'], budget, timeout, test_local_http)
        if entry['kind'] == 'text' and 'text/html' in transfer['content_type'].lower():
            raise FetchError('Server returned an HTML page instead of source')
        validation = validate_payload(temp, entry['kind'])
        # Hard-link the validated file into place, atomically failing if the
        # destination appeared concurrently. Same-directory temporary file.
        import os
        os.link(temp, out)
        return {'id': entry['id'], 'status': 'downloaded', 'path': str(out),
                'source_url': entry.get('source_url'), 'commit': entry.get('commit'),
                **transfer, 'validation': validation}
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def load_entries(paths: list[Path]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen = set()
    for path in paths:
        document = json.loads(path.read_text(encoding='utf-8'))
        if document.get('schema_version') != 1 or not isinstance(document.get('items'), list):
            raise FetchError(f'Unsupported manifest: {path}')
        for item in document['items']:
            if not isinstance(item.get('id'), str) or item['id'] in seen:
                raise FetchError('Missing or duplicate manifest ID')
            seen.add(item['id'])
            if item.get('url') or item.get('resolver'):
                target_path(Path('/validation-root'), item['output'])
                if item['kind'] not in ('text', 'zip', 'jpeg') or item['max_bytes'] <= 0:
                    raise FetchError(f'Invalid entry: {item["id"]}')
                if item.get('commit') and not re.fullmatch(r'[0-9a-f]{40}', item['commit']):
                    raise FetchError('Source commit must be immutable')
            entries.append(item)
    return entries


def choose(entries, groups, ids):
    ids, groups = set(ids), set(groups)
    available_ids = {e['id'] for e in entries}
    available_groups = {e.get('group') for e in entries}
    if ids - available_ids or groups - available_groups:
        raise FetchError(f'Unknown IDs/groups: {sorted(ids-available_ids)} / {sorted(groups-available_groups)}')
    selected = [e for e in entries if e['id'] in ids or e.get('group') in groups]
    # Keep the license from each selected source repository alongside its code.
    repos = {e.get('repo') for e in selected if e.get('repo')}
    for e in entries:
        if e.get('repo') in repos and e.get('upstream_path', '').upper().startswith('LICENSE') and e not in selected:
            selected.append(e)
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, action='append')
    parser.add_argument('--group', action='append', default=[])
    parser.add_argument('--id', action='append', default=[])
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--dest', type=Path, default=KIT/'downloads')
    parser.add_argument('--max-total-mib', type=float, default=16)
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args(argv)
    try:
        if not args.group and not args.id:
            raise FetchError('Select at least one --group or --id. No bulk default.')
        if args.timeout <= 0:
            raise FetchError('Timeout must be positive')
        entries = load_entries(args.manifest or [Path(__file__).with_name('source_manifest.json')])
        selected = choose(entries, args.group, args.id)
        budget = Budget(int(args.max_total_mib * 1024**2))
        plan = {'mode': 'execute' if args.execute else 'dry_run', 'budget_bytes': budget.total,
                'destination': str(args.dest.resolve()), 'selection': [e['id'] for e in selected]}
        print(json.dumps(plan, indent=2))
        if not args.execute:
            return 0
        args.dest.mkdir(parents=True, exist_ok=True)
        receipt = {'started_utc': datetime.now(timezone.utc).isoformat(), 'plan': plan, 'results': []}
        failed = False
        for e in selected:
            try:
                result = fetch_one(e, args.dest, budget, args.timeout)
            except Exception as exc:
                failed = True
                result = {'id': e['id'], 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'}
            receipt['results'].append(result)
            print(f'{e["id"]}: {result["status"]}')
            if failed:
                break  # Diagnose before attempting unrelated speculative work.
        receipt['transfer_bytes'] = budget.used
        receipt['complete'] = not failed
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix='receipt-', suffix='.json',
                                         dir=args.dest, delete=False) as f:
            json.dump(receipt, f, indent=2, ensure_ascii=False)
            print('Receipt:', f.name)
        return 1 if failed else 0
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

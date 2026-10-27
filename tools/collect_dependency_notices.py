"""Collect build-cache evidence for review; this does not certify license completeness."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import json
import re
import zipfile
from pathlib import Path

COORDINATE = re.compile(r"[\w.-]+:[\w.-]+:[\w.+-]+\Z")

def coordinates(report: str) -> list[str]:
    if 'releaseRuntimeClasspath' not in report or 'BUILD SUCCESSFUL' not in report:
        raise ValueError('Expected a successful releaseRuntimeClasspath report')
    found = set()
    for line in report.splitlines():
        if 'FAILED' in line:
            raise ValueError('Unresolved dependency in report')
        match = re.search(r'(?:\+---|\\---) (.+)', line)
        if not match:
            continue
        value = match[1]
        if value.startswith('project ') or value.endswith(' (c)'):
            continue
        value = value.removesuffix(' (*)')
        before, separator, after = value.partition(' -> ')
        if separator:
            value = after if ':' in after else ':'.join(before.split(':')[:2] + [after])
        if not COORDINATE.fullmatch(value):
            raise ValueError(f'Unsupported dependency notation: {value}')
        found.add(value)
    if not found:
        raise ValueError('Empty dependency report')
    return sorted(found)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pom_url(coordinate: str) -> str:
    if not COORDINATE.fullmatch(coordinate):
        raise ValueError('Invalid Maven coordinate')
    group, artifact, version = coordinate.split(':')
    google = group.startswith(('androidx.', 'com.google.android.', 'com.google.firebase', 'com.google.mlkit'))
    base = 'https://dl.google.com/dl/android/maven2/' if google else 'https://repo.maven.apache.org/maven2/'
    return base + group.replace('.', '/') + f'/{artifact}/{version}/{artifact}-{version}.pom'


def fetch_pom(coordinate: str) -> tuple[str, bytes]:
    url = pom_url(coordinate)
    with urllib.request.urlopen(url, timeout=15) as response:
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError('POM exceeds 2 MiB limit')
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('POM contains unsupported XML declarations')
    root = ET.fromstring(data)
    if root.tag.split('}')[-1] != 'project':
        raise ValueError('Response is not a Maven POM')
    return url, data


def archive_notices(archive, prefix='', depth=0, budget=None):
    # Examine nested AAR JARs without extracting any archive paths to disk.
    if budget is None:
        budget = [128 * 1024 * 1024]
    for entry in archive.infolist():
        if entry.is_dir():
            continue
        notice = re.search(r'(^|[/_.-])(license|licence|notice|copying|copyright)([/_.-]|$)', entry.filename, re.I)
        nested = entry.filename.endswith('.jar') and depth < 2
        if not notice and not nested:
            continue
        limit = 4 * 1024 * 1024 if notice else 64 * 1024 * 1024
        if entry.file_size > limit or entry.file_size > budget[0]:
            raise ValueError('Archive evidence exceeds review size limit')
        budget[0] -= entry.file_size
        data = archive.read(entry)
        name = prefix + entry.filename
        if notice:
            yield name, data
        elif nested:
            with zipfile.ZipFile(io.BytesIO(data)) as jar:
                yield from archive_notices(jar, name + '!/', depth + 1, budget)

def collect(report: Path, cache: Path, output: Path, fetch_missing: bool = False) -> dict:
    raw = report.read_bytes()
    modules = coordinates(raw.decode('utf-8'))
    output.mkdir(parents=True, exist_ok=False)
    evidence = output / 'blobs'
    evidence.mkdir()
    def retain(data: bytes) -> str:
        digest = sha(data)
        (evidence / digest).write_bytes(data)
        return digest
    fetched = {}
    if fetch_missing:
        missing = [c for c in modules if not any((cache.joinpath(*c.split(':'))).glob('*/*.pom'))]
        def retrieve(c):
            try:
                return c, fetch_pom(c), None
            except (OSError, ValueError, ET.ParseError) as error:
                return c, None, type(error).__name__
        with ThreadPoolExecutor(max_workers=4) as workers:
            for c, value, error in workers.map(retrieve, missing):
                fetched[c] = (value, error)
    rows = []
    for coordinate in modules:
        group, artifact, version = coordinate.split(':')
        folder = cache / group / artifact / version
        row = {'coordinate': coordinate, 'artifacts': [], 'poms': [], 'notices': [],
               'review_status': 'UNREVIEWED'}
        for file in sorted(folder.glob('*/*')):
            if not file.is_file():
                continue
            if file.suffix == '.pom':
                row['poms'].append({'name': file.name, 'sha256': retain(file.read_bytes())})
            if file.suffix not in ('.jar', '.aar') or file.name.endswith(('-sources.jar', '-javadoc.jar')):
                continue
            row['artifacts'].append({'name': file.name, 'sha256': sha(file.read_bytes())})
            with zipfile.ZipFile(file) as archive:
                for entry_name, data in archive_notices(archive):
                    row['notices'].append({'artifact': file.name, 'entry': entry_name,
                                           'sha256': retain(data)})
        if coordinate in fetched:
            value, error = fetched[coordinate]
            if error:
                row['pom_fetch_error'] = error
            else:
                url, data = value
                row['poms'].append({'name': f'{artifact}-{version}.pom', 'source_url': url,
                                    'sha256': retain(data)})
        row['pom_missing'] = not row['poms']
        row['embedded_notice_missing'] = not row['notices']
        rows.append(row)
    result = {'report_sha256': sha(raw), 'scope': 'Resolved report coordinates; cache candidates, not proof of packaged code. Nested JARs scanned to depth2 with bounded reads; inherited POM licenses require further review.',
              'complete_license_audit': False, 'dependencies': rows}
    (output / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fetch-missing-poms', action='store_true', help='Fetch exact-version POMs from Google Maven or Maven Central')
    args = parser.parse_args()
    result = collect(args.report, args.cache, args.output, args.fetch_missing_poms)
    rows = result['dependencies']
    print(f"Collected {len(rows)} coordinates; {sum(r['pom_missing'] for r in rows)} missing POMs; all UNREVIEWED")

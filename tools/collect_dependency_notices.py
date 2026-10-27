"""Collect build-cache evidence for review; this does not certify license completeness."""
from __future__ import annotations
import argparse
import hashlib
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

def collect(report: Path, cache: Path, output: Path) -> dict:
    raw = report.read_bytes()
    modules = coordinates(raw.decode('utf-8'))
    output.mkdir(parents=True, exist_ok=False)
    evidence = output / 'blobs'
    evidence.mkdir()
    def retain(data: bytes) -> str:
        digest = sha(data)
        (evidence / digest).write_bytes(data)
        return digest
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
                for entry in archive.infolist():
                    if entry.is_dir() or not re.search(r'(^|[/_.-])(license|licence|notice|copying|copyright)([/_.-]|$)', entry.filename, re.I):
                        continue
                    if entry.file_size > 4 * 1024 * 1024:
                        raise ValueError('Notice exceeds 4 MiB review limit')
                    row['notices'].append({'artifact': file.name, 'entry': entry.filename,
                                           'sha256': retain(archive.read(entry))})
        row['pom_missing'] = not row['poms']
        row['embedded_notice_missing'] = not row['notices']
        rows.append(row)
    result = {'report_sha256': sha(raw), 'scope': 'Resolved report coordinates; cache candidates, not proof of packaged code. Nested JAR notices and inherited POM licenses require further review.',
              'complete_license_audit': False, 'dependencies': rows}
    (output / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = collect(args.report, args.cache, args.output)
    rows = result['dependencies']
    print(f"Collected {len(rows)} coordinates; {sum(r['pom_missing'] for r in rows)} missing POMs; all UNREVIEWED")

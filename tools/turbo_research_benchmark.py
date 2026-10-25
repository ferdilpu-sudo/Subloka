"""Opt-in research-only Turbo JNI benchmark. Close active work before running."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import uuid
import wave
from t10_wer import normalize, word_error_rate
from verify_instrumentation_result import verify

PACKAGE = 'app.subloka.caption'


def prepare(root, manifest):
    data = json.loads(manifest.read_text(encoding='utf-8-sig'))
    if data.get('not_eligible_for_private_holdout_or_CP4') is not True:
        raise ValueError('Expected research-only manifest')
    rows = data['samples']
    expected = {f'id-{group}-{i:02}' for group, count in [('clean', 20), ('challenging', 10)] for i in range(1, count + 1)}
    if len(rows) != 30 or {r['id'] for r in rows} != expected:
        raise ValueError('Expected 30 unique research IDs')
    files, inputs = {}, []
    for row in rows:
        if row.get('human_reference_reviewed') is not True or not (row.get('actual_heard_transcript') or '').strip():
            raise ValueError('Missing reviewed reference: ' + row['id'])
        if row['language'] != 'id' or row['category'] not in ('clean', 'challenging') or not row['id'].startswith('id-' + row['category'] + '-'):
            raise ValueError('Unsupported language/category')
        path = (root / row['audio']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Audio escapes dataset directory')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['audio_sha256']:
            raise ValueError('Audio hash mismatch: ' + row['id'])
        with wave.open(io.BytesIO(raw)) as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, 'NONE'):
                raise ValueError('Expected mono PCM16 16kHz WAV')
            frames = wav.getnframes()
            if not 0 < frames <= 960000:
                raise ValueError('Invalid duration')
            pcm = wav.readframes(frames)
            if len(pcm) != frames * 2:
                raise ValueError('Truncated audio')
        if abs(frames / 16000 - row['duration_seconds']) > 0.01:
            raise ValueError('Duration mismatch')
        files[row['id'] + '.pcm'] = pcm
        inputs.append({'id': row['id'], 'pcm_sha256': hashlib.sha256(pcm).hexdigest()})
    files['input.json'] = json.dumps({'samples': inputs}).encode()
    return rows, files


def score(rows, events):
    results = [e for e in events if e.get('event') == 'sample']
    if len(results) != 30 or len({r['id'] for r in results}) != 30 or not events or events[-1] != {'event': 'complete', 'count': 30}:
        raise ValueError('Incomplete or duplicate results; no aggregate score')
    by_id = {r['id']: r for r in results}
    if set(by_id) != {r['id'] for r in rows}:
        raise ValueError('Unexpected result IDs')
    loaded = [e for e in events if e.get('event') == 'loaded']
    if len(loaded) != 1 or loaded[0].get('model') != 'whisper-large-v3-turbo-q5_0':
        raise ValueError('Missing Turbo engine identity')
    summary = {'engine': loaded[0], 'research_only': True, 'CP4_eligible': False, 'groups': {}}
    for category in ('clean', 'challenging'):
        words = errors = elapsed = duration = 0
        for row in rows:
            if row['category'] != category:
                continue
            result = by_id[row['id']]
            n = len(normalize(row['actual_heard_transcript']))
            if n == 0 or result['elapsed_ms'] < 0:
                raise ValueError('Invalid denominator/timing')
            words += n
            errors += round(word_error_rate(row['actual_heard_transcript'], result['text']) * n)
            elapsed += result['elapsed_ms'] / 1000
            duration += row['duration_seconds']
        summary['groups'][category] = {'errors': errors, 'reference_words': words,
            'wer': errors / words, 'inference_seconds': elapsed, 'audio_seconds': duration,
            'rtf_excluding_load': elapsed / duration}
    return summary


def adb(*args, data=None, timeout=30):
    r = subprocess.run(['adb', *args], input=data, capture_output=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(r.stderr.decode(errors='replace') or r.stdout.decode(errors='replace'))
    return r.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--run', action='store_true', help='Explicitly run instrumentation; application must be idle')
    args = parser.parse_args()
    manifest = args.manifest or args.dataset / 'manifest_curation.json'
    rows, files = prepare(args.dataset, manifest)
    print('PASS: 30 WAV hashes, formats, durations and reviewed references verified.', flush=True)
    if not args.run:
        print('Validation only; no device operation. Use --run after installing the matching signed test APK.')
        return
    if adb('shell', 'settings', 'get', 'global', 'airplane_mode_on').strip() != b'1' or adb('shell', 'settings', 'get', 'global', 'wifi_on').strip() != b'0':
        raise RuntimeError('Enable airplane mode and turn Wi-Fi off first')
    token = uuid.uuid4().hex
    local = Path.home() / 'Downloads' / ('Subloka-turbo-' + token)
    local.mkdir()
    (local / 'manifest.json').write_bytes(manifest.read_bytes())
    remote = 'files/research-' + token
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w') as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(remote + '/' + name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    adb('exec-in', 'run-as', PACKAGE, 'tar', '-xf', '-', data=archive.getvalue())
    print('Running 30 samples; report directory:', local, flush=True)
    print('Keep device awake. Results are retained in app-private ' + remote, flush=True)
    output = None
    try:
        log = adb('shell', 'am', 'instrument', '-w', '-r', '-e', 'class', 'app.subloka.TurboResearchBenchmarkTest',
            '-e', 'research', 'turbo30', '-e', 'fixture', token,
            PACKAGE + '.test/androidx.test.runner.AndroidJUnitRunner', timeout=10800).decode(errors='replace')
        (local / 'instrumentation.txt').write_text(log, encoding='utf-8')
        verify(log, 1)
    finally:
        # Retain partial evidence even if instrumentation fails; never call it a full score.
        try:
            output = adb('exec-out', 'run-as', PACKAGE, 'cat', remote + '/results.jsonl')
            (local / 'results.jsonl').write_bytes(output)
        except RuntimeError:
            print('No results file available; inspect instrumentation log.')
    if output is None:
        raise RuntimeError('Missing results; no score produced')
    events = [json.loads(line) for line in output.decode().splitlines()]
    summary = score(rows, events)
    (local / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    print('Summary:', local / 'summary.json')


if __name__ == '__main__':
    main()

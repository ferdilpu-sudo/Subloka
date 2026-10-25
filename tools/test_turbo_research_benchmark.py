import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import wave
from turbo_research_benchmark import prepare, score


class BenchmarkTest(unittest.TestCase):
    def fixture(self, root):
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b'\0\0' * 160)
        raw = buffer.getvalue()
        rows = []
        for group, count in [('clean', 20), ('challenging', 10)]:
            for i in range(1, count + 1):
                sid = f'id-{group}-{i:02}'
                (root / (sid + '.wav')).write_bytes(raw)
                rows.append(dict(id=sid, category=group, language='id', audio=sid + '.wav',
                    audio_sha256=hashlib.sha256(raw).hexdigest(), duration_seconds=.01,
                    human_reference_reviewed=True, actual_heard_transcript='Satu dua tiga'))
        manifest = root / 'manifest.json'
        manifest.write_text(json.dumps(dict(not_eligible_for_private_holdout_or_CP4=True, samples=rows)))
        return rows, manifest

    def test_valid_fixture_and_hash_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); rows, m = self.fixture(root)
            self.assertEqual(len(prepare(root, m)[1]), 31)
            (root / rows[0]['audio']).write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'): prepare(root, m)

    def test_duplicate_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); rows, m = self.fixture(root)
            data = json.loads(m.read_text()); data['samples'][1] = data['samples'][0]
            m.write_text(json.dumps(data))
            with self.assertRaises(ValueError): prepare(root, m)

    def test_weighted_score_and_incomplete_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            rows, _ = self.fixture(Path(temp))
            results = [dict(event='loaded', model='whisper-large-v3-turbo-q5_0', load_ms=10)] + [dict(event='sample', id=r['id'], text='satu tiga', elapsed_ms=20) for r in rows]
            with self.assertRaises(ValueError): score(rows, results)
            results.append(dict(event='complete', count=30))
            summary = score(rows, results)
            self.assertAlmostEqual(summary['groups']['clean']['wer'], 1/3)
            self.assertEqual(summary['groups']['clean']['errors'], 20)
            self.assertFalse(summary['CP4_eligible'])
            results[1] = results[0]
            with self.assertRaises(ValueError): score(rows, results)


if __name__ == '__main__': unittest.main()

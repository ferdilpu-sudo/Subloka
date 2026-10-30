import json
import io
from unittest.mock import patch
import tempfile
import unittest
import zipfile
from pathlib import Path
from collect_dependency_notices import collect, coordinates, pom_url, archive_notices, fetch_pom

REPORT = '''releaseRuntimeClasspath
+--- demo:one:1 -> 2
+--- demo:one:2 (*)
+--- demo:constraint:1 (c)
+--- demo:from-bom -> 3
+--- project ':app'
+--- demo:missing:1
BUILD SUCCESSFUL
'''

class NoticeCollectionTest(unittest.TestCase):
    def test_resolution_constraints_and_failure(self):
        self.assertEqual(['demo:from-bom:3', 'demo:missing:1', 'demo:one:2'], coordinates(REPORT))
        for invalid in ('', REPORT.replace('BUILD SUCCESSFUL', 'BUILD FAILED'), REPORT + '\n+--- demo:bad:1 FAILED'):
            with self.assertRaises(ValueError):
                coordinates(invalid)

    def test_evidence_is_scoped_hashed_and_missing_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'cache/demo/one/2/hash'
            folder.mkdir(parents=True)
            (folder / 'one-2.pom').write_text('<project/>')
            with zipfile.ZipFile(folder / 'one-2.jar', 'w') as z:
                z.writestr('../../LICENSE.txt', 'license evidence')
                z.writestr('classes/Example.class', b'not a notice')
            (root / 'report').write_text(REPORT)
            result = collect(root / 'report', root / 'cache', root / 'out')
            _, missing, present = result['dependencies']
            self.assertTrue(missing['pom_missing'])
            self.assertFalse(present['pom_missing'])
            self.assertEqual(1, len(present['notices']))
            digest = present['notices'][0]['sha256']
            self.assertEqual('license evidence', (root / 'out/blobs' / digest).read_text())
            self.assertFalse((root / 'LICENSE.txt').exists())
            self.assertFalse(json.loads((root / 'out/inventory.json').read_text())['complete_license_audit'])
            with self.assertRaises(FileExistsError):
                collect(root / 'report', root / 'cache', root / 'out')

    def test_nested_notice_and_source_routing(self):
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, 'w') as jar:
            jar.writestr('META-INF/NOTICE', 'nested notice')
        aar = io.BytesIO()
        with zipfile.ZipFile(aar, 'w') as out:
            out.writestr('classes.jar', nested.getvalue())
        with zipfile.ZipFile(aar) as archive:
            self.assertEqual([('classes.jar!/META-INF/NOTICE', b'nested notice')], list(archive_notices(archive)))
        self.assertTrue(pom_url('androidx.core:core:1.0').startswith('https://dl.google.com/'))
        self.assertTrue(pom_url('com.google.guava:guava:1.0').startswith('https://repo.maven.apache.org/'))
        with self.assertRaises(ValueError):
            pom_url('../bad:name:1')

    def test_download_rejects_non_pom_and_oversized_nested_notice(self):
        with patch('collect_dependency_notices.urllib.request.urlopen', return_value=io.BytesIO(b'<html/>')):
            with self.assertRaises(ValueError):
                fetch_pom('demo:one:1')
        content = io.BytesIO()
        with zipfile.ZipFile(content, 'w', compression=zipfile.ZIP_DEFLATED) as out:
            out.writestr('NOTICE', b'x' * (4 * 1024 * 1024 + 1))
        with zipfile.ZipFile(content) as archive:
            with self.assertRaises(ValueError):
                list(archive_notices(archive))

    def test_missing_remote_pom_is_visible_and_success_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / 'report'
            report.write_text(REPORT)
            def fake(coordinate):
                if coordinate == 'demo:one:2':
                    return 'https://repo.maven.apache.org/example.pom', b'<project/>'
                raise OSError('network unavailable')
            with patch('collect_dependency_notices.fetch_pom', side_effect=fake):
                rows = collect(report, root / 'cache', root / 'out', True)['dependencies']
            self.assertTrue(rows[0]['pom_missing'])
            self.assertEqual('OSError', rows[0]['pom_fetch_error'])
            self.assertFalse(rows[-1]['pom_missing'])
            self.assertIn('source_url', rows[-1]['poms'][0])

if __name__ == '__main__':
    unittest.main()

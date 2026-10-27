import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from collect_dependency_notices import collect, coordinates

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

if __name__ == '__main__':
    unittest.main()

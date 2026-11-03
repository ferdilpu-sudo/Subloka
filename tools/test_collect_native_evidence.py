import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect_native_evidence as collector


class NativeEvidenceTest(unittest.TestCase):
    def test_exact_bytes_scope_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / "engine/asr/.cxx/Release/hash/arm64-v8a"
            build.mkdir(parents=True)
            data = b"build libengine.so: CXX_SHARED_LIBRARY_LINKER libc++_static.a\n"
            (build / "build.ninja").write_bytes(data)
            (build / "private.txt").write_text("not in allowlist")
            ndk = root / "ndk"
            ndk.mkdir()
            (ndk / "source.properties").write_text("Pkg.Revision = 28.2.13676358\n")
            out = root / "out"
            report = collector.collect(root, ndk, out)
            self.assertEqual(len(report["files"]), 2)
            copied = next(f for f in report["files"] if f["kind"] == "build")
            self.assertEqual(copied["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual((out / "build" / copied["path"]).read_bytes(), data)
            self.assertIn("engine/translation/.cxx build metadata", report["missing"])
            self.assertIn("ndk/NOTICE.toolchain", report["missing"])
            self.assertEqual(report["review_status"], "UNREVIEWED")

    def test_limits_and_external_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / "engine/asr/.cxx"
            build.mkdir(parents=True)
            (build / "build.ninja").write_bytes(b"x" * 20)
            external = root / "private"
            external.write_text("secret")
            (build / "CMakeCache.txt").symlink_to(external)
            with patch.object(collector, "LIMIT", 10):
                report = collector.collect(root, root / "absent", root / "out")
            self.assertEqual({f["status"] for f in report["files"]},
                             {"size_limit", "rejected_symlink"})
            self.assertFalse((root / "out/build").exists())


if __name__ == "__main__":
    unittest.main()

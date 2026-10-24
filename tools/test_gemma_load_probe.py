"""Exercise the actual C++ file switch with debug and production definitions."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LoadProbeTest(unittest.TestCase):
    def test_debug_opt_in_and_release_isolation(self):
        compiler = shutil.which("g++")
        self.assertIsNotNone(compiler, "g++ required for native load-policy regression")
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            source = work / "probe.cpp"
            source.write_text('''
#include "gemma_load_probe.h"
#include <iostream>
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    std::cout << (gemmaReadLoadProbe(argv[1]) ? "read" : "default");
}
''')
            marker = work / "load-mode-probe.txt"
            for debug in (False, True):
                exe = work / ("debug-probe" if debug else "release-probe")
                subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                                *(["-DSUBLOKA_TRANSLATION_MEMORY_PROBE"] if debug else []),
                                "-I", str(ROOT / "engine/translation/src/main/cpp"),
                                str(source), "-o", str(exe)], check=True)
                for content in (None, b"", b"read", b"read\n", b"read\r\n",
                                b"READ", b"read extra", b"read\x00", b"read\n" + b"x" * 100):
                    if marker.exists():
                        marker.unlink()
                    if content is not None:
                        marker.write_bytes(content)
                    actual = subprocess.check_output([str(exe), str(work / "model.gguf")], text=True)
                    expected = "read" if debug and content in (b"read", b"read\n", b"read\r\n") else "default"
                    self.assertEqual(actual, expected, (debug, content))
                self.assertEqual(subprocess.check_output([str(exe), "model.gguf"], text=True), "default")


if __name__ == "__main__":
    unittest.main()

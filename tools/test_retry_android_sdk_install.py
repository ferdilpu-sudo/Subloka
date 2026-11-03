"""Offline regression tests for transient Android SDK installer retries."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("retry_android_sdk_install.sh")


class AndroidSdkRetryTest(unittest.TestCase):
    def run_mock(self, failures_before_success):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mock = root / "fake_sdkmanager.py"
            counter = root / "counter.txt"
            mock.write_text(
                "import os, sys\n"
                "from pathlib import Path\n"
                "assert sys.argv[1:] == ['--channel=3', 'ndk;28.2.13676358']\n"
                "counter = Path(os.environ['MOCK_COUNTER'])\n"
                "attempt = int(counter.read_text()) + 1 if counter.exists() else 1\n"
                "counter.write_text(str(attempt))\n"
                "sys.exit(1 if attempt <= int(os.environ['MOCK_FAILURES']) else 0)\n",
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "MOCK_COUNTER": str(counter),
                "MOCK_FAILURES": str(failures_before_success),
                "SUBLOKA_SDK_RETRY_DELAY_SECONDS": "0",
            }
            result = subprocess.run(
                ["bash", str(SCRIPT), sys.executable, str(mock),
                 "--channel=3", "ndk;28.2.13676358"],
                capture_output=True, text=True, env=env, timeout=15,
            )
            return result, int(counter.read_text())

    def test_retries_two_transient_errors_then_succeeds(self):
        result, attempts = self.run_mock(2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(attempts, 3)
        self.assertIn("completed on attempt 3", result.stdout)

    def test_persistent_failure_aborts_after_three_attempts(self):
        result, attempts = self.run_mock(99)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(attempts, 3)
        self.assertIn("failed after 3 attempts", result.stderr)

    def test_first_success_does_not_run_extra_attempts(self):
        result, attempts = self.run_mock(0)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(attempts, 1)


if __name__ == "__main__":
    unittest.main()

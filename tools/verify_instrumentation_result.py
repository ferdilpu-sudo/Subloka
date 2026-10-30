"""Fail closed: adb can exit zero even when instrumentation crashes or tests fail."""
import argparse
import re
from pathlib import Path


def verify(text, expected_tests=None):
    if re.search(r"FAILURES!!!|INSTRUMENTATION_FAILED|shortMsg=|Process crashed|INSTRUMENTATION_STATUS_CODE: -(?:1|2)", text):
        raise ValueError("Instrumentation reported a failure")
    summary = re.search(r"OK \((\d+) tests?\)", text)
    codes = re.findall(r"INSTRUMENTATION_CODE:\s*(-?\d+)", text)
    if not summary or int(summary[1]) < 1 or codes != ["-1"]:
        raise ValueError("Missing successful, nonempty instrumentation completion")
    if expected_tests is not None and int(summary[1]) != expected_tests:
        raise ValueError("Unexpected instrumentation test count")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--expected-tests", type=int)
    args = parser.parse_args()
    verify(args.log.read_text(encoding="utf-8"), args.expected_tests)
    print("Instrumentation result verified")

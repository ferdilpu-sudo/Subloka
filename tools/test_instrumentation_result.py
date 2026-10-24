import unittest
from verify_instrumentation_result import verify


class InstrumentationResultTest(unittest.TestCase):
    def test_completed_nonempty_run(self):
        verify("OK (3 tests)\nINSTRUMENTATION_CODE: -1", 3)

    def test_single_test(self):
        verify("OK (1 test)\nINSTRUMENTATION_CODE: -1", 1)

    def test_rejects_crash_failure_and_truncation(self):
        for text in [
            "INSTRUMENTATION_RESULT: shortMsg=Process crashed\nINSTRUMENTATION_CODE: 0",
            "FAILURES!!!\nTests run: 3, Failures: 1\nINSTRUMENTATION_CODE: -1",
            "OK (3 tests)",
            "INSTRUMENTATION_CODE: -1",
            "OK (0 tests)\nINSTRUMENTATION_CODE: -1",
            "OK (3 tests)\nINSTRUMENTATION_CODE: 0",
            "OK (3 tests)\nINSTRUMENTATION_CODE: -1\nINSTRUMENTATION_CODE: 0",
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                verify(text)

    def test_expected_class_did_not_run(self):
        with self.assertRaises(ValueError):
            verify("OK (2 tests)\nINSTRUMENTATION_CODE: -1", 3)


if __name__ == "__main__":
    unittest.main()

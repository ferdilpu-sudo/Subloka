import unittest
from unittest.mock import patch

import translation_resource_probe as probe


class ResourceProbeTest(unittest.TestCase):
    def test_proc_fields_with_spaces_and_parentheses_in_name(self):
        fields = [str(i) for i in range(3, 53)]
        fields[0] = "R"
        parsed = probe.parse_stat("123 (app worker ) name) " + " ".join(fields))
        self.assertEqual(parsed, {"minor_faults": 10, "major_faults": 12,
                                  "cpu_ticks": 29, "start_ticks": 22, "resident_pages": 24})

    def test_deltas_exclude_children_and_reject_restart(self):
        old = {"minor_faults": 10, "major_faults": 20, "cpu_ticks": 30, "start_ticks": 100}
        new = {**old, "major_faults": 25, "cpu_ticks": 130}
        self.assertEqual(probe.delta(old, new), {"minor_faults": 0, "major_faults": 5, "cpu_ticks": 100})
        with self.assertRaises(RuntimeError):
            probe.delta(old, {**new, "start_ticks": 101})

    def test_adb_failure_is_not_treated_as_a_measurement(self):
        with patch.object(probe, "adb", side_effect=RuntimeError("permission denied")):
            with self.assertRaises(RuntimeError):
                probe.sample("123")


if __name__ == "__main__":
    unittest.main()

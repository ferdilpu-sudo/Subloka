"""Offline synthetic regressions for read-only T10 candidate feasibility."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr, redirect_stdout
import io

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_asr_next_feasibility import (
    ALLOWED_QUERIES, CANDIDATES, adb_devices, assess,
    parse_battery_c, parse_data_free_kib, parse_mem_total, probe_device,
    radio_setting, read_frozen_pins, main,
)

PINS = {"asr": "a"*64, "small": "b"*64, "cp4": "c"*64}
DEVICE = {
    "model": "SO-03L",
    "abi": "arm64-v8a",
    "mem": "MemTotal:        5500000 kB\nMemFree: 400000 kB\n",
    "df": "Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/dm-5 55000000 52900000 2100000 97% /data\n",
    "battery": "Current Battery Service state:\n  temperature: 372\n",
    "airplane": "1\n",
    "wifi": "0\n",
}


class FeasibilityTests(unittest.TestCase):
    def test_committed_evidence_pins_pass_without_device_or_network(self):
        pins = read_frozen_pins()
        self.assertEqual(set(pins), set(PINS))
        result = assess(pins, None)
        self.assertEqual(result["CP4"], "BLOCKED")
        self.assertEqual(result["status"], "RESEARCH_ONLY_NO_MODEL_SELECTED")
        self.assertIsNone(result["device_probe"])

    def test_catalog_only_language_verified_models(self):
        self.assertEqual(len(CANDIDATES), 2)
        self.assertEqual(len(set(x["id"] for x in CANDIDATES)), 2)
        for x in CANDIDATES:
            self.assertTrue(x["indonesian_explicitly_supported"])
            self.assertTrue(x["source"].startswith("https://"))
            self.assertFalse(x["pinned_archive_sha256_verified"])
        self.assertNotIn("vosk", " ".join(x["id"] for x in CANDIDATES))

    def test_no_model_download_or_sony_promotion(self):
        report = assess(PINS, None)
        self.assertEqual(report["T11"], "TODO")
        for candidate in report["candidates"]:
            self.assertFalse(candidate["ready_for_model_download"])
            self.assertFalse(candidate["ready_for_sony_inference"])
            self.assertFalse(candidate["ready_for_cp4_promotion"])
            self.assertEqual(len(candidate["requirements_before_download"]), 5)

    def test_adb_exactly_one_ready_device(self):
        self.assertEqual(adb_devices("List of devices attached\nR58M902144 device usb:1-1\n"),
                         "R58M902144")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            adb_devices("List of devices attached\n")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            adb_devices("List of devices attached\nR58M001 device\nR58M002 device\n")
        with self.assertRaisesRegex(ValueError, "not ready"):
            adb_devices("List of devices attached\nR58M001 unauthorized\n")

    def test_memory_memtotal_strict(self):
        self.assertEqual(parse_mem_total(DEVICE["mem"]), 5500000)
        for bad in ["", "MemTotal: 0 kB", "MemTotal: not-a-number kB"]:
            with self.assertRaises(ValueError):
                parse_mem_total(bad)

    def test_df_available_kib_strict(self):
        self.assertEqual(parse_data_free_kib(DEVICE["df"]), 2100000)
        with self.assertRaises(ValueError):
            parse_data_free_kib("Filesystem 1K-blocks Used Available Use% Mounted on\n/dev 2 1 1 20% /cache\n")
        with self.assertRaises(ValueError):
            parse_data_free_kib("bad output")


    def test_df_android_toybox_mounted_on_header_variants(self):
        # Toybox emits TWO header tokens "Mounted on" but one row token "/data".
        self.assertEqual(parse_data_free_kib(
            "Filesystem 1K-blocks Used Available Use% Mounted on\n"
            "/dev/block/dm-5 55000000 52900000 2100000 97% /data\n"
        ), 2100000)
        # Some implementations compress the mount header to a single token.
        for mount_label in ("Mounted", "Mounted_on", "Mountpoint"):
            with self.subTest(header=mount_label):
                self.assertEqual(parse_data_free_kib(
                    "Filesystem 1024-blocks Used Avail Use% " + mount_label + "\n"
                    "/dev/block/dm-5\t55000000\t52900000\t2100000\t97%\t/data\n"
                ), 2100000)

    def test_df_fail_closed_on_wrong_mount_or_extra_rows(self):
        header = "Filesystem 1K-blocks Used Available Use% Mounted on\n"
        row = "/dev/block/dm-5 55000000 52900000 2100000 97% /data\n"
        for malformed in (
            header + row + "/dev/block/dm-6 200000 100000 100000 50% /cache\n",
            header + row.replace("/data", "/cache"),
            header + row.replace("2100000", "abc"),
            header + row.replace("97%", "not-percent"),
            header + row.replace("55000000", "1"),
        ):
            with self.subTest(text=malformed):
                with self.assertRaises(ValueError):
                    parse_data_free_kib(malformed)

    def test_df_fail_closed_on_missing_or_misordered_columns(self):
        row = "/dev/block/dm-5 55000000 52900000 2100000 97% /data\n"
        for header in (
            "Filesystem 1K-blocks Used Free Use% Mounted on\n",
            "Filesystem 1K-blocks Available Used Use% Mounted on\n",
            "Filesystem Used Available Use% Mounted on\n",
            "Filesystem 1K-blocks Used Available Mounted on\n",
        ):
            with self.subTest(header=header):
                with self.assertRaises(ValueError):
                    parse_data_free_kib(header + row)

    def test_battery_proxy_checked_not_cpu(self):
        self.assertEqual(parse_battery_c(DEVICE["battery"]), 37.2)
        with self.assertRaises(ValueError):
            parse_battery_c("temperature: 900\n")
        with self.assertRaises(ValueError):
            parse_battery_c("No reported battery temperature")

    def test_radio_settings_are_verifiable_only(self):
        self.assertEqual(radio_setting("1\n", "airplane"), 1)
        self.assertEqual(radio_setting("0\n", "wifi"), 0)
        with self.assertRaisesRegex(ValueError, "Unverified"):
            radio_setting("null", "wifi")

    def test_probe_mock_only_allowed_read_commands_and_serial(self):
        commands = []
        def fake_query(adb, args):
            self.assertEqual(adb, "adb")
            commands.append(args)
            if args == ["devices", "-l"]:
                return "List of devices attached\nR58M902144 device usb:1-1\n"
            self.assertEqual(args[:2], ["-s", "R58M902144"])
            for key, tail in ALLOWED_QUERIES.items():
                if args[2:] == list(tail):
                    return DEVICE[key]
            raise AssertionError("Undocumented mutating ADB command: " + str(args))

        result = probe_device("adb", fake_query)
        self.assertEqual(result["device_model"], "SO-03L")
        self.assertEqual(result["abi"], "arm64-v8a")
        self.assertEqual(result["battery_c"], 37.2)
        self.assertEqual(result["airplane_mode_on"], 1)
        self.assertEqual(result["wifi_on"], 0)
        self.assertEqual(len(result["device_serial_sha256_prefix"]), 12)
        self.assertEqual(len(commands), len(ALLOWED_QUERIES) + 1)
        self.assertNotIn("R58M902144", json.dumps(result))

    def test_published_weight_is_not_runtime_ram_claim(self):
        def fake_query(adb, args):
            if args == ["devices", "-l"]:
                return "List of devices attached\nR58M902144 device\n"
            return next(DEVICE[key] for key, tail in ALLOWED_QUERIES.items()
                        if args[2:] == list(tail))
        device = probe_device("adb", fake_query)
        report = assess(PINS, device)
        self.assertEqual(report["CP4"], "BLOCKED")
        self.assertEqual(report["device_probe"]["mem_total_kib"], 5500000)
        for x in report["candidates"]:
            self.assertIsInstance(x["rough_two_copies_of_weights_fit_data"], bool)
            self.assertFalse(x["ready_for_model_download"])
            self.assertFalse(x["host_accuracy_verified"])
            self.assertFalse(x["sony_performance_verified"])

    def test_broken_pin_fails_closed(self):
        for k in PINS:
            changed = dict(PINS)
            changed[k] = "invalid"
            with self.assertRaisesRegex(ValueError, "evidence pins"):
                assess(changed, None)
        with self.assertRaises(ValueError):
            assess({"asr": "a"*64}, None)

    def test_main_without_adb_writes_once_never_promotes(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "feasibility.json"
            argv = ["t10_asr_next_feasibility.py", "--json", str(output)]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["CP4"], "BLOCKED")
            self.assertIsNone(payload["device_probe"])
            self.assertFalse(payload["candidates"][0]["ready_for_model_download"])
            saved = output.read_bytes()
            with patch.object(sys, "argv", argv), redirect_stderr(io.StringIO()):
                self.assertEqual(main(), 1)
            self.assertEqual(output.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()

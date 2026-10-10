"""Synthetic-only tests: at most eight 512-byte TAR metadata requests.

No external network, actual WAVs, corpus data or model is loaded.
"""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_atika_tar_header_walk import (
    EXPECTED_TAR_BYTES, MAX_HEADERS, PINNED_METADATA_SHA,
    RangeNotHonored, SELECTION_NAME, fetch_header, load_selection,
    main, walk_headers,
)
from t10_public_id_corpus import REVISION


def header(name: str, size: int, typ: bytes = tarfile.REGTYPE) -> bytes:
    info = tarfile.TarInfo(name=name)
    info.size = size
    info.type = typ
    return info.tobuf(format=tarfile.USTAR_FORMAT)


class HTTPReply:
    def __init__(self, *, status=206, offset=0, body=None,
                 content_range=None, bad_url=False):
        self.status = status
        self.offset = offset
        self.body = io.BytesIO(body if body is not None else header("fixture/a.wav", 1000))
        self.url = "http://untrusted.invalid" if bad_url else "https://cas-bridge.xethub.hf.co/file"
        self.headers = {
            "Content-Range": content_range or
            f"bytes {offset}-{offset+511}/{EXPECTED_TAR_BYTES}",
            "Content-Length": "512",
        }
        self.read_count = 0
        self.bytes_read = 0

    def geturl(self): return self.url

    def read(self, amount):
        if amount > 513:
            raise AssertionError("Unbounded network read")
        self.read_count += 1
        data = self.body.read(amount)
        self.bytes_read += len(data)
        return data

    def __enter__(self): return self

    def __exit__(self, *_): return False


class BoundedTARHeaderWalkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        p = patch("t10_id_independent_holdout.PRIVATE_BASE", self.base)
        p.start()
        self.addCleanup(p.stop)
        self.workspace = self.base / "public"
        self.workspace.mkdir()
        self.selected = [f"data/imperative/M1/{i:02}.wav" for i in range(30)]
        self.save_selection()

    def save_selection(self):
        data = {
            "schema_version": 1,
            "source": {"immutable_upstream_revision": REVISION},
            "selected_category": "Imperative",
            "source_split": "test",
            "sample_count": 30,
            "metadata_sha256": PINNED_METADATA_SHA,
            "all_audio_downloaded": False,
            "items": [
                {"source_audio_tar_member": p} for p in self.selected
            ],
        }
        (self.workspace / SELECTION_NAME).write_text(
            json.dumps(data), encoding="utf-8"
        )

    def test_accepts_existing_frozen_private_selection_without_rewrite(self):
        p = self.workspace / SELECTION_NAME
        before = p.read_bytes()
        names = load_selection(self.workspace)
        self.assertEqual(names, set(self.selected))
        self.assertEqual(before, p.read_bytes())

    def test_prevents_nonprivate_workspace_and_invalid_selection(self):
        with tempfile.TemporaryDirectory() as outside:
            with self.assertRaisesRegex(ValueError, "gitignored"):
                load_selection(Path(outside))
        self.selected[0] = "../../leak.wav"
        self.save_selection()
        with self.assertRaisesRegex(ValueError, "unsafe"):
            load_selection(self.workspace)

    def test_selection_duplicate_and_wrong_revision_rejected(self):
        self.selected[0] = self.selected[1]
        self.save_selection()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            load_selection(self.workspace)
        self.selected[0] = "data/imperative/M1/00.wav"
        self.save_selection()
        p = self.workspace / SELECTION_NAME
        data = json.loads(p.read_text(encoding="utf-8"))
        data["source"]["immutable_upstream_revision"] = "wrong"
        p.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs"):
            load_selection(self.workspace)

    def test_http_206_must_match_requested_offset_and_size(self):
        start = 4096
        good = HTTPReply(offset=start)
        with patch("t10_atika_tar_header_walk.urllib.request.urlopen", return_value=good) as fn:
            payload = fetch_header(start)
        self.assertEqual(len(payload), 512)
        self.assertEqual(good.bytes_read, 512)
        self.assertEqual(fn.call_count, 1)
        self.assertEqual(fn.call_args.args[0].headers["Range"], "bytes=4096-4607")
        wrong = HTTPReply(offset=0)
        with patch("t10_atika_tar_header_walk.urllib.request.urlopen", return_value=wrong):
            with self.assertRaisesRegex(ValueError, "Content-Range"):
                fetch_header(start)
        self.assertEqual(wrong.bytes_read, 0)

    def test_http_200_never_reads_full_tar_body(self):
        response = HTTPReply(status=200, body=b"x" * 100000)
        with patch("t10_atika_tar_header_walk.urllib.request.urlopen", return_value=response):
            with self.assertRaises(RangeNotHonored):
                fetch_header(0)
        self.assertEqual(response.read_count, 0)
        self.assertEqual(response.bytes_read, 0)

    def test_alignment_and_bounds_before_network(self):
        for offset in (-512, 1, EXPECTED_TAR_BYTES):
            with self.subTest(offset=offset):
                with patch("t10_atika_tar_header_walk.urllib.request.urlopen") as fn:
                    with self.assertRaisesRegex(ValueError, "outside pinned"):
                        fetch_header(offset)
                    fn.assert_not_called()

    def test_strict_513_body_cap_rejects_oversized_partial_content(self):
        response = HTTPReply(body=header("fixture/b.wav", 1000) + b"x")
        with patch("t10_atika_tar_header_walk.urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "exactly 512"):
                fetch_header(0)
        self.assertEqual(response.bytes_read, 513)

    def test_three_member_offsets_derived_from_real_tar_header_sizes(self):
        # 1000 bytes -> padded 1024; following header at 512+1024=1536.
        # 1 byte -> padded 512; next header at 1536+512+512=2560.
        offset_map = {
            0: header("fixture/first.wav", 1000),
            1536: header("fixture/second.wav", 1),
            2560: header("fixture/third.wav", 91364),
        }
        observed = []
        def fake_fetch(offset):
            observed.append(offset)
            return offset_map[offset]
        with patch("t10_atika_tar_header_walk.fetch_header", side_effect=fake_fetch):
            report = walk_headers(3, set(self.selected))
        self.assertEqual(observed, [0, 1536, 2560])
        self.assertEqual(report["headers_scanned"], 3)
        self.assertEqual(report["file_headers_seen"], 3)
        self.assertEqual(report["http_body_bytes_max"], 1545)
        self.assertEqual(report["selected_exact_name_matches_in_scanned_headers"], 0)
        self.assertFalse(report["all_30_clip_offsets_found"])
        self.assertFalse(report["full_tar_or_wav_downloaded"])
        self.assertEqual(report["CP4"], "BLOCKED")

    def test_short_walk_counts_exact_member_match_without_leaking_path(self):
        match = self.selected[0]
        with patch("t10_atika_tar_header_walk.fetch_header", return_value=header(match, 200)):
            report = walk_headers(1, set(self.selected))
        self.assertEqual(report["selected_exact_name_matches_in_scanned_headers"], 1)
        self.assertNotIn(match, json.dumps(report))

    def test_end_of_archive_zero_header_stops_without_reading_audio(self):
        def fake(offset):
            return header("fixture/a.wav", 1) if offset == 0 else b"\0" * 512
        with patch("t10_atika_tar_header_walk.fetch_header", side_effect=fake):
            out = walk_headers(5, set(self.selected))
        self.assertEqual(out["headers_scanned"], 1)
        self.assertTrue(out["tar_end_marker_seen"])

    def test_malformed_header_rejected(self):
        with patch("t10_atika_tar_header_walk.fetch_header", return_value=b"x" * 512):
            with self.assertRaisesRegex(ValueError, "Invalid checksummed"):
                walk_headers(1, set(self.selected))

    def test_max_headers_hard_limit(self):
        for bad in (0, 9, -1):
            with patch("t10_atika_tar_header_walk.fetch_header") as fn:
                with self.assertRaisesRegex(ValueError, "hard capped"):
                    walk_headers(bad, set(self.selected))
                fn.assert_not_called()
        self.assertEqual(MAX_HEADERS, 8)

    def test_cli_reports_only_metadata_without_names(self):
        match = self.selected[0]
        with patch("t10_atika_tar_header_walk.fetch_header", return_value=header(match, 0)):
            with patch.object(sys, "argv", [
                "t10_atika_tar_header_walk.py", "--workspace",
                str(self.workspace), "--max-headers", "1",
            ]), redirect_stdout(io.StringIO()) as buf:
                self.assertEqual(main(), 0)
        output = buf.getvalue()
        self.assertIn("BOUNDED_REMOTE_TAR_HEADER_WALK_ONLY", output)
        self.assertIn("NO WAV SAVED", output)
        self.assertNotIn(match, output)
        self.assertIn('"CP4": "BLOCKED"', output)

    def test_cli_on_ignored_range_returns_2(self):
        with patch("t10_atika_tar_header_walk.fetch_header",
                   side_effect=RangeNotHonored("Range ignored")):
            with patch.object(sys, "argv", [
                "t10_atika_tar_header_walk.py", "--workspace",
                str(self.workspace), "--max-headers", "1",
            ]), redirect_stderr(io.StringIO()):
                self.assertEqual(main(), 2)


if __name__ == "__main__":
    unittest.main()

"""Deterministic regression tests for host-only offline Argos ID->EN screening.

All tests use mock model outputs, fake small ZIPs and existing NEW paragraph
fixtures. No network, actual model, Argos Python package or Android required.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace
import socket
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from t10_translation_argos_protocol import (
    DIAGNOSTIC, MODEL_SHA256, MODEL_REVISION, MODEL_URL, OUTPUT_COLUMNS,
    PILOT_IDS, REVIEW_SHA256, STATUS,
    strict_review, pilot_rows, validate_argos_archive, write_csv, sha256, grade,
)
from t10_translation_strategy_ab_review import fixture_data, REVIEW_COLUMNS
from t10_translation_argos_offline_sbd import (
    ensure_offline_sbd, unwrap_local_cached_translation,
)
from t10_translation_argos_stanza_checkpoint import (
    temporary_legacy_tokenizer_checkpoint, legacy_tokenizer_config_compatible,
)
from t10_translation_argos_candidate import (
    no_network, _generate_pilot, local_paths, isolated_argos_env,
    report,
)


def fake_review_data():
    fixtures = fixture_data()
    fails_id = {"id-ab-05", "id-ab-06", "id-ab-08", "id-ab-09",
                "id-ab-14", "id-ab-18", "id-ab-24", "id-ab-29", "id-ab-30"}
    fails_en = {"en-ab-01", "en-ab-04", "en-ab-09", "en-ab-10",
                "en-ab-16", "en-ab-19", "en-ab-26", "en-ab-29"}
    rows = []
    for i, fixture in enumerate(fixtures):
        order = ("whole", "linewise") if i % 2 == 0 else ("linewise", "whole")
        for strategy in order:
            rejected = fixture["id"] in (fails_id | fails_en)
            rows.append({
                "sample": fixture["id"],
                "source_language": fixture["language"],
                "target_language": "en" if fixture["language"] == "id" else "id",
                "source_text": fixture["text"],
                "strategy": strategy,
                "translation": "synthetic output for a test",
                "latency_ms": "40.0",
                "error": "",
                "call_count": "1" if strategy == "whole" else "2",
                "sequence": str(len(rows) + 1),
                "battery_c": "36.0",
                "status": "MAJOR_MEANING_ERROR" if rejected else "ACCEPT",
                "notes": "synthetic inaccurate meaning" if rejected else "",
            })
    return rows


def write_test_csv(file: Path, fields, rows):
    with file.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_pilot_controls():
    fixtures = fixture_data()[:30]
    failures = {"id-ab-05", "id-ab-06", "id-ab-08", "id-ab-09"}
    return [{**f, "mlkit": {"translation": f"baseline output for {f['id']}",
                           "status": "MAJOR_MEANING_ERROR" if f["id"] in failures else "ACCEPT",
                           "notes": "wrong reference" if f["id"] in failures else ""}}
            for f in fixtures]


class T10ArgosIDToENTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def frozen_review(self):
        path = self.dir / "full-fake-review.csv"
        write_test_csv(path, REVIEW_COLUMNS, fake_review_data())
        return path

    def sample_rows(self):
        controls = make_pilot_controls()
        candidates = {
            sid: {"translation": "model inferred " + sid, "latency_ms": 34.5}
            for sid in PILOT_IDS
        }
        return pilot_rows(controls, candidates)

    def write_raw_session(self):
        path = self.dir / "pilot.csv"
        write_csv(path, self.sample_rows())
        meta = {"raw_sha256": sha256(path), "model_sha256": MODEL_SHA256,
                "status": "HOST_PILOT_COMPLETE_REVIEW_PENDING_NOT_CP4"}
        (self.dir / "session.json").write_text(json.dumps(meta))
        return path, meta

    def completed_review(self, raw, decisions):
        original = list(csv.DictReader(raw.open(encoding="utf-8-sig", newline="")))
        for row in original:
            status = decisions.get(row["sample"], row["mlkit_whole_status"])
            row["candidate_review_status"] = status
            row["candidate_notes"] = "candidate error" if status != "ACCEPT" else ""
        rated = self.dir / "rated.csv"
        write_test_csv(rated, OUTPUT_COLUMNS, original)
        return rated

    def test_first_ten_are_deterministic_and_not_cherry_picked(self):
        self.assertEqual(PILOT_IDS, tuple(f"id-ab-{i:02d}" for i in range(1, 11)))
        self.assertEqual(len(PILOT_IDS), 10)
        self.assertTrue(all(f["language"] == "id" for f in fixture_data()[:30]))

    def test_source_fixture_is_distinct_from_frozen_cp4(self):
        rows = fixture_data()
        self.assertEqual(len(rows), 60)
        self.assertTrue(all(len(row["text"].splitlines()) == 2 for row in rows))

    def test_pinned_offline_model_metadata_is_complete(self):
        self.assertEqual(MODEL_REVISION, "a69e5d5f51945c24ad8653c3255b87320af21a48")
        self.assertEqual(MODEL_SHA256, "b494f6109dd7ceae32cb44cc721a14039abce938dc773a70087e73301ef4fed4")
        self.assertEqual(len(REVIEW_SHA256), 64)
        self.assertTrue(MODEL_URL.startswith("https://huggingface.co/"))
        self.assertTrue(MODEL_REVISION in MODEL_URL)
        self.assertTrue(MODEL_URL.endswith("/translate-id_en-1_9.argosmodel"))

    def test_original_review_sha_has_fail_closed_behavior(self):
        input_file = self.frozen_review()
        with self.assertRaisesRegex(ValueError, "SHA256"):
            strict_review(input_file)

    def test_original_full_review_120_source_rows_grade_guard(self):
        review = self.frozen_review()
        with patch("t10_translation_argos_protocol.sha256", return_value=REVIEW_SHA256):
            result = strict_review(review)
        self.assertEqual(len(result), 30)
        self.assertEqual(sum(r["mlkit"]["status"] == "ACCEPT" for r in result), 21)
        self.assertEqual(tuple(r["id"] for r in result[:10]), PILOT_IDS)

    def test_reviewer_cannot_change_original_source_or_strategies(self):
        review = self.frozen_review()
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        rows[0]["source_text"] = "changed original paragraph"
        write_test_csv(review, REVIEW_COLUMNS, rows)
        with patch("t10_translation_argos_protocol.sha256", return_value=REVIEW_SHA256):
            with self.assertRaisesRegex(ValueError, "source or strategy"):
                strict_review(review)

    def test_reviewer_cannot_edit_reviewed_status_counts(self):
        review = self.frozen_review()
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        next(r for r in rows if r["sample"] == "id-ab-01" and r["strategy"] == "whole")["status"] = "MAJOR_MEANING_ERROR"
        rows[0]["notes"] = "test fake"
        write_test_csv(review, REVIEW_COLUMNS, rows)
        with patch("t10_translation_argos_protocol.sha256", return_value=REVIEW_SHA256):
            with self.assertRaisesRegex(ValueError, "Expected unchanged"):
                strict_review(review)

    def test_model_zip_sha_mismatch_refused(self):
        model = self.dir / "fake.argosmodel"
        model.write_bytes(b"NOT model weights")
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            validate_argos_archive(model)

    def test_zip_traversal_refused_before_argos_install(self):
        model = self.dir / "fake.argosmodel"
        with zipfile.ZipFile(model, "w") as z:
            z.writestr("../outside.txt", "unsafe")
            z.writestr("sample/metadata.json", "{}")
        with patch("t10_translation_argos_protocol.sha256", return_value=MODEL_SHA256), patch(
            "t10_translation_argos_protocol.MODEL_BYTES_MIN", 0
        ):
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                validate_argos_archive(model)

    def test_zip_symlink_refused_before_argos_install(self):
        model = self.dir / "fake.argosmodel"
        symlink = zipfile.ZipInfo("package/symlink")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(model, "w") as z:
            z.writestr("sample/metadata.json", "{}")
            z.writestr(symlink, "target")
        with patch("t10_translation_argos_protocol.sha256", return_value=MODEL_SHA256), patch(
            "t10_translation_argos_protocol.MODEL_BYTES_MIN", 0
        ):
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                validate_argos_archive(model)

    def test_zip_valid_shape_requires_metadata(self):
        model = self.dir / "fake.argosmodel"
        with zipfile.ZipFile(model, "w") as z:
            z.writestr("package/model.bin", b"weights")
        with patch("t10_translation_argos_protocol.sha256", return_value=MODEL_SHA256), patch(
            "t10_translation_argos_protocol.MODEL_BYTES_MIN", 0
        ):
            with self.assertRaisesRegex(ValueError, "metadata.json"):
                validate_argos_archive(model)

    def test_network_is_forbidden_during_local_inference(self):
        with no_network():
            with socket.socket() as sk:
                with self.assertRaisesRegex(RuntimeError, "network is forbidden"):
                    sk.connect(("127.0.0.1", 1))
        # Restore the real methods after the guard exits.
        self.assertTrue(callable(socket.socket.connect))


    def _fake_sbd(self, flavor: str):
        class FakeStanza:
            stanza_lang_code = "id"
            stanza_pipeline = None

        class FakeMini:
            lang = ""

        packages = self.dir / "packages"
        package_path = packages / "translate-id_en-1_9"
        package_path.mkdir(parents=True, exist_ok=True)
        if flavor == "stanza":
            resource = package_path / "stanza"
            resource.mkdir()
            (resource / "resources.json").write_text(
                '{"id":{"packages":{"default":{"tokenize":"gsd"}},'
                '"tokenize":{"gsd":{}}}}', encoding="utf-8"
            )
            model_dir = resource / "id" / "tokenize"
            model_dir.mkdir(parents=True)
            (model_dir / "gsd.pt").write_bytes(b"synthetic, never loaded")
            sentencizer = FakeStanza()
        elif flavor == "minisbd":
            resource = package_path / "minisbd"
            resource.mkdir()
            model = resource / "id.onnx"
            model.write_bytes(b"test fixture only")
            sentencizer = FakeMini()
            sentencizer.lang = str(model)
        else:
            resource = None
            sentencizer = SimpleNamespace()
        pkg = SimpleNamespace(
            package_path=package_path,
            packaged_sbd_path=resource,
            from_code="id",
            to_code="en",
        )
        return (SimpleNamespace(pkg=pkg, sentencizer=sentencizer),
                packages, FakeStanza, FakeMini)


    def _fake_argos_1_11_cached_translation(self):
        # Argos get_installed_languages() exposes CachedTranslation
        # wrapping PackageTranslation, rather than a bare PackageTranslation.
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")

        class FakePackageTranslation:
            def __init__(self):
                self.pkg = direct.pkg
                self.sentencizer = direct.sentencizer
                self.from_lang = SimpleNamespace(code="id")
                self.to_lang = SimpleNamespace(code="en")

        class FakeCachedTranslation:
            def __init__(self, underlying):
                self.underlying = underlying
                self.from_lang = underlying.from_lang
                self.to_lang = underlying.to_lang

        backend = FakePackageTranslation()
        cached = FakeCachedTranslation(backend)
        installed = SimpleNamespace(package_path=backend.pkg.package_path)
        return (cached, backend, installed, packages, stanza_cls, mini_cls,
                FakeCachedTranslation, FakePackageTranslation)

    def test_cached_direct_argos_backend_resolves_and_initializes_offline(self):
        (cached, backend, installed, packages, stanza_cls, mini_cls,
         cached_cls, packaged_cls) = self._fake_argos_1_11_cached_translation()
        resolved = unwrap_local_cached_translation(
            cached, installed, cached_cls=cached_cls, packaged_cls=packaged_cls,
        )
        self.assertIs(resolved, backend)
        captured = {}
        def fake_pipeline(**kwargs):
            captured.update(kwargs)
            return object()
        with no_network():
            mode = ensure_offline_sbd(
                resolved, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                pipeline_factory=fake_pipeline,
            )
        self.assertEqual(mode, "PACKAGED_STANZA_RESOURCES_NO_DOWNLOAD")
        self.assertIsNone(captured["download_method"])
        self.assertIsNotNone(backend.sentencizer.stanza_pipeline)

    def test_direct_backend_without_cached_wrapper_is_rejected(self):
        (cached, backend, installed, packages, stanza_cls, mini_cls,
         cached_cls, packaged_cls) = self._fake_argos_1_11_cached_translation()
        with self.assertRaisesRegex(RuntimeError, "CachedTranslation"):
            unwrap_local_cached_translation(
                backend, installed, cached_cls=cached_cls, packaged_cls=packaged_cls,
            )

    def test_cached_pivot_or_remote_backend_is_rejected(self):
        (cached, backend, installed, packages, stanza_cls, mini_cls,
         cached_cls, packaged_cls) = self._fake_argos_1_11_cached_translation()
        cached.underlying = SimpleNamespace(t1=backend, t2=backend)
        with self.assertRaisesRegex(RuntimeError, "pivot/remote/identity"):
            unwrap_local_cached_translation(
                cached, installed, cached_cls=cached_cls, packaged_cls=packaged_cls,
            )

    def test_cached_backend_from_different_installed_package_is_rejected(self):
        (cached, backend, installed, packages, stanza_cls, mini_cls,
         cached_cls, packaged_cls) = self._fake_argos_1_11_cached_translation()
        installed.package_path = self.dir / "different-installed-package"
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            unwrap_local_cached_translation(
                cached, installed, cached_cls=cached_cls, packaged_cls=packaged_cls,
            )

    def test_cached_backend_wrong_language_pair_is_rejected(self):
        (cached, backend, installed, packages, stanza_cls, mini_cls,
         cached_cls, packaged_cls) = self._fake_argos_1_11_cached_translation()
        backend.to_lang = SimpleNamespace(code="id")
        with self.assertRaisesRegex(RuntimeError, "direct id->en"):
            unwrap_local_cached_translation(
                cached, installed, cached_cls=cached_cls, packaged_cls=packaged_cls,
            )


    def _synthetic_legacy_checkpoint_io(self):
        # Simulate old Stanza 1.2 checkpoint without reading torch/model weights.
        original = {
            "model": {"tokenizer_weight": b"unchanged"},
            "vocab": {"special": "unchanged"},
            "config": {"lang": "id", "dropout": 0.25,
                       "feat_funcs": ["space_before", "all_caps", "numeric",
                                      "end_of_para", "start_of_para"]},
        }
        observed = {"original": original}
        def load_fn(path, *, map_location, weights_only):
            self.assertEqual(map_location, "cpu")
            self.assertIs(weights_only, True)
            self.assertTrue(Path(path).is_file())
            observed["loaded"] = True
            return original
        def save_fn(payload, path):
            observed["saved"] = payload
            observed["saved_path"] = Path(path)
            Path(path).write_bytes(b"synthetic tempfile checkpoint")
        return load_fn, save_fn, observed

    def test_legacy_stanza_metadata_overlay_preserves_original_and_model(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        resources = direct.pkg.packaged_sbd_path / "resources.json"
        legacy = '{"id":{"default_processors":{"tokenize":"gsd"},"tokenize":{"gsd":{}}}}'
        resources.write_text(legacy, encoding="utf-8")
        original_model = (direct.pkg.packaged_sbd_path / "id" / "tokenize" / "gsd.pt").read_bytes()
        observed = {}
        load_fn, save_fn, checkpoint = self._synthetic_legacy_checkpoint_io()
        def fake_pipeline(**kwargs):
            self.assertIsNone(kwargs["download_method"])
            overlay = Path(kwargs["resources_filepath"])
            observed["path"] = overlay
            observed["resource"] = json.loads(overlay.read_text(encoding="utf-8"))
            observed["checkpoint_path"] = Path(kwargs["tokenize_model_path"])
            self.assertTrue(overlay.is_file())
            self.assertTrue(observed["checkpoint_path"].is_file())
            return object()
        with no_network():
            mode = ensure_offline_sbd(
                direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                pipeline_factory=fake_pipeline,
                checkpoint_load_fn=load_fn, checkpoint_save_fn=save_fn,
            )
        self.assertEqual(mode, "PACKAGED_STANZA_LEGACY_METADATA_AND_CHECKPOINT_NO_DOWNLOAD")
        self.assertEqual(observed["resource"]["id"]["packages"],
                         {"default": {"tokenize": "gsd"}})
        self.assertEqual(checkpoint["saved"]["config"]["feat_dropout"], 0.0)
        self.assertFalse(checkpoint["saved"]["config"]["use_dictionary"])
        self.assertEqual(checkpoint["saved"]["config"]["feat_funcs"],
                         ["space_before", "capitalized", "numeric",
                          "end_of_para", "start_of_para"])
        self.assertEqual(len(checkpoint["saved"]["config"]["feat_funcs"]),
                         len(checkpoint["original"]["config"]["feat_funcs"]))
        self.assertIsNone(checkpoint["saved"]["lexicon"])
        self.assertIs(checkpoint["saved"]["model"], checkpoint["original"]["model"])
        self.assertIs(checkpoint["saved"]["vocab"], checkpoint["original"]["vocab"])
        self.assertNotIn("feat_dropout", checkpoint["original"]["config"])
        self.assertEqual(resources.read_text(encoding="utf-8"), legacy)
        self.assertEqual((direct.pkg.packaged_sbd_path / "id" / "tokenize" / "gsd.pt").read_bytes(),
                         original_model)
        self.assertFalse(observed["path"].exists())
        self.assertFalse(observed["checkpoint_path"].exists())
        self.assertIsNotNone(direct.sentencizer.stanza_pipeline)



    def test_legacy_all_caps_feature_equivalent_for_per_character_inputs(self):
        config = {"feat_funcs": ["space_before", "all_caps", "numeric",
                                  "capitalized", "all_caps", "end_of_para"],
                  "use_dictionary": False}
        translated = legacy_tokenizer_config_compatible(config)
        self.assertEqual(translated["feat_funcs"],
                         ["space_before", "capitalized", "numeric",
                          "capitalized", "capitalized", "end_of_para"])
        self.assertEqual(len(translated["feat_funcs"]), len(config["feat_funcs"]))
        self.assertEqual(config["feat_funcs"][1], "all_caps")
        # Earlier Stanza uses str.isupper(), newer Stanza uses
        # str[0].isupper(); inputs are individual Unicode text characters.
        for unit in ("A", "z", "7", " ", "É", "ß", "İ", "Ω", "中", "𝔄"):
            self.assertEqual(unit.isupper(), unit[0].isupper())

    def test_legacy_feature_schema_rejects_unknown_without_silent_drop(self):
        for bad in (["all_caps", "unsupported"], ["ALL_CAPS"],
                    ["../all_caps"], [], "all_caps"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(RuntimeError, "Unrecognized legacy"):
                    legacy_tokenizer_config_compatible({"feat_funcs": bad})

    def test_legacy_dictionary_flag_absent_defaults_false_preserving_explicit_true(self):
        original = {"feat_funcs": ["all_caps", "numeric"]}
        translated = legacy_tokenizer_config_compatible(original)
        self.assertIs(translated["use_dictionary"], False)
        self.assertNotIn("use_dictionary", original)
        explicitly_true = legacy_tokenizer_config_compatible({
            "feat_funcs": ["all_caps"], "use_dictionary": True,
        })
        self.assertIs(explicitly_true["use_dictionary"], True)

    def test_legacy_conversion_keeps_existing_feature_positions_and_config(self):
        original = {
            "feat_funcs": ("end_of_para", "all_caps", "numeric", "space_before"),
            "feat_dropout": 0.3,
            "use_dictionary": False,
            "hidden_dim": 256,
        }
        compatible = legacy_tokenizer_config_compatible(original)
        self.assertIs(type(compatible["feat_funcs"]), tuple)
        self.assertEqual(compatible["feat_funcs"],
                         ("end_of_para", "capitalized", "numeric", "space_before"))
        self.assertEqual(compatible["hidden_dim"], 256)
        self.assertEqual(compatible["feat_dropout"], 0.3)
        self.assertEqual(original["feat_funcs"][1], "all_caps")

    def test_legacy_checkpoint_refuses_malformed_payload(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        model = direct.pkg.packaged_sbd_path
        writes = []
        with self.assertRaisesRegex(RuntimeError, "Unexpected legacy Stanza checkpoint"):
            with temporary_legacy_tokenizer_checkpoint(
                model, "id", "gsd", packages.parent,
                load_fn=lambda *a, **k: {"config": {}, "model": {}},
                save_fn=lambda *a, **k: writes.append(1),
            ):
                pass
        self.assertEqual(writes, [])

    def test_legacy_checkpoint_rejects_untrusted_weights_only_fallback(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        def refuse_old_pickle(*args, **kwargs):
            self.assertIs(kwargs["weights_only"], True)
            raise RuntimeError("unsafe older checkpoint encoding")
        calls = []
        with self.assertRaisesRegex(RuntimeError, "unsafe older checkpoint encoding"):
            with temporary_legacy_tokenizer_checkpoint(
                direct.pkg.packaged_sbd_path, "id", "gsd", packages.parent,
                load_fn=refuse_old_pickle,
                save_fn=lambda *a, **k: calls.append(1),
            ):
                pass
        self.assertEqual(calls, [])

    def test_legacy_checkpoint_already_has_current_fields_no_copy(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        load_fn, save_fn, observed = self._synthetic_legacy_checkpoint_io()
        modern = {**observed["original"],
                  "config": {**observed["original"]["config"], "feat_dropout": 0.05,
                             "feat_funcs": ["space_before", "capitalized", "numeric",
                                            "end_of_para", "start_of_para"],
                             "use_dictionary": False},
                  "lexicon": None}
        with temporary_legacy_tokenizer_checkpoint(
            direct.pkg.packaged_sbd_path, "id", "gsd", packages.parent,
            load_fn=lambda *args, **kwargs: modern,
            save_fn=save_fn,
        ) as (temp_file, mode):
            self.assertIsNone(temp_file)
            self.assertEqual(mode, "PACKAGED_STANZA_LEGACY_METADATA_ONLY_NO_DOWNLOAD")
        self.assertNotIn("saved", observed)

    def test_legacy_checkpoint_cleanup_after_pipeline_failure(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        (direct.pkg.packaged_sbd_path / "resources.json").write_text(
            '{"id":{"default_processors":{"tokenize":"gsd"},"tokenize":{"gsd":{}}}}',
            encoding="utf-8"
        )
        load_fn, save_fn, observed = self._synthetic_legacy_checkpoint_io()
        seen = []
        def bad_pipeline(**kwargs):
            seen.append((Path(kwargs["resources_filepath"]),
                         Path(kwargs["tokenize_model_path"])))
            raise KeyError("subsequent-incompatibility")
        with no_network():
            with self.assertRaisesRegex(RuntimeError, "missing_key='subsequent-incompatibility'"):
                ensure_offline_sbd(
                    direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                    pipeline_factory=bad_pipeline,
                    checkpoint_load_fn=load_fn, checkpoint_save_fn=save_fn,
                )
        self.assertEqual(len(seen), 1)
        self.assertFalse(seen[0][0].exists())
        self.assertFalse(seen[0][1].exists())
        self.assertIsNone(direct.sentencizer.stanza_pipeline)

    def test_legacy_checkpoint_rejects_other_model_location(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        with self.assertRaisesRegex(RuntimeError, "outside the isolated model workspace"):
            with temporary_legacy_tokenizer_checkpoint(
                direct.pkg.packaged_sbd_path, "id", "gsd",
                self.dir / "elsewhere",
                load_fn=lambda *a, **k: {},
                save_fn=lambda *a, **k: None,
            ):
                pass

    def test_current_stanza_resources_do_not_need_metadata_overlay(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        called = {}
        def fake_pipeline(**kwargs):
            called.update(kwargs)
            return object()
        with no_network():
            mode = ensure_offline_sbd(
                direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                pipeline_factory=fake_pipeline
            )
        self.assertEqual(mode, "PACKAGED_STANZA_RESOURCES_NO_DOWNLOAD")
        self.assertNotIn("resources_filepath", called)

    def test_legacy_stanza_selected_local_model_must_exist(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        resources = direct.pkg.packaged_sbd_path / "resources.json"
        resources.write_text(
            '{"id":{"default_processors":{"tokenize":"gsd"},"tokenize":{"gsd":{}}}}',
            encoding="utf-8"
        )
        (direct.pkg.packaged_sbd_path / "id" / "tokenize" / "gsd.pt").unlink()
        called = []
        with no_network():
            with self.assertRaisesRegex(RuntimeError, "could not be initialized offline") as cm:
                ensure_offline_sbd(
                    direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                    pipeline_factory=lambda **kwargs: called.append(kwargs)
                )
        self.assertIn("Legacy Stanza default tokenizer model", str(cm.exception.__cause__))
        self.assertEqual(called, [])

    def test_legacy_stanza_default_model_must_match_resource_listing(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        (direct.pkg.packaged_sbd_path / "resources.json").write_text(
            '{"id":{"default_processors":{"tokenize":"other"},"tokenize":{"gsd":{}}}}',
            encoding="utf-8"
        )
        with no_network():
            with self.assertRaisesRegex(RuntimeError, "could not be initialized offline") as cm:
                ensure_offline_sbd(
                    direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                    pipeline_factory=lambda **kwargs: None
                )
        self.assertIn("absent from resource metadata", str(cm.exception.__cause__))

    def test_legacy_stanza_default_tokenizer_rejects_path_like_name(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        (direct.pkg.packaged_sbd_path / "resources.json").write_text(
            '{"id":{"default_processors":{"tokenize":"../gsd"},"tokenize":{"gsd":{}}}}',
            encoding="utf-8"
        )
        with no_network():
            with self.assertRaisesRegex(RuntimeError, "could not be initialized offline") as cm:
                ensure_offline_sbd(
                    direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                    pipeline_factory=lambda **kwargs: None
                )
        self.assertIn("no safe default tokenizer", str(cm.exception.__cause__))

    def test_bundled_stanza_initialization_forces_no_download(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        captured = {}
        sentinel = object()
        def fake_pipeline(**kwargs):
            captured.update(kwargs)
            return sentinel
        with no_network():
            mode = ensure_offline_sbd(
                direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                pipeline_factory=fake_pipeline
            )
        self.assertEqual(mode, "PACKAGED_STANZA_RESOURCES_NO_DOWNLOAD")
        self.assertIsNone(captured["download_method"])
        self.assertEqual(captured["lang"], "id")
        self.assertEqual(captured["processors"], "tokenize")
        self.assertFalse(captured["use_gpu"])
        self.assertEqual(direct.sentencizer.stanza_pipeline, sentinel)

    def test_stanza_unexpected_network_is_still_blocked(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        def fake_bad_pipeline(**kwargs):
            with socket.socket() as sock:
                sock.connect(("example.com", 443))
        with no_network():
            with self.assertRaisesRegex(RuntimeError, "could not be initialized offline"):
                ensure_offline_sbd(
                    direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                    pipeline_factory=fake_bad_pipeline
                )
        self.assertIsNone(direct.sentencizer.stanza_pipeline)


    def test_stanza_keyerror_reports_only_bounded_offline_resource_metadata(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        def invalid_local_pipeline(**kwargs):
            self.assertIsNone(kwargs["download_method"])
            raise KeyError("packages")
        with no_network():
            with self.assertRaisesRegex(RuntimeError, "missing_key='packages'") as cm:
                ensure_offline_sbd(
                    direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                    pipeline_factory=invalid_local_pipeline
                )
        message = str(cm.exception)
        self.assertIn("resources_languages=['id']", message)
        self.assertIn("local_tokenize_models=['gsd.pt']", message)
        self.assertIn("origin=", message)
        self.assertNotIn(str(self.dir), message)
        self.assertIsNone(direct.sentencizer.stanza_pipeline)

    def test_stanza_malformed_local_resource_diagnostic_fails_closed(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        (direct.pkg.packaged_sbd_path / "resources.json").write_text(
            "{this is invalid json", encoding="utf-8"
        )
        calls = []
        def invalid_local_pipeline(**kwargs):
            calls.append(kwargs)
            raise KeyError("id")
        with no_network():
            with self.assertRaisesRegex(RuntimeError, "resources_read_error=JSONDecodeError"):
                ensure_offline_sbd(
                    direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                    pipeline_factory=invalid_local_pipeline
                )
        self.assertEqual(calls, [])
        self.assertIsNone(direct.sentencizer.stanza_pipeline)

    def test_stanza_without_packaged_resources_fails_closed(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        (direct.pkg.packaged_sbd_path / "resources.json").unlink()
        called = []
        def no_call(**kwargs):
            called.append(kwargs)
        with self.assertRaisesRegex(RuntimeError, "missing bundled Stanza"):
            ensure_offline_sbd(
                direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls,
                pipeline_factory=no_call
            )
        self.assertEqual(called, [])

    def test_sbd_rejects_outside_model_package_directory(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("stanza")
        with self.assertRaisesRegex(RuntimeError, "outside isolated benchmark directory"):
            ensure_offline_sbd(
                direct, self.dir / "another-package-root",
                stanza_cls=stanza_cls, mini_cls=mini_cls,
                pipeline_factory=lambda **kwargs: None,
            )

    def test_bundled_minisbd_onnx_is_offline_accepted(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("minisbd")
        mode = ensure_offline_sbd(
            direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls
        )
        self.assertEqual(mode, "PACKAGED_MINISBD_ONNX_NO_DOWNLOAD")

    def test_minisbd_without_bundled_onnx_is_rejected(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("minisbd")
        list((direct.pkg.package_path / "minisbd").glob("*.onnx"))[0].unlink()
        with self.assertRaisesRegex(RuntimeError, "lacks exactly one bundled ONNX"):
            ensure_offline_sbd(
                direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls
            )

    def test_unknown_sentence_boundary_type_is_rejected(self):
        direct, packages, stanza_cls, mini_cls = self._fake_sbd("unknown")
        with self.assertRaisesRegex(RuntimeError, "Unknown Argos sentence-boundary"):
            ensure_offline_sbd(
                direct, packages, stanza_cls=stanza_cls, mini_cls=mini_cls
            )

    def test_argos_packages_are_isolated_in_benchmark_workspace(self):
        model, packages = local_paths(self.dir)
        self.assertTrue(str(model).startswith(str(self.dir)))
        self.assertTrue(str(packages).startswith(str(self.dir)))
        with patch.dict("sys.modules", {}, clear=False):
            with patch.dict("os.environ", {}, clear=False):
                isolated_argos_env(packages)
                self.assertEqual(__import__("os").environ["ARGOS_PACKAGES_DIR"], str(packages))
                self.assertEqual(__import__("os").environ["ARGOS_DEVICE_TYPE"], "cpu")

    def test_pilot_requires_complete_nonblank_outputs(self):
        controls = make_pilot_controls()
        text = {sid: {"translation": "OK", "latency_ms": 11.0} for sid in PILOT_IDS}
        text["id-ab-04"]["translation"] = ""
        with self.assertRaisesRegex(ValueError, "invalid"):
            pilot_rows(controls, text)

    def test_pilot_rejects_missing_sample_or_reordered_selection(self):
        controls = make_pilot_controls()
        text = {sid: {"translation": "OK", "latency_ms": 11.0} for sid in reversed(PILOT_IDS)}
        with self.assertRaisesRegex(ValueError, "first 10"):
            pilot_rows(controls, text)

    def test_pilot_raw_has_no_autofilled_decisions(self):
        p = self.dir / "pilot.csv"
        write_csv(p, self.sample_rows())
        rows = list(csv.DictReader(p.open(encoding="utf-8-sig", newline="")))
        self.assertEqual(len(rows), 10)
        self.assertEqual(tuple(rows[0]), OUTPUT_COLUMNS)
        self.assertTrue(all(row["candidate_review_status"] == "" for row in rows))
        self.assertEqual(rows[0]["sample"], PILOT_IDS[0])

    def test_grade_requires_all_ten_filled(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {})
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        rows[3]["candidate_review_status"] = ""
        write_test_csv(review, OUTPUT_COLUMNS, rows)
        with self.assertRaisesRegex(ValueError, "missing/invalid"):
            grade(raw, review, meta)

    def test_grade_rejects_model_output_edit(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {})
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        rows[0]["argos_translation"] = "tampered response"
        write_test_csv(review, OUTPUT_COLUMNS, rows)
        with self.assertRaisesRegex(ValueError, "altered"):
            grade(raw, review, meta)

    def test_grade_rejects_missing_reason(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {"id-ab-01": "NEGATION_ERROR"})
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        rows[0]["candidate_notes"] = ""
        write_test_csv(review, OUTPUT_COLUMNS, rows)
        with self.assertRaisesRegex(ValueError, "reason"):
            grade(raw, review, meta)

    def test_no_gain_does_not_promote_candidate(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {})
        outcome = grade(raw, review, meta)
        self.assertEqual(outcome["baseline_accept"], 6)
        self.assertEqual(outcome["argos_accept"], 6)
        self.assertEqual(outcome["verdict"], "NO_BASIS_TO_PROMOTE_FROM_HOST_PILOT")
        self.assertEqual(outcome["cp4"], "BLOCKED")

    def test_two_recoveries_and_no_new_errors_only_promising(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {"id-ab-05": "ACCEPT", "id-ab-06": "ACCEPT"})
        outcome = grade(raw, review, meta)
        self.assertEqual(outcome["candidate_wins"], 2)
        self.assertEqual(outcome["candidate_losses"], 0)
        self.assertEqual(outcome["net_additional_accepted"], 2)
        self.assertEqual(outcome["verdict"], "PROMISING_FOR_FULL_30_AND_NEW_INDEPENDENT_HOLDOUT")
        self.assertEqual(outcome["cp4"], "BLOCKED")

    def test_new_critical_negation_error_vetoes_promotion(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {
            "id-ab-05": "ACCEPT", "id-ab-06": "ACCEPT", "id-ab-01": "NEGATION_ERROR"
        })
        outcome = grade(raw, review, meta)
        self.assertEqual(outcome["new_critical_errors"], ["id-ab-01"])
        self.assertEqual(outcome["verdict"], "NO_BASIS_TO_PROMOTE_FROM_HOST_PILOT")

    def test_review_report_is_immutable_after_first_write(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {})
        first = report(self.dir, review)
        self.assertEqual(first["cp4"], "BLOCKED")
        with self.assertRaisesRegex(FileExistsError, "overwrite"):
            report(self.dir, review)

    def test_mock_pilot_generates_ten_outputs_and_session_without_network(self):
        controls = make_pilot_controls()
        source_review = self.dir / "fake-original-review.csv"
        source_review.write_text("synthetic", encoding="utf-8")
        model = self.dir / "model.argosmodel"
        observed = []
        def mock_translate(source):
            observed.append(source)
            return "SIMULATED " + source
        session = _generate_pilot(
            controls, source_review, model, self.dir, mock_translate,
            enforce_offline=True,
        )
        rows = list(csv.DictReader((session / "pilot.csv").open(encoding="utf-8-sig", newline="")))
        self.assertEqual(len(rows), 10)
        self.assertEqual(len(observed), 10)
        self.assertTrue(all(row["candidate_review_status"] == "" for row in rows))
        self.assertEqual(json.loads((session / "session.json").read_text())["cp4"], "BLOCKED")
        self.assertEqual(json.loads((session / "session.json").read_text())["offline_sbd_mode"],
                         "SYNTHETIC_TEST_ONLY")
        self.assertEqual(json.loads((session / "session.json").read_text())["status"],
                         "HOST_PILOT_COMPLETE_REVIEW_PENDING_NOT_CP4")


if __name__ == "__main__":
    unittest.main()

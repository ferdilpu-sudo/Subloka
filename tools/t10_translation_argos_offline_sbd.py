"""Fail-closed local sentence-boundary setup for Argos Translate 1.11.0.

Argos' packaged Stanza sentencizer lazily calls stanza.Pipeline() with its
default download method (DOWNLOAD_RESOURCES). That can request resources.json
from the network even when the translation model and tokenizer are local.

This setup preserves the SAME Argos sentence-boundary model and translator:
it explicitly initializes the bundled Stanza pipeline with download_method=None
before running the 10 fixed paragraphs. It never downloads, substitutes a
sentence model, or changes the pre-registered scoring thresholds.
"""
from __future__ import annotations

from pathlib import Path
import json
import traceback
from t10_translation_argos_stanza_metadata import local_stanza_metadata
from t10_translation_argos_stanza_checkpoint import temporary_legacy_tokenizer_checkpoint
from contextlib import nullcontext



def unwrap_local_cached_translation(
    translation,
    installed_package,
    *,
    cached_cls=None,
    packaged_cls=None,
):
    """Resolve Argos 1.11's direct CachedTranslation(PackageTranslation).

    Language.get_translation() returns a caching wrapper, not the package
    backend itself. Reject any identity, composite, remote, or other backend;
    never fall back to a different inference engine.
    """
    if cached_cls is None or packaged_cls is None:
        from argostranslate.translate import CachedTranslation, PackageTranslation
        if cached_cls is None:
            cached_cls = CachedTranslation
        if packaged_cls is None:
            packaged_cls = PackageTranslation

    backend = getattr(translation, "underlying", None)
    if not isinstance(translation, cached_cls) or not isinstance(backend, packaged_cls):
        raise RuntimeError(
            "Expected Argos CachedTranslation wrapping one direct PackageTranslation; "
            "pivot/remote/identity backends are forbidden"
        )

    source_codes = (
        getattr(getattr(translation, "from_lang", None), "code", None),
        getattr(getattr(backend, "from_lang", None), "code", None),
        getattr(getattr(backend, "pkg", None), "from_code", None),
    )
    target_codes = (
        getattr(getattr(translation, "to_lang", None), "code", None),
        getattr(getattr(backend, "to_lang", None), "code", None),
        getattr(getattr(backend, "pkg", None), "to_code", None),
    )
    if source_codes != ("id", "id", "id") or target_codes != ("en", "en", "en"):
        raise RuntimeError("Argos translation must be the installed direct id->en package")

    expected_path = getattr(installed_package, "package_path", None)
    backend_path = getattr(backend.pkg, "package_path", None)
    if (expected_path is None or backend_path is None or
            Path(expected_path).resolve() != Path(backend_path).resolve()):
        raise RuntimeError("Argos direct backend does not match the isolated installed package")
    return backend


def stanza_failure_diagnostics(
    local_stanza: Path, lang: str, error: Exception,
) -> str:
    """Give bounded local-only metadata, never model contents or absolute paths."""
    missing = error.args[0] if isinstance(error, KeyError) and len(error.args) == 1 else None
    missing_key = repr(missing)[:100] if isinstance(missing, (str, int)) else "(not a simple key)"
    try:
        data = json.loads((local_stanza / "resources.json").read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            structure = "resources_not_object"
        else:
            languages = sorted(str(x) for x in data.keys())
            entry = data.get(lang)
            if isinstance(entry, dict):
                keys = sorted(str(x) for x in entry.keys())
                token = entry.get("tokenize")
                if isinstance(token, dict):
                    models = sorted(str(x) for x in token.keys())
                else:
                    models = []
                structure = (
                    f"resources_languages={languages[:12]!r}; "
                    f"language_keys={keys[:20]!r}; "
                    f"tokenize_packages={models[:12]!r}"
                )
            else:
                structure = (
                    f"resources_languages={languages[:12]!r}; "
                    "language_entry_missing_or_not_object"
                )
    except (OSError, UnicodeError, ValueError) as resource_error:
        structure = f"resources_read_error={type(resource_error).__name__}"

    # Stanza expects language/tokenize/<package>.pt inside bundled SBD tree.
    local_tokenizers = sorted(
        x.name for x in (local_stanza / lang / "tokenize").glob("*.pt")
        if x.is_file()
    )
    trace = traceback.extract_tb(error.__traceback__)
    origin = " > ".join(
        f"{Path(frame.filename).name}:{frame.name}:{frame.lineno}"
        for frame in trace[-3:]
    )
    return (
        f"missing_key={missing_key}; {structure}; "
        f"local_tokenize_models={local_tokenizers[:12]!r}; "
        f"origin={origin[:240]}"
    )


def ensure_offline_sbd(
    direct,
    packages_dir: Path,
    *,
    stanza_cls=None,
    mini_cls=None,
    pipeline_factory=None,
    checkpoint_load_fn=None,
    checkpoint_save_fn=None,
) -> str:
    """Initialize exclusively bundled local sentence-boundary resources.

    Args injected by tests are for synthetic verification without installing
    Argos, Stanza or an actual model. Real inference uses the package's own
    Stanza model and the upstream stanza.Pipeline with download_method=None.
    """
    if stanza_cls is None or mini_cls is None:
        from argostranslate.sbd import MiniSBDSentencizer, StanzaSentencizer
        stanza_cls = StanzaSentencizer
        mini_cls = MiniSBDSentencizer

    pkg = getattr(direct, "pkg", None)
    sentencizer = getattr(direct, "sentencizer", None)
    path = getattr(pkg, "package_path", None)
    if path is None or sentencizer is None:
        raise RuntimeError("Argos direct translation lacks a local model/SBD package")

    package_path = Path(path).resolve()
    if package_path.parent != packages_dir.resolve():
        raise RuntimeError(
            "Argos direct translation loaded model outside isolated benchmark directory"
        )
    sbd_path = getattr(pkg, "packaged_sbd_path", None)
    if sbd_path is not None:
        sbd_path = Path(sbd_path).resolve()
        if sbd_path.parent != package_path:
            raise RuntimeError("Argos sentence-boundary resources are outside pinned package")

    if isinstance(sentencizer, stanza_cls):
        local_stanza = package_path / "stanza"
        if sbd_path != local_stanza or not (local_stanza / "resources.json").is_file():
            raise RuntimeError(
                "Argos package is missing bundled Stanza resources.json; cannot "
                "initialize offline. No download was attempted. Send only session.json "
                "and package SBD diagnostics, not the model file."
            )
        if pipeline_factory is None:
            from stanza import Pipeline
            pipeline_factory = Pipeline
        try:
            with local_stanza_metadata(
                local_stanza, sentencizer.stanza_lang_code, packages_dir.parent,
            ) as (metadata_file, sbd_mode):
                pipeline_args = {
                    "lang": sentencizer.stanza_lang_code,
                    "dir": str(local_stanza),
                    "processors": "tokenize",
                    "use_gpu": False,
                    "logging_level": "WARNING",
                    "download_method": None,  # No Stanza resource/model downloads.
                }
                checkpoint_context = nullcontext((None, "UNCHANGED"))
                if metadata_file is not None:
                    pipeline_args["resources_filepath"] = metadata_file
                    # The legacy metadata adapter validated this name and the
                    # corresponding local .pt checkpoint before staging.
                    overlay_data = json.loads(
                        Path(metadata_file).read_text(encoding="utf-8")
                    )
                    tokenizer_name = overlay_data[sentencizer.stanza_lang_code][
                        "packages"
                    ]["default"]["tokenize"]
                    checkpoint_context = temporary_legacy_tokenizer_checkpoint(
                        local_stanza, sentencizer.stanza_lang_code,
                        tokenizer_name, packages_dir.parent,
                        load_fn=checkpoint_load_fn, save_fn=checkpoint_save_fn,
                    )
                with checkpoint_context as (temporary_model, checkpoint_mode):
                    if temporary_model is not None:
                        # Stanza accepts tokenize_model_path and loads it
                        # during Pipeline construction, while temp file exists.
                        pipeline_args["tokenize_model_path"] = temporary_model
                    pipeline = pipeline_factory(**pipeline_args)
                    if metadata_file is not None and checkpoint_mode != "UNCHANGED":
                        sbd_mode = checkpoint_mode
        except Exception as error:
            detail = stanza_failure_diagnostics(
                local_stanza, sentencizer.stanza_lang_code, error
            )
            raise RuntimeError(
                "Local bundled Stanza tokenizer could not be initialized offline "
                f"({type(error).__name__}). {detail}. "
                "No network fallback is allowed; report this diagnostic only."
            ) from error
        sentencizer.stanza_pipeline = pipeline
        return sbd_mode

    if isinstance(sentencizer, mini_cls):
        local_mini = package_path / "minisbd"
        model_files = list(local_mini.glob("*.onnx"))
        if sbd_path != local_mini or len(model_files) != 1:
            raise RuntimeError(
                "Argos expects MiniSBD but package lacks exactly one bundled ONNX "
                "model; no automatic MiniSBD model download is allowed"
            )
        # Argos' own MiniSBD lazy detector loads this exact bundled ONNX.
        # Outbound socket connections remain blocked for the entire inference.
        if Path(sentencizer.lang).resolve() != model_files[0].resolve():
            raise RuntimeError("Argos MiniSBD points outside bundled local ONNX model")
        return "PACKAGED_MINISBD_ONNX_NO_DOWNLOAD"

    raise RuntimeError(
        "Unknown Argos sentence-boundary model; fail closed rather than "
        "silently selecting a different tokenizer or downloading a model"
    )

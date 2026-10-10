"""Temporary, offline-only Stanza legacy-resource metadata compatibility.

Some verified Argos packages bundle an older Stanza resources.json schema with
`default_processors` and no `packages` entry. Recent Stanza calls
resources[lang]["packages"] even when only tokenize is requested. Re-express
only the already-selected local tokenizer as packages.default.tokenize in a
temporary metadata copy. NEVER modify installed metadata or model weights.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import re
import tempfile


@contextmanager
def local_stanza_metadata(local_stanza: Path, lang: str, staging_dir: Path):
    """Yield (optional resources_filepath, mode) under caller's no_network guard.

    The overlay is confined to the gitignored isolated benchmark workspace,
    removed after Pipeline initialization, and created only if a uniquely
    selected, already-present tokenizer needs a legacy schema bridge.
    """
    local_stanza = local_stanza.resolve()
    staging_dir = staging_dir.resolve()
    if local_stanza.parent.parent.parent != staging_dir:
        raise RuntimeError("Stanza metadata staging must be inside isolated model workspace")

    resources_file = local_stanza / "resources.json"
    if not resources_file.is_file() or resources_file.stat().st_size > 10_000_000:
        raise RuntimeError("Missing or oversized packaged Stanza resources metadata")
    try:
        resources = json.loads(resources_file.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError) as error:
        raise RuntimeError("Invalid bundled Stanza resources metadata") from error
    if not isinstance(resources, dict) or not isinstance(resources.get(lang), dict):
        raise RuntimeError("Bundled Stanza resources lack the expected language")
    entry = resources[lang]

    if "packages" in entry:
        if not isinstance(entry["packages"], dict):
            raise RuntimeError("Invalid packaged Stanza packages metadata")
        yield None, "PACKAGED_STANZA_RESOURCES_NO_DOWNLOAD"
        return

    defaults = entry.get("default_processors")
    selected = defaults.get("tokenize") if isinstance(defaults, dict) else None
    if not isinstance(selected, str) or re.fullmatch(r"[A-Za-z0-9_+-]{1,64}", selected) is None:
        raise RuntimeError("Legacy bundled Stanza metadata has no safe default tokenizer")
    available = entry.get("tokenize")
    if not isinstance(available, dict) or selected not in available:
        raise RuntimeError("Legacy Stanza default tokenizer is absent from resource metadata")
    selected_file = local_stanza / lang / "tokenize" / (selected + ".pt")
    if not selected_file.is_file():
        raise RuntimeError("Legacy Stanza default tokenizer model is not bundled locally")

    # Only extend the legacy language entry with a current-schema alias. The
    # original resource metadata, original tokenizer, and other fields remain.
    entry["packages"] = {"default": {"tokenize": selected}}
    with tempfile.TemporaryDirectory(
        prefix="t10-stanza-metadata-", dir=str(staging_dir)
    ) as temp:
        overlay = Path(temp) / "resources.json"
        overlay.write_text(json.dumps(resources, ensure_ascii=False), encoding="utf-8")
        yield str(overlay), "PACKAGED_STANZA_LEGACY_METADATA_OVERLAY_NO_DOWNLOAD"

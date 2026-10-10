"""Fail-closed, temporary compatibility for pre-Stanza-1.3 tokenizer checkpoints.

Stanza 1.10.1's Trainer.load requires config['feat_dropout'] and
checkpoint['lexicon'], absent from some legacy Argos-bundled Stanza models.
Create an ephemeral copy with *metadata only* (feature dropout 0.0, lexicon
None); model tensors and vocabulary remain exactly the original objects.
Never overwrite a packaged model, change translation weights, download anything,
or allow unsafe pickle fallback. This is a host-only experimental adapter.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import tempfile


@contextmanager
def temporary_legacy_tokenizer_checkpoint(
    local_stanza: Path,
    lang: str,
    tokenizer_name: str,
    staging_dir: Path,
    *,
    load_fn=None,
    save_fn=None,
):
    """Yield (temporary_model_path, mode), or (None, 'UNCHANGED').

    The caller must validate tokenizer_name against the bundled resource
    metadata first and run entirely inside the existing no_network guard.
    The staging directory must be the parent of the isolated packages folder.
    """
    import re

    local_stanza = local_stanza.resolve()
    staging_dir = staging_dir.resolve()
    if local_stanza.parent.parent.parent != staging_dir:
        raise RuntimeError("Legacy tokenizer is outside the isolated model workspace")
    if re.fullmatch(r"[A-Za-z0-9_+-]{1,64}", tokenizer_name) is None:
        raise RuntimeError("Unsafe legacy tokenizer name")
    source = (local_stanza / lang / "tokenize" / (tokenizer_name + ".pt")).resolve()
    if (source.parent != (local_stanza / lang / "tokenize").resolve()
            or not source.is_file()
            or not 0 < source.stat().st_size <= 200_000_000):
        raise RuntimeError("Missing or oversized local legacy tokenizer checkpoint")

    if load_fn is None or save_fn is None:
        import torch
        if load_fn is None:
            load_fn = torch.load
        if save_fn is None:
            save_fn = torch.save
    # No weights_only=False fallback, even if this refuses an ancient model.
    checkpoint = load_fn(str(source), map_location="cpu", weights_only=True)
    if (not isinstance(checkpoint, dict)
            or not isinstance(checkpoint.get("config"), dict)
            or not isinstance(checkpoint.get("model"), dict)
            or not isinstance(checkpoint.get("vocab"), dict)):
        raise RuntimeError("Unexpected legacy Stanza checkpoint structure; refusing conversion")

    config = checkpoint["config"]
    if "feat_dropout" in config and "lexicon" in checkpoint:
        yield None, "PACKAGED_STANZA_LEGACY_METADATA_ONLY_NO_DOWNLOAD"
        return

    # Older Stanza's tokenizer did not apply feature dropout and did not use
    # lexicon dictionaries. Inference remains eval-mode; zero means no dropout.
    # Nothing in checkpoint['model'] / ['vocab'] is touched or regenerated.
    patched = {**checkpoint}
    patched["config"] = {**config}
    if "feat_dropout" not in patched["config"]:
        patched["config"]["feat_dropout"] = 0.0
    if "lexicon" not in patched:
        patched["lexicon"] = None

    with tempfile.TemporaryDirectory(
        prefix="t10-stanza-checkpoint-", dir=str(staging_dir)
    ) as temp:
        target = Path(temp) / "tokenizer-legacy-compat.pt"
        save_fn(patched, str(target))
        if not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError("Temporary legacy tokenizer checkpoint was not written")
        yield str(target), "PACKAGED_STANZA_LEGACY_METADATA_AND_CHECKPOINT_NO_DOWNLOAD"

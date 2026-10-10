"""Fail-closed, temporary compatibility for pre-Stanza-1.3 tokenizer checkpoints.

Stanza 1.10.1's Trainer.load requires config['feat_dropout'] and
checkpoint['lexicon'], absent from some legacy Argos-bundled Stanza models.
The old all_caps per-character feature matches current capitalized, and old
models do not supply use_dictionary. These are converted in temp metadata only.
Create an ephemeral copy with *metadata only* (feature dropout 0.0, lexicon
None); model tensors and vocabulary remain exactly the original objects.
Never overwrite a packaged model, change translation weights, download anything,
or allow unsafe pickle fallback. This is a host-only experimental adapter.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import tempfile


def legacy_tokenizer_config_compatible(config: dict) -> dict:
    """Preserve the exact per-character feature vector used by old Stanza.

    In Stanza 1.2.3 `all_caps` was defined as `x.isupper()`, while the
    current `capitalized` computes `x[0].isupper()`. The tokenizer dataset
    supplies one Unicode character at a time, so these tests are equivalent.
    Rename the feature only, at the same index, preserving input dimensions
    and all existing checkpoint tensors. Never drop or reorder features.
    """
    raw_features = config.get("feat_funcs")
    supported = frozenset((
        "end_of_para", "start_of_para", "space_before",
        "capitalized", "all_caps", "numeric",
    ))
    if (type(raw_features) not in (list, tuple) or not raw_features
            or any(type(feat) is not str or feat not in supported
                   for feat in raw_features)):
        raise RuntimeError("Unrecognized legacy tokenizer feature configuration")
    updated = dict(config)
    if "all_caps" in raw_features:
        updated["feat_funcs"] = type(raw_features)(
            "capitalized" if feat == "all_caps" else feat
            for feat in raw_features
        )
    # Pre-dictionary Stanza checkpoints did not extract dictionary features.
    # The modern TokenizationDataset reads this key unconditionally.
    if "use_dictionary" not in updated:
        updated["use_dictionary"] = False
    return updated


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
    compatible = legacy_tokenizer_config_compatible(config)
    if "feat_dropout" not in compatible:
        compatible["feat_dropout"] = 0.0
    if ("lexicon" in checkpoint and compatible == config):
        yield None, "PACKAGED_STANZA_LEGACY_METADATA_ONLY_NO_DOWNLOAD"
        return

    # All changes are configuration metadata. Same tensor/embedding weights,
    # same feature vector width and position, same tokenizer vocabulary.
    patched = {**checkpoint}
    patched["config"] = compatible
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

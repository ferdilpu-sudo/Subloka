from __future__ import annotations

import re
import sys


def normalize(text: str) -> list[str]:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^\w\s']", " ", text, flags=re.UNICODE)
    return [token for token in text.split() if token]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref = normalize(reference)
    hyp = normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0

    previous = list(range(len(hyp) + 1))
    for i, ref_word in enumerate(ref, start=1):
        current = [i]
        for j, hyp_word in enumerate(hyp, start=1):
            substitution = previous[j - 1] + (ref_word != hyp_word)
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1] / len(ref)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: t10_wer.py <reference-file> <hypothesis-file>")

    reference = open(sys.argv[1], encoding="utf-8").read()
    hypothesis = open(sys.argv[2], encoding="utf-8").read()
    print(f"{word_error_rate(reference, hypothesis):.4f}")

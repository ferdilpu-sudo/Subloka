#!/usr/bin/env bash
set -euo pipefail

MODELS_DIR="${1:?models directory required}"
WORK_DIR="${2:?work directory required}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$WORK_DIR"

cd "$WORK_DIR"
curl -L --fail --retry 3 -o whisper-v1.9.4.tar.gz \
  "https://github.com/ggml-org/whisper.cpp/archive/refs/tags/v1.9.4.tar.gz"
tar -xzf whisper-v1.9.4.tar.gz

cmake -S whisper.cpp-1.9.4 -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DWHISPER_BUILD_TESTS=OFF \
  -DWHISPER_BUILD_EXAMPLES=ON \
  -DGGML_NATIVE=OFF
cmake --build build --config Release --target whisper-cli -j 2

EN_REF="Rina has three red books and does not sell them."
ID_REF="Rina punya tujuh buku biru dan tidak menjualnya."
printf "%s\n" "$EN_REF" > en.ref.txt
printf "%s\n" "$ID_REF" > id.ref.txt

espeak-ng -v en-us -s 145 -w en.raw.wav "$EN_REF"
espeak-ng -v id -s 145 -w id.raw.wav "$ID_REF"
ffmpeg -loglevel error -y -i en.raw.wav -ar 16000 -ac 1 -c:a pcm_s16le en.wav
ffmpeg -loglevel error -y -i id.raw.wav -ar 16000 -ac 1 -c:a pcm_s16le id.wav

CLI="$WORK_DIR/build/bin/whisper-cli"
if [[ ! -x "$CLI" ]]; then
  echo "whisper-cli was not built" >&2
  exit 1
fi

echo "## whisper.cpp v1.9.4 synthetic bilingual smoke" > summary.md
echo >> summary.md
echo "Synthetic TTS is functional smoke only; it is not CP4 quality evidence." >> summary.md
echo >> summary.md
echo "| Model | Language | WER | Wall sec | Max RSS KB |" >> summary.md
echo "|---|---|---:|---:|---:|" >> summary.md

for model in tiny base; do
  for language in en id; do
    MODEL="$MODELS_DIR/ggml-${model}.bin"
    AUDIO="$WORK_DIR/${language}.wav"
    REF="$WORK_DIR/${language}.ref.txt"
    OUT="$WORK_DIR/${model}-${language}.txt"
    METRICS="$WORK_DIR/${model}-${language}.metrics"

    /usr/bin/time -f "%e %M" -o "$METRICS" \
      "$CLI" -m "$MODEL" -f "$AUDIO" -l "$language" -nt > "$OUT" 2>/dev/null

    if [[ ! -s "$OUT" ]] || ! grep -q "[[:alnum:]]" "$OUT"; then
      echo "Empty transcription for $model/$language" >&2
      exit 1
    fi

    WER="$(python3 "$ROOT/tools/t10_wer.py" "$REF" "$OUT")"
    read -r WALL RSS < "$METRICS"
    echo "| $model | $language | $WER | $WALL | $RSS |" >> summary.md
  done
done

cat summary.md

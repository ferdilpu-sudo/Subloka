#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:?output directory required}"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [[ -z "$SDK_ROOT" ]]; then
  echo "ANDROID_SDK_ROOT/ANDROID_HOME is required" >&2
  exit 1
fi

NDK="$SDK_ROOT/ndk/28.2.13676358"
CMAKE="$SDK_ROOT/cmake/3.22.1/bin/cmake"
NINJA="$SDK_ROOT/cmake/3.22.1/bin/ninja"
TOOLCHAIN="$NDK/build/cmake/android.toolchain.cmake"

test -x "$CMAKE"
test -x "$NINJA"
test -f "$TOOLCHAIN"

mkdir -p "$OUT_DIR"
cd "$OUT_DIR"
if [[ ! -d whisper.cpp-1.9.4 ]]; then
  curl -L --fail --retry 3 -o whisper-v1.9.4.tar.gz \
    "https://github.com/ggml-org/whisper.cpp/archive/refs/tags/v1.9.4.tar.gz"
  tar -xzf whisper-v1.9.4.tar.gz
fi

"$CMAKE" -S whisper.cpp-1.9.4 -B build-android -G Ninja \
  -DCMAKE_MAKE_PROGRAM="$NINJA" \
  -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN" \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-26 \
  -DANDROID_STL=c++_static \
  -DCMAKE_BUILD_TYPE=Release \
  -DWHISPER_BUILD_TESTS=OFF \
  -DWHISPER_BUILD_EXAMPLES=ON \
  -DGGML_OPENMP=OFF \
  -DGGML_NATIVE=OFF

"$CMAKE" --build build-android --target whisper-cli -j 2

CLI="$OUT_DIR/build-android/bin/whisper-cli"
test -f "$CLI"
file "$CLI"
echo "Android arm64 benchmark binary: $CLI"

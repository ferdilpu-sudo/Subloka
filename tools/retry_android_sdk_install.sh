#!/usr/bin/env bash
# Retry transient Android SDK archive/network errors without hiding persistent failures.
set -euo pipefail

if (( $# < 2 )); then
    echo "Usage: retry_android_sdk_install.sh sdkmanager <packages...>" >&2
    exit 2
fi

for attempt in 1 2 3; do
    echo "Android SDK installation attempt ${attempt}/3"
    if "$@"; then
        echo "Android SDK installation completed on attempt ${attempt}"
        exit 0
    fi
    if (( attempt == 3 )); then
        echo "::error::Android SDK package installation failed after 3 attempts" >&2
        exit 1
    fi
    echo "::warning::Android SDK installation attempt ${attempt} failed; retrying" >&2
    sleep "${SUBLOKA_SDK_RETRY_DELAY_SECONDS:-15}"
done

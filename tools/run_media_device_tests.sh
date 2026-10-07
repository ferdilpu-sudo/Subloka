#!/usr/bin/env bash
set +e

./gradlew --stacktrace --info :core:media:connectedDebugAndroidTest
status=$?

if [ "$status" -ne 0 ]; then
  echo "=== Android test XML ==="
  find core/media/build/outputs/androidTest-results -type f -name '*.xml' -print -exec cat {} \; || true
  echo "=== Android test reports ==="
  find core/media/build/reports/androidTests/connected/debug -type f -maxdepth 5 -print 2>/dev/null || true
fi

exit "$status"

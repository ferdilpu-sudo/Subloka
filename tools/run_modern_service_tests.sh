#!/usr/bin/env bash
set -euo pipefail

./gradlew --stacktrace :app:installDebug :app:installDebugAndroidTest
mkdir -p app/build/modern-service-tests
app_package=app.subloka.caption
test_runner=app.subloka.caption.test/androidx.test.runner.AndroidJUnitRunner
permission=android.permission.POST_NOTIFICATIONS

# Retain emulator-only diagnostics even if instrumentation or the verifier fails.
trap 'adb logcat -d -v threadtime > app/build/modern-service-tests/logcat.txt || true' EXIT
adb logcat -c

# Change permissions before instrumentation: revocation can kill the target process.
adb shell am force-stop "$app_package"
adb shell pm grant "$app_package" "$permission"
adb shell am instrument -w -r -e class app.subloka.AsrForegroundServiceTest,app.subloka.TranslationForegroundServiceTest,app.subloka.RenderForegroundServiceTest "$test_runner"   | tee app/build/modern-service-tests/granted.txt
python3 tools/verify_instrumentation_result.py app/build/modern-service-tests/granted.txt --expected-tests 13

adb shell am force-stop "$app_package"
adb shell pm revoke "$app_package" "$permission"
adb shell pm clear-permission-flags "$app_package" "$permission" user-set user-fixed
adb shell am instrument -w -r -e class app.subloka.NotificationDeniedServiceTest "$test_runner"   | tee app/build/modern-service-tests/denied.txt
python3 tools/verify_instrumentation_result.py app/build/modern-service-tests/denied.txt --expected-tests 3

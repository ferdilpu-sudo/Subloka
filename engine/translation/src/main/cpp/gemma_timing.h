#pragma once
#include <chrono>
#include <cstdio>
#ifdef __ANDROID__
#include <android/log.h>
#endif

// Metadata only. Never pass model output, caption text or file paths here.
// Scope lifetime also records partial time when inference throws or is cancelled.
class GemmaPhaseTiming {
    const char *phase;
    unsigned long long attempt;
    std::chrono::steady_clock::time_point started = std::chrono::steady_clock::now();
public:
    int tokens = 0;
    const char *outcome = "interrupted_or_failed";
    GemmaPhaseTiming(const char *phaseName, unsigned long long captionAttempt)
        : phase(phaseName), attempt(captionAttempt) {}
    ~GemmaPhaseTiming() noexcept {
        const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - started).count();
        // PID/thread/timestamp correlate this nested event with the Kotlin session.
#ifdef __ANDROID__
        __android_log_print(ANDROID_LOG_INFO, "SubLokaTranslation",
#else
        std::fprintf(stderr,
#endif
            "native_attempt=%llu phase=%s elapsed_ms=%lld tokens=%d outcome=%s\n",
            attempt, phase, static_cast<long long>(ms), tokens, outcome);
    }
};

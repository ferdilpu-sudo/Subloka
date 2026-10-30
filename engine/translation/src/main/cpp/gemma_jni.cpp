#include <jni.h>
#include "gemma_session.h"
static void fail(JNIEnv *env) { env->ThrowNew(env->FindClass("java/lang/IllegalStateException"), "MODEL_FAILURE: gagal menjalankan model terjemahan."); }
extern "C" JNIEXPORT jlong JNICALL Java_app_subloka_engine_translation_NativeGemma_open(JNIEnv *env, jobject, jstring path) {
    const char *p = env->GetStringUTFChars(path, nullptr); if (!p) return 0;
    GemmaSession *session = nullptr;
    try { session = new GemmaSession(p); } catch (...) { fail(env); }
    env->ReleaseStringUTFChars(path, p); return reinterpret_cast<jlong>(session);
}
extern "C" JNIEXPORT jbyteArray JNICALL Java_app_subloka_engine_translation_NativeGemma_run(JNIEnv *env, jobject, jlong h, jbyteArray bytes, jboolean fromId) {
    try {
        if (!h) throw std::runtime_error("MODEL_FAILURE");
        const auto n = env->GetArrayLength(bytes);
        if (n > 16384) throw std::runtime_error("INPUT_TOO_LONG");
        std::string text(n, '\0'); env->GetByteArrayRegion(bytes, 0, n, reinterpret_cast<jbyte *>(text.data()));
        if (env->ExceptionCheck()) return nullptr;
        auto output = reinterpret_cast<GemmaSession *>(h)->translate(text, fromId);
        auto result = env->NewByteArray(output.size());
        if (result) env->SetByteArrayRegion(result, 0, output.size(), reinterpret_cast<const jbyte *>(output.data()));
        return result;
    } catch (...) { fail(env); return nullptr; }
}
extern "C" JNIEXPORT void JNICALL Java_app_subloka_engine_translation_NativeGemma_cancel(JNIEnv *, jobject, jlong h) { if (h) reinterpret_cast<GemmaSession *>(h)->cancel(); }
extern "C" JNIEXPORT void JNICALL Java_app_subloka_engine_translation_NativeGemma_close(JNIEnv *, jobject, jlong h) { delete reinterpret_cast<GemmaSession *>(h); }

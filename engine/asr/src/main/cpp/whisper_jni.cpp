#include <jni.h>
#include <whisper.h>
#include <atomic>
#include <memory>
#include <string>
#include <vector>

namespace {
struct Session {
    whisper_context *ctx = nullptr;
    std::string vad_path;
    std::atomic<bool> cancelled{false};
    ~Session() { if (ctx) whisper_free(ctx); }
};
void fail(JNIEnv *env, const char *message) {
    auto type = env->FindClass("java/lang/IllegalStateException");
    if (type) env->ThrowNew(type, message);
}
bool abort_run(void *data) { return static_cast<Session *>(data)->cancelled.load(); }
void quiet_log(enum ggml_log_level, const char *, void *) {}
}

extern "C" JNIEXPORT jlong JNICALL
Java_app_subloka_engine_asr_NativeWhisper_open(JNIEnv *env, jobject, jstring path, jstring vadPath) {
    const char *name = env->GetStringUTFChars(path, nullptr);
    if (!name) return 0;
    auto session = std::make_unique<Session>();
    const char *vad_name = env->GetStringUTFChars(vadPath, nullptr);
    if (!vad_name) { env->ReleaseStringUTFChars(path, name); return 0; }
    session->vad_path = vad_name;
    env->ReleaseStringUTFChars(vadPath, vad_name);
    whisper_log_set(quiet_log, nullptr); // Never log transcript/media content.
    auto params = whisper_context_default_params();
    params.use_gpu = false;
    params.flash_attn = false;
    session->ctx = whisper_init_from_file_with_params(name, params);
    env->ReleaseStringUTFChars(path, name);
    if (!session->ctx) { fail(env, "MODEL_FAILURE: cannot load caption model"); return 0; }
    return reinterpret_cast<jlong>(session.release());
}

extern "C" JNIEXPORT jobjectArray JNICALL
Java_app_subloka_engine_asr_NativeWhisper_run(JNIEnv *env, jobject, jlong handle, jfloatArray audio, jstring language) {
    auto *session = reinterpret_cast<Session *>(handle);
    const int count = env->GetArrayLength(audio);
    if (!session || count <= 0 || count > 30 * 16000) { fail(env, "Invalid ASR window"); return nullptr; }
    std::vector<float> samples(count);
    env->GetFloatArrayRegion(audio, 0, count, samples.data());
    if (env->ExceptionCheck()) return nullptr;
    const char *lang = env->GetStringUTFChars(language, nullptr);
    if (!lang) return nullptr;
    auto params = whisper_full_default_params(WHISPER_SAMPLING_BEAM_SEARCH);
    params.n_threads = 4;
    params.language = lang;
    params.translate = false;
    params.no_context = true;
    params.no_timestamps = false;
    params.print_realtime = params.print_progress = params.print_timestamps = params.print_special = false;
    params.suppress_nst = true;
    params.vad = true;
    params.vad_model_path = session->vad_path.c_str();
    // Pinned whisper_full_get_segment_t0/t1 map VAD-compressed time back to the
    // original window. Kotlin adds the 30-second window offset exactly once.
    params.abort_callback = abort_run;
    params.abort_callback_user_data = session;
    const int result = whisper_full(session->ctx, params, samples.data(), count);
    env->ReleaseStringUTFChars(language, lang);
    if (result != 0 || session->cancelled.load()) { fail(env, "ASR interrupted or failed"); return nullptr; }
    const auto type = env->FindClass("app/subloka/engine/asr/RawSpeechSegment");
    const auto ctor = env->GetMethodID(type, "<init>", "(JJLjava/lang/String;)V");
    const int n = whisper_full_n_segments(session->ctx);
    auto output = env->NewObjectArray(n, type, nullptr);
    for (int i = 0; i < n && !env->ExceptionCheck(); ++i) {
        // Whisper timestamps are centiseconds; Kotlin contract is microseconds.
        const char *utf8 = whisper_full_get_segment_text(session->ctx, i);
        // Decode standard UTF-8 through String(byte[], UTF-8), not modified JNI UTF-8.
        const std::string text(utf8 ? utf8 : "");
        auto bytes = env->NewByteArray(static_cast<jsize>(text.size()));
        env->SetByteArrayRegion(bytes, 0, static_cast<jsize>(text.size()), reinterpret_cast<const jbyte *>(text.data()));
        auto stringClass = env->FindClass("java/lang/String");
        auto stringCtor = env->GetMethodID(stringClass, "<init>", "([BLjava/lang/String;)V");
        auto encoding = env->NewStringUTF("UTF-8");
        auto string = env->NewObject(stringClass, stringCtor, bytes, encoding);
        auto segment = env->NewObject(type, ctor,
            static_cast<jlong>(whisper_full_get_segment_t0(session->ctx, i) * 10000),
            static_cast<jlong>(whisper_full_get_segment_t1(session->ctx, i) * 10000), string);
        env->SetObjectArrayElement(output, i, segment);
        env->DeleteLocalRef(segment); env->DeleteLocalRef(string); env->DeleteLocalRef(encoding);
        env->DeleteLocalRef(stringClass); env->DeleteLocalRef(bytes);
    }
    return output;
}

extern "C" JNIEXPORT void JNICALL
Java_app_subloka_engine_asr_NativeWhisper_cancel(JNIEnv *, jobject, jlong handle) {
    if (handle) reinterpret_cast<Session *>(handle)->cancelled.store(true);
}
extern "C" JNIEXPORT void JNICALL
Java_app_subloka_engine_asr_NativeWhisper_close(JNIEnv *, jobject, jlong handle) {
    delete reinterpret_cast<Session *>(handle);
}

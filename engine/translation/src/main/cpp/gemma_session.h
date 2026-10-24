#pragma once
#include "llama.h"
#include "gemma_timing.h"
#include <algorithm>
#include <atomic>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

// One foreground operation owns this session; cancel may be called from another thread.
class GemmaSession {
    llama_model *model = nullptr;
    llama_context *ctx = nullptr;
    std::atomic<bool> stopped{false};
    unsigned long long captionAttempt = 0;
    static bool abortDecode(void *p) { return static_cast<GemmaSession *>(p)->stopped.load(); }
    void check() { if (stopped.load()) throw std::runtime_error("PROCESS_INTERRUPTED"); }
    std::vector<llama_token> tokenize(const std::string &s, bool bos, bool special) {
        auto vocab = llama_model_get_vocab(model);
        int n = llama_tokenize(vocab, s.data(), s.size(), nullptr, 0, bos, special);
        if (n >= 0) return {};
        std::vector<llama_token> out(-n);
        n = llama_tokenize(vocab, s.data(), s.size(), out.data(), out.size(), bos, special);
        if (n < 0) throw std::runtime_error("MODEL_FAILURE");
        out.resize(n); return out;
    }
public:
    explicit GemmaSession(const char *path) {
        static std::once_flag init;
        std::call_once(init, [] { llama_log_set([](ggml_log_level, const char *, void *) {}, nullptr); llama_backend_init(); });
        auto mp = llama_model_default_params(); mp.n_gpu_layers = 0; mp.use_extra_bufts = false;
        model = llama_model_load_from_file(path, mp);
        if (!model) throw std::runtime_error("MODEL_FAILURE");
        auto cp = llama_context_default_params();
        cp.n_ctx = 1024; cp.n_batch = 128; cp.n_ubatch = 128;
        cp.n_threads = 4; cp.n_threads_batch = 4;
        cp.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_DISABLED;
        cp.abort_callback = abortDecode; cp.abort_callback_data = this; cp.no_perf = true;
        ctx = llama_init_from_model(model, cp);
        if (!ctx) { llama_model_free(model); model = nullptr; throw std::runtime_error("MODEL_FAILURE"); }
    }
    ~GemmaSession() { if (ctx) llama_free(ctx); if (model) llama_model_free(model); }
    GemmaSession(const GemmaSession &) = delete;
    GemmaSession &operator=(const GemmaSession &) = delete;
    void cancel() { stopped.store(true); }
    std::string translate(const std::string &text, bool fromId) {
        ++captionAttempt;
        check();
        if (text.empty() || text.size() > 16384) throw std::runtime_error("INPUT_TOO_LONG");
        const std::string src = fromId ? "Indonesian" : "English", dst = fromId ? "English" : "Indonesian";
        const std::string sc = fromId ? "id" : "en", tc = fromId ? "en" : "id";
        auto tokens = tokenize("<start_of_turn>user\nYou are a professional " + src + " (" + sc + ") to " + dst + " (" + tc + ") translator. Your goal is to accurately convey the meaning and nuances of the original " + src + " text while adhering to " + dst + " grammar, vocabulary, and cultural sensitivities.\nProduce only the " + dst + " translation, without any additional explanations or commentary. Please translate the following " + src + " text into " + dst + ":\n\n\n", true, true);
        auto body = tokenize(text, false, false); // Treat caption control-token strings as literal text.
        if (body.size() > 384) throw std::runtime_error("INPUT_TOO_LONG");
        tokens.insert(tokens.end(), body.begin(), body.end());
        auto suffix = tokenize("<end_of_turn>\n<start_of_turn>model\n", false, true);
        tokens.insert(tokens.end(), suffix.begin(), suffix.end());
        if (tokens.size() + 256 > 1024) throw std::runtime_error("INPUT_TOO_LONG");
        {
            GemmaPhaseTiming timing("prefill", captionAttempt);
            llama_memory_clear(llama_get_memory(ctx), true);
            for (size_t i = 0; i < tokens.size(); i += 128) {
                check(); auto n = static_cast<int32_t>(std::min(size_t(128), tokens.size() - i));
                if (llama_decode(ctx, llama_batch_get_one(tokens.data() + i, n))) throw std::runtime_error("MODEL_FAILURE");
                timing.tokens += n;
            }
            timing.outcome = "returned";
        }
        GemmaPhaseTiming generation("generation", captionAttempt);
        auto sampler = llama_sampler_init_greedy();
        std::string output;
        try {
            for (int i = 0; i < 256; ++i) {
                check(); auto token = llama_sampler_sample(sampler, ctx, -1);
                if (llama_vocab_is_eog(llama_model_get_vocab(model), token)) {
                    generation.outcome = "returned";
                    llama_sampler_free(sampler); return output;
                }
                std::vector<char> piece(256);
                int n = llama_token_to_piece(llama_model_get_vocab(model), token, piece.data(), piece.size(), 0, false);
                if (n < 0) { piece.resize(-n); n = llama_token_to_piece(llama_model_get_vocab(model), token, piece.data(), piece.size(), 0, false); }
                if (n < 0) throw std::runtime_error("MODEL_FAILURE");
                output.append(piece.data(), n);
                ++generation.tokens;
                if (llama_decode(ctx, llama_batch_get_one(&token, 1))) throw std::runtime_error("MODEL_FAILURE");
            }
            throw std::runtime_error("OUTPUT_TOO_LONG"); // Never publish a truncated caption.
        } catch (...) { llama_sampler_free(sampler); throw; }
    }
};

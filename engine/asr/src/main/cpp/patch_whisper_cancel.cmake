# Bounded patch for pinned whisper.cpp 927cfce. Refuse unknown upstream sources.
file(READ "${WHISPER_SOURCE}" source)
string(SHA256 source_hash "${source}")
if(source_hash STREQUAL "bd6fd9fe05a1554b232eb8d7edb5bca7cf3d1ff87f8e23939c2cd66467ed1295")
    return() # repeated configure
endif()
if(NOT source_hash STREQUAL "c48686fbc2cba1b0ac0f9c8e964188c691e67fff5906f2629f3223ff64f92d16")
    message(FATAL_ERROR "Whisper cancellation patch: unexpected source; review pinned revision")
endif()
set(before [=[                   void * abort_callback_data) {
    const int64_t t_start_us = ggml_time_us();]=])
set(after [=[                   void * abort_callback_data) {
    // SubLoka: interrupt CPU graphs, not only the end of the encoder/decoder.
    if (abort_callback && abort_callback(abort_callback_data)) return false;
    for (auto & backend : wstate.backends) {
        auto * reg = ggml_backend_dev_backend_reg(ggml_backend_get_device(backend));
        auto * set_abort = (ggml_backend_set_abort_callback_t)
            ggml_backend_reg_get_proc_address(reg, "ggml_backend_set_abort_callback");
        if (set_abort) set_abort(backend, abort_callback, abort_callback_data);
    }
    const int64_t t_start_us = ggml_time_us();]=])
string(REPLACE "${before}" "${after}" source "${source}")
file(WRITE "${WHISPER_SOURCE}" "${source}")

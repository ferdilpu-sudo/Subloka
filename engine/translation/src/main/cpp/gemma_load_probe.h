#pragma once
#include <fstream>
#include <string>

// Debug-only A/B switch beside the private model file. Read once before loading.
// Missing/malformed marker and non-debug builds retain upstream defaults.
inline bool gemmaReadLoadProbe(const char *modelPath) {
#ifdef SUBLOKA_TRANSLATION_MEMORY_PROBE
    const std::string path(modelPath);
    const auto slash = path.find_last_of('/');
    if (slash == std::string::npos) return false;
    std::ifstream marker(path.substr(0, slash + 1) + "load-mode-probe.txt");
    // Bounded read; only 'read', with an optional LF/CRLF, opts in.
    char value[8] = {};
    marker.read(value, sizeof(value));
    const std::string mode(value, static_cast<size_t>(marker.gcount()));
    return mode == "read" || mode == "read\n" || mode == "read\r\n";
#else
    (void) modelPath;
    return false;
#endif
}

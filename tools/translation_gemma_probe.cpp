// Public authored-fixture probe. Uses exactly the Android inference core.
#include "../engine/translation/src/main/cpp/gemma_session.h"
#include <chrono>
#include <fstream>
#include <iostream>
#include <thread>
int main(int argc, char **argv) {
    if (argc != 4) return 2;
    try {
        GemmaSession session(argv[1]);
        // Limits must fail before any partial output is returned.
        bool rejected = false;
        try { session.translate(std::string(16385, 'x'), true); } catch (const std::exception &) { rejected = true; }
        if (!rejected) return 4;
        std::ifstream input(argv[2]); std::ofstream output(argv[3]);
        if (!input || !output) return 3;
        std::string line;
        while (std::getline(input, line)) {
            auto a = line.find('\t'), b = line.find('\t', a + 1);
            if (a == std::string::npos || b == std::string::npos) return 5;
            auto start = std::chrono::steady_clock::now();
            auto result = session.translate(line.substr(b + 1), line.substr(a + 1, b - a - 1) == "id");
            // Keep output one TSV row even if the model emits formatting.
            for (auto &ch : result) if (ch == '\t' || ch == '\n' || ch == '\r') ch = ' ';
            auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start).count();
            output << line.substr(0, a) << '\t' << ms << '\t' << result << '\n'; output.flush();
            std::cerr << line.substr(0, a) << ": " << ms << "ms\n";
        }
        // Cancellation during actual decode must throw and leave no returned partial result.
        std::thread cancel([&] { std::this_thread::sleep_for(std::chrono::milliseconds(10)); session.cancel(); });
        rejected = false;
        try { session.translate("Tolong terjemahkan seluruh kalimat ini dengan hati-hati karena maknanya sangat penting untuk percakapan besok pagi.", true); }
        catch (const std::exception &) { rejected = true; }
        cancel.join();
        if (!rejected) return 6;
        std::cerr << "Limits and cancellation PASS\n";
        return 0;
    } catch (...) { std::cerr << "MODEL_FAILURE\n"; return 1; }
}

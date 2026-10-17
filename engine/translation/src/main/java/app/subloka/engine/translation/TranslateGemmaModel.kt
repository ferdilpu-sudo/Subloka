package app.subloka.engine.translation

import app.subloka.core.domain.ManagedModelDescriptor

object TranslateGemmaModel {
    const val TERMS_VERSION = "2026-04-01"
    val descriptor = ManagedModelDescriptor(
        id = "translategemma-4b-q4-k-m", displayName = "TranslateGemma 4B Q4_K_M",
        fileName = "translategemma-4b-it.Q4_K_M.gguf",
        downloadUrl = "https://huggingface.co/mradermacher/translategemma-4b-it-GGUF/resolve/d37868f759d2f817a43d28dd80cf9f982ffa62fd/translategemma-4b-it.Q4_K_M.gguf",
        expectedSha256 = "81200d03e843d2ec1ece6eeafe7d13cb6e5211e1fcd336ade55790b683a08330",
        nominalSizeMiB = 2375, licenseName = "Gemma Terms of Use",
        sourceRevision = "d37868f759d2f817a43d28dd80cf9f982ffa62fd", expectedSizeBytes = 2_489_909_760L,
    )
}

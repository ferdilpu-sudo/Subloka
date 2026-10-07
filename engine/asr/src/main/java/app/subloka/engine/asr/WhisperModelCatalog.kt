package app.subloka.engine.asr

import app.subloka.core.domain.ManagedModelDescriptor

object WhisperModelCatalog {
    private const val MODEL_REVISION = "80da2d8bfee42b0e836fc3a9890373e5defc00a6"
    private const val BASE_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/$MODEL_REVISION"

    val tiny = ManagedModelDescriptor(
        id = "whisper-tiny-multilingual",
        displayName = "Whisper Tiny Multilingual",
        fileName = "ggml-tiny.bin",
        downloadUrl = "$BASE_URL/ggml-tiny.bin?download=true",
        expectedSha256 = "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21",
        nominalSizeMiB = 75,
        licenseName = "MIT",
        sourceRevision = MODEL_REVISION,
    )

    val base = ManagedModelDescriptor(
        id = "whisper-base-multilingual",
        displayName = "Whisper Base Multilingual",
        fileName = "ggml-base.bin",
        downloadUrl = "$BASE_URL/ggml-base.bin?download=true",
        expectedSha256 = "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe",
        nominalSizeMiB = 142,
        licenseName = "MIT",
        sourceRevision = MODEL_REVISION,
    )

    val candidates: List<ManagedModelDescriptor> = listOf(tiny, base)
}

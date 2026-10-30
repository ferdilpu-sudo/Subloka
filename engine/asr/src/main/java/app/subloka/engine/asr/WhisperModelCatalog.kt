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

    // Pinned converted Silero VAD; provision explicitly with the caption model.
    val vad = ManagedModelDescriptor(
        id = "silero-vad-6.2.0",
        displayName = "Silero pendeteksi ucapan",
        fileName = "ggml-silero-v6.2.0.bin",
        downloadUrl = "https://huggingface.co/ggml-org/whisper-vad/resolve/9ffd54a1e1ee413ddf265af9913beaf518d1639b/ggml-silero-v6.2.0.bin?download=true",
        expectedSha256 = "2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987",
        nominalSizeMiB = 1,
        licenseName = "MIT",
        sourceRevision = "9ffd54a1e1ee413ddf265af9913beaf518d1639b",
    )
    val turbo = ManagedModelDescriptor(
        id = "whisper-large-v3-turbo-q5_0",
        displayName = "Whisper Large-v3 Turbo",
        fileName = "ggml-large-v3-turbo-q5_0.bin",
        downloadUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-large-v3-turbo-q5_0.bin?download=true",
        expectedSha256 = "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2",
        nominalSizeMiB = 548,
        licenseName = "MIT",
        sourceRevision = "5359861c739e955e79d9a303bcbc70fb988958b1",
        expectedSizeBytes = 574_041_195L,
    )

    fun captionModel(useTurbo: Boolean): ManagedModelDescriptor = if (useTurbo) turbo else base

    fun captionModels(useTurbo: Boolean): List<ManagedModelDescriptor> = listOf(captionModel(useTurbo), vad)

    val candidates: List<ManagedModelDescriptor> = listOf(tiny, base)
}

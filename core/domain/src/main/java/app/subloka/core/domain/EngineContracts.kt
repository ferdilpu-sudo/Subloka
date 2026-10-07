package app.subloka.core.domain

enum class ModelReadinessState {
    NOT_READY,
    DOWNLOADING,
    READY,
    FAILED,
}

data class ManagedModelDescriptor(
    val id: String,
    val displayName: String,
    val fileName: String,
    val downloadUrl: String,
    val expectedSha256: String,
    val nominalSizeMiB: Int,
    val licenseName: String,
    val sourceRevision: String,
) {
    init {
        require(id.isNotBlank()) { "id must not be blank" }
        require(fileName.isNotBlank()) { "fileName must not be blank" }
        require(downloadUrl.startsWith("https://")) { "model URL must use HTTPS" }
        require(expectedSha256.length == 64) { "expectedSha256 must be SHA-256 hex" }
        require(nominalSizeMiB > 0) { "nominalSizeMiB must be positive" }
    }
}

interface ModelReadiness {
    suspend fun state(): ModelReadinessState
    suspend fun ensureReady(requireWifi: Boolean = true)
}

interface OfflineTranslator : ModelReadiness, AutoCloseable {
    suspend fun translate(
        text: String,
        sourceLanguage: SourceLanguage,
        targetLanguage: SourceLanguage = sourceLanguage.target,
    ): String
}

data class BenchmarkSample(
    val id: String,
    val language: SourceLanguage,
    val referenceText: String,
)

data class BenchmarkMeasurement(
    val sampleId: String,
    val elapsedMs: Long,
    val outputText: String,
)

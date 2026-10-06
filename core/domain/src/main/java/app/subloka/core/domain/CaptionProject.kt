package app.subloka.core.domain

data class CaptionProject(
    val id: String,
    val title: String,
    val sourceUri: String,
    val sourceDisplayName: String,
    val sourceSizeBytes: Long?,
    val sourceFingerprint: String?,
    val durationUs: Long,
    val widthPx: Int,
    val heightPx: Int,
    val rotationDegrees: Int,
    val sourceLanguage: SourceLanguage,
    val targetLanguage: SourceLanguage,
    val contentRevision: Long,
    val createdAtMs: Long,
    val updatedAtMs: Long,
) {
    init {
        require(id.isNotBlank()) { "id must not be blank" }
        require(title.isNotBlank()) { "title must not be blank" }
        require(sourceUri.isNotBlank()) { "sourceUri must not be blank" }
        require(sourceDisplayName.isNotBlank()) { "sourceDisplayName must not be blank" }
        require(durationUs > 0) { "durationUs must be positive" }
        require(widthPx > 0 && heightPx > 0) { "video dimensions must be positive" }
        require(rotationDegrees in setOf(0, 90, 180, 270)) { "unsupported rotationDegrees" }
        require(sourceLanguage != targetLanguage) { "target language must differ from source" }
        require(contentRevision >= 0) { "contentRevision must be non-negative" }
        require(updatedAtMs >= createdAtMs) { "updatedAtMs must not precede createdAtMs" }
    }
}

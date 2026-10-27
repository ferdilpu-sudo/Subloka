package app.subloka.core.domain

interface CaptionRepository {
    /** Publish a staged first generation only when the project is still empty and unchanged. */
    suspend fun publishGenerated(projectId: String, expectedRevision: Long, segments: List<CaptionSegment>): Boolean
    suspend fun list(projectId: String): List<CaptionSegment>
    suspend fun replaceAll(projectId: String, segments: List<CaptionSegment>): EditorMutation<List<CaptionSegment>>
    suspend fun saveSourceText(projectId: String, segmentId: String, sourceText: String): EditorMutation<CaptionSegment>
    suspend fun saveManualTranslation(projectId: String, segmentId: String, translationText: String): EditorMutation<CaptionSegment>
    suspend fun saveTiming(projectId: String, segmentId: String, startUs: Long, endUs: Long): EditorMutation<CaptionSegment>
    suspend fun splitSegment(projectId: String, segmentId: String, splitUs: Long): EditorMutation<List<CaptionSegment>>
    suspend fun mergeWithNext(projectId: String, segmentId: String): EditorMutation<CaptionSegment>
    suspend fun restoreSnapshot(projectId: String, segments: List<CaptionSegment>): EditorMutation<List<CaptionSegment>>

    suspend fun applyMachineTranslation(
        projectId: String,
        segmentId: String,
        expectedSourceRevision: Long,
        translationText: String,
        allowReplaceManual: Boolean = false,
        origin: TranslationOrigin = TranslationOrigin.MACHINE,
    ): EditorMutation<CaptionSegment>?
}

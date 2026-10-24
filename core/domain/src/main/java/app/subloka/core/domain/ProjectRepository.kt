package app.subloka.core.domain

interface ProjectRepository {
    suspend fun upsert(project: CaptionProject): CaptionProject
    /** Same-file URI repair only; null means stale source or incompatible candidate. */
    suspend fun relinkSource(projectId: String, expectedUri: String, expectedFingerprint: String?,
        candidate: MediaDescriptor): CaptionProject?
    suspend fun find(projectId: String): CaptionProject?
    suspend fun list(): List<CaptionProject>
    suspend fun getStyle(projectId: String): CaptionStyle
    suspend fun saveStyle(projectId: String, style: CaptionStyle): EditorMutation<CaptionStyle>
}

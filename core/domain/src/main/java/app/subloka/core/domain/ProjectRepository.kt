package app.subloka.core.domain

interface ProjectRepository {
    suspend fun upsert(project: CaptionProject): CaptionProject
    suspend fun find(projectId: String): CaptionProject?
    suspend fun list(): List<CaptionProject>
    suspend fun getStyle(projectId: String): CaptionStyle
    suspend fun saveStyle(projectId: String, style: CaptionStyle): EditorMutation<CaptionStyle>
}

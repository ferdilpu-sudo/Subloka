package app.subloka.core.database

import androidx.room.withTransaction
import app.subloka.core.domain.CaptionProject
import app.subloka.core.domain.CaptionStyle
import app.subloka.core.domain.EditorMutation
import app.subloka.core.domain.ProjectRepository

class RoomProjectRepository(
    private val database: SubLokaDatabase,
    private val nowMs: () -> Long = System::currentTimeMillis,
) : ProjectRepository {
    private val projectDao = database.projectDao()
    private val styleDao = database.captionStyleDao()

    override suspend fun upsert(project: CaptionProject): CaptionProject {
        projectDao.upsert(project.toEntity())
        return project
    }

    override suspend fun find(projectId: String): CaptionProject? =
        projectDao.find(projectId)?.toDomain()

    override suspend fun list(): List<CaptionProject> =
        projectDao.list().map(ProjectEntity::toDomain)

    override suspend fun getStyle(projectId: String): CaptionStyle {
        requireNotNull(projectDao.find(projectId)) { "Unknown project: $projectId" }
        return styleDao.find(projectId)?.toDomain() ?: CaptionStyle()
    }

    override suspend fun saveStyle(projectId: String, style: CaptionStyle): EditorMutation<CaptionStyle> =
        database.withTransaction {
            requireNotNull(projectDao.find(projectId)) { "Unknown project: $projectId" }
            styleDao.upsert(style.toEntity(projectId))
            bumpRevision(projectId)
            EditorMutation(style, requireProject(projectId).content_revision)
        }

    private suspend fun bumpRevision(projectId: String) {
        check(projectDao.bumpRevision(projectId, nowMs()) == 1) { "Failed to update project revision" }
    }

    private suspend fun requireProject(projectId: String): ProjectEntity =
        requireNotNull(projectDao.find(projectId)) { "Unknown project: $projectId" }
}

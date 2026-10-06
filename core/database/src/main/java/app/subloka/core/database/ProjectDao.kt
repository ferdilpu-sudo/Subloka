package app.subloka.core.database

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert

@Dao
interface ProjectDao {
    @Upsert
    suspend fun upsert(entity: ProjectEntity)

    @Query("SELECT * FROM projects WHERE id = :projectId LIMIT 1")
    suspend fun find(projectId: String): ProjectEntity?

    @Query("SELECT * FROM projects ORDER BY updated_at_ms DESC")
    suspend fun list(): List<ProjectEntity>

    @Query(
        """
        UPDATE projects
        SET content_revision = content_revision + 1,
            updated_at_ms = :updatedAtMs
        WHERE id = :projectId
        """,
    )
    suspend fun bumpRevision(projectId: String, updatedAtMs: Long): Int
}

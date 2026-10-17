package app.subloka.core.database

import androidx.room.Dao
import androidx.room.Upsert
import androidx.room.Query

@Dao
interface ProcessingJobDao {
    @Upsert
    suspend fun save(job: ProcessingJobEntity)

    @Query("SELECT * FROM processing_jobs WHERE id = :id")
    suspend fun find(id: String): ProcessingJobEntity?

    @Query("SELECT * FROM processing_jobs WHERE project_id = :projectId AND kind = 'TRANSLATE' AND state IN ('RUNNING','INTERRUPTED','FAILED') ORDER BY created_at_ms DESC LIMIT 1")
    suspend fun pendingTranslation(projectId: String): ProcessingJobEntity?

    @Query("UPDATE processing_jobs SET state = 'INTERRUPTED', error_code = 'PROCESS_INTERRUPTED', updated_at_ms = :now WHERE kind = 'TRANSLATE' AND state = 'RUNNING'")
    suspend fun recoverTranslations(now: Long)
}

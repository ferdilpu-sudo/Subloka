package app.subloka.core.database

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update

@Dao
interface CaptionDao {
    @Query("SELECT * FROM caption_segments WHERE project_id = :projectId ORDER BY start_us ASC, id ASC")
    suspend fun list(projectId: String): List<CaptionSegmentEntity>

    @Query("SELECT * FROM caption_segments WHERE project_id = :projectId AND id = :segmentId LIMIT 1")
    suspend fun find(projectId: String, segmentId: String): CaptionSegmentEntity?

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertAll(entities: List<CaptionSegmentEntity>)

    @Update
    suspend fun update(entity: CaptionSegmentEntity): Int

    @Query("DELETE FROM caption_segments WHERE project_id = :projectId")
    suspend fun deleteForProject(projectId: String)

    @Query("DELETE FROM caption_segments WHERE project_id = :projectId AND id IN (:segmentIds)")
    suspend fun deleteByIds(projectId: String, segmentIds: List<String>)

    @Query(
        """
        UPDATE caption_segments
        SET translated_text = :translationText,
            translation_source_revision = source_revision,
            translation_status = 'CURRENT',
            translation_origin = 'MACHINE',
            updated_at_ms = :updatedAtMs
        WHERE project_id = :projectId
          AND id = :segmentId
          AND source_revision = :expectedSourceRevision
          AND (:allowReplaceManual = 1 OR translation_origin != 'MANUAL')
        """,
    )
    suspend fun applyMachineTranslation(
        projectId: String,
        segmentId: String,
        expectedSourceRevision: Long,
        translationText: String,
        updatedAtMs: Long,
        allowReplaceManual: Int,
    ): Int
}

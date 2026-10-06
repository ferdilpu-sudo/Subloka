package app.subloka.core.database

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert

@Dao
interface CaptionStyleDao {
    @Upsert
    suspend fun upsert(entity: CaptionStyleEntity)

    @Query("SELECT * FROM caption_styles WHERE project_id = :projectId LIMIT 1")
    suspend fun find(projectId: String): CaptionStyleEntity?
}

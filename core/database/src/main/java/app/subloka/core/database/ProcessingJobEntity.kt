package app.subloka.core.database

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "processing_jobs",
    foreignKeys = [
        ForeignKey(
            entity = ProjectEntity::class,
            parentColumns = ["id"],
            childColumns = ["project_id"],
            onDelete = ForeignKey.SET_NULL,
        ),
    ],
    indices = [Index(value = ["state"]), Index(value = ["project_id"])],
)
data class ProcessingJobEntity(
    @PrimaryKey val id: String,
    val project_id: String?,
    val kind: String,
    val state: String,
    val stage: String,
    val progress: Double?,
    val input_revision: Long?,
    val engine_version: String?,
    val model_version: String?,
    val checkpoint_ref: String?,
    val error_code: String?,
    val created_at_ms: Long,
    val updated_at_ms: Long,
)

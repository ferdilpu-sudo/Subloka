package app.subloka.core.database

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "export_records",
    foreignKeys = [
        ForeignKey(
            entity = ProjectEntity::class,
            parentColumns = ["id"],
            childColumns = ["project_id"],
            onDelete = ForeignKey.CASCADE,
        ),
        ForeignKey(
            entity = ProcessingJobEntity::class,
            parentColumns = ["id"],
            childColumns = ["job_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index(value = ["project_id"]), Index(value = ["job_id"])],
)
data class ExportRecordEntity(
    @PrimaryKey val id: String,
    val project_id: String,
    val job_id: String,
    val snapshot_revision: Long,
    val export_kind: String,
    val display_mode: String,
    val output_uri: String?,
    val profile_json: String,
    val state: String,
    val created_at_ms: Long,
)

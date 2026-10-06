package app.subloka.core.database

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "caption_segments",
    foreignKeys = [
        ForeignKey(
            entity = ProjectEntity::class,
            parentColumns = ["id"],
            childColumns = ["project_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index(value = ["project_id", "start_us"])],
)
data class CaptionSegmentEntity(
    @PrimaryKey val id: String,
    val project_id: String,
    val start_us: Long,
    val end_us: Long,
    val source_text: String,
    val translated_text: String?,
    val source_revision: Long,
    val translation_source_revision: Long?,
    val translation_status: String,
    val translation_origin: String,
    val updated_at_ms: Long,
)

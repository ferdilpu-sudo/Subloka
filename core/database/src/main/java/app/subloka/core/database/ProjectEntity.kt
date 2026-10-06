package app.subloka.core.database

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "projects")
data class ProjectEntity(
    @PrimaryKey val id: String,
    val title: String,
    val source_uri: String,
    val source_display_name: String,
    val source_size_bytes: Long?,
    val source_fingerprint: String?,
    val duration_us: Long,
    val width_px: Int,
    val height_px: Int,
    val rotation_degrees: Int,
    val source_language: String,
    val target_language: String,
    val content_revision: Long,
    val created_at_ms: Long,
    val updated_at_ms: Long,
)

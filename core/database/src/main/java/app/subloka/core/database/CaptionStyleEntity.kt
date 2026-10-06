package app.subloka.core.database

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.PrimaryKey

@Entity(
    tableName = "caption_styles",
    foreignKeys = [
        ForeignKey(
            entity = ProjectEntity::class,
            parentColumns = ["id"],
            childColumns = ["project_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
)
data class CaptionStyleEntity(
    @PrimaryKey val project_id: String,
    val display_mode: String,
    val source_first: Boolean,
    val font_asset_id: String?,
    val source_size_ratio: Float,
    val translation_size_ratio: Float,
    val source_color_argb: Long,
    val translation_color_argb: Long,
    val outline_color_argb: Long,
    val outline_width_ratio: Float,
    val background_color_argb: Long,
    val background_enabled: Boolean,
    val anchor_x: Float,
    val anchor_y: Float,
    val max_width_ratio: Float,
    val line_gap_ratio: Float,
    val alignment: String,
)

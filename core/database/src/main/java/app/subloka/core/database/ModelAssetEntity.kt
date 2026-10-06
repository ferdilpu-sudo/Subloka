package app.subloka.core.database

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "model_assets")
data class ModelAssetEntity(
    @PrimaryKey val id: String,
    val provider: String,
    val language_pair: String?,
    val version: String?,
    val local_path: String?,
    val expected_sha256: String?,
    val actual_sha256: String?,
    val size_bytes: Long?,
    val state: String,
    val verified_at_ms: Long?,
)

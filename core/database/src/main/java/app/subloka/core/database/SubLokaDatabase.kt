package app.subloka.core.database

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [
        ProjectEntity::class,
        CaptionSegmentEntity::class,
        CaptionStyleEntity::class,
        ProcessingJobEntity::class,
        ModelAssetEntity::class,
        ExportRecordEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
abstract class SubLokaDatabase : RoomDatabase() {
    abstract fun projectDao(): ProjectDao
    abstract fun captionDao(): CaptionDao
    abstract fun captionStyleDao(): CaptionStyleDao
}

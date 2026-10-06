package app.subloka.core.database

import android.content.Context
import androidx.room.Room
import app.subloka.core.domain.CaptionRepository
import app.subloka.core.domain.ProjectRepository

class SubLokaPersistence private constructor(
    private val database: SubLokaDatabase,
) : AutoCloseable {
    val projectRepository: ProjectRepository = RoomProjectRepository(database)
    val captionRepository: CaptionRepository = RoomCaptionRepository(database)

    override fun close() {
        database.close()
    }

    companion object {
        internal fun create(context: Context, name: String): SubLokaPersistence {
            val database = Room.databaseBuilder(
                context.applicationContext,
                SubLokaDatabase::class.java,
                name,
            ).build()
            return SubLokaPersistence(database)
        }
    }
}

package app.subloka.core.database

import android.content.Context
import androidx.room.Room

object SubLokaDatabaseFactory {
    fun create(context: Context, name: String = "subloka.db"): SubLokaDatabase =
        Room.databaseBuilder(
            context.applicationContext,
            SubLokaDatabase::class.java,
            name,
        ).build()
}

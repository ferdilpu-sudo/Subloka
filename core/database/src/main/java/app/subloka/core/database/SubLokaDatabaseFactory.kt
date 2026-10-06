package app.subloka.core.database

import android.content.Context

object SubLokaDatabaseFactory {
    fun create(context: Context, name: String = "subloka.db"): SubLokaPersistence =
        SubLokaPersistence.create(context, name)
}

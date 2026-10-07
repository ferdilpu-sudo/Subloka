package app.subloka.core.media

import android.content.ContentResolver
import android.content.Context
import android.content.Intent
import android.net.Uri

class MediaDocumentAccess(context: Context) {
    private val resolver: ContentResolver = context.applicationContext.contentResolver

    fun persistReadPermission(uri: Uri): Boolean =
        try {
            resolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            true
        } catch (_: SecurityException) {
            resolver.persistedUriPermissions.any { permission ->
                permission.uri == uri && permission.isReadPermission
            }
        }

    fun hasPersistedReadPermission(uri: Uri): Boolean =
        resolver.persistedUriPermissions.any { permission ->
            permission.uri == uri && permission.isReadPermission
        }
}

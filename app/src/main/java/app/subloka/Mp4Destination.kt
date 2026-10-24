package app.subloka

import android.content.ContentResolver
import android.net.Uri
import android.provider.DocumentsContract
import java.io.OutputStream

/** Document-provider boundary; staging and save lifecycle stay owned by the ViewModel. */
internal interface Mp4Destination {
    fun open(uri: Uri): OutputStream?
    fun delete(uri: Uri): Boolean
}

internal class AndroidMp4Destination(private val resolver: ContentResolver) : Mp4Destination {
    override fun open(uri: Uri): OutputStream? = resolver.openOutputStream(uri, "wt")
    override fun delete(uri: Uri): Boolean = DocumentsContract.deleteDocument(resolver, uri)
}

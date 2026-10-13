package app.subloka

import app.subloka.core.domain.SrtDocument
import java.io.OutputStream

/** Returns only after write AND close succeed; callers own newly-created document cleanup. */
internal object SrtDocumentWriter {
    fun write(document: SrtDocument, open: () -> OutputStream?) {
        requireNotNull(open()) { "Lokasi tidak dapat ditulis." }.use { output ->
            output.write(document.text.toByteArray(Charsets.UTF_8))
            output.flush()
        }
    }
}

package app.subloka.core.domain

/** Labels are based on the exact prepared SRT filename, never the currently selected mode.
 * A user can change format/language after preparation while the saved snapshot remains valid.
 */
object SrtSaveActions {
    fun languageLabel(document: SrtDocument): String? = when {
        document.name.endsWith(".id.srt", ignoreCase = true) -> "Indonesia"
        document.name.endsWith(".en.srt", ignoreCase = true) -> "Inggris"
        else -> null
    }

    fun saveLabel(document: SrtDocument, index: Int): String =
        languageLabel(document)?.let { "Simpan SRT $it" } ?: "Simpan SRT file ${index + 1}"

    fun resaveLabel(document: SrtDocument, index: Int): String =
        languageLabel(document)?.let { "Simpan ulang SRT $it" }
            ?: "Simpan ulang SRT file ${index + 1}"

    /** Only a write-and-close success marks an index saved in SrtExportViewModel. */
    fun nextUnsaved(documents: List<SrtDocument>, saved: Set<Int>): Int? =
        documents.indices.firstOrNull { it !in saved }
}

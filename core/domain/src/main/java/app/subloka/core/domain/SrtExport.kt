package app.subloka.core.domain

import java.util.Locale

enum class SrtExportMode { SOURCE, TRANSLATION, BOTH }
data class SrtDocument(val name: String, val text: String)

/** Pure, immutable export snapshot. SRT contains timing/text, never visual styling. */
object SrtExport {
    fun documents(title: String, language: SourceLanguage, durationUs: Long,
        segments: List<CaptionSegment>, mode: SrtExportMode): List<SrtDocument> {
        require(segments.isNotEmpty()) { "Belum ada caption untuk diekspor." }
        val ordered = segments.sortedBy { it.startUs }
        require(ordered.map { it.id }.distinct().size == ordered.size) { "Identitas caption ganda." }
        require(ordered.all { it.sourceLanguage == language }) { "Bahasa caption tidak cocok dengan proyek." }
        try { CaptionTimelineValidator.validate(durationUs, ordered) }
        catch (_: IllegalArgumentException) { error("Timing caption tidak valid. Perbaiki di Timing.") }
        require(ordered.all { it.endUs / 1000 > it.startUs / 1000 }) {
            "Ada caption berdurasi kurang dari presisi SRT. Perbaiki di Timing."
        }
        if (mode != SrtExportMode.SOURCE) require(ordered.all {
            it.translationStatus == TranslationStatus.CURRENT &&
                it.translationSourceRevision == it.sourceRevision && it.translationText.isNotBlank()
        }) { "Lengkapi atau perbarui terjemahan terlebih dahulu, atau pilih Asli." }
        val base = title.replace(Regex("[^\\p{L}\\p{N}._ -]"), "_").trim(' ', '.').take(80).ifBlank { "subtitle" }
        fun document(translated: Boolean): SrtDocument {
            val text = ordered.mapIndexed { index, segment ->
                val cue = normalize(if (translated) segment.translationText else segment.sourceText)
                "${index + 1}\r\n${timestamp(segment.startUs)} --> ${timestamp(segment.endUs)}\r\n$cue\r\n\r\n"
            }.joinToString("")
            val code = (if (translated) language.target else language).code.lowercase(Locale.ROOT)
            return SrtDocument("$base.$code.srt", text)
        }
        return when (mode) {
            SrtExportMode.SOURCE -> listOf(document(false))
            SrtExportMode.TRANSLATION -> listOf(document(true))
            SrtExportMode.BOTH -> listOf(document(false), document(true))
        }
    }
    private fun normalize(text: String): String {
        val lines = text.replace("\r\n", "\n").replace('\r', '\n').lines()
            .map { it.trim() }.filter { it.isNotEmpty() }
        require(lines.isNotEmpty()) { "Ada teks caption kosong. Perbaiki sebelum ekspor." }
        require(lines.none { line -> line.any { it.isISOControl() && it != '\t' } || "-->" in line }) {
            "Teks caption berisi karakter kontrol atau panah timestamp SRT. Perbaiki sebelum ekspor."
        }
        return lines.joinToString("\r\n")
    }
    private fun timestamp(us: Long): String {
        val ms = us / 1000
        return String.format(Locale.ROOT, "%02d:%02d:%02d,%03d", ms / 3_600_000,
            ms / 60_000 % 60, ms / 1000 % 60, ms % 1000)
    }
}

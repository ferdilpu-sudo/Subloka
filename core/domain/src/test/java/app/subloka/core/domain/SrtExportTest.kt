package app.subloka.core.domain

import org.junit.Assert.*
import org.junit.Test
import java.util.Locale

class SrtExportTest {
    private fun cue(id: String = "a", start: Long = 1_234_567, end: Long = 2_456_789,
        language: SourceLanguage = SourceLanguage.INDONESIA) = CaptionSegment(id, start, end,
        language, "Halo, dunia!", "Hello, world!", TranslationStatus.CURRENT,
        TranslationOrigin.MANUAL, 3, 3)
    private fun export(rows: List<CaptionSegment>, mode: SrtExportMode = SrtExportMode.BOTH,
        language: SourceLanguage = SourceLanguage.INDONESIA) =
        SrtExport.documents("video/test", language, 8_000_000_000, rows, mode)

    @Test fun bothDirectionsProduceTwoIndependentUtf8FilesWithIdenticalTiming() {
        SourceLanguage.entries.forEach { language ->
            val files = export(listOf(cue(language = language)), language = language)
            assertEquals(listOf("video_test.${language.code.lowercase(Locale.ROOT)}.srt",
                "video_test.${language.target.code.lowercase(Locale.ROOT)}.srt"), files.map { it.name })
            assertEquals("1\r\n00:00:01,234 --> 00:00:02,456\r\nHalo, dunia!\r\n\r\n", files[0].text)
            assertEquals(files[0].text.replace("Halo, dunia!", "Hello, world!"), files[1].text)
        }
    }
    @Test fun staleOrMissingTranslationsBlockOnlyModesThatNeedThem() {
        val rows = listOf(cue().copy(translationStatus = TranslationStatus.STALE))
        assertEquals(1, export(rows, SrtExportMode.SOURCE).size)
        listOf(SrtExportMode.BOTH, SrtExportMode.TRANSLATION).forEach { mode ->
            assertThrows(IllegalArgumentException::class.java) { export(rows, mode) }
            assertThrows(IllegalArgumentException::class.java) { export(listOf(cue().copy(
                translationText = "", translationStatus = TranslationStatus.MISSING)), mode) }
        }
    }
    @Test fun sortsAndNumbersCuesAndFormatsHourRolloverIndependentOfLocale() {
        val old = Locale.getDefault()
        try {
            Locale.setDefault(Locale.forLanguageTag("ar"))
            val text = export(listOf(cue("b", 3_599_999_000, 3_600_001_000), cue()), SrtExportMode.SOURCE)[0].text
            assertTrue(text.contains("2\r\n00:59:59,999 --> 01:00:00,001"))
        } finally { Locale.setDefault(old) }
    }
    @Test fun invalidTimelineCollapsedMillisecondsEmptyAndMixedLanguageAreRejected() {
        listOf(emptyList(), listOf(cue(), cue("b")), listOf(cue(end = 9_000_000_000)),
            listOf(cue(start = 100, end = 999)), listOf(cue().copy(sourceText = " \n ")),
            listOf(cue(language = SourceLanguage.ENGLISH))).forEach { rows ->
            assertThrows(RuntimeException::class.java) { export(rows, SrtExportMode.SOURCE) }
        }
    }
    @Test fun normalizesBlankLinesWithoutBreakingCueStructureAndPreservesUnicode() {
        val text = export(listOf(cue().copy(sourceText = " Hé!\r\n\r\n世界 🌴\rNext ")), SrtExportMode.SOURCE)[0].text
        assertTrue(text.endsWith("Hé!\r\n世界 🌴\r\nNext\r\n\r\n"))
        assertEquals(text, String(text.toByteArray(Charsets.UTF_8), Charsets.UTF_8))
        assertThrows(IllegalArgumentException::class.java) { export(listOf(cue().copy(sourceText = "bad\u0000text"))) }
    }
}

package app.subloka.core.domain

import org.junit.Assert.*
import org.junit.Test

class SrtSaveActionsTest {
    @Test fun preparedNamesDriveLanguageLabelsRegardlessOfProjectDirection() {
        val id = SrtDocument("7.id.srt", "indonesian")
        val en = SrtDocument("7.en.srt", "english")
        assertEquals("Simpan SRT Indonesia", SrtSaveActions.saveLabel(id, 0))
        assertEquals("Simpan SRT Inggris", SrtSaveActions.saveLabel(en, 1))
        assertEquals("Simpan ulang SRT Indonesia", SrtSaveActions.resaveLabel(id, 0))
        assertEquals("Simpan ulang SRT Inggris", SrtSaveActions.resaveLabel(en, 1))
        assertEquals("Inggris", SrtSaveActions.languageLabel(SrtDocument("movie.EN.SRT", "")))
        assertEquals("Indonesia", SrtSaveActions.languageLabel(SrtDocument("movie.ID.SRT", "")))
    }

    @Test fun unknownSuffixDoesNotInventLanguageOrDropFile() {
        val unknown = SrtDocument("legacy.srt", "legacy")
        assertNull(SrtSaveActions.languageLabel(unknown))
        assertEquals("Simpan SRT file 2", SrtSaveActions.saveLabel(unknown, 1))
        assertEquals("Simpan ulang SRT file 2", SrtSaveActions.resaveLabel(unknown, 1))
        assertNull(SrtSaveActions.languageLabel(SrtDocument("7.id.srt.backup", "")))
    }

    @Test fun savePriorityFollowsUnstoredPreparedSnapshot() {
        val documents = listOf(SrtDocument("7.id.srt", "id"), SrtDocument("7.en.srt", "en"))
        assertEquals(0, SrtSaveActions.nextUnsaved(documents, emptySet()))
        assertEquals(1, SrtSaveActions.nextUnsaved(documents, setOf(0)))
        assertEquals(0, SrtSaveActions.nextUnsaved(documents, setOf(1)))
        assertNull(SrtSaveActions.nextUnsaved(documents, setOf(0, 1)))
        assertNull(SrtSaveActions.nextUnsaved(emptyList(), setOf(0)))
    }

    @Test fun actualSrtExportDocumentsHaveRecognizableLanguagesInBothDirections() {
        for (lang in SourceLanguage.entries) {
            val segments = listOf(CaptionSegment("one", 0L, 1_500_000L, lang,
                "Halo", "Hello", TranslationStatus.CURRENT, TranslationOrigin.MANUAL, 1L, 1L))
            val docs = SrtExport.documents("7", lang, 2_000_000L, segments, SrtExportMode.BOTH)
            assertEquals(2, docs.size)
            assertTrue(docs.mapIndexed { i, d -> SrtSaveActions.saveLabel(d, i) }
                .containsAll(listOf("Simpan SRT Indonesia", "Simpan SRT Inggris")))
        }
    }
}

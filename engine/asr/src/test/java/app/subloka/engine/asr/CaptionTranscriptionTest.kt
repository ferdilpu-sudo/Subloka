package app.subloka.engine.asr

import app.subloka.core.domain.*
import org.junit.Assert.*
import org.junit.Test

class CaptionTranscriptionTest {
    @Test fun offsetsClampsAndPreservesRepeatedSpeechAcrossWindows() {
        val result = mutableListOf<CaptionSegment>()
        CaptionTranscription.appendWindow(result, listOf(RawSpeechSegment(0, 35_000_000, "  ulang  ")),
            0, 30_000_000, 32_000_000, SourceLanguage.INDONESIA)
        CaptionTranscription.appendWindow(result, listOf(RawSpeechSegment(0, 4_000_000, "ulang")),
            30_000_000, 2_000_000, 32_000_000, SourceLanguage.INDONESIA)
        assertEquals(listOf("ulang", "ulang"), result.map { it.sourceText })
        assertEquals(listOf(30_000_000L, 32_000_000L), result.map { it.endUs })
        assertEquals(30_000_000L, result[1].startUs)
        assertTrue(result.all { it.translationStatus == TranslationStatus.MISSING && it.translationText.isEmpty() })
        CaptionTimelineValidator.validate(32_000_000, result)
    }
    @Test fun invalidBlankAndFullyOverlappingSegmentsDoNotPublish() {
        val result = mutableListOf<CaptionSegment>()
        CaptionTranscription.appendWindow(result, listOf(RawSpeechSegment(-1, 100, "bad"),
            RawSpeechSegment(0, 100, "ok"), RawSpeechSegment(1, 50, "overlap"),
            RawSpeechSegment(100, 100, "empty"), RawSpeechSegment(200, 500, " ")),
            0, 1000, 1000, SourceLanguage.ENGLISH)
        assertEquals(listOf("ok"), result.map { it.sourceText })
    }
}

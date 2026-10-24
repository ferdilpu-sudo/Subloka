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
    @Test fun speechDetectionTimesKeepSilenceGapsAndWindowOffsetExactlyOnce() {
        val result = mutableListOf<CaptionSegment>()
        CaptionTranscription.appendWindow(result, listOf(
            RawSpeechSegment(12_420_000, 12_920_000, "ucapan pertama"),
            RawSpeechSegment(23_520_000, 26_110_000, "ucapan berikutnya")),
            30_000_000, 30_000_000, 99_541_667, SourceLanguage.INDONESIA)
        CaptionTranscription.appendWindow(result, emptyList(),
            60_000_000, 30_000_000, 99_541_667, SourceLanguage.INDONESIA)
        CaptionTranscription.appendWindow(result, listOf(RawSpeechSegment(2_720_000, 3_710_000, "ucapan akhir")),
            90_000_000, 9_520_750, 99_541_667, SourceLanguage.INDONESIA)
        assertEquals(listOf(42_420_000L, 53_520_000L, 92_720_000L), result.map { it.startUs })
        assertEquals(listOf(42_920_000L, 56_110_000L, 93_710_000L), result.map { it.endUs })
        CaptionTimelineValidator.validate(99_541_667, result)
    }

    @Test fun punctuationOnlyOutputIsNotACaptionButSpeechWithPunctuationIsRetained() {
        val result = mutableListOf<CaptionSegment>()
        CaptionTranscription.appendWindow(result, listOf(RawSpeechSegment(0, 1_000_000, "..."),
            RawSpeechSegment(2_000_000, 3_000_000, "…?!"),
            RawSpeechSegment(4_000_000, 5_000_000, "...tidak mungkin.")),
            0, 6_000_000, 6_000_000, SourceLanguage.INDONESIA)
        assertEquals(listOf("...tidak mungkin."), result.map { it.sourceText })
        assertEquals(4_000_000L, result.single().startUs)
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

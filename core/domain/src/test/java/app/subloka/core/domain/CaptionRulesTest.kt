package app.subloka.core.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class CaptionRulesTest {
    @Test
    fun timelineRejectsOverlapAndOutOfBoundsSegments() {
        val first = segment("a", 0, 1_000_000)
        val overlap = segment("b", 900_000, 2_000_000)
        val tooLong = segment("c", 2_000_000, 4_100_000)

        assertThrows(IllegalArgumentException::class.java) {
            CaptionTimelineValidator.validate(4_000_000, listOf(first, overlap))
        }
        assertThrows(IllegalArgumentException::class.java) {
            CaptionTimelineValidator.validate(4_000_000, listOf(first, tooLong))
        }
    }

    @Test
    fun splitSuggestionPreservesTextWithoutInventingWords() {
        val original = "this place is absolutely beautiful"
        val (left, right) = CaptionEditingRules.splitTextSuggestion(original, 0.5)

        assertEquals(original, CaptionEditingRules.mergeText(left, right))
    }

    private fun segment(id: String, startUs: Long, endUs: Long) = CaptionSegment(
        id = id,
        startUs = startUs,
        endUs = endUs,
        sourceLanguage = SourceLanguage.ENGLISH,
        sourceText = "source",
        translationText = "",
        translationStatus = TranslationStatus.MISSING,
        translationOrigin = TranslationOrigin.NONE,
    )
}

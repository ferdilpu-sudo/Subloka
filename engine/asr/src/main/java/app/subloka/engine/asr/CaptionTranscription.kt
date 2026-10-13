package app.subloka.engine.asr

import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.SourceLanguage
import app.subloka.core.domain.TranslationOrigin
import app.subloka.core.domain.TranslationStatus
import java.util.UUID

object CaptionTranscription {
    /** Non-overlapping windows: preserve legitimate repeated speech, clamp invalid timing. */
    fun appendWindow(
        output: MutableList<CaptionSegment>, raw: List<RawSpeechSegment>,
        offsetUs: Long, windowDurationUs: Long, videoDurationUs: Long, language: SourceLanguage,
    ) {
        val limit = minOf(offsetUs + windowDurationUs, videoDurationUs)
        raw.sortedBy { it.startUs }.forEach { item ->
            if (item.text.isBlank() || item.startUs < 0 || item.endUs <= item.startUs || item.startUs >= windowDurationUs) return@forEach
            val start = maxOf(offsetUs + item.startUs, output.lastOrNull()?.endUs ?: 0L)
            val end = minOf(offsetUs + item.endUs.coerceAtMost(windowDurationUs), limit)
            if (end <= start) return@forEach
            output += CaptionSegment(UUID.randomUUID().toString(), start, end, language, item.text.trim(), "",
                TranslationStatus.MISSING, TranslationOrigin.NONE)
        }
    }
}

package app.subloka.core.domain

/** Automatic generation never replaces a manual or already-current translation. */
object TranslationEligibility {
    fun canGenerate(segment: CaptionSegment): Boolean =
        segment.sourceText.isNotBlank() && segment.translationOrigin != TranslationOrigin.MANUAL &&
            segment.translationStatus != TranslationStatus.CURRENT
}

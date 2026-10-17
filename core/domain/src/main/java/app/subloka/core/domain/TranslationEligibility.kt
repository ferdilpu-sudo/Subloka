package app.subloka.core.domain

/** Automatic generation always protects manual corrections. Replacing current machine output is opt-in. */
object TranslationEligibility {
    fun canGenerate(segment: CaptionSegment): Boolean = canGenerate(segment, false)

    fun canGenerate(segment: CaptionSegment, replaceCurrentMachine: Boolean): Boolean =
        segment.sourceText.isNotBlank() && segment.translationOrigin != TranslationOrigin.MANUAL &&
            (segment.translationStatus != TranslationStatus.CURRENT || replaceCurrentMachine)
}

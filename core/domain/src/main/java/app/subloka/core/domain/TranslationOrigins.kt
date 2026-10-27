package app.subloka.core.domain

/** MACHINE is deliberately unknown: never infer old output's provider from today's selection. */
object TranslationOrigins {
    fun fromEngine(engine: String): TranslationOrigin = when {
        engine.startsWith("gemma:") -> TranslationOrigin.MACHINE_GEMMA
        engine.startsWith("mlkit:") -> TranslationOrigin.MACHINE_MLKIT
        else -> TranslationOrigin.MACHINE
    }

    fun merge(first: CaptionSegment, second: CaptionSegment): TranslationOrigin {
        val origins = listOf(first, second).filter { it.translationText.isNotBlank() }
            .map { it.translationOrigin }.distinct()
        return when {
            origins.isEmpty() -> TranslationOrigin.NONE
            TranslationOrigin.MANUAL in origins -> TranslationOrigin.MANUAL
            origins.size == 1 -> origins.single()
            else -> TranslationOrigin.MACHINE
        }
    }

    fun label(origin: TranslationOrigin): String = when (origin) {
        TranslationOrigin.NONE -> ""
        TranslationOrigin.MACHINE -> "Terjemahan otomatis · penyedia belum tercatat"
        TranslationOrigin.MANUAL -> "Terjemahan diedit manual"
        TranslationOrigin.MACHINE_GEMMA -> "Terjemahan otomatis · TranslateGemma"
        TranslationOrigin.MACHINE_MLKIT -> "Terjemahan otomatis · Google Translate (ML Kit)"
    }
}

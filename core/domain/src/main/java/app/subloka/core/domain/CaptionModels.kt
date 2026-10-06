package app.subloka.core.domain

enum class SourceLanguage(val label: String, val code: String) {
    ENGLISH("English", "EN"),
    INDONESIA("Indonesia", "ID");

    val target: SourceLanguage
        get() = if (this == ENGLISH) INDONESIA else ENGLISH
}

enum class TranslationStatus {
    MISSING,
    PENDING,
    CURRENT,
    STALE,
    FAILED,
}

enum class TranslationOrigin {
    MACHINE,
    MANUAL,
}

data class CaptionSegment(
    val id: Long,
    val startUs: Long,
    val endUs: Long,
    val sourceLanguage: SourceLanguage,
    val sourceText: String,
    val translationText: String,
    val translationStatus: TranslationStatus,
    val translationOrigin: TranslationOrigin = TranslationOrigin.MACHINE,
) {
    init {
        require(startUs >= 0) { "startUs must be non-negative" }
        require(endUs > startUs) { "endUs must be after startUs" }
    }
}

enum class EditorWorkspace {
    CAPTION,
    TIMING,
    STYLE,
}

enum class CaptionDisplayMode {
    DUAL,
    ORIGINAL,
    TRANSLATION,
}

enum class CaptionOrder {
    SOURCE_FIRST,
    TRANSLATION_FIRST,
}

data class CaptionStyle(
    val displayMode: CaptionDisplayMode = CaptionDisplayMode.DUAL,
    val order: CaptionOrder = CaptionOrder.SOURCE_FIRST,
    val sourceSizePercent: Int = 100,
    val translationSizePercent: Int = 92,
    val outlineEnabled: Boolean = true,
    val backgroundEnabled: Boolean = false,
    val bottomPositionPercent: Int = 12,
)

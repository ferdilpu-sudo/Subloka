package app.subloka.demo

import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.ProcessingStage
import app.subloka.core.domain.ProcessingStageState
import app.subloka.core.domain.ProjectSummary
import app.subloka.core.domain.SourceLanguage
import app.subloka.core.domain.TranslationOrigin
import app.subloka.core.domain.TranslationStatus

object DemoData {
    val project = ProjectSummary(
        id = "demo-traveling",
        title = "Traveling",
        sourceFileName = "Traveling.mp4",
        sourceLanguage = SourceLanguage.ENGLISH,
        durationLabel = "03:42",
        resolutionLabel = "1080p",
        lastEditedLabel = "baru saja",
    )

    val stages = listOf(
        ProcessingStage("Menyiapkan audio", ProcessingStageState.COMPLETE),
        ProcessingStage("Mengenali ucapan", ProcessingStageState.ACTIVE),
        ProcessingStage("Menerjemahkan", ProcessingStageState.WAITING),
    )

    val segments = listOf(
        CaptionSegment(
            id = "demo-segment-1",
            startUs = 84_200_000,
            endUs = 88_100_000,
            sourceLanguage = SourceLanguage.ENGLISH,
            sourceText = "This place is absolutely beautiful.",
            translationText = "Tempat ini benar-benar indah.",
            translationStatus = TranslationStatus.CURRENT,
            translationOrigin = TranslationOrigin.MACHINE,
            sourceRevision = 1,
            translationSourceRevision = 1,
        ),
        CaptionSegment(
            id = "demo-segment-2",
            startUs = 88_100_000,
            endUs = 92_600_000,
            sourceLanguage = SourceLanguage.ENGLISH,
            sourceText = "I could stay here all afternoon.",
            translationText = "Aku bisa tinggal di sini sepanjang sore.",
            translationStatus = TranslationStatus.STALE,
            translationOrigin = TranslationOrigin.MACHINE,
            sourceRevision = 2,
            translationSourceRevision = 1,
        ),
        CaptionSegment(
            id = "demo-segment-3",
            startUs = 92_600_000,
            endUs = 96_300_000,
            sourceLanguage = SourceLanguage.ENGLISH,
            sourceText = "Let's keep walking before it gets dark.",
            translationText = "Ayo lanjut jalan sebelum gelap.",
            translationStatus = TranslationStatus.CURRENT,
            translationOrigin = TranslationOrigin.MACHINE,
            sourceRevision = 1,
            translationSourceRevision = 1,
        ),
    )
}

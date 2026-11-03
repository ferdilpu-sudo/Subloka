package app.subloka.core.domain

/** MACHINE is deliberately unknown: never infer old output's provider from today's selection. */
object TranslationOrigins {
    fun fromEngine(engine: String): TranslationOrigin = when {
        engine.startsWith("gemma:") -> TranslationOrigin.MACHINE_GEMMA
        engine.startsWith("mlkit:") -> TranslationOrigin.MACHINE_MLKIT
        else -> TranslationOrigin.MACHINE
    }

    /**
     * Freshness records whether a translation matches the source revision, not
     * whether its meaning has been checked by a bilingual reviewer.
     *
     * Do not infer model output quality from a CURRENT status or provider name.
     */
    fun isCurrentMachineTranslation(segment: CaptionSegment): Boolean =
        segment.translationText.isNotBlank() &&
            segment.translationStatus == TranslationStatus.CURRENT &&
            segment.translationSourceRevision == segment.sourceRevision &&
            when (segment.translationOrigin) {
                TranslationOrigin.MACHINE,
                TranslationOrigin.MACHINE_GEMMA,
                TranslationOrigin.MACHINE_MLKIT -> true
                else -> false
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

    /**
     * Warnings for user-visible translation exports; do not infer the provider of old MACHINE rows.
     * Caller shows these only when TRANSLATION or BOTH is selected.
     * No captions, metadata, or attribution text are injected into SRT/MP4 payloads here.
     */
    fun exportWarnings(segments: List<CaptionSegment>): List<String> {
        val current = segments.filter {
            it.translationStatus == TranslationStatus.CURRENT &&
                it.translationText.isNotBlank() &&
                it.translationSourceRevision == it.sourceRevision
        }
        val oldGoogle = current.count { it.translationOrigin == TranslationOrigin.MACHINE_MLKIT }
        val unknown = current.count { it.translationOrigin == TranslationOrigin.MACHINE }
        val machineCount = current.count(::isCurrentMachineTranslation)
        return buildList {
            if (oldGoogle > 0) add(
                "$oldGoogle caption hasil lama Google Translate (ML Kit) termasuk dalam ekspor. " +
                    "Periksa persyaratan atribusi Google sebelum membagikannya; " +
                    "lihat Privasi dan lisensi."
            )
            if (unknown > 0) add(
                "$unknown caption terjemahan otomatis tidak memiliki catatan penyedia. " +
                    "Jangan menganggapnya berasal dari Google Translate atau TranslateGemma."
            )
            if (machineCount > 0) add(
                "$machineCount caption berisi terjemahan otomatis. Status terbaru bukan jaminan " +
                    "makna benar; periksa pelaku, penerima, kata ganti, penyangkalan, nama, " +
                    "dan angka sebelum ekspor."
            )
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

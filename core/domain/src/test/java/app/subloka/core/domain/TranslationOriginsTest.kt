package app.subloka.core.domain

import org.junit.Assert.assertEquals
import org.junit.Test

class TranslationOriginsTest {
    @Test fun onlyRecognizedFrozenEngineKeysIdentifyProvider() {
        assertEquals(TranslationOrigin.MACHINE_GEMMA, TranslationOrigins.fromEngine("gemma:hash:runtime"))
        assertEquals(TranslationOrigin.MACHINE_MLKIT, TranslationOrigins.fromEngine("mlkit:17.0.3"))
        assertEquals(TranslationOrigin.MACHINE, TranslationOrigins.fromEngine("other:gemma"))
        assertEquals(TranslationOrigin.MACHINE, TranslationOrigins.fromEngine(""))
    }

    @Test fun manualAndLegacyLabelsNeverClaimGoogleProvider() {
        assertEquals("Terjemahan diedit manual", TranslationOrigins.label(TranslationOrigin.MANUAL))
        assertEquals("Terjemahan otomatis · penyedia belum tercatat", TranslationOrigins.label(TranslationOrigin.MACHINE))
    }

    private fun translated(id: String, origin: TranslationOrigin): CaptionSegment =
        CaptionSegment(id, 0, 1_000_000, SourceLanguage.INDONESIA, "Halo", "Hello",
            TranslationStatus.CURRENT, origin, 2, 2)

    @Test fun exportWarningsOnlyForCurrentHistoricallyAttributedMachineOutputs() {
        val google = translated("google", TranslationOrigin.MACHINE_MLKIT)
        val unknown = translated("unknown", TranslationOrigin.MACHINE)
        val gemma = translated("gemma", TranslationOrigin.MACHINE_GEMMA)
        val manual = translated("manual", TranslationOrigin.MANUAL)
        val warnings = TranslationOrigins.exportWarnings(listOf(google, unknown, gemma, manual))
        assertEquals(3, warnings.size)
        assertEquals(true, warnings[0].startsWith("1 caption hasil lama Google Translate (ML Kit)"))
        assertEquals(true, warnings[1].startsWith("1 caption terjemahan otomatis tidak memiliki catatan penyedia"))
        assertEquals(true, warnings[2].startsWith("3 caption berisi terjemahan otomatis"))
        assertEquals(1, TranslationOrigins.exportWarnings(listOf(gemma, manual)).size)
        assertEquals(emptyList<String>(), TranslationOrigins.exportWarnings(listOf(manual)))
    }

    @Test fun staleGoogleOutputIsNotMisrepresentedAsCurrentExport() {
        val old = translated("old", TranslationOrigin.MACHINE_MLKIT)
        assertEquals(emptyList<String>(), TranslationOrigins.exportWarnings(listOf(
            old.copy(translationStatus = TranslationStatus.STALE),
            old.copy(id = "failed", translationStatus = TranslationStatus.FAILED),
            old.copy(id = "pending", translationStatus = TranslationStatus.PENDING)
        )))
    }


    @Test fun reviewWarningsOnlyApplyToFreshMachineOutputsNotManualOrStale() {
        for (origin in listOf(TranslationOrigin.MACHINE, TranslationOrigin.MACHINE_GEMMA,
            TranslationOrigin.MACHINE_MLKIT)) {
            val current = translated("machine", origin)
            assertEquals(true, TranslationOrigins.isCurrentMachineTranslation(current))
            assertEquals(false, TranslationOrigins.isCurrentMachineTranslation(
                current.copy(translationStatus = TranslationStatus.STALE)))
            assertEquals(false, TranslationOrigins.isCurrentMachineTranslation(
                current.copy(translationStatus = TranslationStatus.STALE, translationSourceRevision = 1)))
            // CURRENT with stale revision or blank output is prohibited by
            // CaptionSegment itself. Test the invariant rather than constructing
            // an impossible live caption and falsely blaming the QA helper.
            assertEquals(IllegalArgumentException::class.java, runCatching {
                current.copy(translationSourceRevision = 1)
            }.exceptionOrNull()?.javaClass)
            assertEquals(IllegalArgumentException::class.java, runCatching {
                current.copy(translationText = " ")
            }.exceptionOrNull()?.javaClass)
        }
        val manual = translated("manual", TranslationOrigin.MANUAL)
        assertEquals(false, TranslationOrigins.isCurrentMachineTranslation(manual))
        assertEquals(emptyList<String>(), TranslationOrigins.exportWarnings(listOf(manual)))
    }

}

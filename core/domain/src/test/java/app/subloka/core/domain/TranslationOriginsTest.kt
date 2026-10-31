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
        assertEquals(2, warnings.size)
        assertEquals(true, warnings[0].startsWith("1 caption hasil lama Google Translate (ML Kit)"))
        assertEquals(true, warnings[1].startsWith("1 caption terjemahan otomatis tidak memiliki catatan penyedia"))
        assertEquals(emptyList<String>(), TranslationOrigins.exportWarnings(listOf(gemma, manual)))
    }

    @Test fun staleGoogleOutputIsNotMisrepresentedAsCurrentExport() {
        val old = translated("old", TranslationOrigin.MACHINE_MLKIT)
        assertEquals(emptyList<String>(), TranslationOrigins.exportWarnings(listOf(
            old.copy(translationStatus = TranslationStatus.STALE),
            old.copy(id = "failed", translationStatus = TranslationStatus.FAILED),
            old.copy(id = "pending", translationStatus = TranslationStatus.PENDING)
        )))
    }

}

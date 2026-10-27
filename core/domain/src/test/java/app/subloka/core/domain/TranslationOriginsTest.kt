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
}

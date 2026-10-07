package app.subloka.engine.translation

import androidx.test.ext.junit.runners.AndroidJUnit4
import app.subloka.core.domain.ModelReadinessState
import app.subloka.core.domain.SourceLanguage
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MlKitTranslationInstrumentedTest {
    @Test
    fun downloadsModelsAndTranslatesBothDirections() = runBlocking {
        MlKitOfflineTranslator().use { translator ->
            translator.ensureReady(requireWifi = false)
            assertEquals(ModelReadinessState.READY, translator.state())

            val enToId = translator.translate(
                text = "Rina has 3 red books and does not sell them.",
                sourceLanguage = SourceLanguage.ENGLISH,
            )
            assertTrue(enToId.isNotBlank())
            assertTrue(enToId.contains("Rina", ignoreCase = true))
            assertTrue(enToId.contains("3"))

            val idToEn = translator.translate(
                text = "Rina punya 7 buku biru dan tidak menjualnya.",
                sourceLanguage = SourceLanguage.INDONESIA,
            )
            assertTrue(idToEn.isNotBlank())
            assertTrue(idToEn.contains("Rina", ignoreCase = true))
            assertTrue(idToEn.contains("7"))
        }
    }
}

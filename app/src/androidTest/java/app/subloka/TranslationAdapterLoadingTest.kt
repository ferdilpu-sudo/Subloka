package app.subloka

import androidx.test.ext.junit.runners.AndroidJUnit4
import app.subloka.core.domain.ModelReadinessState
import app.subloka.core.domain.SourceLanguage
import app.subloka.engine.translation.TranslateGemmaOfflineTranslator
import androidx.test.core.app.ApplicationProvider
import android.content.Context
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Fresh emulator app: Gemma never downloads a model implicitly. */
@RunWith(AndroidJUnit4::class)
class TranslationAdapterLoadingTest {
    @Test fun freshAppRequiresExplicitModelProvisioning() = runBlocking {
        TranslateGemmaOfflineTranslator(ApplicationProvider.getApplicationContext<Context>(), termsAccepted = false).use { translator ->
            assertEquals(ModelReadinessState.NOT_READY, translator.state())
            try {
                translator.translate("Synthetic test", SourceLanguage.ENGLISH)
                fail("Must not translate without provisioned models")
            } catch (_: IllegalStateException) { }
            assertEquals(ModelReadinessState.NOT_READY, translator.state())
        }
    }
}


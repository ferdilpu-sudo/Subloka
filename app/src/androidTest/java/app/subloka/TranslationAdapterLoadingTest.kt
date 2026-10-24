package app.subloka

import androidx.test.ext.junit.runners.AndroidJUnit4
import app.subloka.core.domain.ModelReadinessState
import app.subloka.core.domain.SourceLanguage
import app.subloka.engine.translation.MlKitOfflineTranslator
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Fresh emulator app: SDK initializes, no implicit model provisioning/inference. */
@RunWith(AndroidJUnit4::class)
class TranslationAdapterLoadingTest {
    @Test fun freshAppRequiresExplicitModelProvisioning() = runBlocking {
        MlKitOfflineTranslator().use { translator ->
            assertEquals(ModelReadinessState.NOT_READY, translator.state())
            try {
                translator.translate("Synthetic test", SourceLanguage.ENGLISH)
                fail("Must not translate without provisioned models")
            } catch (_: IllegalStateException) { }
            assertEquals(ModelReadinessState.NOT_READY, translator.state())
        }
    }
}

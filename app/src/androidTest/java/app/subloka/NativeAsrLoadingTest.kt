package app.subloka

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import app.subloka.engine.asr.WhisperSpeechSession
import java.io.File
import org.junit.Assert.assertThrows
import org.junit.Test
import org.junit.runner.RunWith

/** Proves APK JNI loading and error propagation only; no model inference claim. */
@RunWith(AndroidJUnit4::class)
class NativeAsrLoadingTest {
    @Test fun bundledNativeEngineRejectsMissingModelWithoutCrashing() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val missing = File(context.cacheDir, "never-installed-test-model.bin")
        check(!missing.exists())
        assertThrows(IllegalStateException::class.java) { WhisperSpeechSession(missing, missing) }
    }
}

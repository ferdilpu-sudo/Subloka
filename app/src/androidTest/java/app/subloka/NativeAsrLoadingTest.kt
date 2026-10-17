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
        // Load both independently linked ggml revisions into one process, without model downloads.
        val type = Class.forName("app.subloka.engine.translation.NativeGemma")
        val instance = type.getField("INSTANCE").get(null)
        val open = type.getDeclaredMethod("open", String::class.java)
        val failure = assertThrows(java.lang.reflect.InvocationTargetException::class.java) {
            open.invoke(instance, missing.absolutePath)
        }
        check(failure.cause is IllegalStateException)
        assertThrows(IllegalStateException::class.java) { WhisperSpeechSession(missing, missing) }
    }
}

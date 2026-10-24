package app.subloka.engine.translation

import app.subloka.core.domain.*
import java.nio.file.Files
import java.security.MessageDigest
import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test

class TranslationModelStoreTest {
    private val bytes = "verified model".toByteArray()
    private val model = TranslateGemmaModel.descriptor.copy(fileName = "test.gguf", expectedSizeBytes = bytes.size.toLong(),
        expectedSha256 = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) })

    @Test fun invalidReplacementPreservesInstalledModelAndRemovesPartial() = runBlocking {
        val dir = Files.createTempDirectory("gemma-test").toFile()
        try {
            val store = TranslationModelStore(dir)
            store.installFrom(model, bytes.inputStream())
            for (invalid in listOf(bytes + 0, bytes.dropLast(1).toByteArray(), ByteArray(bytes.size))) {
                try { store.installFrom(model, invalid.inputStream()); fail("Must reject invalid model") }
                catch (_: IllegalArgumentException) {} catch (_: IllegalStateException) {}
                assertArrayEquals(bytes, store.targetFile(model).readBytes())
                assertFalse(dir.resolve("test.gguf.part").exists())
            }
            assertEquals(ModelReadinessState.READY, store.state(model))
        } finally { dir.deleteRecursively() }
    }
    @Test fun networkLossOrCancellationNeverReplacesVerifiedFile() = runBlocking {
        val dir = Files.createTempDirectory("gemma-stop").toFile()
        try {
            TranslationModelStore(dir).installFrom(model, bytes.inputStream())
            for (cancel in listOf(false, true)) {
                val store = TranslationModelStore(dir, { if (cancel) throw CancellationException() else error("Wi-Fi lost") })
                try { store.installFrom(model, bytes.inputStream()); fail("Must stop") }
                catch (_: CancellationException) {} catch (_: IllegalStateException) {}
                assertArrayEquals(bytes, store.targetFile(model).readBytes())
                assertFalse(dir.resolve("test.gguf.part").exists())
            }
        } finally { dir.deleteRecursively() }
    }
}

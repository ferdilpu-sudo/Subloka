package app.subloka.engine.asr

import app.subloka.core.domain.ManagedModelDescriptor
import app.subloka.core.domain.ModelReadinessState
import java.security.MessageDigest
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WhisperModelStoreTest {
    @Test
    fun validModelIsInstalledAtomicallyAndBecomesReady() = runTest {
        val dir = createTempDir(prefix = "subloka-model-test-")
        try {
            val bytes = "valid whisper fixture".encodeToByteArray()
            val model = descriptor(bytes)
            val store = WhisperModelStore(dir)

            assertEquals(ModelReadinessState.NOT_READY, store.state(model))
            val target = store.installFrom(model, bytes.inputStream())

            assertTrue(target.isFile)
            assertFalse(dir.resolve("${model.fileName}.part").exists())
            assertEquals(bytes.toList(), target.readBytes().toList())
            assertEquals(ModelReadinessState.READY, store.state(model))
        } finally {
            dir.deleteRecursively()
        }
    }

    @Test
    fun checksumMismatchDoesNotPublishPartialModel() = runTest {
        val dir = createTempDir(prefix = "subloka-model-test-")
        try {
            val expectedBytes = "expected".encodeToByteArray()
            val model = descriptor(expectedBytes)
            val store = WhisperModelStore(dir)

            try {
                store.installFrom(model, "corrupt".byteInputStream())
                throw AssertionError("Expected checksum failure")
            } catch (_: IllegalArgumentException) {
                // Expected.
            }

            assertFalse(store.targetFile(model).exists())
            assertFalse(dir.resolve("${model.fileName}.part").exists())
        } finally {
            dir.deleteRecursively()
        }
    }

    private fun descriptor(bytes: ByteArray): ManagedModelDescriptor {
        val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { byte -> "%02x".format(byte.toInt() and 0xff) }
        return ManagedModelDescriptor(
            id = "fixture",
            displayName = "Fixture",
            fileName = "fixture.bin",
            downloadUrl = "https://example.invalid/fixture.bin",
            expectedSha256 = digest,
            nominalSizeMiB = 1,
            licenseName = "TEST",
            sourceRevision = "fixture",
        )
    }
}

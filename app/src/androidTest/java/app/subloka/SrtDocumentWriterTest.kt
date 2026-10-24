package app.subloka

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import app.subloka.core.domain.SrtDocument
import java.io.ByteArrayOutputStream
import java.io.IOException
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SrtDocumentWriterTest {
    @Test fun writesRealUtf8FileAndClosesBeforeReturning() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val file = java.io.File.createTempFile("srt-test", ".srt", context.cacheDir)
        try {
            val document = SrtDocument("id.srt", "1\r\n00:00:00,000 --> 00:00:01,000\r\nHé 🌴\r\n\r\n")
            SrtDocumentWriter.write(document) { file.outputStream() }
            assertArrayEquals(document.text.toByteArray(Charsets.UTF_8), file.readBytes())
        } finally { file.delete() }
    }
    @Test fun failedWriteNullStreamAndFailedCloseNeverReportSuccess() {
        val document = SrtDocument("id.srt", "caption")
        try { SrtDocumentWriter.write(document) { null }; fail("null stream accepted") }
        catch (_: IllegalArgumentException) { }
        var closed = false
        val bad = object : ByteArrayOutputStream() {
            override fun write(b: ByteArray, off: Int, len: Int) { throw IOException("full") }
            override fun close() { closed = true }
        }
        try { SrtDocumentWriter.write(document) { bad }; fail("failed write accepted") }
        catch (_: IOException) { }
        assertTrue(closed)
        val closeFailure = object : ByteArrayOutputStream() {
            override fun close() { throw IOException("close failed") }
        }
        try { SrtDocumentWriter.write(document) { closeFailure }; fail("failed close accepted") }
        catch (_: IOException) { }
    }
}

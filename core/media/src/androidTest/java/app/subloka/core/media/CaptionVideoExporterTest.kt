package app.subloka.core.media

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.util.Base64
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import app.subloka.core.domain.*
import kotlinx.coroutines.*
import java.io.File
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CaptionVideoExporterTest {
    private val context: Context = ApplicationProvider.getApplicationContext()
    private fun source(name: String): File {
        val bytes = InstrumentationRegistry.getInstrumentation().context.assets.open("$name.mp4.b64").use { it.readBytes() }
        return File.createTempFile("input", ".mp4", context.cacheDir).apply { writeBytes(Base64.decode(bytes, Base64.DEFAULT)) }
    }
    private suspend fun project(file: File): CaptionProject {
        val d = AndroidMediaSource(context).inspect(Uri.fromFile(file).toString())
        return CaptionProject("test", "test", d.uri, d.displayName, d.sizeBytes, d.fingerprintSha256,
            d.durationUs, d.widthPx, d.heightPx, d.rotationDegrees, SourceLanguage.INDONESIA,
            SourceLanguage.ENGLISH, 0, 0, 0)
    }
    private fun cue() = CaptionSegment("one", 500_000, 1_000_000, SourceLanguage.INDONESIA,
        "Halo dunia", "Hello world", TranslationStatus.CURRENT, TranslationOrigin.MANUAL, 1, 1)

    @Test fun encodesTimedBilingualPortraitWithAudioAndPreservesSource() = runBlocking {
        val input = source("rotated")
        val bytes = input.readBytes()
        val output = File(context.cacheDir, "output-${System.nanoTime()}.mp4")
        try {
            val p = project(input)
            assertTrue("Fixture must actually have portrait rotation", p.rotationDegrees in setOf(90, 270))
            withTimeout(90_000) { CaptionVideoExporter(context).render(p, listOf(cue()), CaptionStyle(), output) }
            assertArrayEquals(bytes, input.readBytes())
            val d = AndroidMediaSource(context).inspect(Uri.fromFile(output).toString())
            val rotated = d.rotationDegrees in setOf(90, 270)
            assertEquals(240, if (rotated) d.heightPx else d.widthPx)
            assertEquals(320, if (rotated) d.widthPx else d.heightPx)
            assertTrue(d.audioTracks.isNotEmpty())
            MediaMetadataRetriever().use { retriever ->
                retriever.setDataSource(output.absolutePath)
                fun ink(us: Long): Int {
                    val frame = requireNotNull(retriever.getFrameAtTime(us, MediaMetadataRetriever.OPTION_CLOSEST))
                    val result = ink(frame); frame.recycle(); return result
                }
                assertEquals(0, ink(200_000))
                assertTrue("Subtitle must be burned into active frame", ink(700_000) > 25)
                assertEquals("Subtitle must disappear after interval", 0, ink(1_300_000))
            }
        } finally { input.delete(); output.delete() }
    }
    @Test fun sourceOnlyLandscapeAllowsMissingTranslationAndCancelNeverPublishes() = runBlocking {
        val input = source("landscape")
        val output = File(context.cacheDir, "output-${System.nanoTime()}.mp4")
        try {
            val p = project(input)
            val missing = cue().copy(translationStatus = TranslationStatus.MISSING, translationText = "")
            withTimeout(90_000) {
                CaptionVideoExporter(context).render(p, listOf(missing), CaptionStyle(displayMode = CaptionDisplayMode.ORIGINAL), output)
            }
            assertTrue(output.length() > 0); output.delete()
            val started = CompletableDeferred<Unit>()
            val job = launch {
                CaptionVideoExporter(context).render(p, listOf(cue()), CaptionStyle(), output) {
                    started.complete(Unit)
                    cancel("test cancel")
                }
            }
            withTimeout(20_000) { started.await(); job.join() }
            assertFalse("Cancelled output must be removed", output.exists())
        } finally { input.delete(); output.delete() }
    }
    @Test fun sharedPainterUsesHalfOpenBoundariesModesAndRejectsOverflow() {
        val bitmap = Bitmap.createBitmap(720, 1280, Bitmap.Config.ARGB_8888)
        val painter = SubtitlePainter(listOf(cue()), CaptionStyle())
        val canvas = Canvas(bitmap)
        painter.draw(canvas, 720, 1280, 499_999); assertEquals(0, ink(bitmap))
        painter.draw(canvas, 720, 1280, 500_000); assertTrue(ink(bitmap) > 0)
        bitmap.eraseColor(Color.TRANSPARENT)
        painter.draw(canvas, 720, 1280, 1_000_000); assertEquals(0, ink(bitmap))
        val huge = cue().copy(sourceText = "caption ".repeat(300))
        try { SubtitlePainter(listOf(huge), CaptionStyle()).validate(720, 1280); fail("overflow accepted") }
        catch (_: IllegalArgumentException) { }
        bitmap.recycle()
    }
    private fun ink(bitmap: Bitmap): Int {
        var count = 0
        for (y in bitmap.height / 2 until bitmap.height) for (x in 0 until bitmap.width) {
            val c = bitmap.getPixel(x, y)
            if (Color.red(c) > 170 && Color.green(c) > 150 && Color.alpha(c) > 0) count++
        }
        return count
    }
}

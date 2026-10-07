package app.subloka.core.media

import android.content.Context
import android.net.Uri
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import app.subloka.core.domain.PcmSampleFormat
import java.io.File
import java.io.RandomAccessFile
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AndroidPcmDecoderInstrumentedTest {
    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun decodesGeneratedPcmWavWithoutNetworkOrSourceMutation() = runBlocking {
        val source = File(context.cacheDir, "pcm-fixture.wav")
        writePcm16Wav(source, sampleRate = 16_000, sampleCount = 8_000)
        val before = source.readBytes()

        val mediaSource = AndroidMediaSource(context)
        var emittedBytes = 0L
        val summary = mediaSource.decodePcm(
            uri = Uri.fromFile(source).toString(),
            maxOutputBytes = 4_096,
        ) { chunk ->
            emittedBytes += chunk.bytes.size
            assertEquals(16_000, chunk.sampleRate)
            assertEquals(1, chunk.channelCount)
            assertEquals(PcmSampleFormat.S16_LE, chunk.sampleFormat)
        }

        assertTrue(emittedBytes > 0)
        assertTrue(summary.bytesDecoded > 0)
        assertTrue(summary.truncated)
        assertTrue(before.contentEquals(source.readBytes()))
    }

    private fun writePcm16Wav(file: File, sampleRate: Int, sampleCount: Int) {
        val dataSize = sampleCount * 2
        RandomAccessFile(file, "rw").use { out ->
            out.setLength(0)
            out.writeBytes("RIFF")
            writeLeInt(out, 36 + dataSize)
            out.writeBytes("WAVE")
            out.writeBytes("fmt ")
            writeLeInt(out, 16)
            writeLeShort(out, 1)
            writeLeShort(out, 1)
            writeLeInt(out, sampleRate)
            writeLeInt(out, sampleRate * 2)
            writeLeShort(out, 2)
            writeLeShort(out, 16)
            out.writeBytes("data")
            writeLeInt(out, dataSize)
            repeat(sampleCount) { index ->
                val sample = if ((index / 40) % 2 == 0) 8_000 else -8_000
                writeLeShort(out, sample)
            }
        }
    }

    private fun writeLeInt(out: RandomAccessFile, value: Int) {
        out.write(value and 0xff)
        out.write((value ushr 8) and 0xff)
        out.write((value ushr 16) and 0xff)
        out.write((value ushr 24) and 0xff)
    }

    private fun writeLeShort(out: RandomAccessFile, value: Int) {
        out.write(value and 0xff)
        out.write((value ushr 8) and 0xff)
    }
}

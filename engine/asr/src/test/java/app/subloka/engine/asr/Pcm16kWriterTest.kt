package app.subloka.engine.asr

import app.subloka.core.domain.*
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.junit.Assert.*
import org.junit.Test

class Pcm16kWriterTest {
    @Test fun resamplingDoesNotDependOnDecoderChunkBoundaries() {
        for (rate in listOf(44100, 48000)) {
            val bytes = ByteBuffer.allocate(rate * 2).order(ByteOrder.LITTLE_ENDIAN).apply {
                repeat(rate) { putShort(((it % 101) * 200).toShort()) }
            }.array()
            fun convert(split: Boolean): ByteArray {
                val out = ByteArrayOutputStream()
                val writer = Pcm16kWriter(out, 1_000_000)
                val stride = if (split) 1024 else rate
                var frame = 0
                while (frame < rate) {
                    val end = minOf(frame + stride, rate)
                    writer.append(PcmChunk(bytes.copyOfRange(frame * 2, end * 2), frame * 1_000_000L / rate, rate, 1, PcmSampleFormat.S16_LE))
                    frame = end
                }
                assertEquals(16000L, writer.framesWritten)
                return out.toByteArray()
            }
            assertArrayEquals(convert(false), convert(true))
        }
    }
    @Test fun stereoFloatDownmixAndLeadingPtsArePreserved() {
        val out = ByteArrayOutputStream()
        val writer = Pcm16kWriter(out, 1_000_000)
        val bytes = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN).putFloat(0.8f).putFloat(-0.8f).array()
        writer.append(PcmChunk(bytes, 100_000, 16000, 2, PcmSampleFormat.FLOAT32_LE))
        assertEquals(1601L, writer.framesWritten)
        assertTrue(out.toByteArray().all { it == 0.toByte() })
    }
    @Test fun discontinuitiesNonfiniteAndOversizedAudioFailClosed() {
        val writer = Pcm16kWriter(ByteArrayOutputStream(), 1_000_000)
        writer.append(PcmChunk(ByteArray(3200), 0, 16000, 1, PcmSampleFormat.S16_LE))
        assertThrows(IllegalArgumentException::class.java) {
            writer.append(PcmChunk(ByteArray(2), 900_000, 16000, 1, PcmSampleFormat.S16_LE))
        }
        assertThrows(IllegalArgumentException::class.java) {
            val nan = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putFloat(Float.NaN).array()
            Pcm16kWriter(ByteArrayOutputStream(), 100_000).append(PcmChunk(nan, 0, 16000, 1, PcmSampleFormat.FLOAT32_LE))
        }
        assertThrows(IllegalStateException::class.java) {
            Pcm16kWriter(ByteArrayOutputStream(), 100_000).append(PcmChunk(ByteArray(16000), 0, 16000, 1, PcmSampleFormat.S16_LE))
        }
    }
}

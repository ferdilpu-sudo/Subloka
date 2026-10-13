package app.subloka.engine.asr

import app.subloka.core.domain.PcmChunk
import app.subloka.core.domain.PcmSampleFormat
import java.io.OutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.roundToInt

/** Streaming downmix + linear resampling. Preserves the first PTS; rejects discontinuities. */
class Pcm16kWriter(private val output: OutputStream, private val maxDurationUs: Long) {
    private var rate = 0
    private var channels = 0
    private var format = PcmSampleFormat.UNKNOWN
    private var firstPtsUs = 0L
    private var inputFrames = 0L
    private var nextOutput = 0L
    private var previous = 0f
    var framesWritten = 0L
        private set

    fun append(chunk: PcmChunk) {
        require(chunk.sampleRate in 8000..192000 && chunk.channelCount in 1..8)
        require(chunk.presentationTimeUs >= 0)
        if (rate == 0) {
            rate = chunk.sampleRate; channels = chunk.channelCount; format = chunk.sampleFormat
            firstPtsUs = chunk.presentationTimeUs
            require(firstPtsUs <= maxDurationUs) { "Audio starts outside video" }
            repeat((firstPtsUs * 16000 / 1_000_000).toInt()) { write(0f) }
        }
        require(rate == chunk.sampleRate && channels == chunk.channelCount && format == chunk.sampleFormat) {
            "PCM format changed during decoding"
        }
        val expectedPts = firstPtsUs + inputFrames * 1_000_000 / rate
        require(abs(chunk.presentationTimeUs - expectedPts) <= 20_000) { "Audio timestamp discontinuity" }
        val width = when (format) {
            PcmSampleFormat.S16_LE -> 2
            PcmSampleFormat.FLOAT32_LE -> 4
            PcmSampleFormat.U8 -> 1
            else -> error("Unsupported PCM format")
        }
        require(chunk.bytes.size % (width * channels) == 0) { "Incomplete PCM frame" }
        val buffer = ByteBuffer.wrap(chunk.bytes).order(ByteOrder.LITTLE_ENDIAN)
        while (buffer.hasRemaining()) {
            var mono = 0f
            repeat(channels) {
                val value = when (format) {
                    PcmSampleFormat.S16_LE -> buffer.short / 32768f
                    PcmSampleFormat.FLOAT32_LE -> buffer.float
                    else -> ((buffer.get().toInt() and 255) - 128) / 128f
                }
                require(value.isFinite()) { "Invalid PCM sample" }
                mono += value.coerceIn(-1f, 1f) / channels
            }
            if (inputFrames == 0L) previous = mono
            while (nextOutput * rate <= inputFrames * 16000) {
                val fraction = (nextOutput * rate / 16000.0 - (inputFrames - 1)).coerceIn(0.0, 1.0)
                write((previous + (mono - previous) * fraction).toFloat())
                nextOutput++
            }
            previous = mono
            inputFrames++
        }
    }

    private fun write(value: Float) {
        check(framesWritten < (maxDurationUs + 20_000) * 16000 / 1_000_000) { "PCM exceeds video duration" }
        val sample = (value.coerceIn(-1f, 1f) * 32767).roundToInt()
        output.write(sample and 255); output.write((sample shr 8) and 255)
        framesWritten++
    }
}

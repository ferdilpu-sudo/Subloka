package app.subloka.core.media

import android.content.Context
import android.media.AudioFormat
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.net.Uri
import app.subloka.core.domain.MediaErrorCode
import app.subloka.core.domain.MediaSourceException
import app.subloka.core.domain.PcmChunk
import app.subloka.core.domain.PcmDecodeSummary
import app.subloka.core.domain.PcmSampleFormat
import java.nio.ByteBuffer

internal class AndroidPcmDecoder(
    context: Context,
) {
    private val appContext = context.applicationContext

    fun decode(
        uri: Uri,
        audioTrackIndex: Int?,
        maxOutputBytes: Long?,
        onChunk: (PcmChunk) -> Unit,
    ): PcmDecodeSummary {
        val extractor = MediaExtractor()
        try {
            extractor.setDataSource(appContext, uri, null)
            val trackIndex = resolveAudioTrack(extractor, audioTrackIndex)
            val inputFormat = extractor.getTrackFormat(trackIndex)
            val mime = inputFormat.getString(MediaFormat.KEY_MIME)
                ?: throw MediaSourceException(MediaErrorCode.UNSUPPORTED_MEDIA, "Audio MIME tidak tersedia.")
            extractor.selectTrack(trackIndex)

            return if (mime == MediaFormat.MIMETYPE_AUDIO_RAW) {
                decodeRaw(extractor, inputFormat, maxOutputBytes, onChunk)
            } else {
                decodeCompressed(extractor, inputFormat, mime, maxOutputBytes, onChunk)
            }
        } catch (error: MediaSourceException) {
            throw error
        } catch (error: SecurityException) {
            throw MediaSourceException(MediaErrorCode.URI_PERMISSION_LOST, "Izin membaca audio hilang.", error)
        } catch (error: Exception) {
            throw MediaSourceException(MediaErrorCode.DECODE_FAILURE, "Audio gagal didekode menjadi PCM.", error)
        } finally {
            extractor.release()
        }
    }

    private fun resolveAudioTrack(extractor: MediaExtractor, requested: Int?): Int {
        if (requested != null) {
            require(requested in 0 until extractor.trackCount) { "audioTrackIndex di luar range" }
            val mime = extractor.getTrackFormat(requested).getString(MediaFormat.KEY_MIME).orEmpty()
            if (mime.startsWith("audio/")) return requested
            throw MediaSourceException(MediaErrorCode.NO_AUDIO, "Track yang dipilih bukan audio.")
        }

        for (index in 0 until extractor.trackCount) {
            val mime = extractor.getTrackFormat(index).getString(MediaFormat.KEY_MIME).orEmpty()
            if (mime.startsWith("audio/")) return index
        }
        throw MediaSourceException(MediaErrorCode.NO_AUDIO, "Video tidak memiliki track audio.")
    }

    private fun decodeRaw(
        extractor: MediaExtractor,
        format: MediaFormat,
        maxOutputBytes: Long?,
        onChunk: (PcmChunk) -> Unit,
    ): PcmDecodeSummary {
        val sampleRate = positive(format, MediaFormat.KEY_SAMPLE_RATE)
        val channels = positive(format, MediaFormat.KEY_CHANNEL_COUNT)
        val sampleFormat = pcmFormat(format)
        val capacity = if (format.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) {
            format.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE).coerceAtLeast(64 * 1024)
        } else {
            256 * 1024
        }
        val buffer = ByteBuffer.allocate(capacity)

        var bytesDecoded = 0L
        var lastPts = 0L
        var truncated = false
        while (true) {
            buffer.clear()
            val size = extractor.readSampleData(buffer, 0)
            if (size < 0) break

            val remaining = maxOutputBytes?.minus(bytesDecoded)
            val emitSize = if (remaining == null) size else minOf(size.toLong(), remaining).toInt()
            if (emitSize <= 0) {
                truncated = true
                break
            }

            val bytes = ByteArray(emitSize)
            buffer.position(0)
            buffer.get(bytes, 0, emitSize)
            lastPts = extractor.sampleTime.coerceAtLeast(0L)
            onChunk(PcmChunk(bytes, lastPts, sampleRate, channels, sampleFormat))
            bytesDecoded += emitSize

            if (emitSize < size || (maxOutputBytes != null && bytesDecoded >= maxOutputBytes)) {
                truncated = true
                break
            }
            extractor.advance()
        }

        return PcmDecodeSummary(bytesDecoded, lastPts, sampleRate, channels, sampleFormat, truncated)
    }

    private fun decodeCompressed(
        extractor: MediaExtractor,
        inputFormat: MediaFormat,
        mime: String,
        maxOutputBytes: Long?,
        onChunk: (PcmChunk) -> Unit,
    ): PcmDecodeSummary {
        val codec = MediaCodec.createByCodecName(AndroidCodecSelector.findDecoderName(inputFormat))
        var started = false
        try {
            codec.configure(inputFormat, null, null, 0)
            codec.start()
            started = true

            var inputEnded = false
            var outputEnded = false
            var outputFormat = inputFormat
            var bytesDecoded = 0L
            var lastPts = 0L
            var truncated = false
            val info = MediaCodec.BufferInfo()

            while (!outputEnded) {
                if (!inputEnded) {
                    val inputIndex = codec.dequeueInputBuffer(TIMEOUT_US)
                    if (inputIndex >= 0) {
                        val inputBuffer = requireNotNull(codec.getInputBuffer(inputIndex))
                        inputBuffer.clear()
                        val size = extractor.readSampleData(inputBuffer, 0)
                        if (size < 0) {
                            codec.queueInputBuffer(
                                inputIndex,
                                0,
                                0,
                                0,
                                MediaCodec.BUFFER_FLAG_END_OF_STREAM,
                            )
                            inputEnded = true
                        } else {
                            codec.queueInputBuffer(inputIndex, 0, size, extractor.sampleTime, extractor.sampleFlags)
                            extractor.advance()
                        }
                    }
                }

                when (val outputIndex = codec.dequeueOutputBuffer(info, TIMEOUT_US)) {
                    MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> outputFormat = codec.outputFormat
                    MediaCodec.INFO_TRY_AGAIN_LATER -> Unit
                    else -> if (outputIndex >= 0) {
                        val endOfStream = info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0
                        if (info.size > 0) {
                            val outputBuffer = requireNotNull(codec.getOutputBuffer(outputIndex))
                            outputBuffer.position(info.offset)
                            outputBuffer.limit(info.offset + info.size)

                            val remaining = maxOutputBytes?.minus(bytesDecoded)
                            val emitSize = if (remaining == null) info.size else minOf(info.size.toLong(), remaining).toInt()
                            if (emitSize > 0) {
                                val bytes = ByteArray(emitSize)
                                outputBuffer.get(bytes)
                                val sampleRate = positive(outputFormat, MediaFormat.KEY_SAMPLE_RATE)
                                val channels = positive(outputFormat, MediaFormat.KEY_CHANNEL_COUNT)
                                val sampleFormat = pcmFormat(outputFormat)
                                lastPts = info.presentationTimeUs.coerceAtLeast(0L)
                                onChunk(PcmChunk(bytes, lastPts, sampleRate, channels, sampleFormat))
                                bytesDecoded += emitSize
                            }

                            if (emitSize < info.size || (maxOutputBytes != null && bytesDecoded >= maxOutputBytes)) {
                                truncated = true
                                outputEnded = true
                            }
                        }
                        codec.releaseOutputBuffer(outputIndex, false)
                        if (endOfStream) outputEnded = true
                    }
                }
            }

            val sampleRate = positive(outputFormat, MediaFormat.KEY_SAMPLE_RATE)
            val channels = positive(outputFormat, MediaFormat.KEY_CHANNEL_COUNT)
            return PcmDecodeSummary(
                bytesDecoded = bytesDecoded,
                lastPresentationTimeUs = lastPts,
                sampleRate = sampleRate,
                channelCount = channels,
                sampleFormat = pcmFormat(outputFormat),
                truncated = truncated,
            )
        } finally {
            if (started) {
                runCatching { codec.stop() }
            }
            codec.release()
        }
    }

    private fun positive(format: MediaFormat, key: String): Int {
        if (!format.containsKey(key)) {
            throw MediaSourceException(MediaErrorCode.DECODE_FAILURE, "PCM output kehilangan $key.")
        }
        return format.getInteger(key).takeIf { it > 0 }
            ?: throw MediaSourceException(MediaErrorCode.DECODE_FAILURE, "Nilai $key tidak valid.")
    }

    private fun pcmFormat(format: MediaFormat): PcmSampleFormat {
        val encoding = if (format.containsKey(MediaFormat.KEY_PCM_ENCODING)) {
            format.getInteger(MediaFormat.KEY_PCM_ENCODING)
        } else {
            AudioFormat.ENCODING_PCM_16BIT
        }
        return when (encoding) {
            AudioFormat.ENCODING_PCM_16BIT -> PcmSampleFormat.S16_LE
            AudioFormat.ENCODING_PCM_FLOAT -> PcmSampleFormat.FLOAT32_LE
            AudioFormat.ENCODING_PCM_8BIT -> PcmSampleFormat.U8
            else -> PcmSampleFormat.UNKNOWN
        }
    }

    private companion object {
        const val TIMEOUT_US = 10_000L
    }
}

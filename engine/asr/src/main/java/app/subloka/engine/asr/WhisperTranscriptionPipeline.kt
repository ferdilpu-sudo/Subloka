package app.subloka.engine.asr

import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.CaptionTimelineValidator
import app.subloka.core.domain.MediaDescriptor
import app.subloka.core.domain.MediaSource
import app.subloka.core.domain.SourceLanguage
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext

class WhisperTranscriptionPipeline(
    private val media: MediaSource,
    private val cache: File,
    private val openSession: (File) -> SpeechSession = ::WhisperSpeechSession,
) {
    private val cancelled = AtomicBoolean(false)
    private val lock = Any()
    private var session: SpeechSession? = null

    fun cancel() {
        cancelled.set(true)
        synchronized(lock) { session?.cancel() }
    }

    suspend fun transcribe(descriptor: MediaDescriptor, language: SourceLanguage, model: File,
                           onStage: (String) -> Unit): List<CaptionSegment> = withContext(Dispatchers.IO) {
        require(descriptor.durationUs in 1..600_000_000L) { "Prototipe mendukung video maksimal 10 menit." }
        val context = currentCoroutineContext()
        fun checkActive() {
            context.ensureActive()
            if (cancelled.get()) throw CancellationException("Transkripsi dibatalkan")
        }
        cache.mkdirs()
        val pcm = File.createTempFile("asr-", ".pcm", cache)
        try {
            checkActive()
            onStage("Membaca audio…")
            pcm.outputStream().buffered().use { output ->
                val writer = Pcm16kWriter(output, descriptor.durationUs)
                val decoded = media.decodePcm(descriptor.uri, onChunk = { chunk -> checkActive(); writer.append(chunk) })
                check(!decoded.truncated && writer.framesWritten > 0) { "Audio tidak lengkap." }
            }
            checkActive()
            onStage("Memuat model caption…")
            val engine = openSession(model)
            synchronized(lock) { session = engine }
            checkActive()
            val captions = mutableListOf<CaptionSegment>()
            val totalFrames = pcm.length() / 2
            var consumed = 0L
            pcm.inputStream().buffered().use { input ->
                val bytes = ByteArray(30 * 16000 * 2)
                while (consumed < totalFrames) {
                    checkActive()
                    val count = minOf(30 * 16000L, totalFrames - consumed).toInt()
                    var read = 0
                    while (read < count * 2) {
                        val n = input.read(bytes, read, count * 2 - read)
                        check(n > 0) { "PCM cache tidak lengkap." }; read += n
                    }
                    val samples = FloatArray(count) { i ->
                        ((bytes[i * 2].toInt() and 255) or (bytes[i * 2 + 1].toInt() shl 8)).toShort() / 32768f
                    }
                    onStage("Mentranskripsi bagian ${consumed / (30 * 16000) + 1} dari ${(totalFrames + 30 * 16000 - 1) / (30 * 16000)}…")
                    checkActive()
                    // Only digital/nearly digital silence; this is not a general speech detector.
                    if (samples.any { kotlin.math.abs(it) > 0.0001f }) {
                        val raw = engine.transcribe(samples, language.code.lowercase())
                        checkActive()
                        CaptionTranscription.appendWindow(captions, raw, consumed * 1_000_000 / 16000,
                            count * 1_000_000L / 16000, descriptor.durationUs, language)
                    }
                    consumed += count
                }
            }
            checkActive()
            CaptionTimelineValidator.validate(descriptor.durationUs, captions)
            captions
        } finally {
            try { synchronized(lock) { session?.close(); session = null } }
            finally { pcm.delete() }
        }
    }
}

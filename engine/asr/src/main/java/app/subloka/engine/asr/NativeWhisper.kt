package app.subloka.engine.asr

import androidx.annotation.Keep
import java.io.File

@Keep
data class RawSpeechSegment(val startUs: Long, val endUs: Long, val text: String)

/** One owning worker; cancel may be called from the UI thread. */
interface SpeechSession : AutoCloseable {
    fun transcribe(samples: FloatArray, language: String): List<RawSpeechSegment>
    fun cancel()
}

@Keep
internal class NativeWhisper {
    external fun open(path: String): Long
    external fun run(handle: Long, samples: FloatArray, language: String): Array<RawSpeechSegment>
    external fun cancel(handle: Long)
    external fun close(handle: Long)
    companion object { init { System.loadLibrary("subloka_asr") } }
}

class WhisperSpeechSession(model: File) : SpeechSession {
    private val native = NativeWhisper()
    private val lock = Any()
    private var handle = native.open(model.absolutePath).also { check(it != 0L) }

    override fun transcribe(samples: FloatArray, language: String): List<RawSpeechSegment> =
        native.run(handle, samples, language).toList()

    override fun cancel() = synchronized(lock) { if (handle != 0L) native.cancel(handle) }

    override fun close() = synchronized(lock) {
        if (handle != 0L) native.close(handle)
        handle = 0L
    }
}

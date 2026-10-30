package app.subloka

import android.content.Context
import app.subloka.core.database.SubLokaDatabaseFactory
import app.subloka.core.domain.ModelReadinessState
import app.subloka.core.media.AndroidMediaSource
import app.subloka.engine.asr.WhisperModelCatalog
import app.subloka.engine.asr.WhisperModelStore
import app.subloka.engine.asr.WhisperTranscriptionPipeline
import java.io.File
import kotlinx.coroutines.*

internal interface AsrTask {
    val savedMessage: String?
    suspend fun run(request: AsrRequest, onStage: (String) -> Unit)
    fun cancel()
}

internal class LocalAsrTask(private val context: Context) : AsrTask {
    @Volatile private var pipeline: WhisperTranscriptionPipeline? = null
    @Volatile override var savedMessage: String? = null
        private set
    override fun cancel() { pipeline?.cancel() }

    override suspend fun run(request: AsrRequest, onStage: (String) -> Unit) = withContext(Dispatchers.IO) {
        val snapshot = request.project
        val models = WhisperModelStore(File(context.filesDir, "whisper-models"))
        check(WhisperModelCatalog.captionModels(request.useTurbo).all { models.state(it) == ModelReadinessState.READY }) {
            "Model tidak tersedia. Siapkan kembali model."
        }
        onStage("Memeriksa video…")
        val media = AndroidMediaSource(context)
        val descriptor = media.inspect(snapshot.sourceUri)
        check(descriptor.fingerprintSha256 == snapshot.sourceFingerprint) { "Video berubah. Buat proyek baru dari video ini." }
        currentCoroutineContext().ensureActive()
        val worker = WhisperTranscriptionPipeline(media, File(context.cacheDir, "asr"))
        pipeline = worker
        try {
            currentCoroutineContext().ensureActive()
            val result = worker.transcribe(descriptor, snapshot.sourceLanguage,
                models.targetFile(WhisperModelCatalog.captionModel(request.useTurbo)),
                models.targetFile(WhisperModelCatalog.vad), onStage)
            currentCoroutineContext().ensureActive()
            onStage("Menyimpan caption…")
            // Commit is the point of no return. Cancellation during commit must not hide saved output.
            withContext(NonCancellable) {
                SubLokaDatabaseFactory.create(context).use { storage ->
                    check(storage.captionRepository.publishGenerated(snapshot.id, snapshot.contentRevision, result)) {
                        "Proyek berubah. Hasil tidak mengganti caption yang sudah ada."
                    }
                    savedMessage = if (result.isEmpty()) "Tidak ada ucapan yang terdeteksi."
                        else "Caption tersimpan. Periksa teks dan waktunya."
                }
            }
        } finally { pipeline = null }
    }
}

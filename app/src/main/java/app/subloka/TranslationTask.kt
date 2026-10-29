package app.subloka

import android.content.Context
import app.subloka.core.database.SubLokaDatabaseFactory
import app.subloka.core.domain.*
import app.subloka.engine.translation.*
import kotlinx.coroutines.*
import java.util.concurrent.atomic.AtomicBoolean

internal interface TranslationTask {
    val savedMessage: String?
    val completed: Boolean
    val error: String?
    suspend fun run(request: TranslationRequest, onStage: (String) -> Unit)
    fun cancel()
}

/** Owns the translator and database until all publications and cleanup have finished. */
internal class LocalTranslationTask(private val context: Context) : TranslationTask {
    private val cancelled = AtomicBoolean(false)
    @Volatile private var translator: TranslateGemmaOfflineTranslator? = null
    @Volatile override var savedMessage: String? = null
        private set
    @Volatile override var completed = false
        private set
    @Volatile override var error: String? = null
        private set
    override fun cancel() { cancelled.set(true); translator?.cancel() }
    override suspend fun run(request: TranslationRequest, onStage: (String) -> Unit) = withContext(Dispatchers.IO) {
        check(request.useGemma && request.termsAccepted && request.engine.startsWith("gemma:"))
        val engine: OfflineTranslator = TranslateGemmaOfflineTranslator(context, request.termsAccepted, onStage).also {
            translator = it
            if (cancelled.get()) it.cancel()
        }
        try {
            engine.use {
                currentCoroutineContext().ensureActive()
                if (cancelled.get()) throw CancellationException()
                check(engine.state() == ModelReadinessState.READY) { "Model terjemahan belum siap." }
                SubLokaDatabaseFactory.create(context).use { storage ->
                    val recovery = storage.translationRecovery
                    val resume = request.pendingId != null
                    val snapshot = storage.captionRepository.list(request.project.id).filter {
                        resume || ((request.segmentId == null || it.id == request.segmentId) &&
                            TranslationEligibility.canGenerate(it, request.replaceCurrentMachine))
                    }
                    currentCoroutineContext().ensureActive()
                    val checkpoint = recovery.begin(request.project.id, request.engine, snapshot, request.pendingId, allowLegacyGemmaResume = true)
                    val work = snapshot.filter { checkpoint.pending[it.id] == it.sourceRevision }
                    try {
                        val result = CaptionTranslationPipeline(engine).run(work, publish = { source, text ->
                            recovery.publish(checkpoint.id, source, text)
                        }, onProgress = { progress ->
                            onStage("Menerjemahkan ${progress.processed}/${progress.total} • ${progress.applied} tersimpan")
                        }, replaceCurrentMachine = true)
                        withContext(NonCancellable) {
                            recovery.stop(checkpoint.id, interrupted = false)
                            completed = result.failed == 0
                            error = if (completed) null else "Sisa caption dapat dilanjutkan. Untuk teks terlalu panjang, pecah caption lalu buat antrean baru."
                            savedMessage = "${result.applied} tersimpan • ${result.conflicted + if (resume) (request.pendingCount - work.size).coerceAtLeast(0) else 0} dilewati karena berubah • ${result.failed} belum selesai."
                        }
                    } finally {
                        withContext(NonCancellable) { recovery.stop(checkpoint.id, interrupted = true) }
                    }
                }
            }
        } finally { translator = null }
    }
}


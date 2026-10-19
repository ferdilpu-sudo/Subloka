package app.subloka

import android.content.Context
import app.subloka.core.media.CaptionVideoExporter
import java.io.File
import kotlinx.coroutines.*

internal interface RenderTask {
    val savedMessage: String?
    val output: File?
    suspend fun run(request: RenderRequest, onStage: (String) -> Unit)
    fun cancel()
}

/** Transformer cancellation is owned by the service coroutine and unwinds on Main. */
internal class LocalRenderTask(private val context: Context) : RenderTask {
    override var savedMessage: String? = null
        private set
    override var output: File? = null
        private set
    override fun cancel() {} // Cancelling the coroutine cancels Transformer on its owning looper.
    override suspend fun run(request: RenderRequest, onStage: (String) -> Unit) {
        val directory = File(context.filesDir, "mp4-staging")
        val file = File(directory, "${request.id}.mp4")
        var published = false
        try {
            withContext(Dispatchers.IO) {
                check(directory.isDirectory || directory.mkdirs())
                check(directory.usableSpace >= 64L * 1024 * 1024) { "Ruang kosong kurang dari 64 MB. Kosongkan penyimpanan lalu coba lagi." }
            }
            CaptionVideoExporter(context).render(request.project, request.segments, request.style, file) { percent ->
                RenderSession.progress(request.id, percent)
                onStage(percent?.let { "Merender subtitle… $it%" } ?: "Merender subtitle…")
            }
            currentCoroutineContext().ensureActive()
            output = file
            savedMessage = "Video selesai dirender. Simpan MP4 ke lokasi pilihanmu."
            published = true
        } finally {
            if (!published) withContext(NonCancellable + Dispatchers.IO) { file.delete() }
        }
    }
}

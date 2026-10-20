package app.subloka

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.subloka.core.domain.*
import java.io.File
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

class VideoExportViewModel(application: Application) : AndroidViewModel(application) {
    data class State(val busy: Boolean = true, val rendering: Boolean = false, val ready: Boolean = false,
        val pending: Boolean = false, val serviceJobId: String? = null, val progress: Int? = null, val message: String? = null)
    private val _state = MutableStateFlow(State())
    val state = _state.asStateFlow()
    private val directory = File(application.filesDir, "mp4-staging")
    private var output: File? = null
    private var name = "subtitle.mp4"
    internal var destination: Mp4Destination = AndroidMp4Destination(application.contentResolver)
    private var operation: Job? = null
    init {
        operation = viewModelScope.launch {
            try {
                val leftovers = withContext(Dispatchers.IO) {
                    check(directory.isDirectory || directory.mkdirs())
                    if (RenderSession.state.value == null) {
                        getApplication<Application>().getSystemService(android.app.NotificationManager::class.java).cancel(RenderForegroundService.NOTIFICATION)
                        directory.listFiles().orEmpty().also { files -> files.forEach { check(it.delete()) } }.isNotEmpty()
                    } else false
                }
                _state.value = State(busy = false, message = if (leftovers) "Hasil sementara sesi sebelumnya dibersihkan. Render ulang jika belum disimpan." else null)
                RenderSession.state.collect { session ->
                    if (session != null) {
                        output = session.output
                        name = session.request.project.title.replace(Regex("[^\\p{L}\\p{N}._ -]"), "_").take(80).ifBlank { "video" } + "-subtitle.mp4"
                        _state.value = State(busy = session.running, rendering = session.running,
                            ready = session.completed && session.output != null, progress = session.progress,
                            message = session.error ?: session.stage, serviceJobId = session.request.id)
                    }
                }
            } catch (cancel: CancellationException) { throw cancel }
            catch (_: Exception) { _state.value = State(busy = false, message = "Penyimpanan sementara belum siap. Kosongkan ruang dan buka ulang aplikasi.") }
        }
    }
    fun reset() {
        if (_state.value.busy || _state.value.pending) return
        val old = output; output = null
        RenderSession.clear()
        getApplication<Application>().getSystemService(android.app.NotificationManager::class.java).cancel(RenderForegroundService.NOTIFICATION)
        viewModelScope.launch(Dispatchers.IO) { old?.delete() }
        _state.value = State(busy = false)
    }
    fun render(project: CaptionProject, segments: List<CaptionSegment>, style: CaptionStyle) {
        if (_state.value.busy || _state.value.pending) return
        val request = RenderSession.reserve(project, segments, style) ?: return
        val old = output; output = null
        viewModelScope.launch(Dispatchers.IO) { old?.delete() }
        _state.value = State(busy = true, rendering = true, serviceJobId = request.id)
        RenderForegroundService.start(getApplication(), request)
    }
    fun cancelRender() { RenderForegroundService.cancel(getApplication()) }
    fun select(): String? {
        if (_state.value.busy || _state.value.pending || !_state.value.ready) return null
        _state.value = _state.value.copy(pending = true)
        return name
    }
    fun pickerFailed() { _state.value = _state.value.copy(pending = false, message = "Pemilih lokasi gagal. Coba lagi.") }
    fun save(uri: Uri?) {
        val file = output
        if (uri == null) { _state.value = _state.value.copy(pending = false, message = "Simpan dibatalkan. Hasil render masih siap."); return }
        _state.value = _state.value.copy(busy = true, pending = false, message = "Menyimpan MP4…")
        operation = viewModelScope.launch {
            try {
                check(file != null && file.isFile) { "Hasil render terputus. Render ulang proyek." }
                withContext(Dispatchers.IO) {
                    requireNotNull(destination.open(uri)).use { target ->
                        file.inputStream().use { input ->
                            val buffer = ByteArray(64 * 1024)
                            while (true) {
                                ensureActive()
                                val count = input.read(buffer)
                                if (count < 0) break
                                target.write(buffer, 0, count)
                            }
                        }
                        target.flush()
                    }
                }
                _state.value = _state.value.copy(busy = false, message = "MP4 tersimpan. Buka video hasil untuk memeriksa subtitle dan audio.")
            } catch (error: Exception) {
                val removed = withContext(NonCancellable + Dispatchers.IO) {
                    try { destination.delete(uri) }
                    catch (_: Exception) { false }
                }
                _state.value = _state.value.copy(busy = false, message = "Simpan gagal. Coba lokasi lain." +
                    if (removed) "" else " File parsial mungkin tertinggal; hapus dari lokasi yang dipilih.")
                if (error is CancellationException) throw error
            }
        }
    }
}

package app.subloka

import android.app.Application
import android.net.Uri
import android.provider.DocumentsContract
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.subloka.core.domain.*
import app.subloka.core.media.CaptionVideoExporter
import java.io.File
import java.util.UUID
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

class VideoExportViewModel(application: Application) : AndroidViewModel(application) {
    data class State(val busy: Boolean = true, val rendering: Boolean = false, val ready: Boolean = false,
        val pending: Boolean = false, val progress: Int? = null, val message: String? = null)
    private val _state = MutableStateFlow(State())
    val state = _state.asStateFlow()
    private val directory = File(application.filesDir, "mp4-staging")
    private var output: File? = null
    private var name = "subtitle.mp4"
    private var operation: Job? = null
    init {
        operation = viewModelScope.launch {
            try {
                val leftovers = withContext(Dispatchers.IO) {
                    check(directory.isDirectory || directory.mkdirs())
                    directory.listFiles().orEmpty().also { files -> files.forEach { check(it.delete()) } }.isNotEmpty()
                }
                _state.value = State(busy = false, message = if (leftovers) "Hasil sementara sesi sebelumnya dibersihkan. Render ulang jika belum disimpan." else null)
            } catch (cancel: CancellationException) { throw cancel }
            catch (_: Exception) { _state.value = State(busy = false, message = "Penyimpanan sementara belum siap. Kosongkan ruang dan buka ulang aplikasi.") }
        }
    }
    fun reset() {
        if (_state.value.busy || _state.value.pending) return
        val old = output; output = null
        viewModelScope.launch(Dispatchers.IO) { old?.delete() }
        _state.value = State(busy = false)
    }
    fun render(project: CaptionProject, segments: List<CaptionSegment>, style: CaptionStyle) {
        if (_state.value.busy || _state.value.pending) return
        val snapshot = segments.toList()
        val old = output; output = null
        _state.value = State(busy = true, rendering = true, message = "Memeriksa video dan subtitle…")
        operation = viewModelScope.launch {
            val file = File(directory, "${UUID.randomUUID()}.mp4")
            try {
                withContext(Dispatchers.IO) {
                    old?.delete()
                    check(directory.usableSpace >= 64L * 1024 * 1024) { "Ruang kosong kurang dari 64 MB. Kosongkan penyimpanan lalu coba lagi." }
                }
                CaptionVideoExporter(getApplication()).render(project, snapshot, style, file) { percent ->
                    _state.value = _state.value.copy(progress = percent, message = "Merender subtitle… Tetap buka aplikasi.")
                }
                ensureActive()
                output = file
                name = project.title.replace(Regex("[^\\p{L}\\p{N}._ -]"), "_").take(80).ifBlank { "video" } + "-subtitle.mp4"
                _state.value = State(busy = false, ready = true, message = "Video selesai dirender. Simpan MP4 ke lokasi pilihanmu.")
            } catch (cancel: CancellationException) {
                withContext(NonCancellable + Dispatchers.IO) { file.delete() }
                _state.value = State(busy = false, message = "Render dihentikan. Video asli aman; tekan Render MP4 untuk mencoba lagi.")
            } catch (error: Exception) {
                withContext(Dispatchers.IO) { file.delete() }
                _state.value = State(busy = false, message = error.message ?: "Render gagal. Coba lagi atau ekspor SRT.")
            }
        }
    }
    fun cancelRender() { if (_state.value.rendering) operation?.cancel() }
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
                    val resolver = getApplication<Application>().contentResolver
                    requireNotNull(resolver.openOutputStream(uri, "wt")).use { target ->
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
                    try { DocumentsContract.deleteDocument(getApplication<Application>().contentResolver, uri) }
                    catch (_: Exception) { false }
                }
                _state.value = _state.value.copy(busy = false, message = "Simpan gagal. Coba lokasi lain." +
                    if (removed) "" else " File parsial mungkin tertinggal; hapus dari lokasi yang dipilih.")
                if (error is CancellationException) throw error
            }
        }
    }
}

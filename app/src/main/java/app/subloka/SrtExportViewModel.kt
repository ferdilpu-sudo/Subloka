package app.subloka

import android.app.Application
import android.net.Uri
import android.provider.DocumentsContract
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.subloka.core.domain.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Owns one prepared snapshot across picker/rotation; never persists a false export success. */
class SrtExportViewModel(application: Application) : AndroidViewModel(application) {
    data class State(val documents: List<SrtDocument> = emptyList(), val busy: Boolean = false,
        val pending: Int? = null, val saved: Set<Int> = emptySet(), val message: String? = null)
    private val _state = MutableStateFlow(State())
    val state = _state.asStateFlow()
    fun reset() { if (!_state.value.busy && _state.value.pending == null) _state.value = State() }
    fun prepare(title: String, language: SourceLanguage, durationUs: Long,
        segments: List<CaptionSegment>, mode: SrtExportMode) {
        if (_state.value.busy || _state.value.pending != null) return
        val snapshot = segments.toList()
        _state.value = State(busy = true)
        viewModelScope.launch {
            try {
                val files = withContext(Dispatchers.Default) {
                    SrtExport.documents(title, language, durationUs, snapshot, mode)
                }
                _state.value = State(documents = files, message = "SRT siap. Simpan setiap file di bawah.")
            } catch (cancel: CancellationException) { throw cancel }
            catch (error: Exception) { _state.value = State(message = UiFailureMessage.describe(error, "SRT gagal disiapkan. Periksa teks, waktu caption, dan status terjemahan, lalu coba lagi.")) }
        }
    }
    fun select(index: Int): String? {
        val current = _state.value
        if (current.busy || current.pending != null) return null
        val document = current.documents.getOrNull(index) ?: return null
        _state.value = current.copy(pending = index, message = null)
        return document.name
    }
    fun pickerFailed() { _state.value = _state.value.copy(pending = null, message = "Pemilih lokasi tidak tersedia. Coba lagi.") }
    fun save(uri: Uri?) {
        val current = _state.value
        val index = current.pending
        val document = index?.let { current.documents.getOrNull(it) }
        if (uri == null) {
            _state.value = current.copy(pending = null, message = "Penyimpanan dibatalkan. File lain tetap tersimpan.")
            return
        }
        // A process restart loses the snapshot: never write another project's text to a stale picker result.
        if (document == null) {
            _state.value = current.copy(pending = null, busy = true)
            viewModelScope.launch {
                val removed = withContext(Dispatchers.IO) { removeCreated(uri) }
                _state.value = State(message = "Ekspor terputus. Buka proyek dan siapkan SRT lagi." +
                    if (removed) "" else " Hapus dokumen kosong dari lokasi yang dipilih.")
            }
            return
        }
        val savedIndex = requireNotNull(index)
        _state.value = current.copy(busy = true, pending = null)
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    SrtDocumentWriter.write(document) {
                        getApplication<Application>().contentResolver.openOutputStream(uri, "wt")
                    }
                }
                _state.value = current.copy(busy = false, pending = null, saved = current.saved + savedIndex,
                    message = "${document.name} tersimpan (${(current.saved + savedIndex).size}/${current.documents.size} file).")
            } catch (error: Exception) {
                val removed = withContext(NonCancellable + Dispatchers.IO) { removeCreated(uri) }
                _state.value = current.copy(busy = false, pending = null,
                    message = "File gagal disimpan. Pilih lokasi lain dan coba lagi." +
                        if (removed) "" else " File parsial mungkin tertinggal; hapus dari lokasi yang dipilih.")
                if (error is CancellationException) throw error
            }
        }
    }
    private fun removeCreated(uri: Uri): Boolean = try {
        DocumentsContract.deleteDocument(getApplication<Application>().contentResolver, uri)
    } catch (_: Exception) { false }
}

package app.subloka

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.subloka.core.database.SubLokaDatabaseFactory
import app.subloka.core.domain.*
import app.subloka.core.media.AndroidMediaSource
import app.subloka.demo.DemoData
import app.subloka.engine.asr.WhisperModelCatalog
import app.subloka.engine.asr.WhisperModelStore
import app.subloka.engine.asr.WhisperTranscriptionPipeline
import java.io.File
import java.util.UUID
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

enum class PersistenceSaveState { LOADING, SAVING, SAVED, FAILED }
data class AsrUiState(val busy: Boolean = false, val modelReady: Boolean = false,
    val stage: String = "", val error: String? = null, val completed: Boolean = false)

class SubLokaViewModel(application: Application) : AndroidViewModel(application) {
    private val persistence = SubLokaDatabaseFactory.create(application)
    private val projectsRepo = persistence.projectRepository
    private val captionsRepo = persistence.captionRepository
    private val media = AndroidMediaSource(application)
    private val models = WhisperModelStore(File(application.filesDir, "whisper-models"))
    private val queue = Channel<suspend () -> Unit>(Channel.UNLIMITED)
    private var writeFailed = false
    private var operation: Job? = null
    private var pipeline: WhisperTranscriptionPipeline? = null
    private val _segments = MutableStateFlow<List<CaptionSegment>>(emptyList())
    val segments = _segments.asStateFlow()
    private val _style = MutableStateFlow(CaptionStyle())
    val style = _style.asStateFlow()
    private val _saveState = MutableStateFlow(PersistenceSaveState.LOADING)
    val saveState = _saveState.asStateFlow()
    private val _project = MutableStateFlow<CaptionProject?>(null)
    val project = _project.asStateFlow()
    private val _projects = MutableStateFlow<List<CaptionProject>>(emptyList())
    val projects = _projects.asStateFlow()
    private val _asr = MutableStateFlow(AsrUiState())
    val asr = _asr.asStateFlow()

    init {
        viewModelScope.launch {
            try {
                try {
                    if (projectsRepo.list().isEmpty()) {
                        projectsRepo.upsert(DemoData.persistentProject)
                        captionsRepo.replaceAll(DemoData.PROJECT_ID, DemoData.segments)
                    }
                    refreshProjects()
                    _saveState.value = PersistenceSaveState.SAVED
                } catch (error: Exception) {
                    if (error is CancellationException) throw error
                    writeFailed = true; _saveState.value = PersistenceSaveState.FAILED
                }
                for (action in queue) {
                    try { action() }
                    catch (cancel: CancellationException) { currentCoroutineContext().ensureActive() }
                    catch (_: Exception) { writeFailed = true; _saveState.value = PersistenceSaveState.FAILED }
                }
            } finally { persistence.close() }
        }
        viewModelScope.launch {
            val ready = models.state(WhisperModelCatalog.base) == ModelReadinessState.READY
            if (!_asr.value.busy) _asr.value = _asr.value.copy(modelReady = ready)
        }
    }
    private suspend fun refreshProjects() { _projects.value = projectsRepo.list() }
    private suspend fun load(id: String) {
        _project.value = requireNotNull(projectsRepo.find(id))
        _segments.value = captionsRepo.list(id)
        _style.value = projectsRepo.getStyle(id)
    }
    fun openProject(id: String, onComplete: () -> Unit) {
        if (_asr.value.busy) return
        queue.trySend { load(id); _asr.value = _asr.value.copy(error = null, completed = false); onComplete() }
    }
    fun persistMediaSelection(media: MediaDescriptor, sourceLanguage: SourceLanguage, onComplete: (Boolean) -> Unit) {
        if (_asr.value.busy) return
        _saveState.value = PersistenceSaveState.SAVING
        queue.trySend {
            try {
                val now = System.currentTimeMillis()
                val id = UUID.randomUUID().toString()
                projectsRepo.upsert(CaptionProject(id, media.displayName.substringBeforeLast('.').ifBlank { "Video" },
                    media.uri, media.displayName, media.sizeBytes, media.fingerprintSha256, media.durationUs,
                    media.widthPx, media.heightPx, media.rotationDegrees, sourceLanguage, sourceLanguage.target, 0, now, now))
                projectsRepo.saveStyle(id, CaptionStyle(displayMode = CaptionDisplayMode.ORIGINAL))
                load(id); refreshProjects(); _saveState.value = PersistenceSaveState.SAVED
                _asr.value = _asr.value.copy(error = null, completed = false)
                onComplete(true)
            } catch (error: Exception) {
                if (error is CancellationException) throw error
                _saveState.value = PersistenceSaveState.FAILED; onComplete(false)
            }
        }
    }
    fun persistSegments(segments: List<CaptionSegment>) {
        val id = _project.value?.id ?: return
        _saveState.value = PersistenceSaveState.SAVING
        queue.trySend {
            captionsRepo.restoreSnapshot(id, segments)
            if (_project.value?.id == id) { _segments.value = segments; _project.value = projectsRepo.find(id) }
            refreshProjects(); _saveState.value = PersistenceSaveState.SAVED
        }
    }
    fun persistStyle(style: CaptionStyle) {
        val id = _project.value?.id ?: return
        _saveState.value = PersistenceSaveState.SAVING
        queue.trySend {
            projectsRepo.saveStyle(id, style)
            if (_project.value?.id == id) { _style.value = style; _project.value = projectsRepo.find(id) }
            _saveState.value = PersistenceSaveState.SAVED
        }
    }
    fun flush(onComplete: (Boolean) -> Unit) {
        queue.trySend { val success = !writeFailed; writeFailed = false; onComplete(success) }
    }
    fun prepareModel(uri: Uri? = null) {
        if (_asr.value.busy) return
        _asr.value = _asr.value.copy(busy = true, stage = "Menyiapkan dan memverifikasi model…", error = null)
        operation = viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    if (uri == null) models.download(WhisperModelCatalog.base)
                    else getApplication<Application>().contentResolver.openInputStream(uri).use { input ->
                        requireNotNull(input) { "Model tidak dapat dibaca." }
                        models.installFrom(WhisperModelCatalog.base, input)
                    }
                }
                _asr.value = _asr.value.copy(busy = false, modelReady = true, stage = "Model siap digunakan offline.")
            } catch (cancel: CancellationException) {
                _asr.value = _asr.value.copy(busy = false, stage = "Penyiapan model dibatalkan.")
            } catch (_: Exception) {
                _asr.value = _asr.value.copy(busy = false, error = "Model gagal disiapkan. Pilih ggml-base.bin yang benar atau coba unduh lagi.")
            }
        }
    }
    fun startTranscription() {
        val snapshot = _project.value ?: return
        if (_asr.value.busy || !_asr.value.modelReady || _segments.value.isNotEmpty()) return
        _asr.value = _asr.value.copy(busy = true, error = null, completed = false, stage = "Memeriksa video…")
        operation = viewModelScope.launch {
            try {
                check(models.state(WhisperModelCatalog.base) == ModelReadinessState.READY) { "Model tidak tersedia. Siapkan kembali model." }
                val descriptor = media.inspect(snapshot.sourceUri)
                check(descriptor.fingerprintSha256 == snapshot.sourceFingerprint) { "Video berubah. Buat proyek baru dari video ini." }
                val worker = WhisperTranscriptionPipeline(media, File(getApplication<Application>().cacheDir, "asr"))
                pipeline = worker
                val result = worker.transcribe(descriptor, snapshot.sourceLanguage, models.targetFile(WhisperModelCatalog.base)) { stage ->
                    _asr.value = _asr.value.copy(stage = stage)
                }
                val jobContext = currentCoroutineContext()
                jobContext.ensureActive()
                _asr.value = _asr.value.copy(stage = "Menyimpan caption…")
                val completion = CompletableDeferred<Boolean>()
                queue.send {
                    try {
                        withContext(jobContext) {
                            val published = captionsRepo.publishGenerated(snapshot.id, snapshot.contentRevision, result)
                            if (published) { load(snapshot.id); refreshProjects(); _saveState.value = PersistenceSaveState.SAVED }
                            completion.complete(published)
                        }
                    } catch (error: Exception) { completion.completeExceptionally(error) }
                }
                check(completion.await()) { "Proyek berubah. Hasil tidak mengganti caption yang sudah ada." }
                _asr.value = _asr.value.copy(busy = false, completed = true,
                    stage = if (result.isEmpty()) "Tidak ada ucapan yang terdeteksi." else "Caption tersimpan. Periksa teks dan waktunya.")
            } catch (cancel: CancellationException) {
                _asr.value = _asr.value.copy(busy = false, stage = "Transkripsi dihentikan. Buka proyek untuk memeriksa hasil yang sudah tersimpan.")
            } catch (error: Exception) {
                _asr.value = _asr.value.copy(busy = false, error = error.message ?: "Transkripsi gagal. Coba lagi.")
            } catch (_: LinkageError) {
                _asr.value = _asr.value.copy(busy = false, error = "Engine tidak tersedia untuk perangkat ini.")
            } finally { pipeline = null }
        }
    }
    fun cancelOperation() { pipeline?.cancel(); operation?.cancel() }
    override fun onCleared() { cancelOperation(); queue.close(); super.onCleared() }
}

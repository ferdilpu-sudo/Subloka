package app.subloka

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.subloka.core.database.SubLokaDatabaseFactory
import app.subloka.core.domain.*
import app.subloka.demo.DemoData
import app.subloka.engine.translation.TranslateGemmaOfflineTranslator
import app.subloka.engine.translation.TranslateGemmaModel
import app.subloka.engine.translation.MlKitOfflineTranslator
import app.subloka.engine.translation.CaptionTranslationPipeline
import app.subloka.engine.asr.WhisperModelCatalog
import app.subloka.engine.asr.WhisperModelStore
import java.io.File
import java.util.UUID
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

data class SourceRelinkState(val busy: Boolean = false, val unavailable: Boolean = false,
    val message: String? = null, val epoch: Int = 0)

enum class PersistenceSaveState { LOADING, SAVING, SAVED, FAILED }
data class AsrUiState(val busy: Boolean = false, val modelReady: Boolean = false, val useTurbo: Boolean = true,
    val stage: String = "", val error: String? = null, val completed: Boolean = false, val serviceJobId: String? = null)

data class TranslationUiState(val useGemma: Boolean = true, val termsAccepted: Boolean = false, val ready: Boolean = false, val stage: String = "",
    val pendingId: String? = null, val pendingCount: Int = 0, val serviceJobId: String? = null,
    val error: String? = null, val applied: Int = 0, val completed: Boolean = false)

class SubLokaViewModel(application: Application) : AndroidViewModel(application) {
    private val persistence = SubLokaDatabaseFactory.create(application)
    private val projectsRepo = persistence.projectRepository
    private val captionsRepo = persistence.captionRepository
    private val recovery = persistence.translationRecovery
    private val models = WhisperModelStore(File(application.filesDir, "whisper-models"))
    private val queue = Channel<suspend () -> Unit>(Channel.UNLIMITED)
    private var writeFailed = false
    private var operation: Job? = null
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
    private val _asr = MutableStateFlow(AsrUiState(busy = AsrSession.state.value?.running == true || TranslationSession.state.value?.running == true || RenderSession.state.value?.running == true))
    val asr = _asr.asStateFlow()
    private val translationPrefs = application.getSharedPreferences("translation-model", 0)
    private val termsKey = "gemma-terms-${TranslateGemmaModel.TERMS_VERSION}"
    @Volatile private var gemmaTranslator: TranslateGemmaOfflineTranslator? = null
    private val _translation = MutableStateFlow(TranslationUiState(termsAccepted = translationPrefs.getBoolean(termsKey, false)))
    val translation = _translation.asStateFlow()
    private var readinessGeneration = 0L
    private var cleared = false
    private val _sourceRelink = MutableStateFlow(SourceRelinkState())
    val sourceRelink = _sourceRelink.asStateFlow()
    private var sourceCheckGeneration = 0L

    fun checkSource() {
        val project = _project.value ?: return
        if (_sourceRelink.value.busy || project.sourceUri.startsWith("demo://")) return
        val generation = ++sourceCheckGeneration
        viewModelScope.launch {
            val readable = withContext(Dispatchers.IO) {
                try {
                    getApplication<Application>().contentResolver.openAssetFileDescriptor(Uri.parse(project.sourceUri), "r")
                        ?.use { true } ?: false
                } catch (_: Exception) { false }
            }
            if (generation == sourceCheckGeneration && _project.value?.id == project.id &&
                _project.value?.sourceUri == project.sourceUri && !_sourceRelink.value.busy) {
                _sourceRelink.value = _sourceRelink.value.copy(unavailable = !readable)
            }
        }
    }

    fun sourcePlaybackFailed() {
        _sourceRelink.value = _sourceRelink.value.copy(unavailable = true)
    }

    fun relinkPickerFailed() {
        _sourceRelink.value = _sourceRelink.value.copy(message = "Pemilih video tidak dapat dibuka. Coba lagi.")
    }

    fun relinkSource(expectedProjectId: String, uri: Uri, onComplete: () -> Unit) {
        val original = _project.value?.takeIf { it.id == expectedProjectId } ?: return
        if (_asr.value.busy || _sourceRelink.value.busy) return
        ++sourceCheckGeneration
        _sourceRelink.value = _sourceRelink.value.copy(busy = true, message = "Memeriksa video asli…")
        queue.trySend {
            try {
                check(_project.value?.id == original.id && !_asr.value.busy) { "Proyek berubah. Buka kembali proyek yang ingin ditautkan." }
                check(original.sourceFingerprint?.matches(Regex("[0-9a-fA-F]{64}")) == true) {
                    "Identitas video lama tidak tersedia. Penautan ulang aman tidak dapat dilakukan."
                }
                val candidate = app.subloka.core.media.AndroidMediaSource(getApplication()).inspect(uri.toString())
                currentCoroutineContext().ensureActive()
                check(original.sourceFingerprint.equals(candidate.fingerprintSha256, ignoreCase = true) &&
                    original.durationUs == candidate.durationUs && original.widthPx == candidate.widthPx &&
                    original.heightPx == candidate.heightPx && original.rotationDegrees == candidate.rotationDegrees &&
                    (original.sourceSizeBytes == null || candidate.sizeBytes == null || original.sourceSizeBytes == candidate.sizeBytes)) {
                    "Video berbeda dari sumber asli. Pilih file asli yang sama; caption tidak diubah."
                }
                check(app.subloka.core.media.MediaDocumentAccess(getApplication()).persistReadPermission(uri)) {
                    "Izin video tidak dapat disimpan. Pilih file dari penyimpanan perangkat."
                }
                val updated = projectsRepo.relinkSource(original.id, original.sourceUri, original.sourceFingerprint, candidate)
                check(updated != null) { "Sumber proyek berubah. Coba tautkan ulang kembali." }
                _project.value = updated
                refreshProjects()
                _sourceRelink.value = SourceRelinkState(message = "Video berhasil ditautkan ulang.",
                    epoch = _sourceRelink.value.epoch + 1)
                onComplete()
            } catch (error: CancellationException) { throw error }
            catch (error: Exception) {
                _sourceRelink.value = _sourceRelink.value.copy(busy = false,
                    message = UiFailureMessage.describe(error, "Video tidak dapat ditautkan. Pilih file asli yang sama. Caption tetap tersimpan."))
            } finally {
                _sourceRelink.value = _sourceRelink.value.copy(busy = false)
            }
        }
    }


    init {
        viewModelScope.launch {
            try {
                try {
                    if (TranslationSession.state.value?.running != true) recovery.recoverInterrupted()
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
            AsrSession.state.collect { state ->
                if (state != null && RenderSession.state.value?.running != true && TranslationSession.state.value?.running != true) queue.trySend {
                    if (state.running || _project.value?.id == state.request.project.id || _project.value == null) {
                        if (_project.value?.id != state.request.project.id || !state.running) load(state.request.project.id)
                        _asr.value = _asr.value.copy(busy = state.running, useTurbo = state.request.useTurbo,
                            stage = state.stage, error = state.error, completed = state.completed, serviceJobId = state.request.id)
                        if (!state.running) { refreshProjects(); refreshCaptionReadiness() }
                    }
                }
            }
        }
        viewModelScope.launch {
            TranslationSession.state.collect { state ->
                if (state != null && RenderSession.state.value?.running != true && AsrSession.state.value?.running != true) queue.trySend {
                    if (state.running || _project.value?.id == state.request.project.id || _project.value == null) {
                        if (_project.value?.id != state.request.project.id || !state.running) load(state.request.project.id)
                        _translation.value = _translation.value.copy(useGemma = state.request.useGemma,
                            stage = state.stage, error = state.error, completed = state.completed,
                            serviceJobId = state.request.id)
                        _asr.value = _asr.value.copy(busy = state.running)
                        if (!state.running) refreshProjects()
                    }
                }
            }
        }
        viewModelScope.launch {
            RenderSession.state.collect { state ->
                if (state != null && AsrSession.state.value?.running != true && TranslationSession.state.value?.running != true) queue.trySend {
                    if (_project.value?.id != state.request.project.id) load(state.request.project.id)
                    _asr.value = _asr.value.copy(busy = state.running)
                }
            }
        }
        refreshCaptionReadiness()
    }
    private suspend fun refreshProjects() { _projects.value = projectsRepo.list() }
    private suspend fun load(id: String) {
        val previous = _project.value
        _project.value = requireNotNull(projectsRepo.find(id))
        if (previous?.id != id) _sourceRelink.value = SourceRelinkState()
        checkSource()
        _segments.value = captionsRepo.list(id)
        _style.value = projectsRepo.getStyle(id)
        val checkpoint = recovery.pending(id)
        val useGemma = checkpoint?.engine?.startsWith("gemma:") ?: true
        _translation.value = _translation.value.copy(pendingId = checkpoint?.id,
            pendingCount = checkpoint?.pending?.size ?: 0, useGemma = useGemma,
            ready = _translation.value.ready && useGemma == _translation.value.useGemma)
    }
    fun openProject(id: String, onComplete: () -> Unit) {
        if (_asr.value.busy) return
        queue.trySend { load(id); _asr.value = _asr.value.copy(error = null, completed = false); onComplete() }
    }
    fun persistMediaSelection(media: MediaDescriptor, sourceLanguage: SourceLanguage, onComplete: (Boolean) -> Unit) {
        if (_asr.value.busy || _saveState.value == PersistenceSaveState.SAVING) return
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
        if (_asr.value.busy) return
        val id = _project.value?.id ?: return
        _saveState.value = PersistenceSaveState.SAVING
        queue.trySend {
            captionsRepo.restoreSnapshot(id, segments)
            if (_project.value?.id == id) { _segments.value = segments; _project.value = projectsRepo.find(id) }
            refreshProjects(); _saveState.value = if (writeFailed) PersistenceSaveState.FAILED else PersistenceSaveState.SAVED
        }
    }
    fun persistStyle(style: CaptionStyle) {
        if (_asr.value.busy) return
        val id = _project.value?.id ?: return
        _saveState.value = PersistenceSaveState.SAVING
        queue.trySend {
            projectsRepo.saveStyle(id, style)
            if (_project.value?.id == id) { _style.value = style; _project.value = projectsRepo.find(id) }
            _saveState.value = if (writeFailed) PersistenceSaveState.FAILED else PersistenceSaveState.SAVED
        }
    }
    fun retryEditorSave(segments: List<CaptionSegment>, style: CaptionStyle) {
        if (_asr.value.busy) return
        val id = _project.value?.id ?: return
        val snapshot = segments.toList()
        _saveState.value = PersistenceSaveState.SAVING
        queue.trySend {
            captionsRepo.restoreSnapshot(id, snapshot)
            projectsRepo.saveStyle(id, style)
            if (_project.value?.id == id) {
                _segments.value = snapshot
                _style.value = style
                _project.value = projectsRepo.find(id)
            }
            refreshProjects()
            // A navigation request must never clear a failed write. Only a full
            // successful editor retry acknowledges the failed snapshot.
            writeFailed = false
            _saveState.value = PersistenceSaveState.SAVED
        }
    }
    fun flush(onComplete: (Boolean) -> Unit) {
        queue.trySend { onComplete(!writeFailed) }
    }
    private fun refreshCaptionReadiness() {
        val generation = ++readinessGeneration
        val selected = _asr.value.useTurbo
        viewModelScope.launch {
            val ready = captionModelsReady(selected)
            if (generation == readinessGeneration && !_asr.value.busy) {
                _asr.value = _asr.value.copy(modelReady = ready)
            }
        }
    }

    fun selectCaptionModel(useTurbo: Boolean) {
        if (_asr.value.busy || _asr.value.useTurbo == useTurbo) return
        _asr.value = _asr.value.copy(useTurbo = useTurbo, modelReady = false, stage = "", error = null)
        refreshCaptionReadiness()
    }

    private suspend fun captionModelsReady(useTurbo: Boolean): Boolean =
        WhisperModelCatalog.captionModels(useTurbo).all { models.state(it) == ModelReadinessState.READY }

    fun prepareModel(uri: Uri? = null, importVad: Boolean = false) {
        if (_asr.value.busy) return
        val selected = _asr.value.useTurbo
        ++readinessGeneration
        _asr.value = _asr.value.copy(busy = true, stage = "Menyiapkan dan memverifikasi model…", error = null)
        operation = viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    if (uri == null) {
                        // Explicit download action only; do not download again when a model is ready.
                        WhisperModelCatalog.captionModels(selected).forEach { model ->
                            if (models.state(model) != ModelReadinessState.READY) models.download(model)
                        }
                    } else getApplication<Application>().contentResolver.openInputStream(uri).use { input ->
                        requireNotNull(input) { "Model tidak dapat dibaca." }
                        models.installFrom(if (importVad) WhisperModelCatalog.vad else WhisperModelCatalog.captionModel(selected), input)
                    }
                }
                val ready = captionModelsReady(selected)
                _asr.value = _asr.value.copy(busy = false, modelReady = ready,
                    stage = if (ready) "Model caption dan pendeteksi ucapan siap offline."
                    else "Masih ada model yang belum siap. Impor model lainnya atau pilih Unduh model yang belum tersedia.")
            } catch (cancel: CancellationException) {
                _asr.value = _asr.value.copy(busy = false, stage = "Penyiapan model dibatalkan.")
            } catch (_: Exception) {
                _asr.value = _asr.value.copy(busy = false, error = "Model gagal disiapkan. Pastikan file sesuai pilihan model (Turbo/Base atau pendeteksi ucapan), lalu coba lagi.")
            }
        }
    }
    fun startTranscription() {
        val snapshot = _project.value ?: return
        if (_asr.value.busy || !_asr.value.modelReady || _segments.value.isNotEmpty()) return
        val request = AsrSession.reserve(snapshot, _asr.value.useTurbo) ?: return
        ++readinessGeneration
        _asr.value = _asr.value.copy(busy = true, error = null, completed = false,
            serviceJobId = request.id, stage = "Memulai layanan transkripsi…")
        AsrForegroundService.start(getApplication(), request)
    }
    fun selectTranslationModel(useGemma: Boolean) {
        if (!useGemma) return
        if (_asr.value.busy || _translation.value.pendingId != null) return
        _translation.value = _translation.value.copy(useGemma = useGemma, ready = false)
        checkTranslationModel()
    }
    fun acceptGemmaTerms(accepted: Boolean) {
        if (_asr.value.busy) return
        translationPrefs.edit().putBoolean(termsKey, accepted).apply()
        _translation.value = _translation.value.copy(termsAccepted = accepted, ready = false)
        if (accepted) checkTranslationModel()
    }
    fun importTranslationModel(uri: Uri) = translationOperation("Memverifikasi model…") { translator ->
        check(translator is TranslateGemmaOfflineTranslator)
        getApplication<Application>().contentResolver.openInputStream(uri).use { input ->
            translator.importModel(requireNotNull(input))
        }
        _translation.value = _translation.value.copy(ready = true, stage = "Model siap offline.")
    }
    /** Called only after the editor write barrier, from the dedicated translation flow. */
    fun checkTranslationModel() = translationOperation("Memeriksa model terjemahan…") { translator ->
        val ready = (!_translation.value.useGemma || _translation.value.termsAccepted) && translator.state() == ModelReadinessState.READY
        _translation.value = _translation.value.copy(ready = ready,
            stage = if (ready) "Model terjemahan siap offline." else "Model terjemahan belum siap. Unduh terlebih dahulu.")
    }

    fun prepareTranslationModel(requireWifi: Boolean) = translationOperation("Menyiapkan model terjemahan…") { translator ->
        translator.ensureReady(requireWifi)
        _translation.value = _translation.value.copy(ready = true, stage = "Model siap. Anda dapat mematikan koneksi sebelum menerjemahkan.")
    }

    private fun translationEngineKey() = if (_translation.value.useGemma)
        "gemma:${TranslateGemmaModel.descriptor.expectedSha256}:llama-2a667032:prompt1"
        else "mlkit:17.0.3"

    fun discardTranslationRecovery() {
        if (_asr.value.busy) return
        val id = _project.value?.id ?: return
        translationOperation("Menghapus antrean tertunda…") {
            recovery.discard(id)
            _translation.value = _translation.value.copy(stage = "Antrean dihapus. Hasil caption tetap tersimpan.")
        }
    }

    fun resumeTranslation() = startTranslation(resume = true)

    fun startTranslation(segmentId: String? = null, replaceCurrentMachine: Boolean = false, resume: Boolean = false) {
        val selectedProject = _project.value ?: return
        if (!_translation.value.ready || selectedProject.id == DemoData.PROJECT_ID) return
        if (_asr.value.busy || resume != (_translation.value.pendingId != null)) return
        val request = TranslationSession.reserve(selectedProject, _translation.value, translationEngineKey(),
            segmentId, replaceCurrentMachine, resume) ?: return
        _asr.value = _asr.value.copy(busy = true)
        _translation.value = _translation.value.copy(serviceJobId = request.id, completed = false,
            error = null, stage = "Memulai layanan terjemahan…")
        TranslationForegroundService.start(getApplication(), request)
    }

    private fun translationOperation(stage: String, action: suspend (OfflineTranslator) -> Unit) {
        if (_asr.value.busy) return
        _asr.value = _asr.value.copy(busy = true)
        _translation.value = _translation.value.copy(stage = stage, error = null, completed = false, applied = 0)
        val selection = _translation.value
        operation = viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    val translator = if (selection.useGemma) TranslateGemmaOfflineTranslator(getApplication(), selection.termsAccepted) {
                        _translation.value = _translation.value.copy(stage = it)
                    }.also { gemmaTranslator = it } else MlKitOfflineTranslator()
                    try { translator.use { action(it) } } finally { gemmaTranslator = null }
                }
            } catch (cancel: CancellationException) {
                _translation.value = _translation.value.copy(stage = "Dihentikan. Buka Terjemahan dan pilih Lanjutkan sisa terjemahan. Hasil yang sudah tersimpan tetap tersedia.")
            } catch (_: Exception) {
                _translation.value = _translation.value.copy(error = "Proses terjemahan gagal. Periksa model dan coba lagi; hasil yang sudah tersimpan tetap tersedia.")
            } catch (_: LinkageError) {
                _translation.value = _translation.value.copy(error = "Terjemahan belum didukung pada perangkat ini. Gunakan perangkat lain.")
            } finally {
                // Keep the editor locked until its next snapshot includes completed publications.
                withContext(NonCancellable) {
                    if (!cleared) {
                        try { _project.value?.id?.let { load(it) }; refreshProjects() }
                        catch (_: Exception) {
                            _translation.value = _translation.value.copy(error = "Hasil belum dapat dimuat. Kembali dan buka proyek lagi.")
                        }
                    }
                }
                _asr.value = _asr.value.copy(busy = false)
            }
        }
    }

    fun cancelOperation() {
        AsrForegroundService.cancel(getApplication())
        TranslationForegroundService.cancel(getApplication())
        cancelForegroundOnlyOperation()
    }
    fun cancelForegroundOnlyOperation() { gemmaTranslator?.cancel(); operation?.cancel() }
    override fun onCleared() {
        cleared = true
        cancelForegroundOnlyOperation()
        queue.close()
        super.onCleared()
    }
}

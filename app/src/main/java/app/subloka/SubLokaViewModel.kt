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

enum class PersistenceSaveState { LOADING, SAVING, SAVED, FAILED }
data class AsrUiState(val busy: Boolean = false, val modelReady: Boolean = false, val useTurbo: Boolean = true,
    val stage: String = "", val error: String? = null, val completed: Boolean = false, val serviceJobId: String? = null)

data class TranslationUiState(val useGemma: Boolean = true, val termsAccepted: Boolean = false, val ready: Boolean = false, val stage: String = "",
    val pendingId: String? = null, val pendingCount: Int = 0,
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
    private val _asr = MutableStateFlow(AsrUiState(busy = AsrSession.state.value?.running == true))
    val asr = _asr.asStateFlow()
    private val translationPrefs = application.getSharedPreferences("translation-model", 0)
    private val termsKey = "gemma-terms-${TranslateGemmaModel.TERMS_VERSION}"
    @Volatile private var gemmaTranslator: TranslateGemmaOfflineTranslator? = null
    private val _translation = MutableStateFlow(TranslationUiState(termsAccepted = translationPrefs.getBoolean(termsKey, false)))
    val translation = _translation.asStateFlow()
    private var readinessGeneration = 0L
    private var cleared = false

    init {
        viewModelScope.launch {
            try {
                try {
                    recovery.recoverInterrupted()
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
            AsrSession.state.collect { state ->
                if (state != null) queue.trySend {
                    if (state.running || _project.value?.id == state.request.project.id || _project.value == null) {
                        if (_project.value?.id != state.request.project.id || !state.running) load(state.request.project.id)
                        _asr.value = _asr.value.copy(busy = state.running, useTurbo = state.request.useTurbo,
                            stage = state.stage, error = state.error, completed = state.completed, serviceJobId = state.request.id)
                        if (!state.running) { refreshProjects(); refreshCaptionReadiness() }
                    }
                }
            }
        }
        refreshCaptionReadiness()
    }
    private suspend fun refreshProjects() { _projects.value = projectsRepo.list() }
    private suspend fun load(id: String) {
        _project.value = requireNotNull(projectsRepo.find(id))
        _segments.value = captionsRepo.list(id)
        _style.value = projectsRepo.getStyle(id)
        val checkpoint = recovery.pending(id)
        val useGemma = checkpoint?.engine?.startsWith("gemma:") ?: _translation.value.useGemma
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
            refreshProjects(); _saveState.value = PersistenceSaveState.SAVED
        }
    }
    fun persistStyle(style: CaptionStyle) {
        if (_asr.value.busy) return
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
        val pendingCount = _translation.value.pendingCount
        val pendingId = _translation.value.pendingId
        if (resume != (pendingId != null)) return
        val engine = translationEngineKey()
        translationOperation("Menyiapkan caption…") { translator ->
            check(translator.state() == ModelReadinessState.READY)
            // Read after editor save barrier. Resume keeps only original IDs at unchanged source revisions.
            val snapshot = captionsRepo.list(selectedProject.id).filter {
                resume || ((segmentId == null || it.id == segmentId) && TranslationEligibility.canGenerate(it, replaceCurrentMachine))
            }
            val checkpoint = recovery.begin(selectedProject.id, engine, snapshot, if (resume) pendingId else null)
            val work = snapshot.filter { checkpoint.pending[it.id] == it.sourceRevision }
            try {
                val result = CaptionTranslationPipeline(translator).run(work, publish = { source, text ->
                    recovery.publish(checkpoint.id, source, text)
                }, onProgress = { progress ->
                    _translation.value = _translation.value.copy(applied = progress.applied,
                        stage = "Menerjemahkan ${progress.processed}/${progress.total} • ${progress.applied} tersimpan")
                }, replaceCurrentMachine = true)
                recovery.stop(checkpoint.id, interrupted = false)
                _translation.value = _translation.value.copy(completed = result.failed == 0,
                    stage = "${result.applied} tersimpan • ${result.conflicted + if (resume) (pendingCount - work.size).coerceAtLeast(0) else 0} dilewati karena berubah • ${result.failed} belum selesai.",
                    error = if (result.failed > 0) "Sisa caption dapat dilanjutkan. Untuk teks terlalu panjang, pecah caption lalu buat antrean baru." else null)
            } finally {
                // If process death skips this block, startup recovers the persisted RUNNING row.
                withContext(NonCancellable) { recovery.stop(checkpoint.id, interrupted = true) }
            }
        }
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
                _translation.value = _translation.value.copy(error = "Engine terjemahan tidak tersedia untuk perangkat ini.")
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

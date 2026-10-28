package app.subloka

import app.subloka.core.domain.CaptionProject
import java.util.UUID
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal data class TranslationRequest(val id: String, val project: CaptionProject, val useGemma: Boolean, val termsAccepted: Boolean, val engine: String,
    val segmentId: String?, val replaceCurrentMachine: Boolean, val pendingId: String?, val pendingCount: Int)
internal data class TranslationSessionState(val request: TranslationRequest, val running: Boolean = true,
    val stage: String = "Memulai terjemahan…", val completed: Boolean = false, val error: String? = null, val stopping: Boolean = false)

/** Process-local connection between service and recreated UI; never a process-death checkpoint. */
internal object TranslationSession {
    private val mutable = MutableStateFlow<TranslationSessionState?>(null)
    val state = mutable.asStateFlow()
    @Synchronized fun reserve(project: CaptionProject, selection: TranslationUiState, engine: String,
        segmentId: String?, replaceCurrentMachine: Boolean, resume: Boolean): TranslationRequest? {
        if (!selection.useGemma && (!resume || selection.pendingId == null)) return null
        if (RenderSession.state.value?.running == true || mutable.value?.running == true || AsrSession.state.value?.running == true) return null
        return TranslationRequest(UUID.randomUUID().toString(), project, selection.useGemma,
            selection.termsAccepted, engine, segmentId, replaceCurrentMachine,
            if (resume) selection.pendingId else null, selection.pendingCount).also {
            mutable.value = TranslationSessionState(it)
        }
    }
    @Synchronized fun stage(id: String, stage: String) {
        mutable.value?.takeIf { it.request.id == id && it.running && !it.stopping }?.let { mutable.value = it.copy(stage = stage) }
    }
    @Synchronized fun stopping(id: String) {
        mutable.value?.takeIf { it.request.id == id && it.running }?.let {
            mutable.value = it.copy(stopping = true, stage = "Menghentikan terjemahan… Tunggu engine selesai berhenti.")
        }
    }
    @Synchronized fun finish(id: String, stage: String, completed: Boolean, error: String? = null) {
        mutable.value?.takeIf { it.request.id == id && it.running }?.let {
            mutable.value = it.copy(running = false, stage = stage, completed = completed, error = error)
        }
    }
}

package app.subloka

import app.subloka.core.domain.CaptionProject
import java.util.UUID
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal data class AsrRequest(val id: String, val project: CaptionProject, val useTurbo: Boolean)
internal data class AsrSessionState(val request: AsrRequest, val running: Boolean = true,
    val stage: String = "Memulai transkripsi…", val completed: Boolean = false, val error: String? = null, val stopping: Boolean = false)

/** Process-local connection between service and recreated UI; never a process-death checkpoint. */
internal object AsrSession {
    private val mutable = MutableStateFlow<AsrSessionState?>(null)
    val state = mutable.asStateFlow()
    @Synchronized fun reserve(project: CaptionProject, useTurbo: Boolean): AsrRequest? {
        if (mutable.value?.running == true) return null
        return AsrRequest(UUID.randomUUID().toString(), project, useTurbo).also { mutable.value = AsrSessionState(it) }
    }
    @Synchronized fun stage(id: String, stage: String) {
        mutable.value?.takeIf { it.request.id == id && it.running && !it.stopping }?.let { mutable.value = it.copy(stage = stage) }
    }
    @Synchronized fun stopping(id: String) {
        mutable.value?.takeIf { it.request.id == id && it.running }?.let {
            mutable.value = it.copy(stopping = true, stage = "Menghentikan transkripsi… Tunggu engine selesai berhenti.")
        }
    }
    @Synchronized fun finish(id: String, stage: String, completed: Boolean, error: String? = null) {
        mutable.value?.takeIf { it.request.id == id && it.running }?.let {
            mutable.value = it.copy(running = false, stage = stage, completed = completed, error = error)
        }
    }
}

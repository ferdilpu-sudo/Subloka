package app.subloka

import app.subloka.core.domain.*
import java.io.File
import java.util.UUID
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal data class RenderRequest(val id: String, val project: CaptionProject,
    val segments: List<CaptionSegment>, val style: CaptionStyle)
internal data class RenderSessionState(val request: RenderRequest, val running: Boolean = true,
    val stage: String = "Memulai render…", val completed: Boolean = false, val error: String? = null,
    val stopping: Boolean = false, val progress: Int? = null, val output: File? = null)

/** Process-local ownership; partial output is never exposed as ready. */
internal object RenderSession {
    private val mutable = MutableStateFlow<RenderSessionState?>(null)
    val state = mutable.asStateFlow()
    @Synchronized fun reserve(project: CaptionProject, segments: List<CaptionSegment>, style: CaptionStyle): RenderRequest? {
        if (mutable.value?.running == true || AsrSession.state.value?.running == true || TranslationSession.state.value?.running == true) return null
        return RenderRequest(UUID.randomUUID().toString(), project, segments.toList(), style).also {
            mutable.value = RenderSessionState(it)
        }
    }
    @Synchronized fun stage(id: String, stage: String) {
        mutable.value?.takeIf { it.request.id == id && it.running && !it.stopping }?.let { mutable.value = it.copy(stage = stage) }
    }
    @Synchronized fun progress(id: String, progress: Int?) {
        mutable.value?.takeIf { it.request.id == id && it.running && !it.stopping }?.let { mutable.value = it.copy(progress = progress) }
    }
    @Synchronized fun stopping(id: String) {
        mutable.value?.takeIf { it.request.id == id && it.running }?.let {
            mutable.value = it.copy(stopping = true, stage = "Menghentikan render…")
        }
    }
    @Synchronized fun finish(id: String, stage: String, completed: Boolean, error: String? = null, output: File? = null) {
        mutable.value?.takeIf { it.request.id == id && it.running }?.let {
            mutable.value = it.copy(running = false, stage = stage, completed = completed,
                error = error, output = if (completed) output else null)
        }
    }
    @Synchronized fun clear() { if (mutable.value?.running != true) mutable.value = null }
}

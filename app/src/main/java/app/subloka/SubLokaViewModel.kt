package app.subloka

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.subloka.core.database.SubLokaDatabaseFactory
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.CaptionStyle
import app.subloka.demo.DemoData
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class PersistenceSaveState {
    LOADING,
    SAVING,
    SAVED,
    FAILED,
}

class SubLokaViewModel(application: Application) : AndroidViewModel(application) {
    private val persistence = SubLokaDatabaseFactory.create(application)
    private val projectRepository = persistence.projectRepository
    private val captionRepository = persistence.captionRepository

    private val saveQueue = Channel<SaveCommand>(Channel.UNLIMITED)
    private var pendingWrites = 0
    private var saveFailureSinceLastBarrier = false

    private val _segments = MutableStateFlow(DemoData.segments)
    val segments: StateFlow<List<CaptionSegment>> = _segments.asStateFlow()

    private val _style = MutableStateFlow(CaptionStyle())
    val style: StateFlow<CaptionStyle> = _style.asStateFlow()

    private val _saveState = MutableStateFlow(PersistenceSaveState.LOADING)
    val saveState: StateFlow<PersistenceSaveState> = _saveState.asStateFlow()

    init {
        viewModelScope.launch {
            loadOrSeedDemoProject()
            for (command in saveQueue) {
                process(command)
            }
        }
    }

    fun persistSegments(segments: List<CaptionSegment>) {
        pendingWrites += 1
        _saveState.value = PersistenceSaveState.SAVING
        if (saveQueue.trySend(SaveCommand.Segments(segments.toList())).isFailure) {
            pendingWrites -= 1
            saveFailureSinceLastBarrier = true
            _saveState.value = PersistenceSaveState.FAILED
        }
    }

    fun persistStyle(style: CaptionStyle) {
        pendingWrites += 1
        _saveState.value = PersistenceSaveState.SAVING
        if (saveQueue.trySend(SaveCommand.Style(style)).isFailure) {
            pendingWrites -= 1
            saveFailureSinceLastBarrier = true
            _saveState.value = PersistenceSaveState.FAILED
        }
    }

    fun flush(onComplete: (Boolean) -> Unit) {
        viewModelScope.launch {
            val barrier = CompletableDeferred<Boolean>()
            saveQueue.send(SaveCommand.Barrier(barrier))
            onComplete(barrier.await())
        }
    }

    override fun onCleared() {
        saveQueue.close()
        persistence.close()
        super.onCleared()
    }

    private suspend fun loadOrSeedDemoProject() {
        try {
            if (projectRepository.find(DemoData.PROJECT_ID) == null) {
                projectRepository.upsert(DemoData.persistentProject)
                captionRepository.replaceAll(DemoData.PROJECT_ID, DemoData.segments)
            }
            _segments.value = captionRepository.list(DemoData.PROJECT_ID)
            _style.value = projectRepository.getStyle(DemoData.PROJECT_ID)
            _saveState.value = PersistenceSaveState.SAVED
        } catch (_: Throwable) {
            saveFailureSinceLastBarrier = true
            _saveState.value = PersistenceSaveState.FAILED
        }
    }

    private suspend fun process(command: SaveCommand) {
        when (command) {
            is SaveCommand.Segments -> processWrite {
                captionRepository.restoreSnapshot(DemoData.PROJECT_ID, command.value)
                _segments.value = command.value.sortedBy { it.startUs }
            }
            is SaveCommand.Style -> processWrite {
                projectRepository.saveStyle(DemoData.PROJECT_ID, command.value)
                _style.value = command.value
            }
            is SaveCommand.Barrier -> {
                val success = !saveFailureSinceLastBarrier && pendingWrites == 0
                command.result.complete(success)
                saveFailureSinceLastBarrier = false
                if (success) {
                    _saveState.value = PersistenceSaveState.SAVED
                }
            }
        }
    }

    private suspend fun processWrite(block: suspend () -> Unit) {
        try {
            block()
        } catch (_: Throwable) {
            saveFailureSinceLastBarrier = true
            _saveState.value = PersistenceSaveState.FAILED
        } finally {
            pendingWrites = (pendingWrites - 1).coerceAtLeast(0)
            if (!saveFailureSinceLastBarrier) {
                _saveState.value = if (pendingWrites == 0) {
                    PersistenceSaveState.SAVED
                } else {
                    PersistenceSaveState.SAVING
                }
            }
        }
    }

    private sealed interface SaveCommand {
        data class Segments(val value: List<CaptionSegment>) : SaveCommand
        data class Style(val value: CaptionStyle) : SaveCommand
        data class Barrier(val result: CompletableDeferred<Boolean>) : SaveCommand
    }
}

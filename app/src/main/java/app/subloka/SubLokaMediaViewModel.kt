package app.subloka

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.subloka.core.domain.MediaDescriptor
import app.subloka.core.domain.MediaSourceException
import app.subloka.core.media.AndroidMediaSource
import app.subloka.core.media.MediaDocumentAccess
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface MediaSelectionState {
    data object Idle : MediaSelectionState
    data object Loading : MediaSelectionState
    data class Ready(val descriptor: MediaDescriptor) : MediaSelectionState
    data class Error(val message: String) : MediaSelectionState
}

class SubLokaMediaViewModel(application: Application) : AndroidViewModel(application) {
    private val documentAccess = MediaDocumentAccess(application)
    private val mediaSource = AndroidMediaSource(application)

    private val _selection = MutableStateFlow<MediaSelectionState>(MediaSelectionState.Idle)
    val selection: StateFlow<MediaSelectionState> = _selection.asStateFlow()

    fun select(uri: Uri) {
        _selection.value = MediaSelectionState.Loading
        viewModelScope.launch(Dispatchers.IO) {
            try {
                documentAccess.persistReadPermission(uri)
                _selection.value = MediaSelectionState.Ready(mediaSource.inspect(uri.toString()))
            } catch (error: MediaSourceException) {
                _selection.value = MediaSelectionState.Error(error.message ?: "Video tidak dapat digunakan.")
            } catch (_: Throwable) {
                _selection.value = MediaSelectionState.Error("Video tidak dapat digunakan.")
            }
        }
    }

    fun clear() {
        _selection.value = MediaSelectionState.Idle
    }
}

package app.subloka.feature.editor

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.*
import kotlinx.coroutines.delay
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.ui.PlayerView
import app.subloka.core.designsystem.SubLokaColors
import app.subloka.core.domain.CaptionSegment
import app.subloka.core.media.MediaPlaybackController

@Composable
fun VideoPreview(
    segment: CaptionSegment?,
    mediaUri: String?,
    compactHeight: Boolean,
    segments: List<CaptionSegment> = listOfNotNull(segment),
    modifier: Modifier = Modifier,
) {
    val maxHeight = if (compactHeight) 112.dp else 248.dp
    val context = LocalContext.current
    val controller = remember(mediaUri) {
        mediaUri?.let { uri ->
            MediaPlaybackController(context).also { it.load(uri) }
        }
    }

    var positionUs by remember(controller) { mutableLongStateOf(0L) }
    LaunchedEffect(controller, segment?.id) {
        controller?.seekTo((segment?.startUs ?: 0L) / 1000)
    }
    LaunchedEffect(controller) {
        while (controller != null) {
            positionUs = controller.player.currentPosition * 1000
            delay(100)
        }
    }
    val visible = if (controller == null) segment else segments.firstOrNull { positionUs >= it.startUs && positionUs < it.endUs }
    DisposableEffect(controller) {
        onDispose { controller?.close() }
    }

    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = maxHeight)
                .aspectRatio(16f / 9f)
                .background(SubLokaColors.SurfaceHigh),
            contentAlignment = Alignment.Center,
        ) {
            if (controller != null) {
                AndroidView(
                    factory = { viewContext ->
                        PlayerView(viewContext).apply {
                            useController = true
                            player = controller.player
                        }
                    },
                    update = { playerView -> playerView.player = controller.player },
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                Text("VIDEO PREVIEW · PILIH VIDEO", color = SubLokaColors.TextSecondary)
            }

            if (visible != null) {
                Column(
                    modifier = Modifier.align(Alignment.BottomCenter).padding(horizontal = 16.dp, vertical = 14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(visible.sourceText, color = SubLokaColors.TextPrimary, style = MaterialTheme.typography.bodyMedium)
                    Text(visible.translationText, color = SubLokaColors.Warning, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(if (controller == null) "Preview belum tersedia" else "Playback lokal", style = MaterialTheme.typography.bodySmall)
            Text("Media3", color = SubLokaColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
        }
    }
}

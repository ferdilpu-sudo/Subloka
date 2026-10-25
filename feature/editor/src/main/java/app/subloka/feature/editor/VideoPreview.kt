package app.subloka.feature.editor

import androidx.compose.foundation.Canvas
import androidx.compose.ui.graphics.nativeCanvas
import app.subloka.core.domain.CaptionStyle
import app.subloka.core.media.SubtitlePainter
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
    captionStyle: CaptionStyle = CaptionStyle(),
    videoWidth: Int = 16,
    videoHeight: Int = 9,
    segments: List<CaptionSegment> = listOfNotNull(segment),
    onVideoError: () -> Unit = {},
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
    val painter = remember(segments, captionStyle) { SubtitlePainter(segments, captionStyle) }
    val renderError = remember(painter, videoWidth, videoHeight) {
        runCatching { painter.validate(videoWidth, videoHeight) }.exceptionOrNull()?.message
    }
    val latestVideoError by rememberUpdatedState(onVideoError)
    DisposableEffect(controller) {
        val listener = object : androidx.media3.common.Player.Listener {
            override fun onPlayerError(error: androidx.media3.common.PlaybackException) { latestVideoError() }
        }
        controller?.player?.addListener(listener)
        if (controller?.player?.playerError != null) latestVideoError()
        onDispose { controller?.player?.removeListener(listener); controller?.close() }
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
                Text("Pratinjau video belum tersedia", color = SubLokaColors.TextSecondary)
            }

            if (renderError == null) {
                Canvas(Modifier.fillMaxSize()) {
                    val scale = minOf(size.width / videoWidth, size.height / videoHeight)
                    val canvas = drawContext.canvas.nativeCanvas
                    canvas.save()
                    canvas.translate((size.width - videoWidth * scale) / 2, (size.height - videoHeight * scale) / 2)
                    // Render at full oriented resolution, scaled into the player's fit rectangle.
                    canvas.scale(scale, scale)
                    painter.draw(canvas, videoWidth, videoHeight, if (controller == null) segment?.startUs ?: 0 else positionUs)
                    canvas.restore()
                }
            } else Text(renderError, color = SubLokaColors.Warning, modifier = Modifier.align(Alignment.BottomCenter))
        }
    }
}

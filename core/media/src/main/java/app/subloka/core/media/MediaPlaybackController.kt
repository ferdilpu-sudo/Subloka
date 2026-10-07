package app.subloka.core.media

import android.content.Context
import android.net.Uri
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer

class MediaPlaybackController(context: Context) : AutoCloseable {
    private val exoPlayer = ExoPlayer.Builder(context.applicationContext).build()

    val player: Player
        get() = exoPlayer

    fun load(uri: String) {
        exoPlayer.setMediaItem(MediaItem.fromUri(Uri.parse(uri)))
        exoPlayer.prepare()
    }

    fun seekTo(positionMs: Long) {
        exoPlayer.seekTo(positionMs.coerceAtLeast(0L))
    }

    fun play() {
        exoPlayer.play()
    }

    fun pause() {
        exoPlayer.pause()
    }

    override fun close() {
        exoPlayer.release()
    }
}

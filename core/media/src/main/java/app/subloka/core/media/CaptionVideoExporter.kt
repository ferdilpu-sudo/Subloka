package app.subloka.core.media

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.PorterDuff
import android.media.MediaExtractor
import android.media.MediaFormat
import android.net.Uri
import androidx.annotation.OptIn
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.util.UnstableApi
import androidx.media3.effect.CanvasOverlay
import androidx.media3.effect.OverlayEffect
import androidx.media3.effect.Presentation
import androidx.media3.transformer.*
import app.subloka.core.domain.*
import java.io.File
import kotlin.math.abs
import kotlinx.coroutines.*

/** Foreground export. All Transformer calls run on Main; decoding/encoding is internal to Media3. */
@OptIn(UnstableApi::class)
class CaptionVideoExporter(private val context: Context) {
    suspend fun render(project: CaptionProject, segments: List<CaptionSegment>, style: CaptionStyle,
        output: File, onProgress: (Int?) -> Unit = {}) {
        require(!output.exists()) { "Lokasi sementara sudah digunakan." }
        require(project.durationUs <= 600_000_000) { "Prototipe mendukung video hingga 10 menit." }
        require(Uri.parse(project.sourceUri).scheme in setOf("content", "file")) { "Sumber video lokal tidak tersedia." }
        val mode = when (style.displayMode) {
            CaptionDisplayMode.ORIGINAL -> SrtExportMode.SOURCE
            CaptionDisplayMode.TRANSLATION -> SrtExportMode.TRANSLATION
            CaptionDisplayMode.DUAL -> SrtExportMode.BOTH
        }
        // Reuse timing/language/current-translation validation; no file is written here.
        SrtExport.documents(project.title, project.sourceLanguage, project.durationUs, segments, mode)
        var completed = false
        try {
            val size = withContext(Dispatchers.IO) {
                val current = AndroidMediaSource(context).inspect(project.sourceUri)
                check(current.fingerprintSha256 == project.sourceFingerprint) { "Video berubah. Buat proyek baru dari sumber ini." }
                requireSdr(project.sourceUri)
                val rotated = project.rotationDegrees in setOf(90, 270)
                val width = if (rotated) project.heightPx else project.widthPx
                val height = if (rotated) project.widthPx else project.heightPx
                val scale = minOf(1.0, 1280.0 / maxOf(width, height))
                Pair(((width * scale).toInt() / 2 * 2).coerceAtLeast(2),
                    ((height * scale).toInt() / 2 * 2).coerceAtLeast(2)).also {
                    SubtitlePainter(segments, style).validate(it.first, it.second)
                }
            }
            currentCoroutineContext().ensureActive()
            withContext(Dispatchers.Main.immediate) {
                coroutineScope {
                    val finished = CompletableDeferred<Unit>()
                    val painter = SubtitlePainter(segments, style)
                    val overlay = object : CanvasOverlay(true) {
                        override fun onDraw(canvas: Canvas, presentationTimeUs: Long) {
                            canvas.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)
                            painter.draw(canvas, canvas.width, canvas.height, presentationTimeUs)
                        }
                    }
                    val item = EditedMediaItem.Builder(MediaItem.fromUri(project.sourceUri))
                        .setEffects(Effects(emptyList(), listOf(
                            Presentation.createForWidthAndHeight(size.first, size.second, Presentation.LAYOUT_SCALE_TO_FIT),
                            OverlayEffect(listOf(overlay))))).build()
                    val transformer = Transformer.Builder(context)
                        .setVideoMimeType(MimeTypes.VIDEO_H264).setAudioMimeType(MimeTypes.AUDIO_AAC)
                        .setEncoderFactory(DefaultEncoderFactory.Builder(context).setEnableFallback(false).build())
                        .addListener(object : Transformer.Listener {
                            override fun onCompleted(composition: Composition, result: ExportResult) { finished.complete(Unit) }
                            override fun onError(composition: Composition, result: ExportResult, exception: ExportException) {
                                finished.completeExceptionally(IllegalStateException("Render gagal (${exception.errorCode}). Coba video SDR lain atau ekspor SRT.", exception))
                            }
                        }).build()
                    var progressJob: Job? = null
                    try {
                        transformer.start(item, output.absolutePath)
                        progressJob = launch {
                            val progress = ProgressHolder()
                            while (isActive) {
                                onProgress(if (transformer.getProgress(progress) == Transformer.PROGRESS_STATE_AVAILABLE)
                                    progress.progress.coerceIn(0, 99) else null)
                                delay(250)
                            }
                        }
                        finished.await()
                    } finally {
                        progressJob?.cancel()
                        transformer.cancel()
                    }
                }
            }
            withContext(Dispatchers.IO) {
                check(output.length() > 0) { "Hasil video kosong." }
                val rendered = AndroidMediaSource(context).inspect(Uri.fromFile(output).toString())
                val rotated = rendered.rotationDegrees in setOf(90, 270)
                val width = if (rotated) rendered.heightPx else rendered.widthPx
                val height = if (rotated) rendered.widthPx else rendered.heightPx
                check(width == size.first && height == size.second) { "Ukuran hasil tidak sesuai." }
                check(abs(rendered.durationUs - project.durationUs) <= maxOf(250_000L, project.durationUs / 100)) {
                    "Durasi hasil tidak sesuai. File tidak diterbitkan."
                }
                check(rendered.audioTracks.isNotEmpty()) { "Audio hasil tidak tersedia." }
            }
            currentCoroutineContext().ensureActive()
            completed = true
        } finally {
            if (!completed) withContext(NonCancellable + Dispatchers.IO) { output.delete() }
        }
    }
    private fun requireSdr(uri: String) {
        val extractor = MediaExtractor()
        try {
            extractor.setDataSource(context, Uri.parse(uri), null)
            for (index in 0 until extractor.trackCount) {
                val format = extractor.getTrackFormat(index)
                if (format.getString(MediaFormat.KEY_MIME)?.startsWith("video/") != true) continue
                val transfer = if (format.containsKey(MediaFormat.KEY_COLOR_TRANSFER)) format.getInteger(MediaFormat.KEY_COLOR_TRANSFER) else 0
                require(transfer != MediaFormat.COLOR_TRANSFER_ST2084 && transfer != MediaFormat.COLOR_TRANSFER_HLG) {
                    "Video HDR belum didukung. Gunakan video SDR atau ekspor SRT."
                }
            }
        } finally { extractor.release() }
    }
}

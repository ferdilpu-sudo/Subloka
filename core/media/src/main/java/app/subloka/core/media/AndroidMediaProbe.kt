package app.subloka.core.media

import android.content.Context
import android.media.MediaExtractor
import android.media.MediaFormat
import android.net.Uri
import android.provider.OpenableColumns
import app.subloka.core.domain.AudioTrackDescriptor
import app.subloka.core.domain.MediaDescriptor
import app.subloka.core.domain.MediaErrorCode
import app.subloka.core.domain.MediaSourceException
import java.security.MessageDigest

internal class AndroidMediaProbe(
    context: Context,
) {
    private val appContext = context.applicationContext
    private val resolver = appContext.contentResolver

    fun inspect(uri: Uri): MediaDescriptor {
        val extractor = MediaExtractor()
        try {
            extractor.setDataSource(appContext, uri, null)

            var durationUs = 0L
            var width = 0
            var height = 0
            var rotation = 0
            var hasVideo = false
            val audioTracks = mutableListOf<AudioTrackDescriptor>()

            for (index in 0 until extractor.trackCount) {
                val format = extractor.getTrackFormat(index)
                val mime = format.getString(MediaFormat.KEY_MIME).orEmpty()
                if (format.containsKey(MediaFormat.KEY_DURATION)) {
                    durationUs = maxOf(durationUs, format.getLong(MediaFormat.KEY_DURATION))
                }

                when {
                    mime.startsWith("video/") && !hasVideo -> {
                        hasVideo = true
                        width = requiredPositive(format, MediaFormat.KEY_WIDTH)
                        height = requiredPositive(format, MediaFormat.KEY_HEIGHT)
                        rotation = normalizeRotation(
                            if (format.containsKey(MediaFormat.KEY_ROTATION)) {
                                format.getInteger(MediaFormat.KEY_ROTATION)
                            } else {
                                0
                            },
                        )
                    }
                    mime.startsWith("audio/") -> {
                        audioTracks += AudioTrackDescriptor(
                            trackIndex = index,
                            mimeType = mime,
                            sampleRate = optionalPositive(format, MediaFormat.KEY_SAMPLE_RATE),
                            channelCount = optionalPositive(format, MediaFormat.KEY_CHANNEL_COUNT),
                            language = format.getString(MediaFormat.KEY_LANGUAGE),
                        )
                    }
                }
            }

            if (!hasVideo || durationUs <= 0L || width <= 0 || height <= 0) {
                throw MediaSourceException(
                    MediaErrorCode.UNSUPPORTED_MEDIA,
                    "Media tidak memiliki track video yang dapat dibaca.",
                )
            }
            if (audioTracks.isEmpty()) {
                throw MediaSourceException(
                    MediaErrorCode.NO_AUDIO,
                    "Video tidak memiliki track audio.",
                )
            }

            val metadata = queryDocumentMetadata(uri)
            return MediaDescriptor(
                uri = uri.toString(),
                displayName = metadata.first ?: "video",
                sizeBytes = metadata.second,
                fingerprintSha256 = sha256(uri),
                durationUs = durationUs,
                widthPx = width,
                heightPx = height,
                rotationDegrees = rotation,
                audioTracks = audioTracks,
            )
        } catch (error: MediaSourceException) {
            throw error
        } catch (error: SecurityException) {
            throw MediaSourceException(
                MediaErrorCode.URI_PERMISSION_LOST,
                "Izin membaca video tidak tersedia.",
                error,
            )
        } catch (error: Exception) {
            throw MediaSourceException(
                MediaErrorCode.MEDIA_UNAVAILABLE,
                "Video tidak dapat dibuka.",
                error,
            )
        } finally {
            extractor.release()
        }
    }

    private fun queryDocumentMetadata(uri: Uri): Pair<String?, Long?> {
        resolver.query(
            uri,
            arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE),
            null,
            null,
            null,
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
                val name = if (nameIndex >= 0 && !cursor.isNull(nameIndex)) cursor.getString(nameIndex) else null
                val size = if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) cursor.getLong(sizeIndex) else null
                return name to size
            }
        }
        return null to null
    }

    private fun sha256(uri: Uri): String {
        val digest = MessageDigest.getInstance("SHA-256")
        resolver.openInputStream(uri)?.use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                if (read > 0) digest.update(buffer, 0, read)
            }
        } ?: throw MediaSourceException(
            MediaErrorCode.MEDIA_UNAVAILABLE,
            "Video tidak dapat dibaca untuk verifikasi fingerprint.",
        )
        return digest.digest().joinToString("") { byte -> "%02x".format(byte.toInt() and 0xff) }
    }

    private fun requiredPositive(format: MediaFormat, key: String): Int =
        optionalPositive(format, key) ?: 0

    private fun optionalPositive(format: MediaFormat, key: String): Int? =
        if (format.containsKey(key)) format.getInteger(key).takeIf { it > 0 } else null

    private fun normalizeRotation(value: Int): Int {
        val normalized = ((value % 360) + 360) % 360
        return when (normalized) {
            0, 90, 180, 270 -> normalized
            else -> 0
        }
    }
}

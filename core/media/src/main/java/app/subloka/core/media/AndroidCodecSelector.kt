package app.subloka.core.media

import android.media.MediaCodecList
import android.media.MediaFormat
import app.subloka.core.domain.MediaErrorCode
import app.subloka.core.domain.MediaSourceException

internal object AndroidCodecSelector {
    fun findDecoderName(format: MediaFormat): String {
        val mime = format.getString(MediaFormat.KEY_MIME).orEmpty()
        if (mime.isBlank()) {
            throw MediaSourceException(
                MediaErrorCode.UNSUPPORTED_MEDIA,
                "Audio MIME tidak tersedia untuk memilih decoder.",
            )
        }

        return MediaCodecList(MediaCodecList.REGULAR_CODECS)
            .findDecoderForFormat(format)
            ?: throw MediaSourceException(
                MediaErrorCode.UNSUPPORTED_MEDIA,
                "Codec audio tidak didukung perangkat: $mime",
            )
    }
}

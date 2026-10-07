package app.subloka.core.domain

enum class MediaErrorCode {
    MEDIA_UNAVAILABLE,
    URI_PERMISSION_LOST,
    NO_AUDIO,
    UNSUPPORTED_MEDIA,
    DECODE_FAILURE,
}

class MediaSourceException(
    val code: MediaErrorCode,
    message: String,
    cause: Throwable? = null,
) : Exception(message, cause)

data class AudioTrackDescriptor(
    val trackIndex: Int,
    val mimeType: String,
    val sampleRate: Int?,
    val channelCount: Int?,
    val language: String?,
)

data class MediaDescriptor(
    val uri: String,
    val displayName: String,
    val sizeBytes: Long?,
    val fingerprintSha256: String,
    val durationUs: Long,
    val widthPx: Int,
    val heightPx: Int,
    val rotationDegrees: Int,
    val audioTracks: List<AudioTrackDescriptor>,
) {
    init {
        require(uri.isNotBlank()) { "uri must not be blank" }
        require(displayName.isNotBlank()) { "displayName must not be blank" }
        require(fingerprintSha256.length == 64) { "fingerprintSha256 must be SHA-256 hex" }
        require(durationUs > 0) { "durationUs must be positive" }
        require(widthPx > 0 && heightPx > 0) { "video dimensions must be positive" }
        require(rotationDegrees in setOf(0, 90, 180, 270)) { "unsupported rotation" }
        require(audioTracks.isNotEmpty()) { "media must contain at least one audio track" }
    }
}

enum class PcmSampleFormat {
    S16_LE,
    FLOAT32_LE,
    U8,
    UNKNOWN,
}

data class PcmChunk(
    val bytes: ByteArray,
    val presentationTimeUs: Long,
    val sampleRate: Int,
    val channelCount: Int,
    val sampleFormat: PcmSampleFormat,
)

data class PcmDecodeSummary(
    val bytesDecoded: Long,
    val lastPresentationTimeUs: Long,
    val sampleRate: Int,
    val channelCount: Int,
    val sampleFormat: PcmSampleFormat,
    val truncated: Boolean,
)

data class MediaRelinkResult(
    val accepted: Boolean,
    val candidate: MediaDescriptor,
)

interface MediaSource {
    suspend fun inspect(uri: String): MediaDescriptor

    suspend fun decodePcm(
        uri: String,
        audioTrackIndex: Int? = null,
        maxOutputBytes: Long? = null,
        onChunk: (PcmChunk) -> Unit,
    ): PcmDecodeSummary

    suspend fun verifyRelink(
        original: MediaDescriptor,
        candidateUri: String,
    ): MediaRelinkResult
}

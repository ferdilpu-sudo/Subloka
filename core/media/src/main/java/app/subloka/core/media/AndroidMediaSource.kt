package app.subloka.core.media

import android.content.Context
import android.net.Uri
import app.subloka.core.domain.MediaDescriptor
import app.subloka.core.domain.MediaRelinkResult
import app.subloka.core.domain.MediaSource
import app.subloka.core.domain.PcmChunk
import app.subloka.core.domain.PcmDecodeSummary
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AndroidMediaSource(
    context: Context,
) : MediaSource {
    private val probe = AndroidMediaProbe(context)
    private val decoder = AndroidPcmDecoder(context)

    override suspend fun inspect(uri: String): MediaDescriptor =
        withContext(Dispatchers.IO) {
            probe.inspect(Uri.parse(uri))
        }

    override suspend fun decodePcm(
        uri: String,
        audioTrackIndex: Int?,
        maxOutputBytes: Long?,
        onChunk: (PcmChunk) -> Unit,
    ): PcmDecodeSummary = withContext(Dispatchers.IO) {
        decoder.decode(Uri.parse(uri), audioTrackIndex, maxOutputBytes, onChunk)
    }

    override suspend fun verifyRelink(
        original: MediaDescriptor,
        candidateUri: String,
    ): MediaRelinkResult = withContext(Dispatchers.IO) {
        MediaRelinkVerifier.verify(original, probe.inspect(Uri.parse(candidateUri)))
    }
}

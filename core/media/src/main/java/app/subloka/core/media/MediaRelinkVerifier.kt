package app.subloka.core.media

import app.subloka.core.domain.MediaDescriptor
import app.subloka.core.domain.MediaRelinkResult

object MediaRelinkVerifier {
    fun verify(original: MediaDescriptor, candidate: MediaDescriptor): MediaRelinkResult =
        MediaRelinkResult(
            accepted = original.fingerprintSha256 == candidate.fingerprintSha256,
            candidate = candidate,
        )
}

package app.subloka.core.media

import app.subloka.core.domain.AudioTrackDescriptor
import app.subloka.core.domain.MediaDescriptor
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MediaRelinkVerifierTest {
    @Test
    fun exactFingerprintIsAcceptedEvenWhenUriChanges() {
        val original = descriptor("content://old", "a".repeat(64))
        val candidate = descriptor("content://new", "a".repeat(64))

        assertTrue(MediaRelinkVerifier.verify(original, candidate).accepted)
    }

    @Test
    fun differentFingerprintIsRejected() {
        val original = descriptor("content://old", "a".repeat(64))
        val candidate = descriptor("content://new", "b".repeat(64))

        assertFalse(MediaRelinkVerifier.verify(original, candidate).accepted)
    }

    private fun descriptor(uri: String, fingerprint: String) = MediaDescriptor(
        uri = uri,
        displayName = "video.mp4",
        sizeBytes = 1_024,
        fingerprintSha256 = fingerprint,
        durationUs = 1_000_000,
        widthPx = 1_920,
        heightPx = 1_080,
        rotationDegrees = 0,
        audioTracks = listOf(
            AudioTrackDescriptor(
                trackIndex = 1,
                mimeType = "audio/mp4a-latm",
                sampleRate = 48_000,
                channelCount = 2,
                language = null,
            ),
        ),
    )
}

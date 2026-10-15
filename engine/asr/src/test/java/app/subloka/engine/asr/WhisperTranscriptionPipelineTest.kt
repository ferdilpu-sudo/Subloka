package app.subloka.engine.asr

import app.subloka.core.domain.*
import java.io.File
import java.nio.file.Files
import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test

class WhisperTranscriptionPipelineTest {
    private val descriptor = MediaDescriptor("content://test/audio", "test.mp4", 1, "a".repeat(64),
        31_000_000, 640, 480, 0, listOf(AudioTrackDescriptor(0, "audio/test", 16000, 1, null)))
    private fun media(silent: Boolean = false) = object : MediaSource {
        override suspend fun inspect(uri: String) = descriptor
        override suspend fun verifyRelink(original: MediaDescriptor, candidateUri: String) = MediaRelinkResult(true, descriptor)
        override suspend fun decodePcm(uri: String, audioTrackIndex: Int?, maxOutputBytes: Long?, onChunk: (PcmChunk) -> Unit): PcmDecodeSummary {
            repeat(31) { second -> onChunk(PcmChunk(ByteArray(32000) { if (silent) 0 else 10 }, second * 1_000_000L, 16000, 1, PcmSampleFormat.S16_LE)) }
            return PcmDecodeSummary(31 * 32000L, 30_000_000, 16000, 1, PcmSampleFormat.S16_LE, false)
        }
    }
    private class FakeSession(val failSecond: Boolean = false) : SpeechSession {
        var calls = 0; var closed = false; var cancelled = false
        override fun transcribe(samples: FloatArray, language: String): List<RawSpeechSegment> {
            calls++
            check(!failSecond || calls != 2) { "injected native failure" }
            return listOf(RawSpeechSegment(0, samples.size * 1_000_000L / 16000, "speech"))
        }
        override fun cancel() { cancelled = true }
        override fun close() { closed = true }
    }
    @Test fun stagesTwoWindowsAndCleansPrivateCache() = runBlocking {
        val cache = Files.createTempDirectory("pipeline").toFile()
        try {
            val session = FakeSession()
            val result = WhisperTranscriptionPipeline(media(), cache) { _, _ -> session }.transcribe(descriptor, SourceLanguage.ENGLISH, File("unused"), File("unused-vad")) {}
            assertEquals(2, result.size)
            assertEquals(30_000_000L, result[1].startUs)
            assertEquals(31_000_000L, result[1].endUs)
            assertTrue(session.closed)
            assertEquals(0, cache.listFiles()!!.size)
        } finally { cache.deleteRecursively() }
    }
    @Test fun vadModelIsPassedToSessionAndEmptyDetectedWindowDoesNotCompressFollowingTime() = runBlocking {
        val cache = Files.createTempDirectory("vad-pipeline").toFile()
        val base = File("base.bin")
        val vad = File("vad.bin")
        try {
            var calls = 0
            var closed = false
            val session = object : SpeechSession {
                override fun transcribe(samples: FloatArray, language: String): List<RawSpeechSegment> =
                    if (++calls == 1) emptyList() else listOf(RawSpeechSegment(200_000, 800_000, "speech"))
                override fun cancel() {}
                override fun close() { closed = true }
            }
            val result = WhisperTranscriptionPipeline(media(), cache) { actualBase, actualVad ->
                assertEquals(base, actualBase); assertEquals(vad, actualVad); session
            }.transcribe(descriptor, SourceLanguage.INDONESIA, base, vad) {}
            assertEquals(30_200_000L, result.single().startUs)
            assertEquals(30_800_000L, result.single().endUs)
            assertTrue(closed)
            assertEquals(0, cache.listFiles()!!.size)
        } finally { cache.deleteRecursively() }
    }

    @Test fun silenceSkipsInference() = runBlocking {
        val cache = Files.createTempDirectory("pipeline").toFile()
        try {
            val session = FakeSession()
            val result = WhisperTranscriptionPipeline(media(true), cache) { _, _ -> session }.transcribe(descriptor, SourceLanguage.ENGLISH, File("unused"), File("unused-vad")) {}
            assertTrue(result.isEmpty()); assertEquals(0, session.calls); assertTrue(session.closed)
        } finally { cache.deleteRecursively() }
    }
    @Test fun failureAndCancellationNeverReturnPartialResults() = runBlocking {
        for (cancel in listOf(false, true)) {
            val cache = Files.createTempDirectory("pipeline").toFile()
            try {
                val session = FakeSession(failSecond = !cancel)
                val worker = WhisperTranscriptionPipeline(media(), cache) { _, _ -> session }
                var returned = false
                try {
                    worker.transcribe(descriptor, SourceLanguage.ENGLISH, File("unused"), File("unused-vad")) { stage ->
                        if (cancel && stage.contains("bagian 2")) worker.cancel()
                    }
                    returned = true
                } catch (_: CancellationException) { assertTrue(cancel) }
                catch (_: IllegalStateException) { assertFalse(cancel) }
                assertFalse(returned); assertTrue(session.closed)
                assertEquals(0, cache.listFiles()!!.size)
            } finally { cache.deleteRecursively() }
        }
    }
}

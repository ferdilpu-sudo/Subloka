package app.subloka.engine.translation

import app.subloka.core.domain.*
import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test

class CaptionTranslationPipelineTest {
    private fun segment(id: String, language: SourceLanguage = SourceLanguage.INDONESIA,
                        status: TranslationStatus = TranslationStatus.MISSING,
                        origin: TranslationOrigin = TranslationOrigin.NONE,
                        source: String = "Source $id") = CaptionSegment(id, 0, 1_000_000, language, source,
        if (status == TranslationStatus.MISSING) "" else "Existing", status, origin,
        sourceRevision = 2, translationSourceRevision = if (status == TranslationStatus.CURRENT) 2 else null)

    private class FakeTranslator : OfflineTranslator {
        var readiness = ModelReadinessState.READY
        var downloads = 0
        val pairs = mutableListOf<Pair<SourceLanguage, SourceLanguage>>()
        var translateAction: suspend (String) -> String = { "Translation: $it" }
        override suspend fun state() = readiness
        override suspend fun ensureReady(requireWifi: Boolean) { downloads++ }
        override suspend fun translate(text: String, sourceLanguage: SourceLanguage, targetLanguage: SourceLanguage): String {
            pairs += sourceLanguage to targetLanguage
            return translateAction(text)
        }
        override fun close() = Unit
    }

    @Test fun bothDirectionsSkipCurrentManualAndBlankSources() = runBlocking {
        val translator = FakeTranslator()
        val published = mutableListOf<String>()
        val snapshot = listOf(segment("id"), segment("en", SourceLanguage.ENGLISH),
            segment("current", status = TranslationStatus.CURRENT, origin = TranslationOrigin.MACHINE),
            segment("manual", status = TranslationStatus.STALE, origin = TranslationOrigin.MANUAL),
            segment("blank", source = " "))
        val result = CaptionTranslationPipeline(translator).run(snapshot, { source, _ -> published += source.id; true }, {})
        assertEquals(listOf("id", "en"), published)
        assertEquals(listOf(SourceLanguage.INDONESIA to SourceLanguage.ENGLISH, SourceLanguage.ENGLISH to SourceLanguage.INDONESIA), translator.pairs)
        assertEquals(2, result.applied)
        assertEquals(0, translator.downloads)
    }

    @Test fun missingModelFailsBeforeInferenceWithoutImplicitDownload() = runBlocking {
        val translator = FakeTranslator().apply { readiness = ModelReadinessState.NOT_READY }
        var called = false
        try {
            CaptionTranslationPipeline(translator).run(listOf(segment("one")), { _, _ -> called = true; true }, {})
            fail("Expected readiness failure")
        } catch (_: IllegalStateException) { }
        assertFalse(called); assertTrue(translator.pairs.isEmpty()); assertEquals(0, translator.downloads)
    }

    @Test fun failedAndBlankResultsRemainRetryableWhileSuccessfulResultsAreKept() = runBlocking {
        val translator = FakeTranslator().apply {
            translateAction = { text -> when (text) { "Source fail" -> error("injected"); "Source blank" -> " "; else -> "Translated" } }
        }
        val stored = listOf(segment("ok"), segment("fail"), segment("blank")).associateBy { it.id }.toMutableMap()
        suspend fun publish(source: CaptionSegment, text: String): Boolean {
            stored[source.id] = source.copy(translationText = text, translationStatus = TranslationStatus.CURRENT,
                translationOrigin = TranslationOrigin.MACHINE, translationSourceRevision = source.sourceRevision)
            return true
        }
        val first = CaptionTranslationPipeline(translator).run(stored.values.toList(), ::publish, {})
        assertEquals(1, first.applied); assertEquals(2, first.failed)
        translator.translateAction = { "Retried" }
        val retry = CaptionTranslationPipeline(translator).run(stored.values.toList(), ::publish, {})
        assertEquals(2, retry.total); assertEquals(2, retry.applied)
        assertEquals("Translated", stored.getValue("ok").translationText)
    }

    @Test fun revisionConflictIsSkippedWithoutRetryingOrOverwritingIt() = runBlocking {
        val result = CaptionTranslationPipeline(FakeTranslator()).run(listOf(segment("changed")), { _, _ -> false }, {})
        assertEquals(0, result.applied); assertEquals(1, result.conflicted); assertEquals(0, result.failed)
    }

    @Test fun lateSdkResultAfterCancellationCannotPublish() = runBlocking {
        var published = false
        val translator = FakeTranslator().apply {
            translateAction = { currentCoroutineContext().cancel(); "Late SDK result" }
        }
        val job = launch {
            CaptionTranslationPipeline(translator).run(listOf(segment("cancel")), { _, _ -> published = true; true }, {})
        }
        job.join()
        assertTrue(job.isCancelled); assertFalse(published)
    }

    @Test fun persistenceFailureAbortsInsteadOfReportingSuccessfulTranslation() = runBlocking {
        var writes = 0
        try {
            CaptionTranslationPipeline(FakeTranslator()).run(listOf(segment("a"), segment("b")), { _, _ ->
                writes++; error("database unavailable")
            }, {})
            fail("Expected database failure")
        } catch (_: IllegalStateException) { }
        assertEquals(1, writes)
    }
    @Test fun explicitReplacementUpdatesMachineOnlyAndPreservesOldTextOnFailure() = runBlocking {
        val current = segment("machine", status = TranslationStatus.CURRENT, origin = TranslationOrigin.MACHINE)
        val manual = segment("manual", status = TranslationStatus.CURRENT, origin = TranslationOrigin.MANUAL)
        val staleManual = segment("stale-manual", status = TranslationStatus.STALE, origin = TranslationOrigin.MANUAL)
        val published = mutableListOf<String>()
        val translator = FakeTranslator()
        val result = CaptionTranslationPipeline(translator).run(listOf(current, manual, staleManual),
            { source, _ -> published += source.id; true }, {}, replaceCurrentMachine = true)
        assertEquals(listOf("machine"), published); assertEquals(1, result.applied)
        translator.translateAction = { error("model failed") }
        published.clear()
        val failed = CaptionTranslationPipeline(translator).run(listOf(current),
            { source, _ -> published += source.id; true }, {}, replaceCurrentMachine = true)
        assertEquals(1, failed.failed); assertTrue(published.isEmpty())
        assertEquals("Existing", current.translationText)
    }
}

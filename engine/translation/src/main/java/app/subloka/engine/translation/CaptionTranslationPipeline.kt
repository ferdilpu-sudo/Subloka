package app.subloka.engine.translation

import app.subloka.core.domain.CaptionSegment
import app.subloka.core.domain.ModelReadinessState
import app.subloka.core.domain.OfflineTranslator
import app.subloka.core.domain.TranslationEligibility
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive

data class TranslationProgress(val total: Int, val processed: Int = 0, val applied: Int = 0,
                               val conflicted: Int = 0, val failed: Int = 0)

/** Owns no model lifetime. Publication must atomically check revision and protect manual edits. */
class CaptionTranslationPipeline(private val translator: OfflineTranslator) {
    suspend fun run(snapshot: List<CaptionSegment>,
                    publish: suspend (CaptionSegment, String) -> Boolean,
                    onProgress: (TranslationProgress) -> Unit): TranslationProgress {
        check(translator.state() == ModelReadinessState.READY) { "Siapkan model terjemahan terlebih dahulu." }
        val eligible = snapshot.filter(TranslationEligibility::canGenerate)
        var progress = TranslationProgress(eligible.size)
        onProgress(progress)
        for (segment in eligible) {
            currentCoroutineContext().ensureActive()
            val translated = try {
                translator.translate(segment.sourceText, segment.sourceLanguage, segment.sourceLanguage.target)
                    .trim().also { check(it.isNotBlank()) { "Empty translation" } }
            } catch (cancel: CancellationException) { throw cancel }
            catch (_: Exception) {
                progress = progress.copy(processed = progress.processed + 1, failed = progress.failed + 1)
                onProgress(progress)
                continue
            }
            // SDK tasks may finish after cancellation; late output must never be published.
            currentCoroutineContext().ensureActive()
            val applied = publish(segment, translated)
            progress = progress.copy(processed = progress.processed + 1,
                applied = progress.applied + if (applied) 1 else 0,
                conflicted = progress.conflicted + if (applied) 0 else 1)
            onProgress(progress)
        }
        return progress
    }
}

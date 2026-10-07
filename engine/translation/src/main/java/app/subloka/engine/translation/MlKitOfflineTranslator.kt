package app.subloka.engine.translation

import app.subloka.core.domain.ModelReadinessState
import app.subloka.core.domain.OfflineTranslator
import app.subloka.core.domain.SourceLanguage
import com.google.android.gms.tasks.Task
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.common.model.RemoteModelManager
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.TranslateRemoteModel
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlinx.coroutines.suspendCancellableCoroutine

class MlKitOfflineTranslator(
    private val modelManager: RemoteModelManager = RemoteModelManager.getInstance(),
) : OfflineTranslator {
    private val englishToIndonesian = translator(SourceLanguage.ENGLISH, SourceLanguage.INDONESIA)
    private val indonesianToEnglish = translator(SourceLanguage.INDONESIA, SourceLanguage.ENGLISH)

    override suspend fun state(): ModelReadinessState =
        try {
            if (modelsReady()) ModelReadinessState.READY else ModelReadinessState.NOT_READY
        } catch (_: Throwable) {
            ModelReadinessState.FAILED
        }

    override suspend fun ensureReady(requireWifi: Boolean) {
        val conditions = DownloadConditions.Builder().apply {
            if (requireWifi) requireWifi()
        }.build()

        modelManager.download(remoteModel(SourceLanguage.ENGLISH), conditions).awaitResult()
        modelManager.download(remoteModel(SourceLanguage.INDONESIA), conditions).awaitResult()
        check(modelsReady()) { "ML Kit EN/ID translation models are not ready after download" }
    }

    override suspend fun translate(
        text: String,
        sourceLanguage: SourceLanguage,
        targetLanguage: SourceLanguage,
    ): String {
        require(text.isNotBlank()) { "text must not be blank" }
        require(sourceLanguage != targetLanguage) { "source and target must differ" }

        val client = when (sourceLanguage to targetLanguage) {
            SourceLanguage.ENGLISH to SourceLanguage.INDONESIA -> englishToIndonesian
            SourceLanguage.INDONESIA to SourceLanguage.ENGLISH -> indonesianToEnglish
            else -> error("Unsupported translation pair: $sourceLanguage -> $targetLanguage")
        }

        check(state() == ModelReadinessState.READY) { "Translation models are not ready" }
        return client.translate(text).awaitResult()
    }

    override fun close() {
        englishToIndonesian.close()
        indonesianToEnglish.close()
    }

    private suspend fun modelsReady(): Boolean =
        modelManager.isModelDownloaded(remoteModel(SourceLanguage.ENGLISH)).awaitResult() &&
            modelManager.isModelDownloaded(remoteModel(SourceLanguage.INDONESIA)).awaitResult()

    private fun translator(source: SourceLanguage, target: SourceLanguage): Translator =
        Translation.getClient(
            TranslatorOptions.Builder()
                .setSourceLanguage(languageCode(source))
                .setTargetLanguage(languageCode(target))
                .build(),
        )

    private fun remoteModel(language: SourceLanguage): TranslateRemoteModel =
        TranslateRemoteModel.Builder(languageCode(language)).build()

    private fun languageCode(language: SourceLanguage): String = when (language) {
        SourceLanguage.ENGLISH -> TranslateLanguage.ENGLISH
        SourceLanguage.INDONESIA -> TranslateLanguage.INDONESIAN
    }
}

private suspend fun <T> Task<T>.awaitResult(): T =
    suspendCancellableCoroutine { continuation ->
        addOnSuccessListener { result ->
            if (continuation.isActive) continuation.resume(result)
        }
        addOnFailureListener { error ->
            if (continuation.isActive) continuation.resumeWithException(error)
        }
        addOnCanceledListener {
            continuation.cancel()
        }
    }

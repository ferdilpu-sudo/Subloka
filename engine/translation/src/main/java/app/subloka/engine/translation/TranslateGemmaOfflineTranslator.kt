package app.subloka.engine.translation

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import app.subloka.core.domain.*
import java.io.File
import java.io.InputStream
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.*

class TranslateGemmaOfflineTranslator(
    private val context: Context,
    private val termsAccepted: Boolean,
    private val onStage: (String) -> Unit = {},
) : OfflineTranslator {
    private var wifiOnly = false
    private val canceled = AtomicBoolean(false)
    private val lock = Any()
    private var handle = 0L
    private var verified = false
    private val model = TranslateGemmaModel.descriptor
    private val store = TranslationModelStore(File(context.filesDir, "translation-gemma"), {
        check(!canceled.get()) { "PROCESS_INTERRUPTED" }
        if (wifiOnly) {
            val manager = context.getSystemService(ConnectivityManager::class.java)
            check(manager.getNetworkCapabilities(manager.activeNetwork)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true) {
                "Sambungkan Wi-Fi untuk melanjutkan unduhan."
            }
        }
    }, { onStage("Menyiapkan model terjemahan: $it%") })

    override suspend fun state(): ModelReadinessState {
        if (verified) return ModelReadinessState.READY
        return store.state(model).also { verified = it == ModelReadinessState.READY }
    }
    override suspend fun ensureReady(requireWifi: Boolean) {
        check(termsAccepted) { "Tinjau dan setujui ketentuan Gemma terlebih dahulu." }
        if (state() == ModelReadinessState.READY) return
        wifiOnly = requireWifi
        store.download(model); verified = true
    }
    suspend fun importModel(input: InputStream) {
        check(termsAccepted); wifiOnly = false
        store.installFrom(model, input); verified = true
    }
    override suspend fun translate(text: String, sourceLanguage: SourceLanguage, targetLanguage: SourceLanguage): String = withContext(Dispatchers.IO) {
        check(termsAccepted && state() == ModelReadinessState.READY)
        require(text.isNotBlank() && sourceLanguage != targetLanguage)
        currentCoroutineContext().ensureActive()
        if (canceled.get()) throw CancellationException()
        if (handle == 0L) {
            onStage("Memuat TranslateGemma…")
            val opened = NativeGemma.open(store.targetFile(model).absolutePath)
            synchronized(lock) { handle = opened; if (canceled.get()) NativeGemma.cancel(handle) }
        }
        val output = NativeGemma.run(handle, text.toByteArray(Charsets.UTF_8), sourceLanguage == SourceLanguage.INDONESIA)
        currentCoroutineContext().ensureActive()
        if (canceled.get()) throw CancellationException()
        output.toString(Charsets.UTF_8).trim().also { check(it.isNotBlank()) }
    }
    fun cancel() { canceled.set(true); synchronized(lock) { if (handle != 0L) NativeGemma.cancel(handle) } }
    // Owner must call close only once the inference coroutine has unwound.
    override fun close() { synchronized(lock) { if (handle != 0L) { NativeGemma.close(handle); handle = 0L } } }
}

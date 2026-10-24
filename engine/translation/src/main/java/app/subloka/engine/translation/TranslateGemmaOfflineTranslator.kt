package app.subloka.engine.translation

import android.util.Log
import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import app.subloka.core.domain.*
import java.io.File
import java.io.InputStream
import java.util.UUID
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
    private val diagnosticSession = UUID.randomUUID().toString()
    private var captionAttempt = 0
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
        onStage("Memeriksa model terjemahan…")
        return measured("verify") { store.state(model) }.also { verified = it == ModelReadinessState.READY }
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
            val opened = measured("load") { NativeGemma.open(store.targetFile(model).absolutePath) }
            synchronized(lock) { handle = opened; if (canceled.get()) NativeGemma.cancel(handle) }
        }
        currentCoroutineContext().ensureActive()
        if (canceled.get()) throw CancellationException()
        captionAttempt += 1
        onStage("Menerjemahkan caption ke-$captionAttempt…")
        val output = measured("caption_$captionAttempt") {
            NativeGemma.run(handle, text.toByteArray(Charsets.UTF_8), sourceLanguage == SourceLanguage.INDONESIA)
        }
        currentCoroutineContext().ensureActive()
        if (canceled.get()) throw CancellationException()
        output.toString(Charsets.UTF_8).trim().also { check(it.isNotBlank()) }
    }
    // Local diagnostics contain no caption text, file paths, or project identifiers.
    // A returned native call is not proof that the result was published to the database.
    private suspend fun <T> measured(stage: String, block: suspend () -> T): T {
        val started = System.nanoTime()
        var outcome = "failed"
        Log.i("SubLokaTranslation", "session=$diagnosticSession stage=$stage event=start")
        try {
            return block().also { outcome = "returned" }
        } catch (error: CancellationException) {
            outcome = "cancelled"
            throw error
        } finally {
            if (canceled.get()) outcome = "cancelled"
            val elapsedMs = (System.nanoTime() - started) / 1_000_000
            Log.i("SubLokaTranslation", "session=$diagnosticSession stage=$stage event=end elapsed_ms=$elapsedMs outcome=$outcome")
        }
    }

    fun cancel() { canceled.set(true); synchronized(lock) { if (handle != 0L) NativeGemma.cancel(handle) } }
    // Owner must call close only once the inference coroutine has unwound.
    override fun close() { synchronized(lock) { if (handle != 0L) { NativeGemma.close(handle); handle = 0L } } }
}

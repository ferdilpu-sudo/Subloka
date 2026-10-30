package app.subloka

import android.provider.Settings
import androidx.test.platform.app.InstrumentationRegistry
import app.subloka.engine.asr.WhisperModelCatalog
import app.subloka.engine.asr.WhisperSpeechSession
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Explicit opt-in, synthetic-free research; does not touch projects or model files. */
class TurboResearchBenchmarkTest {
    @Test fun runResearchFixture() {
        val args = InstrumentationRegistry.getArguments()
        assumeTrue(args.getString("research") == "turbo30")
        val token = requireNotNull(args.getString("fixture"))
        require(token.matches(Regex("[a-f0-9]{32}")))
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        fun offline() {
            check(Settings.Global.getInt(context.contentResolver, "airplane_mode_on", 0) == 1)
            check(Settings.Global.getInt(context.contentResolver, "wifi_on", 1) == 0)
        }
        fun battery(): Int {
            val info = requireNotNull(context.registerReceiver(null,
                android.content.IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED)))
            val temperature = info.getIntExtra(android.os.BatteryManager.EXTRA_TEMPERATURE, -1)
            check(temperature >= 0) { "Battery temperature unavailable" }
            return temperature
        }
        offline()
        check(AsrSession.state.value?.running != true && TranslationSession.state.value?.running != true &&
            RenderSession.state.value?.running != true) { "Application must be idle" }
        val root = File(context.filesDir, "research-$token")
        val manifest = JSONObject(File(root, "input.json").readText())
        val samples = manifest.getJSONArray("samples")
        check(samples.length() in 1..30)
        fun sha(file: File): String {
            val digest = MessageDigest.getInstance("SHA-256")
            file.inputStream().use { input ->
                val buffer = ByteArray(1024 * 1024)
                while (true) { val n = input.read(buffer); if (n < 0) break; digest.update(buffer, 0, n) }
            }
            return digest.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
        }
        val models = File(context.filesDir, "whisper-models")
        for (descriptor in listOf(WhisperModelCatalog.turbo, WhisperModelCatalog.vad)) {
            check(sha(File(models, descriptor.fileName)) == descriptor.expectedSha256)
        }
        val result = File(root, "results.jsonl")
        check(result.createNewFile()) { "Results already exist" }
        result.bufferedWriter().use { writer ->
            fun emit(value: JSONObject) { writer.write(value.toString()); writer.newLine(); writer.flush() }
            val loadStart = System.nanoTime()
            WhisperSpeechSession(File(models, WhisperModelCatalog.turbo.fileName),
                File(models, WhisperModelCatalog.vad.fileName)).use { session ->
                emit(JSONObject().put("event", "loaded").put("model", WhisperModelCatalog.turbo.id)
                    .put("app_version", context.packageManager.getPackageInfo(context.packageName, 0).versionName)
                    .put("fixture", token).put("model_sha256", WhisperModelCatalog.turbo.expectedSha256)
                    .put("vad_sha256", WhisperModelCatalog.vad.expectedSha256)
                    .put("load_ms", (System.nanoTime() - loadStart) / 1_000_000))
                val timer = Executors.newSingleThreadScheduledExecutor()
                try {
                    for (i in 0 until samples.length()) {
                        offline()
                        val coolingStart = System.nanoTime()
                        var temperature = battery()
                        while (temperature > 380) {
                            emit(JSONObject().put("event", "cooling").put("temperature_tenths_c", temperature))
                            check(System.nanoTime() - coolingStart < TimeUnit.MINUTES.toNanos(15)) {
                                "Cooling timeout; retain results and resume later"
                            }
                            Thread.sleep(15_000)
                            offline()
                            temperature = battery()
                        }
                        val coolingMs = (System.nanoTime() - coolingStart) / 1_000_000
                        val item = samples.getJSONObject(i)
                        val id = item.getString("id")
                        require(id.matches(Regex("id-(clean|challenging)-[0-9]{2}")))
                        val file = File(root, "$id.pcm")
                        check(file.length() in 2L..1_920_000L && file.length() % 2 == 0L)
                        check(sha(file) == item.getString("pcm_sha256"))
                        val bytes = file.readBytes()
                        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
                        val pcm = FloatArray(bytes.size / 2) { buffer.short / 32768f }
                        val started = System.nanoTime()
                        val timedOut = java.util.concurrent.atomic.AtomicBoolean(false)
                        val deadline = timer.schedule({ timedOut.set(true); session.cancel() }, 300, TimeUnit.SECONDS)
                        val segments = try { session.transcribe(pcm, "id") } finally { deadline.cancel(false) }
                        check(!timedOut.get()) { "Sample timed out" }
                        emit(JSONObject().put("event", "sample").put("id", id)
                            .put("elapsed_ms", (System.nanoTime() - started) / 1_000_000)
                            .put("cooling_ms", coolingMs).put("start_temperature_tenths_c", temperature)
                            .put("end_temperature_tenths_c", battery())
                            .put("text", segments.joinToString(" ") { it.text })
                            .put("segments", JSONArray().apply { segments.forEach { s ->
                                put(JSONObject().put("start_us", s.startUs).put("end_us", s.endUs))
                            } }))
                    }
                    emit(JSONObject().put("event", "complete").put("count", samples.length()))
                } finally { timer.shutdownNow() }
            }
        }
    }
}

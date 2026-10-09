package app.subloka.engine.translation

import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.SystemClock
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import app.subloka.core.domain.ModelReadinessState
import app.subloka.core.domain.SourceLanguage
import java.io.File
import java.util.Locale
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * T10 only: paired offline whole-paragraph versus newline sentencewise ML Kit.
 * New paragraph samples are not the frozen original CP4 single-sentence gate.
 */
@RunWith(AndroidJUnit4::class)
class MlKitTranslationStrategyABTest {
    @Test
    fun exportNewParagraphStrategyPairsForReview() = runBlocking {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val app = instrumentation.targetContext
        val fixture = instrumentation.context.assets
            .open("t10_translation_strategy_ab_fixtures.json")
            .bufferedReader(Charsets.UTF_8).use { JSONObject(it.readText()) }
        assertEquals(1, fixture.getInt("version"))
        val samples = fixture.getJSONArray("samples")
        assertEquals("Must check all 60 new paragraphs", 60, samples.length())
        val seen = mutableSetOf<String>()
        var en = 0
        var id = 0
        for (i in 0 until samples.length()) {
            val row = samples.getJSONObject(i)
            val sampleId = row.getString("id")
            assertTrue("Duplicate sample id: $sampleId", seen.add(sampleId))
            val sentences = row.getString("text").split("\n")
            assertEquals("Expected two explicit sentences: $sampleId", 2, sentences.size)
            assertTrue("Empty sentence: $sampleId", sentences.all { it.isNotBlank() })
            when (row.getString("language")) {
                "id" -> id++
                "en" -> en++
                else -> error("Unexpected source language in new fixture")
            }
        }
        assertEquals(30, en)
        assertEquals(30, id)

        val initialBattery = batteryC(app)
        assertTrue("Cool device to battery <40C; start=$initialBattery", initialBattery < 40.0)
        val dir = requireNotNull(app.getExternalFilesDir(null))
        val output = File(dir, "t10-translation-strategy-ab-${System.currentTimeMillis()}.csv")
        val partial = File(dir, "${output.name}.partial")
        var failures = 0
        var sequence = 0
        val startWall = SystemClock.elapsedRealtime()

        MlKitOfflineTranslator().use { translator ->
            // Caller verifies airplane + Wi-Fi off. Absolutely no ensureReady here.
            assertEquals(ModelReadinessState.READY, translator.state())
            partial.bufferedWriter(Charsets.UTF_8).use { writer ->
                writer.appendLine(
                    "sample,source_language,target_language,source_text,strategy," +
                        "translation,latency_ms,error,call_count,sequence,battery_c"
                )
                for (i in 0 until samples.length()) {
                    val row = samples.getJSONObject(i)
                    val sampleId = row.getString("id")
                    val source = row.getString("text")
                    val parts = source.split("\n")
                    val sourceCode = row.getString("language")
                    val sourceLanguage = when (sourceCode) {
                        "en" -> SourceLanguage.ENGLISH
                        "id" -> SourceLanguage.INDONESIA
                        else -> error("Unexpected source language")
                    }
                    val targetCode = if (sourceCode == "id") "en" else "id"
                    // AB/BA alternate within each source paragraph. Retain every pair.
                    val order = if (i % 2 == 0) listOf("whole", "linewise")
                                else listOf("linewise", "whole")
                    for (strategy in order) {
                        val temperature = batteryC(app)
                        check(temperature < 43.0) {
                            "Thermal stop at battery=$temperature C before $sampleId/$strategy"
                        }
                        check(SystemClock.elapsedRealtime() - startWall < 600_000L) {
                            "Diagnostic exceeded 10-minute wall-clock safety budget"
                        }
                        val started = SystemClock.elapsedRealtimeNanos()
                        var translated = ""
                        var failureText = ""
                        try {
                            translated = if (strategy == "whole") {
                                translator.translate(source, sourceLanguage)
                            } else {
                                val pieces = mutableListOf<String>()
                                for (part in parts) {
                                    pieces += translator.translate(part, sourceLanguage)
                                }
                                pieces.joinToString(" ")
                            }
                        } catch (failure: Exception) {
                            failures++
                            failureText = "${failure.javaClass.simpleName}: ${failure.message.orEmpty()}".take(300)
                        }
                        val elapsedMs = (SystemClock.elapsedRealtimeNanos() - started) / 1_000_000.0
                        val endBattery = batteryC(app)
                        check(endBattery < 43.0) {
                            "Thermal stop at battery=$endBattery C after $sampleId/$strategy"
                        }
                        sequence++
                        val values = listOf(
                            sampleId, sourceCode, targetCode, source, strategy,
                            translated, "%.3f".format(Locale.US, elapsedMs), failureText,
                            if (strategy == "whole") "1" else "2",
                            "$sequence", "%.1f".format(Locale.US, endBattery)
                        )
                        writer.appendLine(values.joinToString(",") { csv(it) })
                    }
                }
            }
        }
        check(partial.renameTo(output)) { "Cannot finalize strategy A/B CSV" }
        Log.i("SubLokaT10", "STRATEGY_AB_RESULT_PATH=${output.absolutePath}")
        Log.i("SubLokaT10", "STRATEGY_AB_PAIRED=60; RUNS=120; TRANSLATION_ERRORS=$failures")
        assertTrue(output.isFile)
        assertEquals("Inspect failed offline inference; results preserved in original CSV", 0, failures)
    }

    private fun batteryC(context: android.content.Context): Double {
        val state = requireNotNull(
            context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        ) { "Cannot sample battery-temperature proxy" }
        val tenths = state.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1)
        check(tenths >= 0) { "Battery temperature sensor unavailable" }
        return tenths / 10.0
    }

    private fun csv(value: String): String = "\"${value.replace("\"", "\"\"")}\""
}

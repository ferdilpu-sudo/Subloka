package app.subloka.engine.translation

import android.os.SystemClock
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import app.subloka.core.domain.ModelReadinessState
import app.subloka.core.domain.SourceLanguage
import java.io.File
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** T10/CP4: produces raw EN<->ID outputs for independent human quality review. */
@RunWith(AndroidJUnit4::class)
class MlKitTranslationBenchmarkTest {
    @Test
    fun exportOfflineTranslationsForHumanReview() = runBlocking {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val fixture = instrumentation.context.assets.open("t10_translation_fixtures.json")
            .bufferedReader(Charsets.UTF_8).use { JSONObject(it.readText()) }
        val samples = fixture.getJSONArray("samples")
        assertEquals("T10 fixture must contain exactly 60 rows", 60, samples.length())

        val seen = mutableSetOf<String>()
        var englishCount = 0
        var indonesianCount = 0
        for (index in 0 until samples.length()) {
            val row = samples.getJSONObject(index)
            assertTrue("Duplicate sample ID", seen.add(row.getString("id")))
            assertTrue("Empty input", row.getString("text").isNotBlank())
            when (row.getString("language")) {
                "en" -> englishCount++
                "id" -> indonesianCount++
                else -> error("Unsupported source language in fixture")
            }
        }
        assertEquals(30, englishCount)
        assertEquals(30, indonesianCount)

        val directory = requireNotNull(instrumentation.targetContext.getExternalFilesDir(null)) {
            "Cannot access app-specific external files directory"
        }
        val output = File(directory, "t10-translation-${System.currentTimeMillis()}.csv")
        val partial = File(directory, "${output.name}.partial")
        var failures = 0

        MlKitOfflineTranslator().use { translator ->
            // Deliberately avoid ensureReady() here: benchmark must work after models
            // were downloaded and the phone has been placed in airplane mode.
            assertEquals(
                "Translation models must be downloaded before offline benchmark",
                ModelReadinessState.READY,
                translator.state(),
            )
            partial.bufferedWriter(Charsets.UTF_8).use { writer ->
                writer.appendLine("sample,source_language,target_language,source_text,translation,latency_ms,error")
                for (index in 0 until samples.length()) {
                    val row = samples.getJSONObject(index)
                    val sourceLanguage = when (row.getString("language")) {
                        "en" -> SourceLanguage.ENGLISH
                        "id" -> SourceLanguage.INDONESIA
                        else -> error("Unexpected language")
                    }
                    val targetLanguage = when (sourceLanguage) {
                        SourceLanguage.ENGLISH -> SourceLanguage.INDONESIA
                        SourceLanguage.INDONESIA -> SourceLanguage.ENGLISH
                    }
                    val sourceCode = row.getString("language")
                    val targetCode = if (sourceCode == "en") "id" else "en"
                    val text = row.getString("text")
                    val startNs = SystemClock.elapsedRealtimeNanos()
                    var translated = ""
                    var errorMessage = ""
                    try {
                        translated = translator.translate(text, sourceLanguage, targetLanguage)
                    } catch (failure: Exception) {
                        failures++
                        errorMessage = "${failure.javaClass.simpleName}: ${failure.message.orEmpty()}".take(300)
                    }
                    val elapsedMs = (SystemClock.elapsedRealtimeNanos() - startNs) / 1_000_000.0
                    val values = listOf(
                        row.getString("id"), sourceCode, targetCode, text,
                        translated, "%.3f".format(java.util.Locale.US, elapsedMs), errorMessage,
                    )
                    writer.appendLine(values.joinToString(",") { csv(it) })
                }
            }
        }

        check(partial.renameTo(output)) { "Could not finalize benchmark CSV: ${partial.absolutePath}" }
        Log.i("SubLokaT10", "RESULT_PATH=${output.absolutePath}")
        Log.i("SubLokaT10", "SAMPLES=${samples.length()}; TRANSLATION_ERRORS=$failures")
        assertTrue("Raw translation CSV was not written", output.isFile)
        assertEquals("Translation failures are recorded in CSV; investigate before CP4", 0, failures)
    }

    private fun csv(value: String): String = "\"${value.replace("\"", "\"\"")}\""
}

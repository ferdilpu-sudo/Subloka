package app.subloka

import android.content.Intent
import android.content.IntentFilter
import android.media.MediaExtractor
import android.media.MediaFormat
import android.net.Uri
import android.os.BatteryManager
import android.os.Build
import android.os.Debug
import android.os.SystemClock
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import app.subloka.core.media.AndroidMediaSource
import java.io.File
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.runner.RunWith
import org.junit.Test

/**
 * T10 physical-device test for a REAL >=10-minute MP4 with audio.
 *
 * This invokes the media adapter used by app import, not the unimplemented
 * production ASR -> translation -> subtitle-export pipeline (T11-T14).
 * Therefore MEDIA_STAGE_PASS is NEVER a full app E2E / CP4 PASS.
 */
@RunWith(AndroidJUnit4::class)
class RealVideoTenMinuteMediaTest {
    @Test
    fun inspectAndDecodeRealTenMinuteVideoWithoutModifyingSource() = runBlocking {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val arguments = InstrumentationRegistry.getArguments()
        val name = arguments.getString("reportName").orEmpty()
        require(Regex("^t10-video10-[A-Za-z0-9-]+\\.json$").matches(name)) {
            "Pass a unique safe reportName through instrumentation"
        }
        val dir = requireNotNull(context.getExternalFilesDir(null)) {
            "App-specific external storage is unavailable"
        }
        val video = File(dir, "t10-real-video.mp4")
        val report = File(dir, name)
        check(!report.exists()) { "Refusing to overwrite an earlier video benchmark: $name" }
        val output = JSONObject()
        val started = SystemClock.elapsedRealtime()
        output.put("schema_version", 1)
        output.put("type", "T10_REAL_VIDEO_MEDIA_STAGE_ONLY_NOT_CP4")
        output.put("full_app_e2e", "BLOCKED_ASR_TRANSLATION_RENDER_EXPORT_NOT_INTEGRATED")
        output.put("source_file_name", video.name)
        output.put("source_bytes", video.length())
        output.put("device_manufacturer", Build.MANUFACTURER)
        output.put("device_model", Build.MODEL)
        output.put("android_sdk", Build.VERSION.SDK_INT)
        output.put("abi", Build.SUPPORTED_ABIS.firstOrNull().orEmpty())
        output.put("status", "MEDIA_STAGE_FAILED")
        var failure: Throwable? = null
        try {
            check(video.isFile && video.canRead() && video.length() > 0L) {
                "Input absent: push real >=600-second MP4 into app-specific files first"
            }
            val firstBattery = batteryC(context)
            output.put("battery_start_c", firstBattery)
            check(firstBattery < 40.0) { "Battery >=40 C before starting; cool phone first" }
            val media = AndroidMediaSource(context)
            val uri = Uri.fromFile(video).toString()
            val inspectStarted = SystemClock.elapsedRealtime()
            val descriptor = media.inspect(uri)
            output.put("inspect_wall_ms", SystemClock.elapsedRealtime() - inspectStarted)
            output.put("source_sha256", descriptor.fingerprintSha256)
            output.put("duration_us", descriptor.durationUs)
            output.put("width_px", descriptor.widthPx)
            output.put("height_px", descriptor.heightPx)
            output.put("rotation_degrees", descriptor.rotationDegrees)
            output.put("audio_track_count", descriptor.audioTracks.size)
            output.put("audio_mime", descriptor.audioTracks.first().mimeType)
            // Require a real >=600-second file; avoid running a surprise hour-long media job.
            check(descriptor.durationUs in 600_000_000L..900_000_000L) {
                "Require original real media 600-900 s, got ${descriptor.durationUs / 1_000_000.0} s"
            }
            output.put("video_mime", videoMime(context, uri))
            var chunks = 0L
            var firstPtsUs = -1L
            var lastPtsUs = -1L
            var peakPssKb = Debug.getPss()
            var peakHeapBytes = usedJavaHeap()
            var maxBattery = firstBattery
            var lastSampleAt = SystemClock.elapsedRealtime()
            val decodingStart = SystemClock.elapsedRealtime()
            val summary = media.decodePcm(uri, maxOutputBytes = null) { chunk ->
                check(chunk.bytes.isNotEmpty()) { "Empty PCM chunk encountered" }
                if (firstPtsUs < 0) firstPtsUs = chunk.presentationTimeUs
                // Decoders can repeat PTS for adjacent output buffers, but may not run backwards.
                check(chunk.presentationTimeUs >= lastPtsUs) { "PCM timestamp moved backwards" }
                lastPtsUs = chunk.presentationTimeUs
                chunks++
                val now = SystemClock.elapsedRealtime()
                if (now - lastSampleAt >= 2_000L) {
                    val t = batteryC(context)
                    maxBattery = maxOf(maxBattery, t)
                    peakPssKb = maxOf(peakPssKb, Debug.getPss())
                    peakHeapBytes = maxOf(peakHeapBytes, usedJavaHeap())
                    check(t < 43.0) { "Battery-temperature stop at $t C (not CPU die)" }
                    check(now - started < 1_200_000L) { "Media diagnostic exceeded 20-minute wall clock" }
                    lastSampleAt = now
                }
            }
            output.put("decode_wall_ms", SystemClock.elapsedRealtime() - decodingStart)
            output.put("chunks", chunks)
            output.put("pcm_bytes_decoded", summary.bytesDecoded)
            output.put("pcm_first_pts_us", firstPtsUs)
            output.put("pcm_last_pts_us", lastPtsUs)
            output.put("pcm_sample_rate", summary.sampleRate)
            output.put("pcm_channel_count", summary.channelCount)
            output.put("pcm_sample_format", summary.sampleFormat.name)
            output.put("pcm_truncated", summary.truncated)
            val lastBattery = batteryC(context)
            maxBattery = maxOf(maxBattery, lastBattery)
            peakPssKb = maxOf(peakPssKb, Debug.getPss())
            peakHeapBytes = maxOf(peakHeapBytes, usedJavaHeap())
            output.put("battery_end_c", lastBattery)
            output.put("battery_peak_c", maxBattery)
            output.put("peak_process_pss_kb_sampled", peakPssKb)
            output.put("peak_java_heap_used_bytes_sampled", peakHeapBytes)
            check(maxBattery < 43.0) { "Battery-temperature stop at end of decode" }
            check(summary.bytesDecoded > 0 && chunks > 0 && !summary.truncated) {
                "PCM decode did not produce a complete stream"
            }
            check(lastPtsUs >= descriptor.durationUs - 5_000_000L) {
                "Audio ended >5s before video duration; cannot claim complete ten-minute media"
            }
            val after = media.inspect(uri)
            output.put("source_sha256_after", after.fingerprintSha256)
            output.put("source_unchanged", after.fingerprintSha256 == descriptor.fingerprintSha256)
            check(descriptor.fingerprintSha256 == after.fingerprintSha256) {
                "Source file content changed during media diagnostic"
            }
            output.put("status", "MEDIA_STAGE_PASS_NOT_FULL_E2E")
        } catch (error: Throwable) {
            failure = error
            output.put("error_type", error.javaClass.simpleName)
            output.put("error_message", (error.message ?: "unspecified failure").take(350))
        } finally {
            output.put("total_wall_ms", SystemClock.elapsedRealtime() - started)
            output.put("memory_is_sampled_not_true_peak", true)
            output.put("temperature_is_battery_not_cpu_die", true)
            output.put("offline_connection_verified_by", "Windows ADB harness preflight; not verified in-test")
            val partial = File(dir, "$name.partial")
            partial.writeText(output.toString(2) + "\n", Charsets.UTF_8)
            check(partial.renameTo(report)) { "Cannot finalize benchmark evidence JSON" }
            Log.i("SubLokaT10Video", "T10_VIDEO_REPORT_PATH=${report.absolutePath}")
            Log.i("SubLokaT10Video", "T10_VIDEO_STATUS=${output.getString("status")}")
        }
        failure?.let { throw AssertionError("T10 media diagnostic failed: ${it.message}", it) }
        assertEquals("MEDIA_STAGE_PASS_NOT_FULL_E2E", output.getString("status"))
    }

    private fun batteryC(context: android.content.Context): Double {
        val state = requireNotNull(
            context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        ) { "Battery-temperature sensor unavailable" }
        val tenths = state.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1)
        check(tenths in 100..600) { "Unreliable battery temperature reading: $tenths" }
        return tenths / 10.0
    }

    private fun usedJavaHeap(): Long =
        Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()

    private fun videoMime(context: android.content.Context, uriText: String): String {
        val extractor = MediaExtractor()
        try {
            extractor.setDataSource(context, Uri.parse(uriText), null)
            for (index in 0 until extractor.trackCount) {
                val mime = extractor.getTrackFormat(index).getString(MediaFormat.KEY_MIME).orEmpty()
                if (mime.startsWith("video/")) return mime
            }
            error("Missing video track MIME")
        } finally {
            extractor.release()
        }
    }
}

package app.subloka

import android.Manifest
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.lifecycle.Lifecycle
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import app.subloka.core.database.SubLokaDatabaseFactory
import app.subloka.core.domain.CaptionStyle
import app.subloka.demo.DemoData
import java.util.UUID
import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Invoked only by the modern-API runner after revocation, before instrumentation starts. */
@RunWith(AndroidJUnit4::class)
class NotificationDeniedServiceTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()

    private class Worker {
        val entered = CompletableDeferred<Unit>()
        val finish = CompletableDeferred<Unit>()
        @Volatile var saved: String? = null
        @Volatile var cancelled = false
        suspend fun run() {
            entered.complete(Unit)
            finish.await()
            saved = "Synthetic task completed"
        }
    }

    @Test fun asrCompletesAndCancelsWithoutNotificationPermission() = runBlocking { exercise("asr") }
    @Test fun translationCompletesAndCancelsWithoutNotificationPermission() = runBlocking { exercise("translation") }
    @Test fun renderCompletesAndCancelsWithoutNotificationPermission() = runBlocking { exercise("render") }

    private suspend fun exercise(kind: String) {
        assertTrue("Modern runner must use API33+", Build.VERSION.SDK_INT >= 33)
        assertEquals(PackageManager.PERMISSION_DENIED, context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS))
        assertFalse(context.getSystemService(NotificationManager::class.java).areNotificationsEnabled())
        for (cancel in listOf(false, true)) {
            val worker = Worker()
            val oldAsr = AsrForegroundService.taskFactory
            val oldTranslation = TranslationForegroundService.taskFactory
            val oldRender = RenderForegroundService.taskFactory
            var scenario: ActivityScenario<MainActivity>? = null
            fun running() = when (kind) {
                "asr" -> AsrSession.state.value?.running == true
                "translation" -> TranslationSession.state.value?.running == true
                else -> RenderSession.state.value?.running == true
            }
            fun stop() {
                when (kind) {
                    "asr" -> AsrForegroundService.cancel(context)
                    "translation" -> TranslationForegroundService.cancel(context)
                    else -> RenderForegroundService.cancel(context)
                }
            }
            try {
                AsrForegroundService.taskFactory = { object : AsrTask {
                    override val savedMessage get() = worker.saved
                    override suspend fun run(request: AsrRequest, onStage: (String) -> Unit) { onStage("Fixture"); worker.run() }
                    override fun cancel() { worker.cancelled = true }
                } }
                TranslationForegroundService.taskFactory = { object : TranslationTask {
                    override val savedMessage get() = worker.saved
                    override val completed get() = worker.saved != null
                    override val error: String? = null
                    override suspend fun run(request: TranslationRequest, onStage: (String) -> Unit) { onStage("Fixture"); worker.run() }
                    override fun cancel() { worker.cancelled = true }
                } }
                RenderForegroundService.taskFactory = { object : RenderTask {
                    override val savedMessage get() = worker.saved
                    override val output: java.io.File? = null
                    override suspend fun run(request: RenderRequest, onStage: (String) -> Unit) { onStage("Fixture"); worker.run() }
                    override fun cancel() { worker.cancelled = true }
                } }
                val project = DemoData.persistentProject.copy(id = UUID.randomUUID().toString())
                withContext(Dispatchers.IO) { SubLokaDatabaseFactory.create(context).use { it.projectRepository.upsert(project) } }
                scenario = ActivityScenario.launch(MainActivity::class.java)
                scenario.onActivity {
                    when (kind) {
                        "asr" -> AsrForegroundService.start(it, requireNotNull(AsrSession.reserve(project, true)))
                        "translation" -> TranslationForegroundService.start(it, requireNotNull(
                            TranslationSession.reserve(project, TranslationUiState(), "fixture", null, false, false)))
                        else -> RenderForegroundService.start(it, requireNotNull(RenderSession.reserve(project, emptyList(), CaptionStyle())))
                    }
                }
                withTimeout(15_000) { worker.entered.await() }
                scenario.moveToState(Lifecycle.State.CREATED)
                assertTrue(running())
                if (cancel) {
                    scenario.moveToState(Lifecycle.State.RESUMED)
                    scenario.onActivity { stop() }
                } else worker.finish.complete(Unit)
                withTimeout(15_000) { while (running()) delay(25) }
                val completed = when (kind) {
                    "asr" -> AsrSession.state.value!!.completed
                    "translation" -> TranslationSession.state.value!!.completed
                    else -> RenderSession.state.value!!.completed
                }
                val error = when (kind) {
                    "asr" -> AsrSession.state.value!!.error
                    "translation" -> TranslationSession.state.value!!.error
                    else -> RenderSession.state.value!!.error
                }
                assertEquals(!cancel, completed)
                assertEquals(cancel, worker.cancelled)
                assertNull(error)
                assertEquals(PackageManager.PERMISSION_DENIED, context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS))
            } finally {
                worker.finish.complete(Unit)
                withContext(Dispatchers.Main) { stop() }
                withTimeout(15_000) { while (running()) delay(25) }
                scenario?.close()
                AsrForegroundService.taskFactory = oldAsr
                TranslationForegroundService.taskFactory = oldTranslation
                RenderForegroundService.taskFactory = oldRender
            }
        }
    }
}

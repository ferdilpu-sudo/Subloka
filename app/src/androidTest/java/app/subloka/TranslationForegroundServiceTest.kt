package app.subloka

import android.app.NotificationManager
import android.content.Context
import androidx.lifecycle.Lifecycle
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import app.subloka.core.database.SubLokaDatabaseFactory
import app.subloka.demo.DemoData
import java.util.UUID
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.first
import org.junit.After
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TranslationForegroundServiceTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val manager get() = context.getSystemService(NotificationManager::class.java)
    private var scenario: ActivityScenario<MainActivity>? = null
    private val originalFactory = TranslationForegroundService.taskFactory

    private class ControlledTask(val delayCancellation: Boolean = false) : TranslationTask {
        val entered = CompletableDeferred<Unit>()
        val finish = CompletableDeferred<Unit>()
        val releaseCancellation = CompletableDeferred<Unit>()
        @Volatile var cancelled = false
        @Volatile override var savedMessage: String? = null
        override val completed get() = savedMessage != null
        override val error: String? = null
        override suspend fun run(request: TranslationRequest, onStage: (String) -> Unit) {
            onStage("Terjemahan uji sedang berjalan")
            entered.complete(Unit)
            try { finish.await() }
            catch (cancel: CancellationException) {
                if (delayCancellation) withContext(NonCancellable) {
                    onStage("Late progress must not replace stopping")
                    releaseCancellation.await()
                }
                throw cancel
            }
            savedMessage = "Caption uji tersimpan"
        }
        override fun cancel() { cancelled = true }
    }

    private suspend fun start(worker: ControlledTask): TranslationRequest {
        TranslationForegroundService.taskFactory = { worker }
        val project = DemoData.persistentProject.copy(id = UUID.randomUUID().toString(), title = "Service lifecycle fixture")
        withContext(Dispatchers.IO) { SubLokaDatabaseFactory.create(context).use { it.projectRepository.upsert(project) } }
        scenario = ActivityScenario.launch(MainActivity::class.java)
        lateinit var request: TranslationRequest
        scenario!!.onActivity {
            request = requireNotNull(TranslationSession.reserve(project, TranslationUiState(), "fixture", null, false, false))
            TranslationForegroundService.start(it, request)
        }
        withTimeout(15_000) { worker.entered.await() }
        return request
    }

    @After fun cleanup() = runBlocking {
        TranslationForegroundService.cancel(context)
        withTimeout(15_000) {
            while (TranslationSession.state.value?.running == true) delay(50)
        }
        scenario?.close()
        TranslationForegroundService.taskFactory = originalFactory
    }

    @Test fun continuesAfterActivityStopAndDestructionAndReattaches() = runBlocking {
        val worker = ControlledTask()
        val request = start(worker)
        val source = DemoData.segments.first().copy(id = UUID.randomUUID().toString())
        val checkpoint = withContext(Dispatchers.IO) {
            SubLokaDatabaseFactory.create(context).use {
                it.captionRepository.replaceAll(request.project.id, listOf(source))
                it.translationRecovery.begin(request.project.id, "fixture", listOf(source))
            }
        }
        scenario!!.moveToState(Lifecycle.State.CREATED)
        assertTrue(TranslationSession.state.value!!.running)
        assertFalse(worker.cancelled)
        scenario!!.close(); scenario = null
        assertTrue(TranslationSession.state.value!!.running)
        assertFalse(worker.cancelled)
        assertTrue(manager.activeNotifications.any { it.id == TranslationForegroundService.NOTIFICATION })
        scenario = ActivityScenario.launch(MainActivity::class.java)
        val loaded = CompletableDeferred<Unit>()
        scenario!!.onActivity {
            androidx.lifecycle.ViewModelProvider(it)[SubLokaViewModel::class.java].flush { loaded.complete(Unit) }
        }
        withTimeout(15_000) { loaded.await() }
        assertTrue(TranslationSession.state.value!!.running)
        // Recreated ViewModel must not mark the still-active Room checkpoint interrupted.
        withContext(Dispatchers.IO) {
            SubLokaDatabaseFactory.create(context).use {
                assertTrue(it.translationRecovery.publish(checkpoint.id, source, "Still publishing after recreation"))
                assertNull(it.translationRecovery.pending(request.project.id))
            }
        }
        worker.finish.complete(Unit)
        val terminal = withTimeout(15_000) { TranslationSession.state.filterNotNull().first { it.request.id == request.id && !it.running } }
        assertTrue(terminal.completed)
        assertNull(terminal.error)
        withTimeout(5_000) { while (manager.activeNotifications.any { it.id == TranslationForegroundService.NOTIFICATION }) delay(50) }
    }

    @Test fun notificationCancelStopsWorkerWithoutFalseSuccess() = runBlocking {
        val worker = ControlledTask()
        val request = start(worker)
        scenario!!.moveToState(Lifecycle.State.CREATED)
        val notification = manager.activeNotifications.first { it.id == TranslationForegroundService.NOTIFICATION }.notification
        notification.actions.first().actionIntent.send()
        val terminal = withTimeout(15_000) { TranslationSession.state.filterNotNull().first { it.request.id == request.id && !it.running } }
        assertTrue(worker.cancelled)
        assertFalse(terminal.completed)
        assertNull(worker.savedMessage)
    }

    @Test fun cancellationAcknowledgedWhileWorkerIsStillStopping() = runBlocking {
        val worker = ControlledTask(delayCancellation = true)
        val request = start(worker)
        try {
            manager.activeNotifications.first { it.id == TranslationForegroundService.NOTIFICATION }
                .notification.actions.first().actionIntent.send()
            val stopping = withTimeout(5_000) {
                TranslationSession.state.filterNotNull().first { it.request.id == request.id && it.stopping }
            }
            assertTrue(stopping.running)
            assertTrue(stopping.stage.startsWith("Menghentikan"))
            assertNull(TranslationSession.reserve(request.project, TranslationUiState(), "fixture", null, false, false))
            withTimeout(5_000) { while (!worker.cancelled) delay(25) }
            assertTrue(TranslationSession.state.value!!.stage.startsWith("Menghentikan"))
        } finally { worker.releaseCancellation.complete(Unit) }
        val terminal = withTimeout(15_000) {
            TranslationSession.state.filterNotNull().first { it.request.id == request.id && !it.running }
        }
        assertFalse(terminal.completed)
        assertNull(terminal.error)
    }

    @Test fun cancellationAfterCommitStillReportsSavedResult() = runBlocking {
        val worker = ControlledTask()
        val request = start(worker)
        worker.savedMessage = "Caption sudah disimpan sebelum pembatalan"
        manager.activeNotifications.first { it.id == TranslationForegroundService.NOTIFICATION }.notification.actions.first().actionIntent.send()
        val terminal = withTimeout(15_000) { TranslationSession.state.filterNotNull().first { it.request.id == request.id && !it.running } }
        assertTrue(terminal.completed)
        assertEquals(worker.savedMessage, terminal.stage)
        assertNull(terminal.error)
    }
}

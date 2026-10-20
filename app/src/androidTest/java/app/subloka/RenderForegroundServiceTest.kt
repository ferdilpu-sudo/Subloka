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
class RenderForegroundServiceTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val manager get() = context.getSystemService(NotificationManager::class.java)
    private var scenario: ActivityScenario<MainActivity>? = null
    private val originalFactory = RenderForegroundService.taskFactory

    private class ControlledTask(val delayCancellation: Boolean = false) : RenderTask {
        val entered = CompletableDeferred<Unit>()
        val finish = CompletableDeferred<Unit>()
        val releaseCancellation = CompletableDeferred<Unit>()
        @Volatile var cancelled = false
        @Volatile override var savedMessage: String? = null
        override var output: java.io.File? = null
        override suspend fun run(request: RenderRequest, onStage: (String) -> Unit) {
            onStage("Render uji sedang berjalan")
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

    private suspend fun start(worker: ControlledTask): RenderRequest {
        RenderForegroundService.taskFactory = { worker }
        val project = DemoData.persistentProject.copy(id = UUID.randomUUID().toString(), title = "Service lifecycle fixture")
        withContext(Dispatchers.IO) { SubLokaDatabaseFactory.create(context).use { it.projectRepository.upsert(project) } }
        scenario = ActivityScenario.launch(MainActivity::class.java)
        lateinit var request: RenderRequest
        scenario!!.onActivity {
            request = requireNotNull(RenderSession.reserve(project, emptyList(), app.subloka.core.domain.CaptionStyle()))
            RenderForegroundService.start(it, request)
        }
        withTimeout(15_000) {
            while (!worker.entered.isCompleted) {
                val state = RenderSession.state.value
                check(state?.running == true) { "Service stopped before worker entry: $state" }
                delay(25)
            }
            worker.entered.await()
        }
        return request
    }

    @After fun cleanup() = runBlocking {
        RenderForegroundService.cancel(context)
        withTimeout(15_000) {
            while (RenderSession.state.value?.running == true) delay(50)
        }
        scenario?.close()
        RenderForegroundService.taskFactory = originalFactory
        manager.cancel(RenderForegroundService.NOTIFICATION)
    }

    @Test fun continuesAfterActivityStopAndDestructionAndReattaches() = runBlocking {
        val worker = ControlledTask()
        val request = start(worker)
        scenario!!.moveToState(Lifecycle.State.CREATED)
        assertTrue(RenderSession.state.value!!.running)
        assertFalse(worker.cancelled)
        scenario!!.close(); scenario = null
        assertTrue(RenderSession.state.value!!.running)
        assertFalse(worker.cancelled)
        assertTrue(manager.activeNotifications.any { it.id == RenderForegroundService.NOTIFICATION })
        scenario = ActivityScenario.launch(MainActivity::class.java)
        assertTrue(RenderSession.state.value!!.running)
        worker.finish.complete(Unit)
        val terminal = withTimeout(15_000) { RenderSession.state.filterNotNull().first { it.request.id == request.id && !it.running } }
        assertTrue(terminal.completed)
        assertNull(terminal.error)
        assertTrue(manager.activeNotifications.any { it.id == RenderForegroundService.NOTIFICATION })
    }

    @Test fun notificationCancelStopsWorkerWithoutFalseSuccess() = runBlocking {
        val worker = ControlledTask()
        val request = start(worker)
        scenario!!.moveToState(Lifecycle.State.CREATED)
        val notification = manager.activeNotifications.first { it.id == RenderForegroundService.NOTIFICATION }.notification
        notification.actions.first().actionIntent.send()
        val terminal = withTimeout(15_000) { RenderSession.state.filterNotNull().first { it.request.id == request.id && !it.running } }
        assertTrue(worker.cancelled)
        assertFalse(terminal.completed)
        assertNull(worker.savedMessage)
    }

    @Test fun cancellationAcknowledgedWhileWorkerIsStillStopping() = runBlocking {
        val worker = ControlledTask(delayCancellation = true)
        val request = start(worker)
        try {
            manager.activeNotifications.first { it.id == RenderForegroundService.NOTIFICATION }
                .notification.actions.first().actionIntent.send()
            val stopping = withTimeout(5_000) {
                RenderSession.state.filterNotNull().first { it.request.id == request.id && it.stopping }
            }
            assertTrue(stopping.running)
            assertTrue(stopping.stage.startsWith("Menghentikan"))
            assertNull(RenderSession.reserve(request.project, emptyList(), app.subloka.core.domain.CaptionStyle()))
            withTimeout(5_000) { while (!worker.cancelled) delay(25) }
            assertTrue(RenderSession.state.value!!.stage.startsWith("Menghentikan"))
        } finally { worker.releaseCancellation.complete(Unit) }
        val terminal = withTimeout(15_000) {
            RenderSession.state.filterNotNull().first { it.request.id == request.id && !it.running }
        }
        assertFalse(terminal.completed)
        assertNull(terminal.error)
    }

    @Test fun readyOutputSurvivesActivityRecreation() = runBlocking {
        val worker = ControlledTask()
        val request = start(worker)
        val directory = java.io.File(context.filesDir, "mp4-staging").apply { mkdirs() }
        val file = java.io.File(directory, "test-${request.id}.mp4").apply { writeBytes(byteArrayOf(1, 2, 3)) }
        try {
            // Synthetic output tests ownership only, not MP4 codec validity.
            worker.output = file
            worker.finish.complete(Unit)
            withTimeout(15_000) { RenderSession.state.filterNotNull().first { !it.running } }
            scenario!!.close(); scenario = ActivityScenario.launch(MainActivity::class.java)
            lateinit var viewModel: VideoExportViewModel
            scenario!!.onActivity { viewModel = androidx.lifecycle.ViewModelProvider(it)[VideoExportViewModel::class.java] }
            withTimeout(15_000) { viewModel.state.first { it.ready } }
            assertTrue(file.isFile)
            assertNotNull(viewModel.select())
            viewModel.save(null)
            assertTrue(viewModel.state.value.ready)
        } finally { file.delete() }
    }

    @Test fun cancellationAfterCommitStillReportsSavedResult() = runBlocking {
        val worker = ControlledTask()
        val request = start(worker)
        worker.savedMessage = "Caption sudah disimpan sebelum pembatalan"
        manager.activeNotifications.first { it.id == RenderForegroundService.NOTIFICATION }.notification.actions.first().actionIntent.send()
        val terminal = withTimeout(15_000) { RenderSession.state.filterNotNull().first { it.request.id == request.id && !it.running } }
        assertTrue(terminal.completed)
        assertEquals(worker.savedMessage, terminal.stage)
        assertNull(terminal.error)
    }
}

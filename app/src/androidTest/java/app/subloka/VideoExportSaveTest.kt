package app.subloka

import android.app.Application
import android.net.Uri
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import app.subloka.core.domain.CaptionStyle
import app.subloka.demo.DemoData
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.IOException
import java.io.OutputStream
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.first
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Exercises real ViewModel copy/cleanup/retry with synthetic bytes, not codec validity. */
@RunWith(AndroidJUnit4::class)
class VideoExportSaveTest {
    private val application = ApplicationProvider.getApplicationContext<Application>()
    private val uri = Uri.parse("content://subloka-test/output.mp4")
    private val bytes = ByteArray(150_000) { (it % 251).toByte() }

    private class Destination(
        val mode: String = "ok",
        val deletion: String = "ok",
        val entered: CountDownLatch? = null,
        val release: CountDownLatch? = null,
    ) : Mp4Destination {
        val data = ByteArrayOutputStream()
        @Volatile var closed = false
        @Volatile var deletes = 0
        @Volatile var writes = 0

        override fun open(uri: Uri): OutputStream? {
            if (mode == "open") throw IOException("open denied")
            if (mode == "null") return null
            return object : OutputStream() {
                override fun write(value: Int) { write(byteArrayOf(value.toByte()), 0, 1) }
                override fun write(buffer: ByteArray, offset: Int, count: Int) {
                    writes++
                    if (mode == "write" && writes == 2) throw IOException("disk full")
                    data.write(buffer, offset, count)
                    if (mode == "blocked-write" && writes == 1) {
                        entered!!.countDown()
                        check(release!!.await(10, TimeUnit.SECONDS))
                    }
                }
                override fun flush() { if (mode == "flush") throw IOException("flush failed") }
                override fun close() {
                    closed = true
                    if (mode == "blocked-close") {
                        entered!!.countDown()
                        check(release!!.await(10, TimeUnit.SECONDS))
                    }
                    if (mode == "close") throw IOException("close failed")
                }
            }
        }
        override fun delete(uri: Uri): Boolean {
            deletes++
            if (deletion == "throw") throw IOException("delete denied")
            if (deletion == "false") return false
            data.reset()
            return true
        }
    }

    private suspend fun fixture(block: suspend (VideoExportViewModel, ViewModelStore, File) -> Unit) {
        val file = File.createTempFile("save-fixture", ".mp4", application.cacheDir)
        file.writeBytes(bytes)
        val store = ViewModelStore()
        lateinit var vm: VideoExportViewModel
        try {
            withContext(Dispatchers.Main) {
                RenderSession.clear()
                val request = requireNotNull(RenderSession.reserve(
                    DemoData.persistentProject, emptyList(), CaptionStyle()))
                RenderSession.finish(request.id, "Ready fixture", true, output = file)
                vm = VideoExportViewModel(application)
                store.put("save-test", vm)
            }
            withTimeout(10_000) { vm.state.first { it.ready && !it.busy } }
            block(vm, store, file)
        } finally {
            withContext(Dispatchers.Main) { store.clear(); RenderSession.clear() }
            file.delete()
        }
    }

    private suspend fun save(vm: VideoExportViewModel, destination: Destination) {
        withContext(Dispatchers.Main) {
            vm.destination = destination
            assertNotNull(vm.select())
            vm.save(uri)
        }
    }

    private suspend fun terminal(vm: VideoExportViewModel, prefix: String) =
        withTimeout(10_000) { vm.state.first { !it.busy && it.message?.startsWith(prefix) == true } }

    @Test fun providerFailuresRetainStagingAndAllowByteExactRetry() = runBlocking {
        for (mode in listOf("null", "open", "write", "flush", "close")) {
            fixture { vm, _, file ->
                val failed = Destination(mode)
                save(vm, failed)
                val state = terminal(vm, "Simpan gagal")
                assertTrue(state.ready)
                assertFalse(state.pending)
                assertEquals(1, failed.deletes)
                if (mode !in listOf("null", "open")) assertTrue(failed.closed)
                assertEquals(0, failed.data.size())
                assertArrayEquals(bytes, file.readBytes())

                val retry = Destination()
                save(vm, retry)
                terminal(vm, "MP4 tersimpan")
                assertTrue(retry.closed)
                assertEquals(0, retry.deletes)
                assertArrayEquals(bytes, retry.data.toByteArray())
                assertArrayEquals(bytes, file.readBytes())
            }
        }
    }

    @Test fun failedCleanupWarnsWithoutFalseSuccessAndKeepsRetryAvailable() = runBlocking {
        for (deletion in listOf("false", "throw")) {
            fixture { vm, _, file ->
                val failed = Destination("write", deletion)
                save(vm, failed)
                val state = terminal(vm, "Simpan gagal")
                assertTrue(state.message!!.contains("File parsial mungkin tertinggal"))
                assertTrue(failed.data.size() > 0)
                assertTrue(state.ready)
                assertArrayEquals(bytes, file.readBytes())
                save(vm, Destination())
                terminal(vm, "MP4 tersimpan")
            }
        }
    }

    @Test fun successIsNotPublishedUntilDestinationCloseCompletes() = runBlocking {
        fixture { vm, _, _ ->
            val entered = CountDownLatch(1)
            val release = CountDownLatch(1)
            try {
                save(vm, Destination("blocked-close", entered = entered, release = release))
                assertTrue(withContext(Dispatchers.IO) { entered.await(5, TimeUnit.SECONDS) })
                assertTrue(vm.state.value.busy)
                assertFalse(vm.state.value.message.orEmpty().startsWith("MP4 tersimpan"))
            } finally { release.countDown() }
            terminal(vm, "MP4 tersimpan")
        }
    }

    @Test fun viewModelDestructionCancelsCopyAndCleansPartialDestination() = runBlocking {
        fixture { vm, store, file ->
            val entered = CountDownLatch(1)
            val release = CountDownLatch(1)
            val target = Destination("blocked-write", entered = entered, release = release)
            try {
                save(vm, target)
                assertTrue(withContext(Dispatchers.IO) { entered.await(5, TimeUnit.SECONDS) })
                withContext(Dispatchers.Main) { store.clear() }
            } finally { release.countDown() }
            terminal(vm, "Simpan gagal")
            assertEquals(1, target.writes)
            assertTrue(target.closed)
            assertEquals(1, target.deletes)
            assertEquals(0, target.data.size())
            assertArrayEquals(bytes, file.readBytes())
            assertTrue(RenderSession.state.value!!.completed)
        }
    }
}

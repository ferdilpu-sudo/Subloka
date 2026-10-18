package app.subloka

import android.Manifest
import android.content.pm.PackageManager
import android.app.*
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import kotlinx.coroutines.*

/** Owns ASR independently of the Activity; explicit stop and process death never restart it. */
class AsrForegroundService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var operation: Job? = null
    private var task: AsrTask? = null
    private var requestId: String? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var stopMessage = "Transkripsi dihentikan. Jalankan lagi dari awal; caption lama tetap tersimpan."

    override fun onBind(intent: Intent?): IBinder? = null
    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL, "Transkripsi", NotificationManager.IMPORTANCE_LOW))
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val id = intent?.getStringExtra(JOB)
        if (intent?.action == CANCEL) {
            if (id != null && id == requestId) {
                AsrSession.stopping(id)
                updateNotification(id, AsrSession.state.value!!.stage)
                // Native cleanup can hold the pipeline lock. Never wait for it on Main.
                val worker = task
                val running = operation
                scope.launch(Dispatchers.IO) {
                    try { worker?.cancel() } finally { running?.cancel() }
                }
            }
            else if (operation == null) {
                // A cancel may reach the service before its start command.
                if (id != null) AsrSession.finish(id, stopMessage, false)
                stopSelf(startId)
            }
            return START_NOT_STICKY
        }
        if (operation?.isCompleted == false) return START_NOT_STICKY
        val request = AsrSession.state.value?.takeIf { it.running && it.request.id == id }?.request
        // A stale start still needs foreground promotion to satisfy startForegroundService's deadline.
        try {
            ServiceCompat.startForeground(this, NOTIFICATION, notification(id ?: "", "Memulai transkripsi…"),
                if (Build.VERSION.SDK_INT >= 35) ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROCESSING
                else if (Build.VERSION.SDK_INT >= 29) ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC else 0)
        } catch (_: Exception) {
            if (id != null) AsrSession.finish(id, "", false, "Layanan transkripsi tidak dapat dimulai. Buka aplikasi dan coba lagi.")
            stopSelf(startId)
            return START_NOT_STICKY
        }
        if (request == null) { stopForeground(STOP_FOREGROUND_REMOVE); stopSelf(startId); return START_NOT_STICKY }
        requestId = request.id
        operation = scope.launch {
            val watchdog = scope.launch {
                delay(MAX_RUNTIME)
                stopMessage = "Batas waktu transkripsi tercapai. Coba video yang lebih pendek."
                task?.cancel()
                operation?.cancel()
            }
            var error: String? = null
            var message = stopMessage
            try {
                wakeLock = getSystemService(PowerManager::class.java).newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK, "SubLoka:transcription").apply { acquire(MAX_RUNTIME + 60_000L) }
                val worker = taskFactory(applicationContext)
                task = worker
                withTimeout(MAX_RUNTIME) {
                    worker.run(request) { stage ->
                        AsrSession.stage(request.id, stage)
                        scope.launch { updateNotification(request.id, stage) }
                    }
                }
            } catch (_: TimeoutCancellationException) {
                task?.cancel()
                message = "Batas waktu transkripsi tercapai. Coba video yang lebih pendek."
            } catch (_: CancellationException) { message = stopMessage }
            catch (failure: Exception) {
                if (AsrSession.state.value?.let { it.request.id == request.id && it.stopping } == true) {
                    message = stopMessage
                } else error = failure.message ?: "Transkripsi gagal. Coba lagi."
            }
            catch (_: LinkageError) { error = "Engine tidak tersedia untuk perangkat ini." }
            finally {
                watchdog.cancel()
                val saved = task?.savedMessage
                task = null
                wakeLock?.let { if (it.isHeld) it.release() }; wakeLock = null
                AsrSession.finish(request.id, saved ?: message, saved != null, if (saved != null) null else error)
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
        return START_NOT_STICKY
    }
    private fun updateNotification(id: String, stage: String) {
        if (AsrSession.state.value?.let { it.running && it.request.id == id } != true) return
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION, notification(id, AsrSession.state.value?.takeIf { it.request.id == id && it.stopping }?.stage ?: stage))
    }
    private fun notification(id: String, stage: String): Notification {
        val open = PendingIntent.getActivity(this, 0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val stop = PendingIntent.getService(this, id.hashCode(),
            Intent(this, AsrForegroundService::class.java).setAction(CANCEL).putExtra(JOB, id),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, CHANNEL).setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("SubLoka • Transkripsi").setContentText(stage).setContentIntent(open)
            .setOngoing(true).setOnlyAlertOnce(true).setProgress(0, 0, true)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Hentikan", stop).build()
    }
    override fun onTimeout(startId: Int, fgsType: Int) {
        stopMessage = "Batas layanan Android tercapai. Transkripsi dihentikan."
        task?.cancel(); operation?.cancel()
        stopForeground(STOP_FOREGROUND_REMOVE); stopSelf()
    }
    override fun onDestroy() {
        task?.cancel(); scope.cancel()
        wakeLock?.let { if (it.isHeld) it.release() }; wakeLock = null
        super.onDestroy()
    }
    companion object {
        private const val CHANNEL = "asr-processing"
        internal const val NOTIFICATION = 4001
        private const val JOB = "job"
        private const val CANCEL = "app.subloka.CANCEL_ASR"
        private const val MAX_RUNTIME = 6 * 60 * 60 * 1000L
        internal var taskFactory: (Context) -> AsrTask = ::LocalAsrTask
        internal fun start(context: Context, request: AsrRequest) {
            try {
                context.startForegroundService(Intent(context, AsrForegroundService::class.java).putExtra(JOB, request.id))
            } catch (_: Exception) {
                AsrSession.finish(request.id, "", false, "Buka aplikasi lalu mulai transkripsi kembali.")
            }
        }
        internal fun cancel(context: Context) {
            val request = AsrSession.state.value?.takeIf { it.running }?.request ?: return
            context.startService(Intent(context, AsrForegroundService::class.java).setAction(CANCEL).putExtra(JOB, request.id))
        }
    }
}

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

/** Owns TRANSLATION independently of the Activity; explicit stop and process death never restart it. */
class TranslationForegroundService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var operation: Job? = null
    private var task: TranslationTask? = null
    private var requestId: String? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var stopMessage = "Terjemahan dihentikan. Pilih Lanjutkan sisa terjemahan; hasil tersimpan tetap tersedia."

    override fun onBind(intent: Intent?): IBinder? = null
    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL, "Terjemahan", NotificationManager.IMPORTANCE_LOW))
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val id = intent?.getStringExtra(JOB)
        if (intent?.action == CANCEL) {
            if (id != null && id == requestId) {
                TranslationSession.stopping(id)
                updateNotification(id, TranslationSession.state.value!!.stage)
                // Native cleanup can hold the pipeline lock. Never wait for it on Main.
                val worker = task
                val running = operation
                scope.launch(Dispatchers.IO) {
                    try { worker?.cancel() } finally { running?.cancel() }
                }
            }
            else if (operation == null) {
                // A cancel may reach the service before its start command.
                if (id != null) TranslationSession.finish(id, stopMessage, false)
                stopSelf(startId)
            }
            return START_NOT_STICKY
        }
        if (operation?.isCompleted == false) return START_NOT_STICKY
        val request = TranslationSession.state.value?.takeIf { it.running && it.request.id == id }?.request
        // A stale start still needs foreground promotion to satisfy startForegroundService's deadline.
        try {
            ServiceCompat.startForeground(this, NOTIFICATION, notification(id ?: "", "Memulai terjemahan…"),
                if (Build.VERSION.SDK_INT >= 35) ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROCESSING
                else if (Build.VERSION.SDK_INT >= 29) ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC else 0)
        } catch (_: Exception) {
            if (id != null) TranslationSession.finish(id, "", false, "Layanan terjemahan tidak dapat dimulai. Buka aplikasi dan coba lagi.")
            stopSelf(startId)
            return START_NOT_STICKY
        }
        if (request == null) { stopForeground(STOP_FOREGROUND_REMOVE); stopSelf(startId); return START_NOT_STICKY }
        requestId = request.id
        operation = scope.launch {
            val watchdog = scope.launch {
                delay(MAX_RUNTIME)
                stopMessage = "Batas waktu terjemahan tercapai. Coba video yang lebih pendek."
                task?.cancel()
                operation?.cancel()
            }
            var error: String? = null
            var message = stopMessage
            try {
                wakeLock = getSystemService(PowerManager::class.java).newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK, "SubLoka:translation").apply { acquire(MAX_RUNTIME + 60_000L) }
                val worker = taskFactory(applicationContext)
                task = worker
                withTimeout(MAX_RUNTIME) {
                    worker.run(request) { stage ->
                        TranslationSession.stage(request.id, stage)
                        scope.launch { updateNotification(request.id, stage) }
                    }
                }
            } catch (_: TimeoutCancellationException) {
                task?.cancel()
                message = "Batas waktu terjemahan tercapai. Coba video yang lebih pendek."
            } catch (_: CancellationException) { message = stopMessage }
            catch (failure: Exception) {
                if (TranslationSession.state.value?.let { it.request.id == request.id && it.stopping } == true) {
                    message = stopMessage
                } else error = failure.message ?: "Terjemahan gagal. Coba lagi."
            }
            catch (_: LinkageError) { error = "Engine tidak tersedia untuk perangkat ini." }
            finally {
                watchdog.cancel()
                val saved = task?.savedMessage
                val taskCompleted = task?.completed == true
                val taskError = task?.error
                task = null
                wakeLock?.let { if (it.isHeld) it.release() }; wakeLock = null
                TranslationSession.finish(request.id, saved ?: message, saved != null && taskCompleted, if (saved != null) taskError else error)
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
        return START_NOT_STICKY
    }
    private fun updateNotification(id: String, stage: String) {
        if (TranslationSession.state.value?.let { it.running && it.request.id == id } != true) return
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION, notification(id, TranslationSession.state.value?.takeIf { it.request.id == id && it.stopping }?.stage ?: stage))
    }
    private fun notification(id: String, stage: String): Notification {
        val open = PendingIntent.getActivity(this, 0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val stop = PendingIntent.getService(this, id.hashCode(),
            Intent(this, TranslationForegroundService::class.java).setAction(CANCEL).putExtra(JOB, id),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, CHANNEL).setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("SubLoka • Terjemahan").setContentText(stage).setContentIntent(open)
            .setOngoing(true).setOnlyAlertOnce(true).setProgress(0, 0, true)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Hentikan", stop).build()
    }
    override fun onTimeout(startId: Int, fgsType: Int) {
        stopMessage = "Batas layanan Android tercapai. Terjemahan dihentikan."
        task?.cancel(); operation?.cancel()
        stopForeground(STOP_FOREGROUND_REMOVE); stopSelf()
    }
    override fun onDestroy() {
        task?.cancel(); scope.cancel()
        wakeLock?.let { if (it.isHeld) it.release() }; wakeLock = null
        super.onDestroy()
    }
    companion object {
        private const val CHANNEL = "translation-processing"
        internal const val NOTIFICATION = 4002
        private const val JOB = "job"
        private const val CANCEL = "app.subloka.CANCEL_TRANSLATION"
        private const val MAX_RUNTIME = 6 * 60 * 60 * 1000L
        internal var taskFactory: (Context) -> TranslationTask = ::LocalTranslationTask
        internal fun start(context: Context, request: TranslationRequest) {
            try {
                context.startForegroundService(Intent(context, TranslationForegroundService::class.java).putExtra(JOB, request.id))
            } catch (_: Exception) {
                TranslationSession.finish(request.id, "", false, "Buka aplikasi lalu mulai terjemahan kembali.")
            }
        }
        internal fun cancel(context: Context) {
            val request = TranslationSession.state.value?.takeIf { it.running }?.request ?: return
            context.startService(Intent(context, TranslationForegroundService::class.java).setAction(CANCEL).putExtra(JOB, request.id))
        }
    }
}

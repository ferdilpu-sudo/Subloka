package app.subloka

import android.app.Notification
import android.app.NotificationManager
import kotlinx.coroutines.delay
import kotlinx.coroutines.withTimeoutOrNull

/** Worker entry and notification publication are separate asynchronous events. */
internal suspend fun NotificationManager.awaitStopAction(notificationId: Int): Notification.Action {
    check(areNotificationsEnabled()) { "Notification permission must be granted for notification-action tests" }
    return withTimeoutOrNull(15_000) {
        var action: Notification.Action? = null
        while (action == null) {
            action = activeNotifications.firstOrNull { it.id == notificationId }
                ?.notification?.actions?.firstOrNull { it.title.toString() == "Hentikan" }
            if (action == null) delay(25)
        }
        action
    } ?: throw AssertionError(
        "Notification $notificationId did not publish Hentikan within 15 seconds; active IDs=" +
            activeNotifications.joinToString { it.id.toString() },
    )
}

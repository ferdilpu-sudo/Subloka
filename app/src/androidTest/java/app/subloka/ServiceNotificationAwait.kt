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

/** Terminal session state can arrive before Android publishes its replacement notification. */
internal suspend fun NotificationManager.awaitNotificationTitle(notificationId: Int, title: String): Notification {
    check(areNotificationsEnabled()) { "Notification permission must be granted for notification tests" }
    return withTimeoutOrNull(15_000) {
        var result: Notification? = null
        while (result == null) {
            result = activeNotifications.firstOrNull { it.id == notificationId }?.notification
                ?.takeIf { it.extras.getCharSequence(Notification.EXTRA_TITLE)?.toString() == title }
            if (result == null) delay(25)
        }
        result
    } ?: throw AssertionError(
        "Notification $notificationId did not publish title '$title' within 15 seconds; active titles=" +
            activeNotifications.joinToString { "${it.id}:${it.notification.extras.getCharSequence(Notification.EXTRA_TITLE)}" },
    )
}

package app.subloka

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import app.subloka.feature.projects.ProcessingScreen
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class ProcessingStatusUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun cancelRetryAndCompletedActionsFollowActualStateAtLargeFont() {
        var busy by mutableStateOf(true)
        var stopping by mutableStateOf(false)
        var completed by mutableStateOf(false)
        var error by mutableStateOf<String?>(null)
        var cancels = 0
        var retries = 0
        var opens = 0
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                MaterialTheme {
                    Box(Modifier.size(320.dp, 400.dp)) {
                        ProcessingScreen(busy, "Tahap engine", error, completed,
                            onCancel = { cancels++; stopping = true }, onRetry = { retries++ },
                            onOpenEditor = { opens++ }, onBack = {}, stopping = stopping)
                    }
                }
            }
        }
        compose.onNodeWithText("Hentikan").assertIsDisplayed().performClick()
        compose.onNodeWithText("Menghentikan…").assertIsDisplayed().assertIsNotEnabled()
        compose.onNodeWithText("Coba lagi").assertDoesNotExist()
        compose.runOnIdle { assertEquals(1, cancels); busy = false; stopping = false; error = "Proses terputus" }
        compose.onNodeWithText("Coba lagi").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, retries); error = null; completed = true }
        compose.onNodeWithText("Buka editor").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, opens) }
    }
}

package app.subloka

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import app.subloka.core.domain.CaptionStyle
import app.subloka.feature.editor.EditorScreen
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class SourceRelinkUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun missingSourceWithNoCaptionsStillOffersRecovery() {
        var opened = 0
        compose.setContent {
            MaterialTheme {
                EditorScreen(emptyList(), CaptionStyle(), null, "Tersimpan", false, {}, {}, {}, {},
                    demoMode = false, sourceUnavailable = true, onRelink = { opened++ })
            }
        }
        compose.onNodeWithText("Tautkan ulang video").performScrollTo().performClick()
        compose.runOnIdle { assertEquals(1, opened) }
    }

    @Test fun verificationBlocksAnotherPickAndBack() {
        compose.setContent {
            MaterialTheme { RelinkVideoScreen("original.mp4", true, "Memeriksa video asli…", {}, {}) }
        }
        compose.onNodeWithText("Pilih video asli").assertIsNotEnabled()
        compose.onNodeWithText("Kembali ke editor").assertIsNotEnabled()
    }

    @Test fun rejectionExplainsRetryAndKeepsBackAvailable() {
        var picked = 0
        var backed = 0
        compose.setContent {
            MaterialTheme {
                RelinkVideoScreen("original.mp4", false, "Video berbeda dari sumber asli.",
                    { picked++ }, { backed++ })
            }
        }
        compose.onNodeWithText("Video berbeda dari sumber asli.").assertExists()
        compose.onNodeWithText("Pilih video asli").performScrollTo().performClick()
        compose.onNodeWithText("Kembali ke editor").performScrollTo().performClick()
        compose.runOnIdle { assertEquals(1, picked); assertEquals(1, backed) }
    }
}

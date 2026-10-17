package app.subloka

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import app.subloka.feature.projects.TranslationSetupScreen
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class TranslationRecoveryUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun pendingReplacementOffersResumeAndRequiresExplicitDiscard() {
        var resumed = 0
        var discarded = 0
        compose.setContent {
            MaterialTheme {
                TranslationSetupScreen(ready = true, busy = false, stage = "", error = null,
                    recoveryCount = 2, hasRecovery = true, onResume = { resumed++ }, onDiscardRecovery = { discarded++ },
                    eligibleCount = 0, replaceableCount = 3, pairLabel = "Indonesia → English",
                    useGemma = true, termsAccepted = true, onModelSelected = {}, onTermsAccepted = {},
                    onImport = {}, onCheck = {}, onDownload = {}, onTranslate = {}, onCancel = {}, onBack = {})
            }
        }
        compose.onNodeWithText("Indonesia → English • 2 caption dapat diterjemahkan").assertExists()
        compose.onNodeWithText("ML Kit • ringan").assertIsNotEnabled()
        compose.onNodeWithText("Ganti juga hasil terjemahan otomatis yang sudah ada").assertDoesNotExist()
        compose.onNodeWithText("Lanjutkan sisa terjemahan").performScrollTo().performClick()
        compose.runOnIdle { assertEquals(1, resumed) }
        compose.onNodeWithText("Hapus antrean tertunda").performScrollTo().performClick()
        compose.runOnIdle { assertEquals(0, discarded) }
        compose.onNodeWithText("Hapus antrean", substring = false).performClick()
        compose.runOnIdle { assertEquals(1, discarded) }
    }
}

package app.subloka

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import app.subloka.core.designsystem.SubLokaTheme
import app.subloka.core.domain.*
import app.subloka.feature.projects.ModelSetupScreen
import app.subloka.feature.projects.NewProjectScreen
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class ProjectSetupUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun videoLanguageAndRetryRemainReachableAtLargeFont() {
        val video = MediaDescriptor("content://fixture/video", "Video percobaan.mp4", null, "a".repeat(64),
            60_000_000L, 1080, 1920, 0, listOf(AudioTrackDescriptor(0, "audio/aac", 16000, 1, null)))
        var selected by mutableStateOf<MediaDescriptor?>(null)
        var error by mutableStateOf<String?>(null)
        var language: SourceLanguage? = null
        var picks = 0
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                SubLokaTheme {
                    Box(Modifier.size(320.dp, 480.dp)) {
                        NewProjectScreen(selected, false, error, { picks++ }, {}, { language = it })
                    }
                }
            }
        }
        compose.onNodeWithText("Pilih video").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, picks); selected = video }
        compose.onNodeWithText("Vertikal", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Indonesia").performScrollTo().performClick()
        compose.onNodeWithText("Lanjut ke model").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(SourceLanguage.INDONESIA, language); error = "Proyek gagal disimpan. Coba lagi."; language = null }
        compose.onNodeWithText("Coba lanjut lagi").performClick()
        compose.runOnIdle { assertEquals(SourceLanguage.INDONESIA, language); selected = video.copy(durationUs = 601_000_000L); error = null }
        compose.onNodeWithText("Lanjut ke model").assertIsNotEnabled()
        compose.onNodeWithText("Ganti video").performScrollTo().performClick()
        compose.runOnIdle { assertEquals(2, picks) }
    }

    @Test fun modelPrimaryActionTracksReadinessAndBusyState() {
        var ready by mutableStateOf(false)
        var busy by mutableStateOf(false)
        var downloads = 0
        var starts = 0
        var cancels = 0
        compose.setContent {
            SubLokaTheme {
                Box(Modifier.size(320.dp, 480.dp)) {
                    ModelSetupScreen(ready, busy, "", null, true, {}, {}, {},
                        { downloads++ }, { starts++ }, {}, { cancels++ })
                }
            }
        }
        compose.onNodeWithText("Mulai transkripsi").assertDoesNotExist()
        compose.onNodeWithText("Unduh model yang diperlukan").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, downloads); assertEquals(0, starts); busy = true }
        compose.onNodeWithText("Turbo").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText("Batalkan").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, cancels); busy = false; ready = true }
        compose.onNodeWithText("Mulai transkripsi").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, starts); assertEquals(1, downloads) }
    }
}

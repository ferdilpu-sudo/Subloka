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
import app.subloka.demo.DemoData
import app.subloka.feature.export.ExportScreen
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class ExportFlowUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun staleTranslationDoesNotBlockOriginalOrSavingPreparedOutput() {
        var rendering by mutableStateOf(false)
        var ready by mutableStateOf(false)
        var pending by mutableStateOf(false)
        var documents by mutableStateOf(emptyList<SrtDocument>())
        var prepared: SrtExportMode? = null
        var rendered: SrtExportMode? = null
        var savedIndex: Int? = null
        var stops = 0
        var saves = 0
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                SubLokaTheme {
                    Box(Modifier.size(320.dp, 480.dp)) {
                        ExportScreen(
                            segments = DemoData.segments, sourceLanguage = SourceLanguage.ENGLISH,
                            demoMode = false, busy = rendering, pending = pending,
                            documents = documents, saved = emptySet(), message = null,
                            onPrepare = { prepared = it }, onSave = { savedIndex = it }, onBack = {},
                            videoReady = ready, videoRendering = rendering, videoMessage = null, videoProgress = null,
                            onRender = { rendered = it }, onSaveVideo = { saves++ }, onCancelVideo = { stops++ },
                        )
                    }
                }
            }
        }
        compose.onNodeWithText("Siapkan SRT").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(SrtExportMode.SOURCE, prepared) }
        compose.onNodeWithText("Keduanya").performScrollTo().performClick()
        compose.onNodeWithText("Siapkan SRT").assertIsNotEnabled()
        compose.runOnIdle { documents = listOf(SrtDocument("fixture.en.srt", "fixture")) }
        compose.onNodeWithText("Simpan file 1").performScrollTo().performClick()
        compose.runOnIdle { assertEquals(0, savedIndex) }
        compose.onNodeWithText("MP4").performScrollTo().performClick()
        compose.onNodeWithText("Render MP4").assertIsNotEnabled()
        compose.onNodeWithText("Asli (${SourceLanguage.ENGLISH.label})").performScrollTo().performClick()
        compose.onNodeWithText("Render MP4").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(SrtExportMode.SOURCE, rendered); rendering = true }
        compose.onNodeWithText("Hentikan render").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, stops); rendering = false; ready = true }
        compose.onNodeWithText("Keduanya").performScrollTo().performClick()
        compose.onNodeWithText("Render ulang dengan pilihan ini").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText("Simpan MP4").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(1, saves); pending = true }
        compose.onNodeWithText("Simpan MP4").assertIsNotEnabled()
        compose.runOnIdle { pending = false }
        compose.onNodeWithText("Simpan MP4").performClick()
        compose.runOnIdle { assertEquals(2, saves) }
    }
}

package app.subloka

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import app.subloka.core.domain.*
import app.subloka.feature.editor.EditorScreen
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertTrue

class EditorLayoutTest {
    @get:Rule val compose = createComposeRule()

    @Test fun narrowShortEditorKeepsExportAndScrollableToolsReachableAtLargeFont() {
        var exported = false
        val caption = CaptionSegment("one", 0, 2_000_000, SourceLanguage.INDONESIA,
            "Kalimat panjang untuk pemeriksaan editor. ".repeat(10), "",
            TranslationStatus.MISSING)
        compose.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 1.5f)) {
                MaterialTheme {
                    Box(Modifier.size(320.dp, 480.dp)) {
                        EditorScreen(listOf(caption), CaptionStyle(), null, "Tersimpan", false,
                            {}, {}, {}, { exported = true },
                            demoMode = false,
                            projectTitle = "Judul proyek sangat panjang yang tidak boleh menimpa ekspor".repeat(3))
                    }
                }
            }
        }
        compose.onNodeWithText("Ekspor").assertIsDisplayed().performClick()
        compose.runOnIdle { assertTrue(exported) }
        val titleBounds = compose.onNodeWithText("Judul proyek", substring = true).fetchSemanticsNode().boundsInRoot
        val exportBounds = compose.onNodeWithText("Ekspor").fetchSemanticsNode().boundsInRoot
        assertTrue("Title must not overlap export", titleBounds.right <= exportBounds.left)
        compose.onNodeWithContentDescription("Kembali").assertIsDisplayed()
        compose.onNodeWithText("Caption").assertIsSelected()
        compose.onNodeWithText("Teks asli").assertIsDisplayed()
        compose.onNodeWithText("Merge next").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Timing").performClick()
        compose.onNodeWithText("Perubahan berhenti", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Style").performClick()
        compose.onNodeWithText("Translation", substring = false).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Preview dan MP4", substring = true).performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Ekspor").assertIsDisplayed()
    }
}
